import React, { useState, useEffect } from 'react';
import styles from './styles.module.css';

interface RateLimitBannerProps {
  cooldownUntil: number;
}

export default function RateLimitBanner({ cooldownUntil }: RateLimitBannerProps) {
  const [remaining, setRemaining] = useState('');

  useEffect(() => {
    const tick = () => {
      const diff = Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000));
      const mins = Math.floor(diff / 60);
      const secs = diff % 60;
      setRemaining(mins > 0 ? `${mins}m ${secs}s` : `${secs}s`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [cooldownUntil]);

  return (
    <div className={styles.rateLimitBanner} role="alert">
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
        <polyline points="12 6 12 12 16 14" />
      </svg>
      <span>
        Too many attempts. Try again in <strong>{remaining}</strong>.
      </span>
    </div>
  );
}
