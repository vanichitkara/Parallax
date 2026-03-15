import { useState } from 'react'
import './LandingPage.css'
import logo from '../assets/logo.png'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function LandingPage({ onLogin }) {
  const [showLogin, setShowLogin] = useState(false)
  const [isSignUp, setIsSignUp] = useState(false)
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin(e) {
    e.preventDefault()
    setLoading(true)
    setError('')
    
    try {
      const endpoint = isSignUp ? '/signup' : '/login'
      const body = isSignUp 
        ? JSON.stringify({ name, email, password })
        : JSON.stringify({ email, password })

      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body
      })
      
      const data = await res.json()
      
      if (!res.ok) {
        throw new Error(data.detail || 'Authentication failed')
      }

      if (isSignUp) {
        // Automatically log in after signup
        const token = btoa(`${email.toLowerCase()}:${password}`)
        onLogin(token, { name, email: email.toLowerCase() })
      } else {
        onLogin(data.token, data.user)
      }
    } catch (err) {
      setError(err.message || 'Cannot connect to the backend server.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="landing-container">
      {/* Abstract Background Elements */}
      <div className="bg-shape shape-1"></div>
      <div className="bg-shape shape-2"></div>
      <div className="bg-shape shape-3"></div>

      <nav className="landing-nav">
        <div className="logo">
          <img src={logo} alt="Parallax" style={{ width: 32, height: 32, objectFit: 'contain', marginRight: 8 }} />
          <span className="logo-text">Parallax</span>
        </div>
        {!showLogin && <button className="btn btn-ghost" onClick={() => { setShowLogin(true); setIsSignUp(false); }}>Sign In</button>}
      </nav>

      <main className="landing-main">
        {showLogin ? (
          <div className="login-card fade-in">
            <div className="auth-tabs">
              <button 
                className={`auth-tab ${!isSignUp ? 'active' : ''}`} 
                onClick={() => { setIsSignUp(false); setError(''); }}
              >
                Login
              </button>
              <button 
                className={`auth-tab ${isSignUp ? 'active' : ''}`} 
                onClick={() => { setIsSignUp(true); setError(''); }}
              >
                Sign Up
              </button>
            </div>
            
            <h2>{isSignUp ? 'Create Account' : 'Welcome Back'}</h2>
            <p>{isSignUp ? 'Join Parallax to start UX testing.' : 'Enter your credentials to access the dashboard.'}</p>
            
            <form onSubmit={handleLogin} className="login-form">
              {isSignUp && (
                <div className="form-group">
                  <label className="form-label">Full Name</label>
                  <input 
                    type="text" 
                    className="input" 
                    placeholder="e.g. John Doe"
                    required
                    value={name}
                    onChange={e => setName(e.target.value)}
                  />
                </div>
              )}
              <div className="form-group">
                <label className="form-label">Email Address</label>
                <input 
                  type="email" 
                  className="input" 
                  placeholder="name@company.com"
                  required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Password</label>
                <input 
                  type="password" 
                  className="input" 
                  placeholder="Enter your password"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                />
              </div>
              {error && <div className="error-text">⚠ {error}</div>}
              <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%', marginTop: '1rem' }}>
                {loading ? 'Processing...' : (isSignUp ? 'Create Account' : 'Access Dashboard')}
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => setShowLogin(false)} style={{ width: '100%', marginTop: '0.5rem' }}>
                Back
              </button>
            </form>
          </div>
        ) : (
          <div className="hero-section fade-in">
            <div className="hero-content">
              <h1 className="hero-title">
                Autopilot for<br/>
                <span className="text-gradient">UX Testing</span>
              </h1>
              <p className="hero-desc">
                Deploy diverse AI persona agents to navigate your web applications, 
                identify friction points, and generate comprehensive accessibility and UX reports instantly.
              </p>
              <div className="hero-actions">
                <button className="btn btn-primary btn-lg" onClick={() => setShowLogin(true)}>
                  Launch Dashboard 
                  <span style={{ marginLeft: 8 }}>→</span>
                </button>
                <a href="#features" className="btn btn-ghost btn-lg">Learn more</a>
              </div>
            </div>
            
            <div className="hero-visual">
              <div className="glass-card mockup-card">
                <div className="mockup-header">
                  <div className="dots"><span></span><span></span><span></span></div>
                  <div className="mockup-url">parallax-agent.testing</div>
                </div>
                <div className="mockup-body">
                  <div className="mockup-step">
                    <div className="step-icon">👵</div>
                    <div className="step-text">
                      <strong>Martha (72)</strong> is navigating to checkout...
                      <div className="progress-bar"><div className="progress-fill fill-70"></div></div>
                    </div>
                  </div>
                  <div className="mockup-step">
                    <div className="step-icon">♿</div>
                    <div className="step-text">
                      <strong>Sam (Screen Reader)</strong> detected 2 ARIA issues.
                      <div className="progress-bar"><div className="progress-fill fill-100 danger"></div></div>
                    </div>
                  </div>
                  <div className="mockup-step opacity-50">
                    <div className="step-icon">📱</div>
                    <div className="step-text">
                      <strong>Dev (Gen Z)</strong> is waiting in queue...
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {!showLogin && (
        <section id="features" className="features-section fade-in" style={{ animationDelay: '0.2s' }}>
          <div className="feature-grid">
            <div className="feature-card glass-card">
              <div className="f-icon">🤖</div>
              <h3>Multi-Agent Orchestration</h3>
              <p>Run sequential UX tests using LLM-powered agents with unique cognitive profiles and tech literacy levels.</p>
            </div>
            <div className="feature-card glass-card">
              <div className="f-icon">👁️</div>
              <h3>Vision Capabilities</h3>
              <p>Agents actually 'see' your interface using Gemini Vision, clicking elements based on visual hierarchy rather than DOM structure.</p>
            </div>
            <div className="feature-card glass-card">
              <div className="f-icon">📊</div>
              <h3>Actionable Reports</h3>
              <p>Aggregates findings across all personas into prioritized recommendations and cross-persona patterns.</p>
            </div>
          </div>
        </section>
      )}

      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-left">
            <div className="logo footer-logo">
              <img src={logo} alt="Parallax" style={{ width: 20, height: 20, objectFit: 'contain', marginRight: 6 }} />
              <span>Parallax</span>
            </div>
            <p className="copyright">© 2026 Parallax AI. All rights reserved.</p>
          </div>
          <div className="footer-right">
            <a href="https://github.com/vanichitkara/Parallax/blob/main/README.md">Documentation</a>
            <a href="https://github.com/vanichitkara/Parallax">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
