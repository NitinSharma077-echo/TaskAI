import json
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.approval import run_agent_loop
from app.agents.graph import run_agent
from app.agents.planner import AgentDecision
from app.agents.planner import decide_next_action
from app.database.database import Base
from app.models.approval import Approval
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.task import Task
from app.models.user import User  # noqa: F401
from app.tools.current_time import current_time_tool


class AgentLoopTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()

    def _task(self, description="do the work"):
        task = Task(
            title=description,
            description=description,
            status="pending",
            plan_data="[]",
            current_step_index=0,
            execution_history="[]",
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def test_observes_results_and_selects_multiple_actions(self):
        task = self._task("research a topic and create a task")
        decisions = iter(
            [
                AgentDecision(
                    action="tool",
                    title="Research topic",
                    tool="web_search",
                    args={"query": "agent loops"},
                    rationale="Need evidence.",
                ),
                AgentDecision(
                    action="tool",
                    title="Create follow-up",
                    tool="task_create",
                    args={"title": "Read findings"},
                    rationale="Turn the finding into work.",
                ),
                AgentDecision(
                    action="final",
                    response="Research completed and the follow-up task was created.",
                ),
            ]
        )
        calls = []

        def fake_execute(name, args):
            calls.append((name, args))
            return {"ok": True, "tool": name, "output": {"done": name}, "error": None}

        with patch("app.agents.approval.decide_next_action", side_effect=lambda *a: next(decisions)), patch(
            "app.agents.approval.execute_tool", side_effect=fake_execute
        ):
            outcome = run_agent_loop(self.db, task.id)

        self.assertEqual(outcome["status"], "completed")
        self.assertEqual([call[0] for call in calls], ["web_search", "task_create"])
        self.db.refresh(task)
        self.assertEqual(task.current_step_index, 2)
        self.assertEqual(len(json.loads(task.execution_history)), 2)
        self.assertEqual(len(json.loads(task.plan_data)), 2)

    def test_approval_executes_exact_call_once(self):
        task = self._task("send a message")
        proposed = AgentDecision(
            action="tool",
            title="Send the message",
            tool="telegram",
            args={"chat_id": "42", "message": "hello"},
        )
        with patch("app.agents.approval.decide_next_action", return_value=proposed):
            paused = run_agent_loop(self.db, task.id)

        self.assertEqual(paused["status"], "awaiting_approval")
        approval = self.db.query(Approval).filter(Approval.id == paused["approval_id"]).one()
        approval.status = "approved"
        self.db.commit()

        final = AgentDecision(action="final", response="Message sent.")
        with patch("app.agents.approval.decide_next_action", return_value=final), patch(
            "app.agents.approval.execute_tool",
            return_value={"ok": True, "tool": "telegram", "output": {"sent": True}, "error": None},
        ) as execute:
            outcome = run_agent_loop(self.db, task.id, approval.id)
            duplicate = run_agent_loop(self.db, task.id, approval.id)

        self.assertEqual(outcome["status"], "completed")
        self.assertEqual(duplicate["status"], "error")
        execute.assert_called_once_with("telegram", {"chat_id": "42", "message": "hello"})
        self.db.refresh(approval)
        self.assertEqual(approval.status, "executed")

    def test_task_can_pause_for_and_resume_with_user_input(self):
        ask = AgentDecision(action="ask_user", response="Which city?")
        with patch("app.agents.approval.decide_next_action", return_value=ask):
            paused = run_agent("Find the weather", self.db)

        self.assertEqual(paused["status"], "needs_input")
        final = AgentDecision(action="final", response="I now have the city.")
        with patch("app.agents.approval.decide_next_action", return_value=final):
            resumed = run_agent("Pune", self.db, paused["task_id"])

        self.assertEqual(resumed["status"], "completed")
        task = self.db.query(Task).filter(Task.id == paused["task_id"]).one()
        self.assertIn("Additional user input: Pune", task.description)

    def test_failed_observation_can_be_recovered_with_a_new_action(self):
        task = self._task("find the answer")
        decisions = iter(
            [
                AgentDecision(action="tool", title="First search", tool="web_search", args={"query": "first"}),
                AgentDecision(action="tool", title="Retry search", tool="web_search", args={"query": "more specific"}),
                AgentDecision(action="final", response="Recovered with a more specific search."),
            ]
        )
        executions = iter(
            [
                {"ok": False, "tool": "web_search", "output": None, "error": "temporary failure"},
                {"ok": True, "tool": "web_search", "output": {"result": "answer"}, "error": None},
            ]
        )
        with patch("app.agents.approval.decide_next_action", side_effect=lambda *a: next(decisions)), patch(
            "app.agents.approval.execute_tool", side_effect=lambda *a: next(executions)
        ):
            outcome = run_agent_loop(self.db, task.id)

        self.assertEqual(outcome["status"], "completed")
        self.assertEqual([event["status"] for event in outcome["results"]], ["failed", "success"])

    def test_malformed_model_decision_degrades_safely(self):
        with patch("app.agents.planner.query_llm", return_value="not json at all"):
            decision = decide_next_action("search for bounded agents", [], [], 3)

        self.assertEqual(decision.action, "tool")
        self.assertEqual(decision.tool, "web_search")
        self.assertEqual(decision.args, {"query": "bounded agents"})

    def test_time_requests_use_a_grounded_timezone_aware_tool(self):
        with patch("app.agents.planner.query_llm", return_value='{"action":"ask_user","response":"Which time?"}'):
            decision = decide_next_action("What is the current time in Pune?", [], [], 3)

        self.assertEqual(decision.action, "tool")
        self.assertEqual(decision.tool, "current_time")
        self.assertEqual(decision.args, {"timezone": "Asia/Kolkata"})
        observation = current_time_tool("Asia/Kolkata")
        self.assertEqual(observation["status"], "success")
        self.assertEqual(observation["utc_offset"], "+0530")


if __name__ == "__main__":
    unittest.main()
