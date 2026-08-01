import { useState, useRef, useEffect, type FormEvent } from 'react'
import { Eye, EyeOff, AlertCircle, KeyRound, Loader2, Clock } from 'lucide-react'
import { Button } from '@cyberfox/ui/ui/components/button'
import { useAuth } from '@/contexts/AuthContext'

export function PasswordLogin() {
  const { loginWithPassword, authError, clearError, rateLimitRemaining, cooldownUntil } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [clientCooldown, setClientCooldown] = useState(0)
  const lastAttemptRef = useRef(0)
  const usernameInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    usernameInputRef.current?.focus()
  }, [])

  const cooldownSeconds = cooldownUntil ? Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000)) : 0

  useEffect(() => {
    if (cooldownSeconds > 0) {
      const timer = setInterval(() => {
        setClientCooldown((prev) => Math.max(0, prev - 1))
      }, 1000)
      return () => clearInterval(timer)
    }
  }, [cooldownSeconds])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (loading || cooldownSeconds > 0) return

    const now = Date.now()
    if (now - lastAttemptRef.current < 2000) {
      setClientCooldown(2)
      return
    }

    if (!username.trim() || !password.trim()) {
      return
    }

    lastAttemptRef.current = now
    setLoading(true)
    clearError()
    try {
      await loginWithPassword(username.trim(), password)
    } catch {
      // Error is set in context
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="login-username"
          className="text-xs font-medium"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          Username
        </label>
        <input
          ref={usernameInputRef}
          id="login-username"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Enter your username"
          autoComplete="username"
          required
          disabled={loading}
          className="w-full rounded-lg border px-3 py-2 text-sm outline-none transition-all placeholder:text-text-tertiary disabled:opacity-50"
          style={{
            borderColor: 'color-mix(in srgb, var(--midground-base) 15%, transparent)',
            background: 'color-mix(in srgb, var(--midground-base) 3%, var(--background-base))',
            color: 'var(--midground)',
          }}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="login-password"
          className="text-xs font-medium"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          Password
        </label>
        <div className="relative">
          <input
            id="login-password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            autoComplete="current-password"
            required
            disabled={loading}
            className="w-full rounded-lg border px-3 py-2 pr-10 text-sm outline-none transition-all placeholder:text-text-tertiary disabled:opacity-50"
            style={{
              borderColor: 'color-mix(in srgb, var(--midground-base) 15%, transparent)',
              background: 'color-mix(in srgb, var(--midground-base) 3%, var(--background-base))',
              color: 'var(--midground)',
            }}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 transition-colors"
            style={{ color: 'var(--color-text-tertiary)' }}
            tabIndex={-1}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {authError && (
        <div
          className="flex items-start gap-2 rounded-lg border px-3 py-2 text-xs"
          style={{
            borderColor: 'color-mix(in srgb, var(--color-destructive) 30%, transparent)',
            background: 'color-mix(in srgb, var(--color-destructive) 8%, transparent)',
            color: 'var(--color-destructive)',
          }}
        >
          <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
          <span>{authError}</span>
        </div>
      )}

      {rateLimitRemaining >= 0 && rateLimitRemaining <= 3 && (
        <div
          className="flex items-center gap-2 rounded-lg border px-3 py-2 text-xs"
          style={{
            borderColor: 'color-mix(in srgb, var(--color-warning) 30%, transparent)',
            background: 'color-mix(in srgb, var(--color-warning) 8%, transparent)',
            color: 'var(--color-warning)',
          }}
        >
          <AlertCircle className="h-3 w-3 shrink-0" />
          <span>{rateLimitRemaining} login attempt{rateLimitRemaining !== 1 ? 's' : ''} remaining</span>
        </div>
      )}

      {cooldownSeconds > 0 && (
        <div
          className="flex items-center gap-2 rounded-lg border px-3 py-2 text-xs"
          style={{
            borderColor: 'color-mix(in srgb, var(--color-destructive) 30%, transparent)',
            background: 'color-mix(in srgb, var(--color-destructive) 8%, transparent)',
            color: 'var(--color-destructive)',
          }}
        >
          <Clock className="h-3 w-3 shrink-0" />
          <span>Too many attempts. Try again in {cooldownSeconds}s</span>
        </div>
      )}

      {clientCooldown > 0 && (
        <div
          className="flex items-center gap-2 rounded-lg border px-3 py-2 text-xs"
          style={{
            borderColor: 'color-mix(in srgb, var(--color-warning) 30%, transparent)',
            background: 'color-mix(in srgb, var(--color-warning) 8%, transparent)',
            color: 'var(--color-warning)',
          }}
        >
          <Clock className="h-3 w-3 shrink-0" />
          <span>Please wait {clientCooldown}s before trying again</span>
        </div>
      )}

      <Button
        type="submit"
        disabled={loading || cooldownSeconds > 0 || clientCooldown > 0 || !username.trim() || !password.trim()}
        className="w-full"
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <KeyRound className="h-4 w-4" />
        )}
        {loading ? 'Signing in...' : 'Sign in with Password'}
      </Button>
    </form>
  )
}
