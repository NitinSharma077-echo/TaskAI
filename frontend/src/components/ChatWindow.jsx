import React, { useEffect, useRef } from 'react';
import { ArrowUp, Bot, Braces, Search, Sparkles, Trash2, User } from 'lucide-react';

const STARTERS = [
  { icon: Search, label: 'Research a topic', prompt: 'Research the latest developments in ' },
  { icon: Braces, label: 'Plan a workflow', prompt: 'Create and execute a plan to ' },
];

export function ChatWindow({
  messages,
  input,
  setInput,
  onSend,
  onClear,
  loading,
  model,
  agentStatus,
}) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (input.trim() && !loading) onSend(input.trim());
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  };

  return (
    <section className="chat-canvas" aria-label="Agent conversation">
      <header className="chat-header">
        <div className="agent-identity">
          <div className="agent-mark" aria-hidden="true">
            <Sparkles size={18} />
          </div>
          <div>
            <p className="eyebrow">LOCAL AGENT CHANNEL</p>
            <h2>TaskPilot / <span>{model}</span></h2>
          </div>
        </div>
        <div className="chat-header-actions">
          <span className={`signal-pill signal-${agentStatus}`}>
            <span className="signal-dot" />
            {agentStatus === 'idle' ? 'standing by' : agentStatus.replace('_', ' ')}
          </span>
          <button className="icon-button danger" onClick={onClear} title="Clear conversation" aria-label="Clear conversation">
            <Trash2 size={16} />
          </button>
        </div>
      </header>

      <div className="message-stream" aria-live="polite">
        {messages.length === 0 ? (
          <div className="agent-empty-state">
            <div className="orbital-agent" aria-hidden="true">
              <span className="orbit orbit-one" />
              <span className="orbit orbit-two" />
              <Bot size={34} />
            </div>
            <p className="eyebrow">OBSERVE · DECIDE · ACT</p>
            <h3>Give the agent an outcome.</h3>
            <p>It will choose tools, inspect results, recover from failures, and pause before sensitive actions.</p>
            <div className="starter-grid">
              {STARTERS.map(({ icon: Icon, label, prompt }) => (
                <button key={label} type="button" onClick={() => setInput(prompt)}>
                  <Icon size={15} />
                  <span>{label}</span>
                  <ArrowUp size={13} className="starter-arrow" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message, index) => {
            const isUser = message.role === 'user';
            return (
              <article
                key={message.id ?? `${message.role}-${index}`}
                className={`message-row ${isUser ? 'message-user' : 'message-agent'}`}
              >
                <div className="message-avatar" aria-hidden="true">
                  {isUser ? <User size={15} /> : <Bot size={15} />}
                </div>
                <div className="message-body">
                  <span className="message-author">{isUser ? 'You' : 'TaskPilot'}</span>
                  <p>{message.content}</p>
                </div>
              </article>
            );
          })
        )}

        {loading && (
          <div className="thinking-row" role="status">
            <span className="thinking-pulse" />
            <span>Ollama is reasoning through the next action</span>
            <span className="thinking-dots">•••</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="command-composer" onSubmit={handleSubmit}>
        <div className="composer-input-wrap">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe the outcome you want the agent to achieve…"
            rows={1}
            disabled={loading}
            aria-label="Message TaskPilot"
          />
          <span className="composer-hint">Enter to send · Shift + Enter for a new line</span>
        </div>
        <button type="submit" className="send-command" disabled={loading || !input.trim()} aria-label="Send message">
          <ArrowUp size={19} />
        </button>
      </form>
    </section>
  );
}
