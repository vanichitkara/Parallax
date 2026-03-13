import { useState } from 'react'
import TestRunner from './components/TestRunner'
import LiveFeed from './components/LiveFeed'
import ReportView from './components/ReportView'
import JourneyView from './components/JourneyView'
import './index.css'
import './App.css'

const TABS = ['Live Test', 'Journey Replay', 'UX Report']

export default function App() {
  const [activeTab, setActiveTab] = useState('Live Test')
  const [runId, setRunId] = useState(null)
  const [runData, setRunData] = useState(null)   // final completed run data
  const [running, setRunning] = useState(false)

  function handleRunStarted(id) {
    setRunId(id)
    setRunData(null)
    setRunning(true)
    setActiveTab('Live Test')
  }

  function handleRunComplete(data) {
    setRunData(data)
    setRunning(false)
  }

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-mark">⟨P⟩</div>
          <div>
            <div className="logo-title">Parallax</div>
            <div className="logo-sub">UX Intelligence</div>
          </div>
        </div>

        <nav className="sidebar-nav">
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
        </nav>

        <div className="sidebar-footer">
          <div className="status-row">
            <div className={`pulse-dot ${running ? '' : 'dot-idle'}`} />
            <span className="status-label">{running ? 'Test running…' : 'Idle'}</span>
          </div>
          {runId && <div className="run-id-label mono">run: {runId}</div>}
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
              <TestRunner onRunStarted={handleRunStarted} running={running} />
              {runId && (
                <LiveFeed
                  runId={runId}
                  onComplete={handleRunComplete}
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
