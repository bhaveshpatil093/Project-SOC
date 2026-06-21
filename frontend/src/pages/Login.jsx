import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { ShieldAlert, Loader2, Lock } from 'lucide-react'

export const Login = () => {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setFieldErrors({})
    setIsSubmitting(true)

    const result = await login(username, password)
    if (result.success) {
      navigate('/dashboard')
    } else {
      setError(result.error)
      if (result.code === 'VALIDATION_ERROR' && result.fields) {
        setFieldErrors(result.fields)
      }
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg\_primary)] flex flex-col items-center justify-center relative overflow-hidden">
      {/* Background decorations */}
      <div className="absolute top-0 left-0 w-full h-full bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-[var(--bg\_primary)] via-[var(--bg\_secondary)] to-[var(--bg\_secondary)]"></div>
      <div className="absolute -top-[500px] -right-[500px] w-[1000px] h-[1000px] rounded-full bg-blue-500/5 blur-3xl"></div>

      <div className="z-10 w-full max-w-md p-8">
        <div className="flex flex-col items-center mb-8">
          <div className="w-20 h-20 bg-blue-600 rounded-2xl flex items-center justify-center mb-6 shadow-lg shadow-blue-900/20 border border-blue-500/30">
            <ShieldAlert className="w-10 h-10 text-[var(--text\_primary)]" />
          </div>
          <h1 className="text-3xl font-bold text-[var(--text\_primary)] tracking-tight">
            ISRO ISTRAC
          </h1>
          <p className="text-[var(--text\_secondary)] mt-2 font-medium">
            Advanced SOC Analytics Platform
          </p>
        </div>

        <div className="bg-[var(--bg\_primary)]/60 backdrop-blur-xl border border-[var(--border)] rounded-2xl p-8 shadow-2xl">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 flex items-start">
                <ShieldAlert className="w-5 h-5 text-red-400 mt-0.5 mr-3 flex-shrink-0" />
                <p className="text-sm text-red-200">{error}</p>
              </div>
            )}

            <div className="space-y-1">
              <label className="text-sm font-medium text-[var(--text\_secondary)] ml-1">
                Personnel ID
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className={`w-full bg-[var(--bg\_primary)]/50 border ${fieldErrors.username ? 'border-red-500' : 'border-[var(--border)]'} rounded-xl px-4 py-3 text-[var(--text\_primary)] placeholder-[var(--text\_secondary)] focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all`}
                placeholder="Enter your tracking designation"
              />
              {fieldErrors.username && (
                <p className="text-xs text-red-400 mt-1">{fieldErrors.username}</p>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-[var(--text\_secondary)] ml-1">
                Passcode
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className={`w-full bg-[var(--bg\_primary)]/50 border ${fieldErrors.password ? 'border-red-500' : 'border-[var(--border)]'} rounded-xl px-4 py-3 text-[var(--text\_primary)] placeholder-[var(--text\_secondary)] focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all`}
                placeholder="••••••••"
              />
              {fieldErrors.password && (
                <p className="text-xs text-red-400 mt-1">{fieldErrors.password}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-blue-600 hover:bg-blue-500 text-[var(--text\_primary)] font-medium rounded-xl px-4 py-3 transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-[var(--bg\_primary)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center shadow-lg shadow-blue-900/20"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  Authenticating...
                </>
              ) : (
                <>
                  <Lock className="w-4 h-4 mr-2" />
                  Sign In
                </>
              )}
            </button>
          </form>
        </div>

        <div className="mt-8 text-center">
          <p className="text-xs text-[var(--text\_secondary)] font-medium">
            RESTRICTED ACCESS • AUTHORIZED PERSONNEL ONLY
          </p>
        </div>
      </div>
    </div>
  )
}
