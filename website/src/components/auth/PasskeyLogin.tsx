import React, { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import styles from './styles.module.css';

interface PasskeyLoginProps {
  onPasswordFallback: () => void;
}

export default function PasskeyLogin({ onPasswordFallback }: PasskeyLoginProps) {
  const { loginWithPasskey, authError, clearError } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [isSupported, setIsSupported] = useState(true);

  useEffect(() => {
    if (typeof window !== 'undefined' && !window.PublicKeyCredential) {
      setIsSupported(false);
    }
  }, []);

  const handlePasskeyLogin = async () => {
    clearError();
    setIsLoading(true);
    try {
      await loginWithPasskey();
    } catch {
      // Error state is set in context
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.authSection}>
      <div className={styles.passkeyIllustration} aria-hidden="true">
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#FFD700"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 2a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />
          <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
          <path d="M15 13l2 2 4-4" />
        </svg>
      </div>
      <h2 className={styles.authTitle}>Passkey Authentication</h2>
      <p className={styles.authDescription}>
        Use your fingerprint, face, or security key to sign in securely.
      </p>

      {!isSupported ? (
        <div className={styles.warningBanner}>
          Your browser does not support passkeys. Please use password login.
        </div>
      ) : (
        <button
          type="button"
          className={styles.passkeyButton}
          onClick={handlePasskeyLogin}
          disabled={isLoading}
          aria-label="Authenticate with passkey"
        >
          {isLoading ? (
            <span className={styles.spinner} aria-hidden="true" />
          ) : (
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          )}
          <span>{isLoading ? 'Authenticating...' : 'Authenticate with Passkey'}</span>
        </button>
      )}

      {authError && (
        <div className={styles.errorBanner} role="alert">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{authError}</span>
        </div>
      )}

      <button type="button" className={styles.textButton} onClick={onPasswordFallback}>
        Sign in with password instead
      </button>
    </div>
  );
}
