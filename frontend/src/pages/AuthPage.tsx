import { useState } from 'react'
import { notifications } from '@mantine/notifications'
import { IconArrowRight } from '@tabler/icons-react'
import { useNavigate } from 'react-router-dom'
import { login, signup } from '../lib/auth'

type AuthPageProps = {
  onAuthSuccess: () => void
}

export function AuthPage({ onAuthSuccess }: AuthPageProps) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const nav = useNavigate()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      if (mode === 'login') {
        await login({ email, password, device: 'web' })
        notifications.show({ title: 'Welcome back', message: 'Logged in successfully.' })
      } else {
        await signup({ username, email, password })
        notifications.show({ title: 'Account created', message: 'You are now signed in.' })
      }
      onAuthSuccess()
      nav('/')
    } catch (e) {
      notifications.show({
        title: 'Authentication failed',
        message: e instanceof Error ? e.message : 'Unknown error',
        color: 'red',
      })
    } finally {
      setLoading(false)
    }
  }

  const canSubmit = email.trim() && password.trim() && (mode === 'login' || username.trim())

  return (
    <div className="auth-shell">
      {/* ───── Left: Branding Panel ───── */}
      <div className="auth-left">
        <div className="auth-left-inner">
          {/* Logo */}
          <div className="auth-brand-row">
            <div className="ff-logo-badge">FF</div>
            <span className="ff-logo-text">Fieldforce</span>
          </div>

          {/* Content pushed to vertical center */}
          <div className="auth-left-center">
            <div className="auth-status-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/></svg>
              <span>PostgreSQL + pgvector connected</span>
            </div>

            <h1 className="auth-hero-title">
              Answers grounded<br/>
              in <span className="teal-accent">your documents.</span>
            </h1>

            <p className="auth-hero-subtitle">
              A focused workspace for asking questions, keeping conversation context, and citing every source your model relies on.
            </p>

            <div className="auth-feature-row">
              <div className="auth-feature-pill">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <span>Threaded chat</span>
              </div>
              <div className="auth-feature-pill">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/></svg>
                <span>Streaming answers</span>
              </div>
              <div className="auth-feature-pill">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                <span>JWT secured</span>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="auth-left-footer">
            © 2026 Fieldforce · Internal preview
          </div>
        </div>
      </div>

      {/* ───── Right: Auth Form ───── */}
      <div className="auth-right">
        <div className="auth-form-container">
          <form onSubmit={onSubmit} className="auth-form">
            <div className="auth-form-header">
              <h2 className="auth-form-title">
                {mode === 'login' ? 'Welcome back' : 'Create an account'}
              </h2>
              <p className="auth-form-subtitle">
                {mode === 'login' ? (
                  <><span className="teal-accent">Sign in</span> to continue to your workspace.</>
                ) : (
                  <>Set up your workspace to start using <span className="teal-accent">Fieldforce</span>.</>
                )}
              </p>
            </div>

            {mode === 'signup' && (
              <div className="auth-field">
                <label className="auth-label" htmlFor="auth-username">USERNAME</label>
                <input
                  id="auth-username"
                  className="auth-input"
                  type="text"
                  placeholder="ali"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoComplete="username"
                />
              </div>
            )}

            <div className="auth-field">
              <label className="auth-label" htmlFor="auth-email">EMAIL</label>
              <input
                id="auth-email"
                className="auth-input"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div className="auth-field">
              <label className="auth-label" htmlFor="auth-password">PASSWORD</label>
              <input
                id="auth-password"
                className="auth-input"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            <button
              type="submit"
              className="auth-submit-btn"
              disabled={!canSubmit || loading}
            >
              <span>{loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}</span>
              {!loading && <IconArrowRight size={17} stroke={2} />}
            </button>

            <p className="auth-toggle-text">
              {mode === 'login' ? 'New to Fieldforce? ' : 'Already have an account? '}
              <button
                type="button"
                className="auth-toggle-link"
                onClick={() => setMode((m) => (m === 'login' ? 'signup' : 'login'))}
              >
                {mode === 'login' ? 'Create an account' : 'Sign in'}
              </button>
            </p>
          </form>
        </div>
      </div>
    </div>
  )
}
