import { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const PERSONA_META = {
  martha: { emoji: '👵', label: 'Martha' },
  raj:    { emoji: '👨‍💻', label: 'Raj' },
  yuki:   { emoji: '🌸', label: 'Yuki' },
  sam:    { emoji: '♿', label: 'Sam' },
  dev:    { emoji: '📱', label: 'Dev' },
  priya:  { emoji: '🏪', label: 'Priya' },
  carlos: { emoji: '🔨', label: 'Carlos' },
}

export default function JourneyView({ journeys }) {
  const personas = journeys ? Object.keys(journeys) : []
  const [activePersona, setActivePersona] = useState(null)
  const [activeStep, setActiveStep] = useState(0)

  const currentPersona = activePersona || personas[0]
  const journey = journeys?.[currentPersona]
  const steps = journey?.steps || []
  const step = steps[activeStep]

  if (!journeys || personas.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">◈</div>
        <p>Run a test first to view journey replays</p>
      </div>
    )
  }

  function screenshotUrl(persona, stepNum) {
    const dir = journeys[persona]?.output_dir           // e.g. "martha_20260303_162907"
    const files = journeys[persona]?.screenshot_files || []
    // Match "step_01_navigate.png", "step_02_click_element.png", etc.
    const prefix = `step_${String(stepNum).padStart(2, '0')}`
    const file = files.find(f => f.startsWith(prefix))
    if (file && dir) return `${API_BASE}/screenshots/${dir}/${file}`
    return null
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

      {/* Journey summary bar */}
      {journey && (
        <div className="card" style={{ marginBottom: 16, display: 'flex', gap: 24, flexWrap: 'wrap', padding: '12px 18px' }}>
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
              {(() => {
                const src = screenshotUrl(currentPersona, step.step_number)
                return src
                  ? <img src={src} alt={`Step ${step.step_number}`} className="step-screenshot" onError={e => { e.target.style.display='none' }} />
                  : <div className="persona-screenshot-placeholder" style={{ height: 200 }}>No screenshot for step {step.step_number}</div>
              })()}

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

function StatItem({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: '0.7rem', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div style={{ fontWeight: 700, fontSize: '1rem', marginTop: 2 }}>{value}</div>
    </div>
  )
}
