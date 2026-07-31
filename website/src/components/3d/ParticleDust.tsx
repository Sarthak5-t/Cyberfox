import React, { useMemo, useRef, useCallback } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

const PARTICLE_COUNT = 300;
const GOLD = '#FFD700';
const SPREAD = 8;

interface ParticleDustProps {
  mouseFactor?: number;
}

function Particles({ mouseFactor = 0.02 }: ParticleDustProps) {
  const pointsRef = useRef<THREE.Points>(null);
  const { viewport } = useThree();
  const mouse = useRef({ x: 0, y: 0 });

  const handlePointerMove = useCallback((e: { clientX: number; clientY: number }) => {
    mouse.current.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.current.y = -(e.clientY / window.innerHeight) * 2 + 1;
  }, []);

  React.useEffect(() => {
    window.addEventListener('pointermove', handlePointerMove);
    return () => window.removeEventListener('pointermove', handlePointerMove);
  }, [handlePointerMove]);

  const [positions, velocities] = useMemo(() => {
    const pos = new Float32Array(PARTICLE_COUNT * 3);
    const vel = new Float32Array(PARTICLE_COUNT * 3);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const i3 = i * 3;
      pos[i3] = (Math.random() - 0.5) * SPREAD * viewport.width;
      pos[i3 + 1] = (Math.random() - 0.5) * SPREAD * viewport.height;
      pos[i3 + 2] = (Math.random() - 0.5) * 5;
      vel[i3] = (Math.random() - 0.5) * 0.005;
      vel[i3 + 1] = (Math.random() - 0.5) * 0.005;
      vel[i3 + 2] = (Math.random() - 0.5) * 0.005;
    }
    return [pos, vel];
  }, [viewport]);

  const sizes = useMemo(() => {
    const s = new Float32Array(PARTICLE_COUNT);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      s[i] = Math.random() * 3 + 1;
    }
    return s;
  }, []);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
    return geo;
  }, [positions, sizes]);

  useFrame((_, delta) => {
    if (!pointsRef.current) return;
    const pos = pointsRef.current.geometry.attributes.position.array as Float32Array;
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const i3 = i * 3;
      pos[i3] += velocities[i3] * delta * 30 + mouse.current.x * mouseFactor * delta * 15;
      pos[i3 + 1] += velocities[i3 + 1] * delta * 30 + mouse.current.y * mouseFactor * delta * 15;
      pos[i3 + 2] += velocities[i3 + 2] * delta * 30;

      if (Math.abs(pos[i3]) > (SPREAD / 2) * viewport.width) velocities[i3] *= -1;
      if (Math.abs(pos[i3 + 1]) > (SPREAD / 2) * viewport.height) velocities[i3 + 1] *= -1;
      if (Math.abs(pos[i3 + 2]) > 2.5) velocities[i3 + 2] *= -1;
    }
    pointsRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={pointsRef} geometry={geometry} frustumCulled={false}>
      <pointsMaterial
        size={0.04}
        color={GOLD}
        transparent
        opacity={0.4}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </points>
  );
}

export default function ParticleDust(props: ParticleDustProps) {
  return <Particles {...props} />;
}
