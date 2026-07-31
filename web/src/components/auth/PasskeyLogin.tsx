import { useState, type FormEvent } from 'react'
import { Fingerprint, AlertCircle, Loader2, Shield } from 'lucide-react'
import { Button } from '@nous-research/ui/ui/components/button'
import { useAuth, PASKEY_ENABLED } from '@/contexts/AuthContext'

export function PasskeyLogin() {
  const { loginWithPasskey, authError, clearError, isCheckingSession } = useAuth()
  const [loading, setLoading] = useState(false)

  const handlePasskeyLogin = async (e: FormEvent) => {
    e.preventDefault()
    if (loading) return
    setLoading(true)
    clearError()
    try {
      await loginWithPasskey()
    } catch {
      // Error is set in context
    } finally {
      setLoading(false)
    }
  }

  if (!PASKEY_ENABLED) {
    return (
      <div
        className="flex items-center gap-2 rounded-lg border px-3 py-2 text-xs"
        style={{
          borderColor: 'color-mix(in srgb, var(--color-warning) 30%, transparent)',
          background: 'color-mix(in srgb, var(--color-warning) 8%, transparent)',
          color: 'var(--color-warning)',
        }}
      >
        <Shield className="h-3.5 w-3.5 shrink-0" />
        <span>WebAuthn not available in this browser. Use password login instead.</span>
      </div>
    )
  }

  return (
    <form onSubmit={handlePasskeyLogin} className="flex flex-col gap-3">
      <Button
        type="submit"
        disabled={loading || isCheckingSession}
        variant="primary"
        className="w-full"
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Fingerprint className="h-4 w-4" />
        )}
        {loading ? 'Authenticating...' : 'Sign in with Passkey'}
      </Button>

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
    </form>
  )
}
