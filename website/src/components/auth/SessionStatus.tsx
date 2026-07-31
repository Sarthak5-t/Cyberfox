import React from 'react';
import { useAuth } from './AuthContext';
import styles from './styles.module.css';

export default function SessionStatus() {
  const { user, isAuthenticated, isCheckingSession, logout } = useAuth();

  if (isCheckingSession) {
    return (
      <div className={styles.sessionPill} aria-label="Checking session">
        <span className={styles.sessionDotChecking} aria-hidden="true" />
        <span className={styles.sessionText}>Checking...</span>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return null;
  }

  return (
    <div className={styles.sessionPill}>
      <span className={styles.sessionDotActive} aria-hidden="true" />
      <span className={styles.sessionText}>{user.name}</span>
      <button
        type="button"
        className={styles.sessionLogout}
        onClick={logout}
        aria-label="Sign out"
        title="Sign out"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
      </button>
    </div>
  );
}
