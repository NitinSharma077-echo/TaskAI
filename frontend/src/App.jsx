import React, { useState, useEffect } from 'react';
import { 
  Bot, Settings, Layers, MessageSquare,
  Database, RefreshCw, Terminal,
  LogOut, Cpu, Sliders, Activity, Wifi, WifiOff,
  ArrowRight, ShieldCheck, Waypoints, Gauge
} from 'lucide-react';
import { ChatWindow } from './components/ChatWindow';
import { ToolStatus } from './components/ToolStatus';
import { ApprovalCard } from './components/ApprovalCard';
import { ExecutionResult } from './components/ExecutionResult';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

export default function App() {
  // Session State
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [authMode, setAuthMode] = useState('login'); // login | register | guest
  const [authForm, setAuthForm] = useState({ username: '', email: '', password: '' });
  const [authError, setAuthError] = useState('');

  // Active View State
  const [activeTab, setActiveTab] = useState('workspace'); // workspace | tasks | settings

  // Chat/Agent State
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeTask, setActiveTask] = useState(null);
  
  // Pipeline State
  const [activePlan, setActivePlan] = useState([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [agentStatus, setAgentStatus] = useState('idle'); // idle | running | awaiting_approval | failed | completed
  const [pendingApproval, setPendingApproval] = useState(null);
  const [historyTrace, setHistoryTrace] = useState([]);

  // Database Tasks State
  const [tasksList, setTasksList] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [selectedTaskLogs, setSelectedTaskLogs] = useState([]);

  // Settings State
  const [settingsForm, setSettingsForm] = useState({
    llm_provider: 'ollama',
    gemini_api_key: '',
    ollama_api_url: 'http://localhost:11434',
    ollama_model: 'qwen2.5:1.5b',
    gemini_model: 'gemini-1.5-flash',
    telegram_bot_token: '',
    telegram_chat_id: '',
    whatsapp_phone_number: ''
  });
  const [settingsMessage, setSettingsMessage] = useState('');
  const [ollamaStatus, setOllamaStatus] = useState({ connected: false, models: [], active_model: '', loading: true });

  // ----------------------------------------------------
  // Initial Fetches
  // ----------------------------------------------------
  useEffect(() => {
    if (!token && authMode !== 'guest') return;

    fetchHistory();
    fetchTasks();
    fetchIntegrations();
    fetchOllamaStatus();
  }, [token, authMode]);

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/chat/history`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data);
      }
    } catch (e) {
      console.error('Error fetching chat history:', e);
    }
  };

  const fetchTasks = async () => {
    try {
      const res = await fetch(`${API_BASE}/tasks/`);
      if (res.ok) {
        const data = await res.json();
        setTasksList(data);
      }
    } catch (e) {
      console.error('Error fetching tasks:', e);
    }
  };

  const fetchIntegrations = async () => {
    try {
      const res = await fetch(`${API_BASE}/integrations/`);
      if (res.ok) {
        const data = await res.json();
        setSettingsForm(prev => ({
          ...prev,
          telegram_bot_token: data.telegram_bot_token || '',
          telegram_chat_id: data.telegram_chat_id || '',
          whatsapp_phone_number: data.whatsapp_phone_number || '',
          llm_provider: 'ollama',
          ollama_api_url: data.ollama_api_url || prev.ollama_api_url,
          ollama_model: data.ollama_model || prev.ollama_model,
          gemini_model: data.gemini_model || prev.gemini_model,
          gemini_api_key: data.gemini_api_key || '',
        }));
      }
    } catch (e) {
      console.error('Error fetching integrations settings:', e);
    }
  };

  const fetchOllamaStatus = async () => {
    setOllamaStatus(prev => ({ ...prev, loading: true }));
    try {
      const res = await fetch(`${API_BASE}/integrations/ollama/status`);
      if (!res.ok) throw new Error('Ollama status request failed');
      const data = await res.json();
      setOllamaStatus({ ...data, loading: false });
    } catch (error) {
      console.error('Error checking Ollama:', error);
      setOllamaStatus({ connected: false, models: [], active_model: '', loading: false });
    }
  };

  // ----------------------------------------------------
  // Authentication Handlers
  // ----------------------------------------------------
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      if (authMode === 'register') {
        const res = await fetch(`${API_BASE}/users/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(authForm)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Registration failed');
        setAuthMode('login');
        setAuthError('Registration successful. Please log in.');
      } else {
        const res = await fetch(`${API_BASE}/users/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: authForm.email, password: authForm.password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Login failed');
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
      }
    } catch (err) {
      setAuthError(err.message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken('');
    setAuthMode('login');
  };

  // ----------------------------------------------------
  // Chat / Agent Handlers
  // ----------------------------------------------------
  const handleSendMessage = async (text) => {
    setInput('');
    setLoading(true);
    setAgentStatus('running');
    setPendingApproval(null);

    // Optimistically update UI
    setMessages(prev => [...prev, { role: 'user', content: text }]);

    try {
      const res = await fetch(`${API_BASE}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          task_id: activeTask?.status === 'needs_input' ? activeTask.id : null
        })
      });
      if (!res.ok) throw new Error('API server returned error');
      const data = await res.json();

      setMessages(prev => [...prev, { role: 'assistant', content: data.agent_response }]);

      if (data.status === 'awaiting_approval') {
        setAgentStatus('awaiting_approval');
        setPendingApproval({
          id: data.approval_id,
          tool: data.tool_name,
          args: data.tool_args
        });
      } else {
        setAgentStatus(data.status === 'error' ? 'failed' : data.status);
      }

      if (data.task_id) {
        // Fetch active task details
        fetchTaskDetail(data.task_id);
      }
      fetchTasks();
    } catch (e) {
      console.error(e);
      setAgentStatus('failed');
      setMessages(prev => [...prev, { role: 'assistant', content: 'Execution error occurred while calling the agent.' }]);
    } finally {
      setLoading(false);
    }
  };

  const fetchTaskDetail = async (taskId) => {
    try {
      const res = await fetch(`${API_BASE}/tasks/${taskId}`);
      if (res.ok) {
        const task = await res.json();
        setActiveTask(task);
        setActivePlan(JSON.parse(task.plan_data || '[]'));
        setCurrentStepIndex(task.current_step_index);
        setHistoryTrace(JSON.parse(task.execution_history || '[]'));
      }
    } catch (e) {
      console.error('Error fetching task details:', e);
    }
  };

  const handleClearChat = async () => {
    try {
      await fetch(`${API_BASE}/chat/history`, { method: 'DELETE' });
      setMessages([]);
      setActiveTask(null);
      setActivePlan([]);
      setHistoryTrace([]);
      setAgentStatus('idle');
      setPendingApproval(null);
    } catch (e) {
      console.error(e);
    }
  };

  // ----------------------------------------------------
  // Approval Actions
  // ----------------------------------------------------
  const handleApprove = async (approvalId) => {
    setLoading(true);
    setAgentStatus('running');
    setPendingApproval(null);

    try {
      const res = await fetch(`${API_BASE}/approvals/${approvalId}/approve`, { method: 'POST' });
      const data = await res.json();

      setMessages(prev => [...prev, { role: 'assistant', content: data.agent_response }]);

      if (data.status === 'awaiting_approval') {
        setAgentStatus('awaiting_approval');
        setPendingApproval({
          id: data.approval_id,
          tool: data.tool_name,
          args: data.tool_args
        });
      } else {
        setAgentStatus(data.status === 'error' ? 'failed' : data.status);
      }

      if (data.task_id) {
        fetchTaskDetail(data.task_id);
      }
      fetchTasks();
    } catch (e) {
      console.error(e);
      setAgentStatus('failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDeny = async (approvalId) => {
    setLoading(true);
    setPendingApproval(null);

    try {
      const res = await fetch(`${API_BASE}/approvals/${approvalId}/deny`, { method: 'POST' });
      const data = await res.json();

      setMessages(prev => [...prev, { role: 'assistant', content: data.agent_response }]);
      setAgentStatus('failed');
      
      if (data.task_id) {
        fetchTaskDetail(data.task_id);
      }
      fetchTasks();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // ----------------------------------------------------
  // Task Audit Logs Viewer
  // ----------------------------------------------------
  const selectTaskForAudit = async (task) => {
    setSelectedTask(task);
    setSelectedTaskLogs([]);
    try {
      const res = await fetch(`${API_BASE}/tasks/${task.id}/logs`);
      if (res.ok) {
        const data = await res.json();
        setSelectedTaskLogs(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const deleteTask = async (taskId) => {
    try {
      const res = await fetch(`${API_BASE}/tasks/${taskId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchTasks();
        if (selectedTask?.id === taskId) {
          setSelectedTask(null);
          setSelectedTaskLogs([]);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  // ----------------------------------------------------
  // Settings / Configurations Handlers
  // ----------------------------------------------------
  const saveSettings = async (e) => {
    e.preventDefault();
    setSettingsMessage('');
    try {
      // 1. Save integrations keys
      const resInt = await fetch(`${API_BASE}/integrations/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          telegram_bot_token: settingsForm.telegram_bot_token,
          telegram_chat_id: settingsForm.telegram_chat_id,
          whatsapp_phone_number: settingsForm.whatsapp_phone_number,
          google_calendar_configured: true,
          llm_provider: 'ollama',
          ollama_api_url: settingsForm.ollama_api_url,
          ollama_model: settingsForm.ollama_model,
          gemini_api_key: settingsForm.gemini_api_key,
          gemini_model: settingsForm.gemini_model
        })
      });

      if (resInt.ok) {
        setSettingsMessage('Configuration saved and applied successfully.');
        fetchIntegrations();
        fetchOllamaStatus();
      } else {
        throw new Error('Failed to save configurations');
      }
    } catch (e) {
      setSettingsMessage('Error saving configurations.');
    }
  };

  // Render Login flow if not logged in AND not skipped
  if (!token && authMode !== 'guest') {
    return (
      <main className="auth-shell">
        <div className="auth-ambient auth-ambient-one" />
        <div className="auth-ambient auth-ambient-two" />

        <header className="auth-brand" aria-label="TaskPilot AI">
          <span className="auth-brand-mark"><Bot size={19} /></span>
          <span><strong>TASKPILOT</strong><small>LOCAL AGENT OS</small></span>
        </header>

        <div className="auth-layout animate-slide-in">
          <section className="auth-story" aria-labelledby="auth-story-title">
            <p className="eyebrow">YOUR OPERATIONS, ORCHESTRATED</p>
            <h1 id="auth-story-title">Delegate the busywork.<br /><span>Keep the judgment.</span></h1>
            <p className="auth-story-copy">
              Plan, approve, and audit agent work from one focused command center—powered by your local models and governed by you.
            </p>

            <div className="auth-feature-list">
              <div className="auth-feature">
                <span><Waypoints size={18} /></span>
                <div><strong>Visible execution</strong><p>Follow every planned step and tool call in real time.</p></div>
              </div>
              <div className="auth-feature">
                <span><ShieldCheck size={18} /></span>
                <div><strong>Human checkpoints</strong><p>Sensitive actions wait for your explicit approval.</p></div>
              </div>
              <div className="auth-feature">
                <span><Gauge size={18} /></span>
                <div><strong>Local-first control</strong><p>Run with Ollama and keep your workspace close.</p></div>
              </div>
            </div>

            <div className="auth-proof">
              <span><i className="proof-dot" /> Local runtime ready</span>
              <span>Observe · Decide · Act</span>
            </div>
          </section>

        <section className="auth-card">
          <div className="auth-card-heading" style={{ textAlign: 'center', marginBottom: '24px' }}>
            <div style={{
              background: 'linear-gradient(135deg, var(--primary), #818cf8)',
              width: '54px',
              height: '54px',
              borderRadius: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              margin: '0 auto 16px auto',
              boxShadow: 'var(--shadow-glow)'
            }}>
              <Bot size={28} />
            </div>
            <h2 style={{ fontFamily: 'var(--font-title)', fontWeight: 800, fontSize: '24px', letterSpacing: '-0.02em' }}>
              TaskPilot AI
            </h2>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13.5px', marginTop: '6px' }}>
              Autonomous AI Agent Workspace
            </p>
          </div>

          <form onSubmit={handleAuthSubmit} className="auth-form" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {authMode === 'register' && (
              <div className="auth-field" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label htmlFor="auth-username" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Username</label>
                <input
                  id="auth-username"
                  type="text"
                  required
                  placeholder="alex_pilot"
                  autoComplete="username"
                  value={authForm.username}
                  onChange={(e) => setAuthForm(prev => ({ ...prev, username: e.target.value }))}
                />
              </div>
            )}
            <div className="auth-field" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label htmlFor="auth-email" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Email address</label>
              <input
                id="auth-email"
                type="email"
                required
                placeholder="developer@taskpilot.ai"
                autoComplete="email"
                value={authForm.email}
                onChange={(e) => setAuthForm(prev => ({ ...prev, email: e.target.value }))}
              />
            </div>
            <div className="auth-field" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label htmlFor="auth-password" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>Password</label>
              <input
                id="auth-password"
                type="password"
                required
                placeholder="Enter your password"
                autoComplete={authMode === 'register' ? 'new-password' : 'current-password'}
                value={authForm.password}
                onChange={(e) => setAuthForm(prev => ({ ...prev, password: e.target.value }))}
              />
            </div>

            {authError && (
              <div className="auth-error" role="alert" style={{
                color: 'var(--accent-rose)',
                fontSize: '13px',
                textAlign: 'center',
                padding: '8px',
                borderRadius: '6px',
                backgroundColor: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.2)'
              }}>
                {authError}
              </div>
            )}

            <button type="submit" className="btn-primary auth-submit" style={{ padding: '12px', fontSize: '14px', marginTop: '4px' }}>
              {authMode === 'register' ? 'Create Workspace Account' : 'Sign In to Workspace'}
              <ArrowRight size={17} />
            </button>
          </form>

          <div className="auth-alternatives" style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '20px', textAlign: 'center' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              {authMode === 'register' ? 'Already have an account?' : "Don't have an account?"}{' '}
              <button
                type="button"
                onClick={() => {
                  setAuthMode(authMode === 'register' ? 'login' : 'register');
                  setAuthError('');
                }}
                style={{
                  background: 'none',
                  color: 'var(--primary)',
                  fontWeight: 600,
                  fontSize: '13px'
                }}
              >
                {authMode === 'register' ? 'Sign In' : 'Create Account'}
              </button>
            </span>

            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              marginTop: '8px',
              paddingTop: '16px',
              borderTop: '1px solid var(--border-color)'
            }}>
              <button
                type="button"
                onClick={() => setAuthMode('guest')}
                className="btn-secondary auth-guest"
                style={{
                  fontSize: '13px',
                  padding: '8px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <span>Explore in guest mode</span>
                <ArrowRight size={15} />
              </button>
            </div>
          </div>
        </section>
        </div>

        <footer className="auth-footer">TaskPilot AI · Private by design · Built for deliberate automation</footer>
      </main>
    );
  }

  return (
    <div className="agent-shell">
      {/* Sidebar Navigation */}
      <aside className="control-rail" style={{
        width: '260px',
        backgroundColor: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border-color)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0
      }}>
        {/* Top Branding */}
        <div className="brand-lockup" style={{
          padding: '20px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <div className="brand-glyph" style={{
            background: 'linear-gradient(135deg, var(--primary), #818cf8)',
            padding: '6px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            color: 'white'
          }}>
            <Bot size={18} />
          </div>
          <div>
            <h1 style={{ fontFamily: 'var(--font-title)', fontWeight: 800, fontSize: '16px' }}>TASKPILOT</h1>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>LOCAL AGENT OS / 01</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="rail-nav" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <button
            className={activeTab === 'workspace' ? 'nav-active' : ''}
            onClick={() => setActiveTab('workspace')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              width: '100%',
              padding: '10px 14px',
              borderRadius: '8px',
              textAlign: 'left',
              color: activeTab === 'workspace' ? 'white' : 'var(--text-secondary)',
              backgroundColor: activeTab === 'workspace' ? 'var(--bg-tertiary)' : 'transparent',
              borderLeft: activeTab === 'workspace' ? '3px solid var(--primary)' : 'none'
            }}
          >
            <MessageSquare size={16} />
            <span>Workspace</span>
          </button>
          <button
            className={activeTab === 'tasks' ? 'nav-active' : ''}
            onClick={() => {
              setActiveTab('tasks');
              fetchTasks();
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              width: '100%',
              padding: '10px 14px',
              borderRadius: '8px',
              textAlign: 'left',
              color: activeTab === 'tasks' ? 'white' : 'var(--text-secondary)',
              backgroundColor: activeTab === 'tasks' ? 'var(--bg-tertiary)' : 'transparent',
              borderLeft: activeTab === 'tasks' ? '3px solid var(--primary)' : 'none'
            }}
          >
            <Database size={16} />
            <span>Task Database</span>
          </button>
          <button
            className={activeTab === 'settings' ? 'nav-active' : ''}
            onClick={() => setActiveTab('settings')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              width: '100%',
              padding: '10px 14px',
              borderRadius: '8px',
              textAlign: 'left',
              color: activeTab === 'settings' ? 'white' : 'var(--text-secondary)',
              backgroundColor: activeTab === 'settings' ? 'var(--bg-tertiary)' : 'transparent',
              borderLeft: activeTab === 'settings' ? '3px solid var(--primary)' : 'none'
            }}
          >
            <Settings size={16} />
            <span>Configurations</span>
          </button>
        </nav>

        {/* Tasks List */}
        <div className="rail-runs" style={{ flex: 1, padding: '16px', overflowY: 'auto', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '10px', letterSpacing: '0.05em' }}>
            Run History
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {tasksList.length === 0 ? (
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No tasks registered.</span>
            ) : (
              tasksList.map((t) => (
                <button
                  type="button"
                  className="run-card"
                  key={t.id}
                  onClick={() => {
                    setActiveTab('workspace');
                    fetchTaskDetail(t.id);
                  }}
                  style={{
                    padding: '8px 12px',
                    borderRadius: '8px',
                    backgroundColor: activeTask?.id === t.id ? 'rgba(99, 102, 241, 0.1)' : 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid',
                    borderColor: activeTask?.id === t.id ? 'rgba(99, 102, 241, 0.2)' : 'var(--border-color)',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                >
                  <div style={{ fontSize: '12px', fontWeight: 600, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                    {t.title}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>ID: {t.id}</span>
                    <span style={{
                      fontSize: '9px',
                      textTransform: 'uppercase',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontWeight: 600,
                      backgroundColor: 
                        t.status === 'completed' ? 'rgba(16, 185, 129, 0.15)' : 
                        t.status === 'awaiting_approval' ? 'rgba(245, 158, 11, 0.15)' : 
                        t.status === 'failed' ? 'rgba(244, 63, 94, 0.15)' : 'rgba(6, 182, 212, 0.15)',
                      color:
                        t.status === 'completed' ? 'var(--accent-emerald)' : 
                        t.status === 'awaiting_approval' ? 'var(--accent-amber)' : 
                        t.status === 'failed' ? 'var(--accent-rose)' : 'var(--accent-cyan)'
                    }}>
                      {t.status}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Footer info & Logout */}
        <div style={{
          padding: '16px 20px',
          borderTop: '1px solid var(--border-color)',
          background: 'rgba(0,0,0,0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-emerald)' }}></div>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>SQLite Connected</span>
          </div>
          {token && (
            <button
              onClick={handleLogout}
              title="Sign Out"
              style={{ background: 'none', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}
            >
              <LogOut size={16} />
            </button>
          )}
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="command-main" style={{ flex: 1, display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-primary)', overflow: 'hidden' }}>
        {/* Top Header info */}
        <header className="command-bar" style={{
          height: '64px',
          borderBottom: '1px solid var(--border-color)',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-secondary)',
          flexShrink: 0
        }}>
          <div className="model-readout">
            <div className="model-icon"><Cpu size={17} /></div>
            <div>
              <p className="eyebrow">INFERENCE ENGINE</p>
              <strong>Ollama / {settingsForm.ollama_model}</strong>
            </div>
          </div>

          <div className="command-telemetry">
            <button type="button" className={`ollama-health ${ollamaStatus.connected ? 'is-online' : 'is-offline'}`} onClick={fetchOllamaStatus}>
              {ollamaStatus.connected ? <Wifi size={14} /> : <WifiOff size={14} />}
              <span>{ollamaStatus.loading ? 'checking' : ollamaStatus.connected ? 'local runtime online' : 'runtime offline'}</span>
            </button>
            <span className="cycle-readout"><Activity size={14} /> {historyTrace.length} cycles</span>
            <span className={`badge badge-${agentStatus === 'idle' ? 'pending' : agentStatus}`}>
              <span className="signal-dot" /> {agentStatus.replace('_', ' ')}
            </span>
          </div>
        </header>

        {/* Tab Views */}
        <div className="view-stage" style={{ flex: 1, overflow: 'hidden', padding: '24px', position: 'relative' }}>
          
          {/* VIEW: WORKSPACE */}
          {activeTab === 'workspace' && (
            <div className="workspace-grid" style={{ display: 'flex', gap: '24px', height: '100%', overflow: 'hidden' }}>
              {/* Left Side: Chat */}
              <div className="chat-column" style={{ flex: 3, display: 'flex', flexDirection: 'column', height: '100%' }}>
                <ChatWindow
                  messages={messages}
                  input={input}
                  setInput={setInput}
                  onSend={handleSendMessage}
                  onClear={handleClearChat}
                  loading={loading}
                  model={settingsForm.ollama_model}
                  agentStatus={agentStatus}
                />
              </div>

              {/* Right Side: Tool Execution and Pipeline Status */}
              <div className="intelligence-column" style={{ flex: 2, display: 'flex', flexDirection: 'column', gap: '20px', height: '100%', overflowY: 'auto' }}>
                {/* Active Plan / Steps */}
                <section className="plan-panel">
                  <header className="panel-heading">
                    <div><p className="eyebrow">LIVE REASONING GRAPH</p><h3><Layers size={16} /> Action pipeline</h3></div>
                    <span>{currentStepIndex}/{activePlan.length}</span>
                  </header>
                  <ToolStatus
                    plan={activePlan}
                    currentStepIndex={currentStepIndex}
                    status={agentStatus}
                  />
                </section>

                {/* Human Approval Alert (if triggered) */}
                {pendingApproval && (
                  <ApprovalCard
                    approvalId={pendingApproval.id}
                    toolName={pendingApproval.tool}
                    toolArgs={pendingApproval.args}
                    onApprove={handleApprove}
                    onDeny={handleDeny}
                  />
                )}

                {/* Log outputs of execution */}
                <ExecutionResult history={historyTrace} />
              </div>
            </div>
          )}

          {/* VIEW: TASK DATABASE / AUDIT LOG */}
          {activeTab === 'tasks' && (
            <div className="records-grid" style={{ display: 'flex', gap: '24px', height: '100%', overflow: 'hidden' }}>
              {/* Left list */}
              <div className="glass-panel" style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ fontFamily: 'var(--font-title)', fontWeight: 700 }}>Task Records</h3>
                  <button onClick={fetchTasks} style={{ background: 'none', color: 'var(--primary)' }}>
                    <RefreshCw size={16} />
                  </button>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {tasksList.map((t) => (
                    <div
                      key={t.id}
                      onClick={() => selectTaskForAudit(t)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          selectTaskForAudit(t);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      aria-label={`Inspect task ${t.title}`}
                      style={{
                        padding: '14px',
                        borderRadius: '10px',
                        border: '1px solid var(--border-color)',
                        backgroundColor: selectedTask?.id === t.id ? 'rgba(255, 255, 255, 0.05)' : 'transparent',
                        cursor: 'pointer'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 600, fontSize: '14px' }}>{t.title}</span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteTask(t.id);
                          }}
                          style={{ color: 'var(--accent-rose)', background: 'none', fontSize: '11px' }}
                        >
                          Delete
                        </button>
                      </div>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '6px' }}>{t.description}</p>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px', fontSize: '11px', color: 'var(--text-muted)' }}>
                        <span>Created: {new Date(t.created_at).toLocaleString()}</span>
                        <span className={`badge badge-${t.status === 'idle' ? 'pending' : t.status}`}>{t.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Right audit logs detail */}
              <div className="glass-panel" style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
                <h3 style={{ fontFamily: 'var(--font-title)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Terminal size={18} style={{ color: 'var(--accent-cyan)' }} />
                  Audit & Logs Tracker
                </h3>
                {selectedTask ? (
                  <div>
                    <div style={{ paddingBottom: '12px', borderBottom: '1px solid var(--border-color)', marginBottom: '14px' }}>
                      <h4>{selectedTask.title}</h4>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        ID: {selectedTask.id} | Status: <strong style={{ color: 'var(--primary)' }}>{selectedTask.status}</strong>
                      </p>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {selectedTaskLogs.length === 0 ? (
                        <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>No system logs generated yet for this task.</div>
                      ) : (
                        selectedTaskLogs.map((log) => (
                          <div key={log.id} style={{
                            padding: '10px 14px',
                            backgroundColor: 'rgba(0, 0, 0, 0.2)',
                            borderRadius: '8px',
                            borderLeft: '2px solid var(--primary)',
                            fontSize: '12.5px'
                          }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <strong style={{ color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)' }}>{log.action}</strong>
                              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{new Date(log.created_at).toLocaleTimeString()}</span>
                            </div>
                            <span style={{ color: 'var(--text-primary)' }}>{log.details}</span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', fontSize: '13px' }}>
                    Select a task record to inspect system audit logs.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW: SETTINGS */}
          {activeTab === 'settings' && (
            <div className="settings-panel" style={{ maxWidth: '760px', margin: '0 auto', padding: '32px', overflowY: 'auto', height: '100%' }}>
              <h3 style={{ fontFamily: 'var(--font-title)', fontWeight: 800, fontSize: '20px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sliders size={20} style={{ color: 'var(--primary)' }} />
                Configuration Center
              </h3>

              <form onSubmit={saveSettings} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                
                {/* LLM Engine Config */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', borderBottom: '1px solid var(--border-color)', paddingBottom: '20px' }}>
                  <h4 style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>1. Local Inference Engine</h4>
                  <div className={`ollama-config-card ${ollamaStatus.connected ? 'is-online' : 'is-offline'}`}>
                    <div className="ollama-config-icon"><Cpu size={20} /></div>
                    <div>
                      <strong>Ollama is the active agent runtime</strong>
                      <p>{ollamaStatus.connected ? `${ollamaStatus.models.length} generation models detected locally.` : 'Start Ollama, then refresh the connection.'}</p>
                    </div>
                    <button type="button" onClick={fetchOllamaStatus}><RefreshCw size={14} /> Refresh</button>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '10px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Ollama Service URL</label>
                    <input
                      type="text"
                      placeholder="http://localhost:11434"
                      value={settingsForm.ollama_api_url}
                      onChange={(e) => setSettingsForm(prev => ({ ...prev, ollama_api_url: e.target.value }))}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Ollama Model Name</label>
                    <select
                      value={settingsForm.ollama_model}
                      onChange={(e) => setSettingsForm(prev => ({ ...prev, ollama_model: e.target.value }))}
                    >
                      {!ollamaStatus.models.some(model => model.name === settingsForm.ollama_model) && (
                        <option value={settingsForm.ollama_model}>{settingsForm.ollama_model}</option>
                      )}
                      {ollamaStatus.models.map(model => (
                        <option key={model.name} value={model.name}>
                          {model.name} {model.parameter_size ? `· ${model.parameter_size}` : ''} {model.quantization ? `· ${model.quantization}` : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Telegram Config */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', borderBottom: '1px solid var(--border-color)', paddingBottom: '20px' }}>
                  <h4 style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>2. Telegram Integrations</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Telegram Bot Token</label>
                    <input
                      type="password"
                      placeholder="5900000000:AA..."
                      value={settingsForm.telegram_bot_token}
                      onChange={(e) => setSettingsForm(prev => ({ ...prev, telegram_bot_token: e.target.value }))}
                    />
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Default Chat ID / Username</label>
                    <input
                      type="text"
                      placeholder="123456789"
                      value={settingsForm.telegram_chat_id}
                      onChange={(e) => setSettingsForm(prev => ({ ...prev, telegram_chat_id: e.target.value }))}
                    />
                  </div>
                </div>

                {/* WhatsApp Config */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <h4 style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>3. WhatsApp Integrations</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Recipient Phone Number</label>
                    <input
                      type="text"
                      placeholder="+1234567890"
                      value={settingsForm.whatsapp_phone_number}
                      onChange={(e) => setSettingsForm(prev => ({ ...prev, whatsapp_phone_number: e.target.value }))}
                    />
                  </div>
                </div>

                {settingsMessage && (
                  <div style={{
                    color: 'var(--accent-emerald)',
                    fontSize: '13px',
                    textAlign: 'center',
                    padding: '8px',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    border: '1px solid rgba(16, 185, 129, 0.2)'
                  }}>
                    {settingsMessage}
                  </div>
                )}

                <button type="submit" className="btn-primary" style={{ padding: '12px 0', fontSize: '14px', marginTop: '12px' }}>
                  Save and Apply Configurations
                </button>

              </form>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
