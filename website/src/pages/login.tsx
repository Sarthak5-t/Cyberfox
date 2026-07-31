import React from 'react';
import Layout from '@theme/Layout';
import BrowserOnly from '@docusaurus/BrowserOnly';

function LoginPageContent() {
  const LoginPage = React.lazy(() => import('@site/src/components/auth/LoginPage'));

  return (
    <Layout
      title="Login"
      description="Secure Terminal Gateway — Cyberfox Agent Authentication"
      noFooter
    >
      <React.Suspense
        fallback={
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '100vh',
              background: '#07070d',
              color: '#FFD700',
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: '0.85rem',
            }}
          >
            Initializing secure connection...
          </div>
        }
      >
        <LoginPage />
      </React.Suspense>
    </Layout>
  );
}

export default function Login() {
  return (
    <BrowserOnly
      fallback={
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            background: '#07070d',
            color: '#FFD700',
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          Secure Terminal Gateway
        </div>
      }
    >
      {() => <LoginPageContent />}
    </BrowserOnly>
  );
}
