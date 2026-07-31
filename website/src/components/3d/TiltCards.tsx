import React, { useRef, useCallback, useEffect, useState } from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';

interface TiltCardProps {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  tiltMax?: number;
  perspective?: number;
  scale?: number;
  glare?: boolean;
}

function TiltCardInner({
  children,
  className,
  style,
  tiltMax = 8,
  perspective = 1000,
  scale = 1.02,
  glare = false,
}: TiltCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [transform, setTransform] = useState('');
  const [glareStyle, setGlareStyle] = useState<React.CSSProperties>({});
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReducedMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const isTouchDevice =
    typeof window !== 'undefined' && ('ontouchstart' in window || navigator.maxTouchPoints > 0);

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (reducedMotion || isTouchDevice || !cardRef.current) return;
      const rect = cardRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = ((y - centerY) / centerY) * -tiltMax;
      const rotateY = ((x - centerX) / centerX) * tiltMax;
      setTransform(
        `perspective(${perspective}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(${scale}, ${scale}, ${scale})`,
      );
      if (glare) {
        const glareX = (x / rect.width) * 100;
        const glareY = (y / rect.height) * 100;
        setGlareStyle({
          background: `radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255,215,0,0.08) 0%, transparent 60%)`,
        });
      }
    },
    [tiltMax, perspective, scale, glare, reducedMotion, isTouchDevice],
  );

  const handlePointerLeave = useCallback(() => {
    setTransform('');
    setGlareStyle({});
  }, []);

  return (
    <div
      ref={cardRef}
      className={className}
      style={{
        ...style,
        transform,
        transition: transform ? 'none' : 'transform 0.4s ease, box-shadow 0.4s ease',
        willChange: 'transform',
        position: 'relative',
      }}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
    >
      {glare && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            pointerEvents: 'none',
            borderRadius: 'inherit',
            zIndex: 2,
            ...glareStyle,
          }}
          aria-hidden="true"
        />
      )}
      {children}
    </div>
  );
}

export default function TiltCard(props: TiltCardProps) {
  return (
    <BrowserOnly
      fallback={
        <div className={props.className} style={props.style}>
          {props.children}
        </div>
      }
    >
      {() => <TiltCardInner {...props} />}
    </BrowserOnly>
  );
}
