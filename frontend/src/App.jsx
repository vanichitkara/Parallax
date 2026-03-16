import { useState, useEffect } from 'react'
import TestRunner from './components/TestRunner'
import LiveFeed from './components/LiveFeed'
import ReportView from './components/ReportView'
import JourneyView from './components/JourneyView'
import LandingPage from './components/LandingPage'
import './index.css'
import './App.css'
import logo from './assets/logo.png'

const TABS = ['Live Test', 'Journey Replay', 'UX Report']

export default function App() {
  const [activeTab, setActiveTab] = useState('Live Test')
  const [runId, setRunId] = useState(null)      // The run being VIEWED
  const [runData, setRunData] = useState(null)   // The data for the viewed run
  const [activeRunId, setActiveRunId] = useState(null) // The currently RUNNING test
  const [history, setHistory] = useState([])     // List of all user runs
  const [running, setRunning] = useState(false)
  
  // Auth state
  const [authToken, setAuthToken] = useState(localStorage.getItem('parallax_auth'))
  const [userData, setUserData] = useState(() => {
    const saved = localStorage.getItem('parallax_user')
    return saved ? JSON.parse(saved) : null
  })

  // Load runs on mount / login
  useEffect(() => {
    if (authToken) {
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      fetch(`${API_BASE}/runs`, {
        headers: { 'Authorization': `Basic ${authToken}` }
      })
      .then(r => r.json())
      .then(data => {
        if (data.runs) {
          setHistory(data.runs)
          if (data.runs.length > 0 && !runId) {
            const latest = data.runs[0]
            setRunId(latest.run_id)
            setRunData(latest)
          }
        }
      })
      .catch(err => console.error("Error loading runs:", err))
    }
  }, [authToken, running]) // Refresh history when a run starts/finishes

  function handleLogin(token, user) {
    localStorage.setItem('parallax_auth', token)
    if (user) localStorage.setItem('parallax_user', JSON.stringify(user))
    setAuthToken(token)
    if (user) setUserData(user)
  }

  function handleLogout() {
    localStorage.removeItem('parallax_auth')
    localStorage.removeItem('parallax_user')
    setAuthToken(null)
    setUserData(null)
    setHistory([])
    setRunId(null)
    setRunData(null)
    setActiveRunId(null)
    setRunning(false)
    setActiveTab('Live Test')
    window.scrollTo(0, 0)
  }

  if (!authToken) {
    return <LandingPage onLogin={handleLogin} />
  }

  function handleRunStarted(id, personas) {
    setRunId(id)
    setActiveRunId(id)
    setRunData({ run_id: id, status: 'running', personas: personas, logs: [] })
    setRunning(true)
    setActiveTab('Live Test')
  }

  function handleRunComplete(data) {
    if (data.run_id === activeRunId) {
      setRunning(false)
      setActiveRunId(null)
    }
    // Update the viewed run data if it matches the completed one
    if (data.run_id === runId) {
      setRunData(data)
    }
  }

  function handleSelectRun(run) {
    setRunId(run.run_id)
    setRunData(run)
    if (run.status === 'running') {
      setActiveTab('Live Test')
    } else {
      setActiveTab('Journey Replay')
    }
  }

  function handleReturnToActive() {
    if (!activeRunId) return
    setRunId(activeRunId)
    setRunData(null)
    setActiveTab('Live Test')
  }

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <img src={logo} alt="Parallax" style={{ width: 32, height: 32, objectFit: 'contain' }} />
          <div>
            <div className="logo-title">Parallax</div>
            <div className="logo-sub">UX Intelligence</div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-label">Main</div>
          {TABS.map(tab => (
            <button
              key={tab}
              className={`nav-item ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              <span className="nav-icon">{tabIcon(tab)}</span>
              {tab}
            </button>
          ))}

          <div className="nav-section-label" style={{ marginTop: '20px' }}>Recent Runs</div>
          <div className="history-list">
            {running && activeRunId && (
              <button
                className={`history-item active-pulse ${runId === activeRunId ? 'active' : ''}`}
                onClick={handleReturnToActive}
              >
                <div className="history-run-id">run: {activeRunId}</div>
                <div className="history-meta">Currently Streaming...</div>
                <div className="history-status status-running">LIVE NOW</div>
              </button>
            )}
            {history
              .filter(r => r.run_id !== activeRunId)
              .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
              .map(run => {
                const baseTitle = run.short_title || run.task || run.url || `run: ${run.run_id}`
                const title = baseTitle.length > 80 ? `${baseTitle.slice(0, 77)}…` : baseTitle
                return (
                  <button
                    key={run.run_id}
                    className={`history-item ${runId === run.run_id ? 'active' : ''}`}
                    onClick={() => handleSelectRun(run)}
                  >
                    <div className="history-run-id">
                      {title}
                    </div>
                    <div className="history-meta">
                      {new Date(run.created_at).toLocaleDateString()} {new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {run.personas?.length} agent{run.personas?.length > 1 ? 's' : ''}
                    </div>
                    <div className={`history-status status-${run.status}`}>{run.status}</div>
                  </button>
                )
              })}
            {history.length === 0 && !running && <div className="history-empty">No previous runs</div>}
          </div>
        </nav>

        <div className="sidebar-footer">
          {userData && (
            <div className="user-profile">
              <div className="user-avatar">{userData.name?.[0]?.toUpperCase() || 'U'}</div>
              <div className="user-info">
                <div className="user-name">{userData.name}</div>
                <div className="user-email">{userData.email}</div>
              </div>
            </div>
          )}
          <div className="status-row">
            <div className={`pulse-dot ${running ? '' : 'dot-idle'}`} />
            <span className="status-label">{running ? 'Test running…' : 'Idle'}</span>
          </div>
          {runId && <div className="run-id-label mono">run: {runId}</div>}
          <button className="btn btn-ghost btn-sign-out" onClick={handleLogout}>
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        <div className="top-bar">
          <div>
            <h1 className="page-title">{activeTab}</h1>
            <p className="page-sub">
              {activeTab === 'Live Test' && 'Configure and launch a multi-persona UX test'}
              {activeTab === 'Journey Replay' && "Step through each persona's navigation journey"}
              {activeTab === 'UX Report' && 'Aggregated findings and prioritized recommendations'}
            </p>
          </div>
        </div>

        <div className="content-area">
          {activeTab === 'Live Test' && (
            <div className="live-layout">
              <TestRunner onRunStarted={handleRunStarted} running={running} authToken={authToken} />
              {runId && (
                <LiveFeed
                  runId={runId}
                  onComplete={handleRunComplete}
                  initialData={runData}
                />
              )}
            </div>
          )}
          {activeTab === 'Journey Replay' && (
            <JourneyView journeys={runData?.journeys} />
          )}
          {activeTab === 'UX Report' && (
            <ReportView report={runData?.report} journeys={runData?.journeys} />
          )}
        </div>
      </main>
    </div>
  )
}

function tabIcon(tab) {
  if (tab === 'Live Test') return '▶'
  if (tab === 'Journey Replay') return '◈'
  if (tab === 'UX Report') return '◎'
  return '•'
}
