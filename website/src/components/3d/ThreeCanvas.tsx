import React, { Suspense } from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';
import ThreeErrorBoundary from './ErrorBoundary';

const FALLBACK_STYLE: React.CSSProperties = {
  width: '100%',
  height: '100%',
  minHeight: 'inherit',
  background: 'transparent',
};

function CanvasInner({
  children,
  cameraPos,
  ...props
}: {
  children: React.ReactNode;
  cameraPos?: [number, number, number];
  controls?: boolean;
}) {
  const { Canvas } = require('@react-three/fiber');
  return (
    <Canvas
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      camera={{ position: cameraPos ?? [0, 0, 5], fov: 60 }}
      style={{ width: '100%', height: '100%', display: 'block' }}
      onCreated={({ gl }) => {
        gl.setClearColor(0x000000, 0);
      }}
      {...props}
    >
      {children}
    </Canvas>
  );
}

function LoadingSkeleton({ label }: { label: string }) {
  return (
    <div style={FALLBACK_STYLE} role="status" aria-label={`Loading ${label} 3D scene`}>
      <div
        style={{
          width: '100%',
          height: '100%',
          minHeight: 200,
          background: 'linear-gradient(135deg, rgba(255,215,0,0.02) 0%, rgba(255,215,0,0.06) 100%)',
          borderRadius: 12,
          animation: 'pulse 2s ease-in-out infinite',
        }}
      />
    </div>
  );
}

interface ThreeCanvasProps {
  children: React.ReactNode;
  label?: string;
  cameraPos?: [number, number, number];
  controls?: boolean;
  style?: React.CSSProperties;
}

export default function ThreeCanvas({
  children,
  label = '3D scene',
  cameraPos,
  controls,
  style,
}: ThreeCanvasProps) {
  return (
    <BrowserOnly fallback={<LoadingSkeleton label={label} />}>
      {() => (
        <div
          style={{
            width: '100%',
            height: '100%',
            position: 'relative',
            ...style,
          }}
          role="img"
          aria-label={label}
        >
          <ThreeErrorBoundary>
            <Suspense fallback={<LoadingSkeleton label={label} />}>
              <CanvasInner cameraPos={cameraPos} controls={controls}>
                {children}
              </CanvasInner>
            </Suspense>
          </ThreeErrorBoundary>
        </div>
      )}
    </BrowserOnly>
  );
}
