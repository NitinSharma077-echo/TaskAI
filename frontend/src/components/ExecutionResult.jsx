import React, { useState } from 'react';
import { CheckCircle2, ChevronDown, CircleX, TerminalSquare } from 'lucide-react';

export function ExecutionResult({ history }) {
  const [openItems, setOpenItems] = useState({});

  if (!history?.length) {
    return (
      <section className="trace-panel trace-empty">
        <TerminalSquare size={18} />
        <p>Observations will appear here after tools run.</p>
      </section>
    );
  }

  return (
    <section className="trace-panel" aria-label="Execution observations">
      <header className="panel-heading compact">
        <div><p className="eyebrow">OBSERVATION LOG</p><h3>Tool telemetry</h3></div>
        <span>{history.length} event{history.length === 1 ? '' : 's'}</span>
      </header>
      <div className="trace-list">
        {history.map((item, index) => {
          const isOpen = openItems[index] ?? index === history.length - 1;
          const succeeded = item.status !== 'failed';
          return (
            <article key={`${item.iteration ?? index}-${item.tool}`} className={`trace-event ${succeeded ? 'trace-success' : 'trace-failed'}`}>
              <button
                type="button"
                className="trace-trigger"
                onClick={() => setOpenItems((current) => ({ ...current, [index]: !isOpen }))}
                aria-expanded={isOpen}
              >
                {succeeded ? <CheckCircle2 size={16} /> : <CircleX size={16} />}
                <span><strong>{item.step_title}</strong><code>{item.tool}</code></span>
                <ChevronDown size={15} className={isOpen ? 'chevron-open' : ''} />
              </button>
              {isOpen && (
                <div className="trace-payload">
                  {item.rationale && <p className="trace-rationale">{item.rationale}</p>}
                  <pre>{JSON.stringify(item.result, null, 2)}</pre>
                  {!succeeded && <p className="trace-error">{item.error || 'Tool execution failed.'}</p>}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
