import React from 'react';
import { Check, ShieldAlert, X } from 'lucide-react';

export function ApprovalCard({ approvalId, toolName, toolArgs, onApprove, onDeny }) {
  let parsedArgs = {};
  try {
    parsedArgs = typeof toolArgs === 'string' ? JSON.parse(toolArgs) : toolArgs;
  } catch {
    parsedArgs = { raw: toolArgs };
  }

  return (
    <aside className="approval-card" aria-labelledby={`approval-${approvalId}`}>
      <div className="approval-beacon"><ShieldAlert size={20} /></div>
      <div className="approval-content">
        <p className="eyebrow">HUMAN CHECKPOINT</p>
        <h3 id={`approval-${approvalId}`}>External action needs clearance</h3>
        <p>The agent wants to run <code>{toolName}</code>. Review the exact payload before it leaves this workspace.</p>
        <pre>{JSON.stringify(parsedArgs, null, 2)}</pre>
        <div className="approval-actions">
          <button type="button" className="approve-button" onClick={() => onApprove(approvalId)}>
            <Check size={16} /> Approve once
          </button>
          <button type="button" className="deny-button" onClick={() => onDeny(approvalId)}>
            <X size={16} /> Deny
          </button>
        </div>
      </div>
    </aside>
  );
}
