import React from 'react';
import { Check, Circle, Loader2, ShieldQuestion, TriangleAlert } from 'lucide-react';

export function ToolStatus({ plan, currentStepIndex, status }) {
  if (!plan?.length) {
    return (
      <div className="pipeline-empty">
        <span className="pipeline-radar" />
        <p>No actions selected yet.</p>
        <small>The plan grows as the agent observes results.</small>
      </div>
    );
  }

  return (
    <ol className="pipeline-list">
      {plan.map((step, index) => {
        const completed = index < currentStepIndex;
        const active = index === currentStepIndex && status === 'running';
        const awaiting = index === currentStepIndex && status === 'awaiting_approval';
        const failed = step.status === 'failed' || (index === currentStepIndex && status === 'failed');
        const state = failed ? 'failed' : awaiting ? 'approval' : active ? 'active' : completed ? 'done' : 'queued';
        const Icon = failed ? TriangleAlert : awaiting ? ShieldQuestion : active ? Loader2 : completed ? Check : Circle;

        return (
          <li key={`${step.tool}-${index}`} className={`pipeline-step step-${state}`}>
            <div className="step-rail">
              <span className="step-index">{String(index + 1).padStart(2, '0')}</span>
              <span className="step-line" />
            </div>
            <div className="step-card">
              <div className="step-copy">
                <strong>{step.title}</strong>
                <code>{step.tool}</code>
              </div>
              <span className="step-state"><Icon size={15} className={active ? 'spin' : ''} />{state}</span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
