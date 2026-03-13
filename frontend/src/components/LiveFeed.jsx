import { useEffect, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WS_BASE  = API_BASE.replace(/^http/, 'ws')

const PERSONA_META = {
  martha: { emoji: '👵', label: 'Martha', age: 72,  maxFrustration: 3 },
  raj:    { emoji: '👨‍💻', label: 'Raj',    age: 28,  maxFrustration: 8 },
  yuki:   { emoji: '🌸', label: 'Yuki',   age: 34,  maxFrustration: 5 },
  sam:    { emoji: '♿', label: 'Sam',    age: 40,  maxFrustration: 6 },
  dev:    { emoji: '📱', label: 'Dev',    age: 16,  maxFrustration: 2 },
  priya:  { emoji: '🏪', label: 'Priya',  age: 55,  maxFrustration: 4 },
  carlos: { emoji: '🔨', label: 'Carlos', age: 45,  maxFrustration: 4 },
}

function parseLogLine(line) {
  if (line.includes('📍 Step'))    return { type: 'step',    text: line }
  if (line.includes('👁️') || line.includes('Sees:')) return { type: 'sees', text: line }
  if (line.includes('😐') || line.includes('😤') || line.includes('😕') || line.includes('🤩') || line.includes('😡') || line.includes('Feeling:')) return { type: 'emotion', text: line }
  if (line.includes('🔍 Issue'))   return { type: 'issue',   text: line }
  if (line.includes('✅'))         return { type: 'done',    text: line }
  if (line.includes('❌') || line.includes('gave up')) return { type: 'error', text: line }
  return { type: 'normal', text: line }
}

function extractPersonaState(logs) {
  // Parse logs to build per-persona live state
  const states = {}
  let currentPersona = null

  for (const line of logs) {
    // Detect persona header
    const personaMatch = line.match(/🧑 (\w+) \(age/)
    if (personaMatch) {
      currentPersona = personaMatch[1].toLowerCase()
      if (!states[currentPersona]) {
        states[currentPersona] = { step: 0, stepLabel: '', sees: '', emotion: 'neutral', frustration: 0, done: false, success: false, issues: 0 }
      }
    }
    if (!currentPersona) continue

    const s = states[currentPersona]
    const stepMatch = line.match(/📍 Step (\d+): (.+?)\s*—/)
    if (stepMatch) { s.step = parseInt(stepMatch[1]); s.stepLabel = stepMatch[2] }

    const seesMatch = line.match(/(?:👁️|Sees:)\s*(.+)/)
    if (seesMatch) s.sees = seesMatch[1].slice(0, 120)

    const frustMatch = line.match(/Frustration:\s*(\d+)/)
    if (frustMatch) s.frustration = parseInt(frustMatch[1])

    const emotionMatch = line.match(/(?:😐|😤|😕|🤩|😡|Feeling:)\s*(\w+)/)
    if (emotionMatch) s.emotion = emotionMatch[1]

    if (line.includes('🔍 Issue')) s.issues = (s.issues || 0) + 1

    if (line.includes('✅') && line.includes('completed')) { s.done = true; s.success = true }
    if (line.includes('❌') && (line.includes('gave up') || line.includes('Gave up'))) { s.done = true; s.success = false }
  }

  return states
}

export default function LiveFeed({ runId, onComplete }) {
  const [logs, setLogs] = useState([])
  const [personaStates, setPersonaStates] = useState({})
  const [status, setStatus] = useState('connecting')
  const logEndRef = useRef(null)
  const wsRef = useRef(null)

  useEffect(() => {
    if (!runId) return
    setLogs([])
    setPersonaStates({})
    setStatus('connecting')

    const ws = new WebSocket(`${WS_BASE}/ws/${runId}`)
    wsRef.current = ws

    ws.onopen = () => setStatus('connected')
    ws.onclose = () => setStatus('disconnected')
    ws.onerror = () => setStatus('error')

    ws.onmessage = (evt) => {
      const event = JSON.parse(evt.data)

      if (event.type === 'state') {
        // Replay existing logs
        const existing = event.run?.logs || []
        setLogs(existing)
        setPersonaStates(extractPersonaState(existing))
      } else if (event.type === 'log') {
        setLogs(prev => {
          const next = [...prev, event.line]
          setPersonaStates(extractPersonaState(next))
          return next
        })
      } else if (event.type === 'complete') {
        setStatus('complete')
        if (onComplete) onComplete(event)
      } else if (event.type === 'error') {
        setStatus('error')
      }
    }

    return () => ws.close()
  }, [runId])

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs.length])

  const activePersonas = Object.keys(personaStates)

  return (
    <div className="live-feed">
      <div className="live-feed-header">
        <h2>📡 Live Feed</h2>
        <span className={`badge ${status === 'complete' ? 'badge-success' : status === 'error' ? 'badge-danger' : 'badge-info'}`}>
          {status === 'connecting' ? '⟳ Connecting' : status === 'connected' ? '● Streaming' : status === 'complete' ? '✓ Complete' : status}
        </span>
      </div>

      {/* Persona cards */}
      {activePersonas.length > 0 && (
        <div className="persona-cards">
          {activePersonas.map(pid => {
            const meta = PERSONA_META[pid] || { emoji: '🙂', label: pid, maxFrustration: 5 }
            const state = personaStates[pid]
            const frustPct = Math.min(100, (state.frustration / meta.maxFrustration) * 100)
            const frustClass = frustPct > 66 ? 'high' : frustPct > 33 ? 'mid' : ''
            const cardClass = state.done ? (state.success ? 'done-ok' : 'done-fail') : (state.step > 0 ? 'active' : '')

            return (
              <div key={pid} className={`persona-card ${cardClass}`}>
                <div className="persona-card-header">
                  <div className="persona-avatar">{meta.emoji}</div>
                  <div>
                    <div className="persona-name">{meta.label}</div>
                    <div className="persona-meta">Age {meta.age} · Step {state.step}</div>
                  </div>
                  <div style={{ marginLeft: 'auto' }}>
                    {state.done
                      ? <span className={`badge ${state.success ? 'badge-success' : 'badge-danger'}`}>{state.success ? '✓ Done' : '✗ Gave up'}</span>
                      : state.step > 0 ? <span className="badge badge-info">● Active</span>
                      : <span className="badge badge-default">Queued</span>
                    }
                  </div>
                </div>

                <div className="persona-card-body">
                  {state.sees
                    ? <p className="persona-thought">"{state.sees}"</p>
                    : <div className="persona-screenshot-placeholder">Waiting…</div>
                  }
                  {state.step > 0 && (
                    <>
                      <div className="frustration-bar">
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-3)', width: 70 }}>Frustration</span>
                        <div className="frustration-track">
                          <div className={`frustration-fill ${frustClass}`} style={{ width: `${frustPct}%` }} />
                        </div>
                        <span className="frustration-label">{state.frustration}/{meta.maxFrustration}</span>
                      </div>
                      {state.issues > 0 && (
                        <div style={{ fontSize: '0.72rem', color: 'var(--warning)' }}>
                          ⚠ {state.issues} issue{state.issues > 1 ? 's' : ''} found
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Log console */}
      <div className="log-console">
        {logs.length === 0 && <span style={{ color: 'var(--text-3)' }}>Waiting for pipeline output…</span>}
        {logs.map((line, i) => {
          const { type, text } = parseLogLine(line)
          return <div key={i} className={`log-line ${type}`}>{text}</div>
        })}
        <div ref={logEndRef} />
      </div>
    </div>
  )
}
