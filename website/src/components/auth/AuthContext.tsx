import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';

interface AuthUser {
  id: string;
  name: string;
  email: string;
  roles: string[];
}

interface AuthState {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isCheckingSession: boolean;
  authError: string | null;
  rateLimitRemaining: number;
  cooldownUntil: number | null;
}

interface AuthActions {
  loginWithPasskey: () => Promise<void>;
  loginWithPassword: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
  clearError: () => void;
}

type AuthContextValue = AuthState & AuthActions;

const AuthContext = createContext<AuthContextValue | null>(null);

function getApiBase(): string {
  return '';
}

function AuthProviderInner({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [rateLimitRemaining, setRateLimitRemaining] = useState(-1);
  const [cooldownUntil, setCooldownUntil] = useState<number | null>(null);
  const cooldownTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearError = useCallback(() => setAuthError(null), []);

  const refreshSession = useCallback(async () => {
    try {
      const res = await fetch(`${getApiBase()}/api/auth/session`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data.user);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setIsCheckingSession(false);
    }
  }, []);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  useEffect(() => {
    if (cooldownUntil && cooldownUntil > Date.now()) {
      cooldownTimerRef.current = setInterval(() => {
        if (Date.now() >= (cooldownUntil ?? 0)) {
          setCooldownUntil(null);
          setRateLimitRemaining(-1);
          if (cooldownTimerRef.current) clearInterval(cooldownTimerRef.current);
        }
      }, 1000);
    }
    return () => {
      if (cooldownTimerRef.current) clearInterval(cooldownTimerRef.current);
    };
  }, [cooldownUntil]);

  const updateRateLimit = useCallback((res: Response) => {
    const remaining = res.headers.get('X-RateLimit-Remaining');
    if (remaining !== null) {
      setRateLimitRemaining(parseInt(remaining, 10));
    }
    const retryAfter = res.headers.get('Retry-After');
    if (retryAfter !== null) {
      const seconds = parseInt(retryAfter, 10);
      setCooldownUntil(Date.now() + seconds * 1000);
    }
  }, []);

  const loginWithPasskey = useCallback(async () => {
    setAuthError(null);
    try {
      const { startAuthentication } = await import('@simplewebauthn/browser');

      const optsRes = await fetch(`${getApiBase()}/api/auth/passkey/options`, {
        credentials: 'include',
      });
      if (!optsRes.ok) throw new Error('Failed to get authentication options');
      const opts = await optsRes.json();

      const authResp = await startAuthentication({ optionsJSON: opts.publicKey });

      const verifyRes = await fetch(`${getApiBase()}/api/auth/passkey/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(authResp),
      });

      if (!verifyRes.ok) {
        updateRateLimit(verifyRes);
        const err = await verifyRes.json().catch(() => ({}));
        throw new Error(err.message || 'Passkey verification failed');
      }

      const data = await verifyRes.json();
      setUser(data.user);
      setRateLimitRemaining(-1);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Authentication failed';
      setAuthError(message);
      throw err;
    }
  }, [updateRateLimit]);

  const loginWithPassword = useCallback(
    async (email: string, password: string) => {
      setAuthError(null);
      try {
        const csrfRes = await fetch(`${getApiBase()}/api/auth/csrf`, {
          credentials: 'include',
        });
        if (!csrfRes.ok) throw new Error('Could not fetch security token');
        const { csrfToken } = await csrfRes.json();

        const res = await fetch(`${getApiBase()}/api/auth/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken,
          },
          credentials: 'include',
          body: JSON.stringify({ email, password }),
        });

        if (!res.ok) {
          updateRateLimit(res);
          const err = await res.json().catch(() => ({}));
          if (res.status === 429) {
            throw new Error(err.message || 'Too many attempts. Please wait.');
          }
          throw new Error(err.message || 'Invalid credentials');
        }

        const data = await res.json();
        setUser(data.user);
        setAuthError(null);
        setRateLimitRemaining(-1);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Login failed';
        setAuthError(message);
        throw err;
      }
    },
    [updateRateLimit],
  );

  const logout = useCallback(async () => {
    try {
      await fetch(`${getApiBase()}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch {
      // Even if the server call fails, clear local state
    }
    setUser(null);
    setAuthError(null);
    setRateLimitRemaining(-1);
    setCooldownUntil(null);
  }, []);

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
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

interface AuthProviderProps {
  children: React.ReactNode;
}

export default function AuthProvider({ children }: AuthProviderProps) {
  return (
    <BrowserOnly fallback={<>{children}</>}>
      {() => <AuthProviderInner>{children}</AuthProviderInner>}
    </BrowserOnly>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}
