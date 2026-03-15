import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const PERSONA_META = {
  martha: { emoji: '👵', label: 'Martha', age: 72, desc: 'Retired schoolteacher. Uses iPad for email and Facebook only. Low tech proficiency.' },
  raj:    { emoji: '👨‍💻', label: 'Raj', age: 28, desc: 'Senior software engineer. Power user of every app. High technical skills.' },
  yuki:   { emoji: '🌸', label: 'Yuki', age: 34, desc: 'Marketing manager. English is second language. Intermediate technical proficiency.' },
  sam:    { emoji: '♿', label: 'Sam', age: 40, desc: 'Accountant. Legally blind, uses screen reader (JAWS). Screen reader accessibility testing.' },
  dev:    { emoji: '📱', label: 'Dev', age: 16, desc: 'High school student. Lives on TikTok and Instagram. Very short attention span.' },
  priya:  { emoji: '🏪', label: 'Priya', age: 55, desc: 'Small business owner. Uses phone primarily. Mobile-first mindset.' },
  carlos: { emoji: '🔨', label: 'Carlos', age: 45, desc: 'Construction worker. Colorblind (deuteranopia). Prefers direct interactions.' },
}

export default function JourneyView({ journeys }) {
  const personas = journeys ? Object.keys(journeys) : []
  const [activePersona, setActivePersona] = useState(null)
  const [activeStep, setActiveStep] = useState(0)

  const currentPersona = activePersona || personas[0]
  const journey = journeys?.[currentPersona]
  const steps = journey?.steps || []
  const step = steps[activeStep]
  const personaMeta = currentPersona ? (PERSONA_META[currentPersona] || { emoji: '🙂', label: currentPersona }) : null

  if (!journeys || personas.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">◈</div>
        <p>Run a test first to view journey replays</p>
      </div>
    )
  }

  function getScreenshotUrl(persona, step) {
    // If the step already has a full cloud URL, use it directly (best for production)
    if (step?.screenshot_url && step.screenshot_url.startsWith('http')) {
      return step.screenshot_url
    }

    const dir = journeys[persona]?.output_dir
    const files = journeys[persona]?.screenshot_files || []
    const prefix = `step_${String(step.step_number).padStart(2, '0')}`
    const file = files.find(f => f.startsWith(prefix))
    if (!file || !dir) return null

    const bucket = import.meta.env.VITE_GCS_BUCKET
    if (bucket) {
      return `https://storage.googleapis.com/${bucket}/${dir}/${file}`
    }
    return `${API_BASE}/screenshots/${dir}/${file}`
  }

  return (
    <div className="journey-view">
      {/* Persona tabs */}
      <div className="journey-tabs">
        {personas.map(pid => {
          const meta = PERSONA_META[pid] || { emoji: '🙂', label: pid }
          const j = journeys[pid]
          return (
            <button
              key={pid}
              className={`journey-tab ${currentPersona === pid ? 'active' : ''}`}
              onClick={() => { setActivePersona(pid); setActiveStep(0) }}
            >
              {meta.emoji} {meta.label}
              {j?.task_completed != null && (
                <span style={{ marginLeft: 6, fontSize: '0.7rem' }}>
                  {j.task_completed ? '✅' : '❌'}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Persona description + journey summary bar */}
      {journey && (
        <div className="card" style={{ marginBottom: 16, display: 'flex', gap: 24, flexWrap: 'wrap', padding: '12px 18px' }}>
          {personaMeta && (
            <div style={{ maxWidth: 320 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                <div style={{ fontSize: '1.4rem' }}>{personaMeta.emoji}</div>
                <div>
                  <div style={{ fontWeight: 700 }}>
                    {personaMeta.label}
                    {personaMeta.age && <span style={{ color: 'var(--text-3)', marginLeft: 4 }}>· Age {personaMeta.age}</span>}
                  </div>
                  {personaMeta.desc && (
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-2)' }}>
                      {personaMeta.desc}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          <StatItem label="Steps" value={steps.length} />
          <StatItem label="Result" value={journey.task_completed ? '✅ Completed' : '❌ Failed'} />
          <StatItem label="Max Frustration" value={journey.max_frustration ?? '—'} />
          <StatItem label="Issues Found" value={journey.total_issues ?? steps.reduce((n, s) => n + (s.ux_issues?.length || 0), 0)} />
        </div>
      )}

      {steps.length === 0 ? (
        <div className="empty-state"><p>No steps recorded</p></div>
      ) : (
        <div className="journey-layout">
          {/* Step list */}
          <div className="step-list">
            {steps.map((s, i) => (
              <button
                key={i}
                className={`step-btn ${activeStep === i ? 'active' : ''}`}
                onClick={() => setActiveStep(i)}
              >
                <span className="step-num">Step {s.step_number}</span>
                {s.action?.type || 'action'}
              </button>
            ))}
          </div>

          {/* Step detail */}
          {step && (
            <div className="step-detail">
              {/* Screenshot */}
              <ScreenshotReplay 
                src={getScreenshotUrl(currentPersona, step)} 
                stepNum={step.step_number} 
              />

              <div className="step-detail-row">
                <div className="detail-card">
                  <h4>👁 What they saw</h4>
                  <p>{step.observation || '—'}</p>
                </div>
                <div className="detail-card">
                  <h4>💭 What they thought</h4>
                  <p>{step.thinking || '—'}</p>
                </div>
                <div className="detail-card">
                  <h4>🎬 Action taken</h4>
                  <p>
                    <strong>{step.action?.type}</strong>
                    {step.action?.text && ` → "${step.action.text}"`}
                    {step.action?.reason && <><br /><span style={{ color: 'var(--text-2)', fontSize: '0.8rem' }}>{step.action.reason}</span></>}
                  </p>
                </div>
                <div className="detail-card">
                  <h4>😤 Emotional state</h4>
                  <p>
                    {step.emotion || 'neutral'} · Frustration: {step.frustration_level ?? '—'}
                    {(step.confusion_points?.length > 0) && (
                      <><br /><span style={{ color: 'var(--warning)', fontSize: '0.78rem' }}>
                        ⚠ {step.confusion_points[0]}
                      </span></>
                    )}
                  </p>
                </div>
              </div>

              {/* UX Issues */}
              {step.ux_issues?.length > 0 && (
                <div>
                  <h4 style={{ fontSize: '0.78rem', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>Issues detected</h4>
                  {step.ux_issues.map((issue, j) => (
                    <div key={j} style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', marginBottom: 8 }}>
                      <span className={`badge badge-${issue.severity === 'critical' ? 'danger' : issue.severity === 'high' ? 'warning' : 'info'}`} style={{ marginBottom: 6 }}>
                        {issue.severity}
                      </span>
                      <div style={{ fontWeight: 600, marginBottom: 2 }}>{issue.title}</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-2)' }}>{issue.description}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ScreenshotReplay({ src, stepNum }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  // Reset state when src changes
  useEffect(() => {
    setLoading(true)
    setError(false)
  }, [src])

  if (!src) {
    return <div className="persona-screenshot-placeholder" style={{ height: 200 }}>No screenshot for step {stepNum}</div>
  }

  return (
    <div className="screenshot-container">
      {loading && (
        <div className="screenshot-loading">
          <div className="skeleton" style={{ width: '100%', height: '100%' }} />
          <div style={{ position: 'absolute', color: 'var(--text-3)', fontSize: '0.85rem', fontWeight: 600 }}>
            🛰 LOADING SCREENSHOT...
          </div>
        </div>
      )}
      <img 
        src={src} 
        alt={`Step ${stepNum}`} 
        className="step-screenshot" 
        style={{ display: loading ? 'none' : 'block' }}
        onLoad={() => setLoading(false)}
        onError={() => { setLoading(false); setError(true) }}
      />
      {error && !loading && (
        <div className="persona-screenshot-placeholder">Failed to load screenshot</div>
      )}
    </div>
  )
}

function StatItem({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div style={{ fontWeight: 700, fontSize: '1rem', marginTop: 2 }}>{value}</div>
    </div>
  )
}
