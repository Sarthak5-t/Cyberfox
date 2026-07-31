import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react'

interface AuthUser {
  user_id: string
  email: string
  display_name: string
  org_id: string
  provider: string
  expires_at: number
}

interface AuthState {
  user: AuthUser | null
  isAuthenticated: boolean
  isCheckingSession: boolean
  authError: string | null
  rateLimitRemaining: number
  cooldownUntil: number | null
}

interface AuthActions {
  loginWithPasskey: () => Promise<void>
  loginWithPassword: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshSession: () => Promise<void>
  clearError: () => void
}

type AuthContextValue = AuthState & AuthActions

const AuthContext = createContext<AuthContextValue | null>(null)

const API_BASE = ''

const PASKEY_ENABLED =
  typeof window !== 'undefined' &&
  window.PublicKeyCredential !== undefined

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isCheckingSession, setIsCheckingSession] = useState(true)
  const [authError, setAuthError] = useState<string | null>(null)
  const [rateLimitRemaining, setRateLimitRemaining] = useState(-1)
  const [cooldownUntil, setCooldownUntil] = useState<number | null>(null)
  const cooldownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const clearError = useCallback(() => setAuthError(null), [])

  const handleRateLimitHeaders = useCallback((res: Response) => {
    const remaining = res.headers.get('X-RateLimit-Remaining')
    if (remaining !== null) {
      setRateLimitRemaining(parseInt(remaining, 10))
    }
    const retryAfter = res.headers.get('Retry-After')
    if (retryAfter !== null) {
      const seconds = parseInt(retryAfter, 10)
      setCooldownUntil(Date.now() + seconds * 1000)
    }
  }, [])

  const refreshSession = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/me`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setUser(data)
      } else {
        setUser(null)
      }
    } catch {
      setUser(null)
    } finally {
      setIsCheckingSession(false)
    }
  }, [])

  useEffect(() => {
    refreshSession()
  }, [refreshSession])

  useEffect(() => {
    if (cooldownUntil && cooldownUntil > Date.now()) {
      cooldownTimerRef.current = setInterval(() => {
        if (Date.now() >= (cooldownUntil ?? 0)) {
          setCooldownUntil(null)
          setRateLimitRemaining(-1)
          if (cooldownTimerRef.current) clearInterval(cooldownTimerRef.current)
        }
      }, 1000)
    }
    return () => {
      if (cooldownTimerRef.current) clearInterval(cooldownTimerRef.current)
    }
  }, [cooldownUntil])

  const loginWithPasskey = useCallback(async () => {
    setAuthError(null)
    try {
      if (!PASKEY_ENABLED) {
        throw new Error('WebAuthn is not supported in this browser')
      }

      const { startAuthentication } = await import('@simplewebauthn/browser')

      const optsRes = await fetch(`${API_BASE}/api/auth/passkey/start`, {
        credentials: 'include',
      })
      if (!optsRes.ok) {
        if (optsRes.status === 501 || optsRes.status === 404) {
          throw new Error('Passkey authentication is not configured on this server')
        }
        throw new Error('Failed to start passkey authentication')
      }
      const opts = await optsRes.json()

      const authResp = await startAuthentication({ optionsJSON: opts.publicKey })

      const verifyRes = await fetch(`${API_BASE}/api/auth/passkey/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(authResp),
      })

      if (!verifyRes.ok) {
        handleRateLimitHeaders(verifyRes)
        const err = await verifyRes.json().catch(() => ({}))
        throw new Error(err.message || 'Passkey verification failed')
      }

      const data = await verifyRes.json()
      setUser(data.user)
      setRateLimitRemaining(-1)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Authentication failed'
      setAuthError(message)
      throw err
    }
  }, [handleRateLimitHeaders])

  const loginWithPassword = useCallback(
    async (email: string, password: string) => {
      setAuthError(null)
      try {
        const csrfRes = await fetch(`${API_BASE}/api/auth/csrf`, {
          credentials: 'include',
        })
        if (!csrfRes.ok) throw new Error('Could not fetch security token')
        const { csrfToken } = await csrfRes.json()

        const res = await fetch(`${API_BASE}/api/auth/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken,
          },
          credentials: 'include',
          body: JSON.stringify({ email, password }),
        })

        if (!res.ok) {
          handleRateLimitHeaders(res)
          const err = await res.json().catch(() => ({}))
          if (res.status === 429) {
            throw new Error(err.message || 'Too many attempts. Please wait.')
          }
          throw new Error(err.message || 'Invalid credentials')
        }

        const data = await res.json()
        setUser(data.user)
        setAuthError(null)
        setRateLimitRemaining(-1)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Login failed'
        setAuthError(message)
        throw err
      }
    },
    [handleRateLimitHeaders],
  )

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      })
    } catch {
      // Even if the server call fails, clear local state
    }
    setUser(null)
    setAuthError(null)
    setRateLimitRemaining(-1)
    setCooldownUntil(null)
  }, [])

  const value: AuthContextValue = {
    user,
    isAuthenticated: user !== null,
    isCheckingSession,
    authError,
    rateLimitRemaining,
    cooldownUntil,
    loginWithPasskey,
    loginWithPassword,
    logout,
    refreshSession,
    clearError,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}

export { PASKEY_ENABLED }
