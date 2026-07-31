import { useRef, useMemo, useEffect, useState } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

const NODE_COUNT = 80
const GOLD = '#FFD700'
const PULSE_SPEED = 0.3

interface Node {
  position: THREE.Vector3
  velocity: THREE.Vector3
  phase: number
}

function Network({ mouse }: { mouse: React.RefObject<[number, number]> }) {
  const groupRef = useRef<THREE.Group>(null)
  const edgeRef = useRef<THREE.LineSegments>(null)

  const nodes = useMemo<Node[]>(() => {
    const arr: Node[] = []
    for (let i = 0; i < NODE_COUNT; i++) {
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const r = 2.5 + Math.random() * 1.5
      arr.push({
        position: new THREE.Vector3(
          r * Math.sin(phi) * Math.cos(theta),
          r * Math.sin(phi) * Math.sin(theta),
          r * Math.cos(phi),
        ),
        velocity: new THREE.Vector3(
          (Math.random() - 0.5) * 0.008,
          (Math.random() - 0.5) * 0.008,
          (Math.random() - 0.5) * 0.008,
        ),
        phase: Math.random() * Math.PI * 2,
      })
    }
    return arr
  }, [])

  const nodePositions = useMemo(() => new Float32Array(NODE_COUNT * 3), [])
  const nodeColors = useMemo(() => new Float32Array(NODE_COUNT * 3), [])
  const edgePairs: [number, number][] = useMemo(() => {
    const pairs: [number, number][] = []
    for (let i = 0; i < NODE_COUNT; i++) {
      for (let j = i + 1; j < NODE_COUNT; j++) {
        if (Math.random() < 0.08) pairs.push([i, j])
      }
    }
    return pairs
  }, [])

  const edgePositions = useMemo(() => new Float32Array(edgePairs.length * 6), [edgePairs])

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    const mx = mouse.current?.[0] ?? 0
    const my = mouse.current?.[1] ?? 0

    for (let i = 0; i < NODE_COUNT; i++) {
      const n = nodes[i]
      n.position.x += n.velocity.x + Math.sin(t * 0.3 + n.phase) * 0.002 + mx * 0.003
      n.position.y += n.velocity.y + Math.cos(t * 0.4 + n.phase) * 0.002 + my * 0.003
      n.position.z += n.velocity.z + Math.sin(t * 0.2 + n.phase * 1.3) * 0.002

      const len = n.position.length()
      if (len > 4.5 || len < 1.5) n.position.multiplyScalar(0.99)

      nodePositions[i * 3] = n.position.x
      nodePositions[i * 3 + 1] = n.position.y
      nodePositions[i * 3 + 2] = n.position.z

      const pulse = 0.4 + 0.6 * (0.5 + 0.5 * Math.sin(t * PULSE_SPEED + n.phase))
      nodeColors[i * 3] = pulse
      nodeColors[i * 3 + 1] = 0.85 * pulse
      nodeColors[i * 3 + 2] = 0.15 * pulse
    }

    for (let e = 0; e < edgePairs.length; e++) {
      const [i, j] = edgePairs[e]
      const a = nodes[i].position
      const b = nodes[j].position
      edgePositions[e * 6] = a.x
      edgePositions[e * 6 + 1] = a.y
      edgePositions[e * 6 + 2] = a.z
      edgePositions[e * 6 + 3] = b.x
      edgePositions[e * 6 + 4] = b.y
      edgePositions[e * 6 + 5] = b.z
    }

    if (groupRef.current) {
      const geo = (groupRef.current.children[0] as THREE.Points).geometry
      geo.attributes.position.needsUpdate = true
      geo.attributes.color.needsUpdate = true
    }
    if (edgeRef.current) {
      edgeRef.current.geometry.attributes.position.needsUpdate = true
    }
  })

  return (
    <group ref={groupRef}>
      <points>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[nodePositions, 3]}
          />
          <bufferAttribute
            attach="attributes-color"
            args={[nodeColors, 3]}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.12}
          vertexColors
          transparent
          opacity={0.9}
          sizeAttenuation
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
      <lineSegments ref={edgeRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[edgePositions, 3]}
          />
        </bufferGeometry>
        <lineBasicMaterial color={GOLD} transparent opacity={0.15} depthWrite={false} />
      </lineSegments>
    </group>
  )
}

interface NeuralNetworkHeroProps {
  className?: string
}

export function NeuralNetworkHero({ className }: NeuralNetworkHeroProps) {
  const mouse = useRef<[number, number]>([0, 0])
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      mouse.current = [
        (e.clientX / window.innerWidth - 0.5) * 2,
        -(e.clientY / window.innerHeight - 0.5) * 2,
      ]
    }
    window.addEventListener('mousemove', handler, { passive: true })
    setReady(true)
    return () => window.removeEventListener('mousemove', handler)
  }, [])

  if (!ready) return null

  return (
    <div className={className} aria-hidden>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 50 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: 'transparent' }}
        onCreated={({ gl }) => gl.setClearColor(0x000000, 0)}
      >
        <Network mouse={mouse} />
      </Canvas>
    </div>
  )
}
