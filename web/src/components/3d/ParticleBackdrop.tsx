import { useRef, useMemo, useEffect, type RefObject } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'

const PARTICLE_COUNT = 600
const SPREAD = 15
const GOLD = '#FFD700'

interface ParticleMesh extends THREE.Points {
  userData: {
    velocities: Float32Array
  }
}

function Particles({ mouse }: { mouse: RefObject<[number, number]> }) {
  const mesh = useRef<ParticleMesh>(null)
  const { viewport } = useThree()

  const { positions, velocities } = useMemo(() => {
    const pos = new Float32Array(PARTICLE_COUNT * 3)
    const vel = new Float32Array(PARTICLE_COUNT * 3)
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      pos[i * 3] = (Math.random() - 0.5) * SPREAD * viewport.width
      pos[i * 3 + 1] = (Math.random() - 0.5) * SPREAD * viewport.height
      pos[i * 3 + 2] = (Math.random() - 0.5) * 8
      vel[i * 3] = (Math.random() - 0.5) * 0.005
      vel[i * 3 + 1] = (Math.random() - 0.5) * 0.005
      vel[i * 3 + 2] = (Math.random() - 0.5) * 0.005
    }
    return { positions: pos, velocities: vel }
  }, [viewport])

  useEffect(() => {
    if (mesh.current) {
      mesh.current.userData.velocities = velocities
    }
  }, [velocities])

  useFrame(({ clock }) => {
    if (!mesh.current) return
    const pos = mesh.current.geometry.attributes.position.array as Float32Array
    const vel = mesh.current.userData.velocities
    const time = clock.getElapsedTime()
    const mx = mouse.current?.[0] ?? 0
    const my = mouse.current?.[1] ?? 0

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      pos[i * 3] += vel[i * 3] + Math.sin(time + i) * 0.001 + mx * 0.002
      pos[i * 3 + 1] += vel[i * 3 + 1] + Math.cos(time + i) * 0.001 + my * 0.002
      pos[i * 3 + 2] += vel[i * 3 + 2] + Math.sin(time * 0.5 + i * 0.1) * 0.001

      if (Math.abs(pos[i * 3]) > SPREAD * viewport.width / 2) pos[i * 3] *= -0.9
      if (Math.abs(pos[i * 3 + 1]) > SPREAD * viewport.height / 2) pos[i * 3 + 1] *= -0.9
      if (Math.abs(pos[i * 3 + 2]) > 4) pos[i * 3 + 2] *= -0.9
    }
    mesh.current.geometry.attributes.position.needsUpdate = true
  })

  return (
    <points ref={mesh}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.04}
        color={GOLD}
        transparent
        opacity={0.5}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  )
}

export function ParticleBackdrop() {
  const mouse = useRef<[number, number]>([0, 0])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      mouse.current = [
        (e.clientX / window.innerWidth - 0.5) * 2,
        -(e.clientY / window.innerHeight - 0.5) * 2,
      ]
    }
    window.addEventListener('mousemove', handler, { passive: true })
    return () => window.removeEventListener('mousemove', handler)
  }, [])

  return (
    <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }}>
      <Canvas
        camera={{ position: [0, 0, 6], fov: 60 }}
        dpr={[1, 1.5]}
        gl={{ antialias: false, alpha: true }}
        style={{ background: 'transparent' }}
        onCreated={({ gl }) => {
          gl.setClearColor(0x000000, 0)
        }}
      >
        <Particles mouse={mouse} />
      </Canvas>
    </div>
  )
}
