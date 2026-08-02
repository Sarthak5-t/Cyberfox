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
  loginWithPassword: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshSession: () => Promise<void>
  clearError: () => void
}

type AuthContextValue = AuthState & AuthActions

const AuthContext = createContext<AuthContextValue | null>(null)

const API_BASE = ''

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

  const loginWithPassword = useCallback(
    async (username: string, password: string) => {
      setAuthError(null)
      try {
        const res = await fetch(`${API_BASE}/auth/password-login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ provider: 'basic', username, password }),
        })

        if (!res.ok) {
          handleRateLimitHeaders(res)
          const err = await res.json().catch(() => ({}))
          if (res.status === 429) {
            throw new Error(err.message || 'Too many attempts. Please wait.')
          }
          throw new Error(err.message || 'Invalid credentials')
        }

        await refreshSession()
        setAuthError(null)
        setRateLimitRemaining(-1)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Login failed'
        setAuthError(message)
        throw err
      }
    },
    [handleRateLimitHeaders, refreshSession],
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
