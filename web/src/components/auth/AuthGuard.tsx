import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

const AUTH_REQUIRED =
  typeof window !== 'undefined' &&
  window.__CYBERFOX_AUTH_REQUIRED__ === true

interface AuthGuardProps {
  children: ReactNode
  fallback?: ReactNode
}

function ShimmerSkeleton() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#07070d]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-pulse rounded-full border border-[#FFD700]/20 bg-[#FFD700]/5" />
        <div className="h-3 w-32 animate-pulse rounded bg-[#FFD700]/10" />
      </div>
    </div>
  )
}

export function AuthGuard({ children, fallback }: AuthGuardProps) {
  const { isAuthenticated, isCheckingSession } = useAuth()
  const location = useLocation()

  if (!AUTH_REQUIRED) {
    return <>{children}</>
  }

  if (isCheckingSession) {
    return fallback ?? <ShimmerSkeleton />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}
