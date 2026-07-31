import React, { useState, useRef, useCallback } from 'react';
import { useAuth } from './AuthContext';
import RateLimitBanner from './RateLimitBanner';
import styles from './styles.module.css';

interface PasswordFallbackProps {
  onBackToPasskey: () => void;
}

export default function PasswordFallback({ onBackToPasskey }: PasswordFallbackProps) {
  const { loginWithPassword, authError, cooldownUntil, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const lastAttemptRef = useRef(0);
  const emailRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      clearError();

      const cooldownActive = cooldownUntil && cooldownUntil > Date.now();
      if (cooldownActive) return;

      const timeSinceLastAttempt = Date.now() - lastAttemptRef.current;
      if (timeSinceLastAttempt < 2000) {
        return;
      }

      if (!email.trim() || !password.trim()) {
        return;
      }

      lastAttemptRef.current = Date.now();
      setIsLoading(true);
      try {
        await loginWithPassword(email.trim(), password);
      } catch {
        // Error is set in context
      } finally {
        setIsLoading(false);
      }
    },
    [email, password, loginWithPassword, clearError, cooldownUntil],
  );

  const isCooldown = cooldownUntil !== null && cooldownUntil > Date.now();

  return (
    <div className={styles.authSection}>
      {isCooldown && cooldownUntil && <RateLimitBanner cooldownUntil={cooldownUntil} />}

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
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      </div>
      <h2 className={styles.authTitle}>Password Login</h2>
      <p className={styles.authDescription}>Enter your credentials to access the terminal.</p>

      <form className={styles.form} onSubmit={handleSubmit} noValidate>
        <div className={styles.fieldGroup}>
          <label htmlFor="auth-email" className={styles.label}>
            Email
          </label>
          <input
            ref={emailRef}
            id="auth-email"
            type="email"
            className={styles.input}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="agent@cyberfox.dev"
            autoComplete="username"
            autoFocus
            disabled={isCooldown}
            required
            aria-describedby={authError ? 'auth-error' : undefined}
          />
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="auth-password" className={styles.label}>
            Password
          </label>
          <input
            id="auth-password"
            type="password"
            className={styles.input}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;"
            autoComplete="current-password"
            disabled={isCooldown}
            required
            aria-describedby={authError ? 'auth-error' : undefined}
          />
        </div>

        {authError && (
          <div id="auth-error" className={styles.errorBanner} role="alert">
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

        <button
          type="submit"
          className={styles.submitButton}
          disabled={isLoading || isCooldown || !email.trim() || !password.trim()}
        >
          {isLoading ? (
            <>
              <span className={styles.spinner} aria-hidden="true" />
              <span>Authenticating...</span>
            </>
          ) : (
            'Sign In'
          )}
        </button>
      </form>

      <button type="button" className={styles.textButton} onClick={onBackToPasskey}>
        Use passkey instead
      </button>
    </div>
  );
}
