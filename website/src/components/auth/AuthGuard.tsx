import React from 'react';
import { useAuth } from './AuthContext';
import styles from './styles.module.css';

interface AuthGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export default function AuthGuard({ children, fallback }: AuthGuardProps) {
  const { isAuthenticated, isCheckingSession } = useAuth();

  if (isCheckingSession) {
    return (
      <div className={styles.guardSkeleton} role="status" aria-label="Checking authentication">
        <div className={styles.guardShimmer} />
        <div className={styles.guardShimmer} style={{ width: '60%' }} />
      </div>
    );
  }

  if (!isAuthenticated) {
    if (fallback) return <>{fallback}</>;
    return null;
  }

  return <>{children}</>;
}
