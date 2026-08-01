import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { Typography } from '@cyberfox/ui/ui/components/typography/index'
import { useAuth } from '@/contexts/AuthContext'
import { PasswordLogin } from '@/components/auth/PasswordLogin'
import { NeuralNetworkHero } from '@/components/3d/NeuralNetworkHero'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, isCheckingSession } = useAuth()

  useEffect(() => {
    if (isAuthenticated && !isCheckingSession) {
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/sessions'
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, isCheckingSession, navigate, location])

  if (isCheckingSession) {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: 'var(--background-base)' }}>
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-pulse rounded-full border border-current/20 bg-midground/5" />
          <div className="h-3 w-32 animate-pulse rounded bg-midground/10 text-xs text-text-tertiary text-center">
            Verifying session...
          </div>
        </div>
      </div>
    )
  }

  if (isAuthenticated) {
    return null
  }

  return (
    <div className="relative flex min-h-screen min-w-0 flex-col overflow-hidden" style={{ background: 'var(--background-base)' }}>
      {/* 3D neural network background */}
      <div className="pointer-events-none fixed inset-0 z-0 opacity-40">
        <NeuralNetworkHero className="h-full w-full" />
      </div>

      {/* Subtle gradient overlay */}
      <div
        className="pointer-events-none fixed inset-0 z-[1]"
        style={{
          background: 'linear-gradient(135deg, var(--background-base) 0%, transparent 40%, transparent 60%, var(--background-base) 100%)',
        }}
      />

      {/* Content */}
      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          {/* Brand header */}
          <div className="mb-8 text-center">
            <div className="mb-3 inline-flex items-center justify-center gap-2">
              <Sparkles className="h-5 w-5" style={{ color: 'var(--midground)' }} />
            </div>
            <Typography
              className="text-2xl font-semibold tracking-tight"
              style={{ color: 'var(--midground)' }}
            >
              Welcome back
            </Typography>
            <Typography
              className="mt-1 text-sm"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Sign in to Cyberfox Agent
            </Typography>
          </div>

          {/* Auth card */}
          <div
            className="rounded-xl border border-current/10 shadow-lg shadow-black/5 backdrop-blur-sm"
            style={{
              background: 'color-mix(in srgb, var(--background-base) 80%, transparent)',
              borderColor: 'color-mix(in srgb, var(--midground-base) 10%, transparent)',
            }}
          >
            {/* Auth form */}
            <div className="p-5">
              <PasswordLogin />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div
          className="fixed bottom-4 left-1/2 -translate-x-1/2 text-[0.6rem] tracking-widest"
          style={{ color: 'var(--color-text-tertiary)' }}
        >
          Cyberfox Agent
        </div>
      </div>
    </div>
  )
}
