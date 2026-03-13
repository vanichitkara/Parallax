const SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }

function severityColor(sev) {
  if (sev === 'critical') return 'sev-critical'
  if (sev === 'high')     return 'sev-high'
  if (sev === 'medium')   return 'sev-medium'
  return 'sev-low'
}

export default function ReportView({ report, journeys }) {
  if (!report && !journeys) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">◎</div>
        <p>Run a test to generate a UX report</p>
      </div>
    )
  }

  const personas = journeys ? Object.keys(journeys) : []

  // Collect all issues from journeys
  const allIssues = []
  for (const pid of personas) {
    const steps = journeys?.[pid]?.steps || []
    for (const step of steps) {
      for (const issue of step.ux_issues || []) {
        allIssues.push({ ...issue, persona: pid, step: step.step_number })
      }
    }
  }

  // Deduplicate by title and sort by severity
  const dedupedIssues = []
  const seen = new Set()
  for (const issue of allIssues.sort((a,b) => (SEV_ORDER[a.severity]??99) - (SEV_ORDER[b.severity]??99))) {
    const key = issue.title?.toLowerCase().substring(0, 40)
    if (!seen.has(key)) {
      seen.add(key)
      dedupedIssues.push(issue)
    }
  }

  const completed = personas.filter(p => journeys?.[p]?.task_completed).length
  const avgFrustration = personas.length > 0
    ? (personas.reduce((s, p) => s + (journeys?.[p]?.max_frustration || 0), 0) / personas.length).toFixed(1)
    : 0
  const avgSteps = personas.length > 0
    ? (personas.reduce((s, p) => s + (journeys?.[p]?.steps?.length || 0), 0) / personas.length).toFixed(1)
    : 0

  return (
    <div className="report-view">
      <div className="report-header">
        <h2>UX Analysis Report</h2>
        {report?.url && <p>Tested: <strong>{report.url}</strong></p>}
        {report?.task && <p style={{ marginTop: 2 }}>Task: {report.task}</p>}
      </div>

      {/* Summary metrics */}
      <div className="summary-grid">
        <div className="summary-card">
          <div className="summary-value" style={{ color: 'var(--success)' }}>{completed}/{personas.length}</div>
          <div className="summary-label">Task Completion</div>
        </div>
        <div className="summary-card">
          <div className="summary-value" style={{ color: 'var(--warning)' }}>{avgFrustration}</div>
          <div className="summary-label">Avg Frustration</div>
        </div>
        <div className="summary-card">
          <div className="summary-value">{avgSteps}</div>
          <div className="summary-label">Avg Steps</div>
        </div>
        <div className="summary-card">
          <div className="summary-value" style={{ color: 'var(--danger)' }}>{dedupedIssues.length}</div>
          <div className="summary-label">Unique Issues</div>
        </div>
      </div>

      {/* Persona comparison table */}
      {personas.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <h3 style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-3)', marginBottom: 12 }}>
            Persona Comparison
          </h3>
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--bg-2)', fontSize: '0.75rem', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  {['Persona','Age','Tech','Steps','Frustration','Result'].map(h => (
                    <th key={h} style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {personas.map((pid, i) => {
                  const j = journeys[pid]
                  return (
                    <tr key={pid} style={{ borderTop: '1px solid var(--border)', background: i % 2 === 0 ? 'transparent' : 'var(--bg-2)' }}>
                      <td style={{ padding: '10px 14px', fontWeight: 600 }}>{pid.charAt(0).toUpperCase() + pid.slice(1)}</td>
                      <td style={{ padding: '10px 14px', color: 'var(--text-2)' }}>{j?.persona_age || '—'}</td>
                      <td style={{ padding: '10px 14px', color: 'var(--text-2)' }}>{j?.persona_tech_level || '—'}</td>
                      <td style={{ padding: '10px 14px' }}>{j?.steps?.length || 0}</td>
                      <td style={{ padding: '10px 14px' }}>{j?.max_frustration ?? '—'}</td>
                      <td style={{ padding: '10px 14px' }}>
                        <span className={`badge ${j?.task_completed ? 'badge-success' : 'badge-danger'}`}>
                          {j?.task_completed ? '✓ Done' : '✗ Failed'}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Issues */}
      {dedupedIssues.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <h3 style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-3)', marginBottom: 12 }}>
            Prioritized Issues ({dedupedIssues.length})
          </h3>
          <div className="issue-list">
            {dedupedIssues.map((issue, i) => (
              <div key={i} className="issue-card">
                <div className={`issue-severity ${severityColor(issue.severity)}`} />
                <div className="issue-body">
                  <div className="issue-title">{issue.title || 'Unnamed Issue'}</div>
                  <div className="issue-desc">{issue.description}</div>
                  <div className="issue-affected">
                    <span className={`badge badge-${issue.severity === 'critical' ? 'danger' : issue.severity === 'high' ? 'warning' : 'info'}`}>
                      {issue.severity}
                    </span>
                    <span style={{ marginLeft: 8, color: 'var(--text-3)' }}>
                      {issue.category || ''} · Found by {issue.persona} at step {issue.step}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* AI narrative */}
      {report?.analysis && (
        <div>
          <h3 style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-3)', marginBottom: 12 }}>
            AI Analysis
          </h3>
          <div className="report-text">{report.analysis}</div>
        </div>
      )}
    </div>
  )
}
