import React, { useState, lazy, Suspense } from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';
import PasskeyLogin from './PasskeyLogin';
import PasswordFallback from './PasswordFallback';
import SessionStatus from './SessionStatus';
import styles from './styles.module.css';

const ParticleDust = lazy(() => import('@site/src/components/3d/ParticleDust'));

function ThreeBackground() {
  return (
    <BrowserOnly>
      {() => (
        <Suspense fallback={null}>
          <div className={styles.loginCanvasWrap}>
            <ParticleDust mouseFactor={0.03} />
          </div>
        </Suspense>
      )}
    </BrowserOnly>
  );
}

function LoginForm() {
  const [usePassword, setUsePassword] = useState(false);

  return (
    <div className={styles.loginCard}>
      <div className={styles.loginHeader}>
        <div className={styles.loginLogo} aria-hidden="true">
          <svg
            width="40"
            height="40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#FFD700"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        </div>
        <h1 className={styles.loginGreeting}>Secure Terminal Gateway</h1>
        <p className={styles.loginSub}>Cyberfox Agent Authentication</p>
      </div>

      <div className={styles.loginDivider} aria-hidden="true">
        <span className={styles.dividerLine} />
        <span className={styles.dividerIcon}>✦</span>
        <span className={styles.dividerLine} />
      </div>

      {usePassword ? (
        <PasswordFallback onBackToPasskey={() => setUsePassword(false)} />
      ) : (
        <PasskeyLogin onPasswordFallback={() => setUsePassword(true)} />
      )}

      <div className={styles.loginFooter}>
        <SessionStatus />
        <p className={styles.loginFooterText}>
          Protected by WebAuthn &bull; HttpOnly Secure Cookies
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <div className={styles.loginPage}>
      <ThreeBackground />
      <div className={styles.loginOverlay}>
        <LoginForm />
      </div>
    </div>
  );
}
