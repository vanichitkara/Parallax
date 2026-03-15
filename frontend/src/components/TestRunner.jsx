import { useState } from 'react'

const ALL_PERSONAS = [
  { id: 'martha', label: 'Martha', emoji: '👵', age: 72, desc: 'Retired schoolteacher. Uses iPad for email and Facebook only. Low tech proficiency.' },
  { id: 'raj',    label: 'Raj',    emoji: '👨‍💻', age: 28, desc: 'Senior software engineer. Power user of every app. High technical skills.' },
  { id: 'yuki',   label: 'Yuki',   emoji: '🌸', age: 34, desc: 'Marketing manager. English is second language. Intermediate technical proficiency.' },
  { id: 'sam',    label: 'Sam',    emoji: '♿', age: 40, desc: 'Accountant. Legally blind, uses screen reader (JAWS). Screen reader accessibility testing.' },
  { id: 'dev',    label: 'Dev',    emoji: '📱', age: 16, desc: 'High school student. Lives on TikTok and Instagram. Very short attention span.' },
  { id: 'priya',  label: 'Priya',  emoji: '🏪', age: 55, desc: 'Small business owner. Uses phone primarily. Mobile-first mindset.' },
  { id: 'carlos', label: 'Carlos', emoji: '🔨', age: 45, desc: 'Construction worker. Colorblind (deuteranopia). Prefers direct interactions.' },
]

const DEMO_PRESETS = [
  { label: 'National Insurance', url: 'https://nationalinsurance.nic.co.in/', task: 'Find the claims procedure for universal health insurance' },
  { label: 'GitHub Trending', url: 'https://github.com/trending', task: 'Browse the trending repositories and find the name of the top repository today' },
  { label: 'Wikipedia', url: 'https://en.wikipedia.org', task: 'Find information about climate change and navigate to a related topic' },
]

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function TestRunner({ onRunStarted, running, authToken }) {
  const [url, setUrl] = useState('')
  const [task, setTask] = useState('')
  const [selectedPersonas, setSelectedPersonas] = useState(['martha', 'raj'])
  const [error, setError] = useState('')

  function togglePersona(id) {
    setSelectedPersonas(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    )
  }

  function applyPreset(preset) {
    setUrl(preset.url)
    setTask(preset.task)
  }

  async function handleStart() {
    if (!url.trim() || !task.trim()) { setError('URL and task are required.'); return }
    if (selectedPersonas.length === 0) { setError('Select at least one persona.'); return }
    setError('')

    try {
      const res = await fetch(`${API_BASE}/test`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...(authToken ? { 'Authorization': `Basic ${authToken}` } : {})
        },
        body: JSON.stringify({ url: url.trim(), task: task.trim(), personas: selectedPersonas }),
      })
      const data = await res.json()
      if (res.ok) {
        onRunStarted(data.run_id, selectedPersonas)
      } else {
        setError(data.detail || 'Failed to start test')
      }
    } catch (e) {
      setError('Could not connect to API. Is the backend running?')
    }
  }

  return (
    <div className="card test-runner">
      <h2>⚙️ Configure Test</h2>
      <div className="form-grid">
        {/* Presets */}
        <div className="form-group">
          <label className="form-label">Quick Presets</label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {DEMO_PRESETS.map(p => (
              <button key={p.label} className="btn btn-ghost" style={{ fontSize: '0.78rem', padding: '6px 12px' }} onClick={() => applyPreset(p)}>
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* URL */}
        <div className="form-group">
          <label className="form-label">Target URL</label>
          <input className="input" placeholder="https://example.com" value={url} onChange={e => setUrl(e.target.value)} disabled={running} />
        </div>

        {/* Task */}
        <div className="form-group">
          <label className="form-label">User Task</label>
          <input className="input" placeholder="e.g. Find the claims procedure for health insurance" value={task} onChange={e => setTask(e.target.value)} disabled={running} />
        </div>

        {/* Personas */}
        <div className="form-group">
          <label className="form-label">Personas ({selectedPersonas.length} selected)</label>
          <div className="persona-grid">
            {ALL_PERSONAS.map(p => (
              <button
                key={p.id}
                className={`persona-chip ${selectedPersonas.includes(p.id) ? 'selected' : ''}`}
                onClick={() => togglePersona(p.id)}
                disabled={running}
              >
                <div className="persona-chip-icon">{p.emoji}</div>
                <div className="persona-chip-body">
                  <div className="persona-chip-name">{p.label}, {p.age}</div>
                  <div className="persona-chip-desc">{p.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {error && <div style={{ color: 'var(--danger)', fontSize: '0.82rem' }}>⚠ {error}</div>}

        <button className="btn btn-primary" onClick={handleStart} disabled={running} style={{ width: 'fit-content' }}>
          {running ? '⏳ Running…' : '▶ Start Test'}
        </button>
      </div>
    </div>
  )
}
