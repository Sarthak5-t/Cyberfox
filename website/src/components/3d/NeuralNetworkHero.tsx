import React, { useMemo, useRef, useState, useCallback } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { Line } from '@react-three/drei';
import * as THREE from 'three';
import ThreeCanvas from './ThreeCanvas';

const NODE_COUNT = 80;
const EDGE_DISTANCE = 2.5;
const GOLD = '#FFD700';
const GOLD_DIM = 'rgba(255, 215, 0, 0.15)';

interface Node {
  position: THREE.Vector3;
  velocity: THREE.Vector3;
  pulsePhase: number;
}

function generateNodes(): Node[] {
  const nodes: Node[] = [];
  for (let i = 0; i < NODE_COUNT; i++) {
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const r = 1.5 + Math.random() * 1.5;
    nodes.push({
      position: new THREE.Vector3(
        r * Math.sin(phi) * Math.cos(theta),
        r * Math.sin(phi) * Math.sin(theta),
        r * Math.cos(phi),
      ),
      velocity: new THREE.Vector3(
        (Math.random() - 0.5) * 0.002,
        (Math.random() - 0.5) * 0.002,
        (Math.random() - 0.5) * 0.002,
      ),
      pulsePhase: Math.random() * Math.PI * 2,
    });
  }
  return nodes;
}

function computeEdges(nodes: Node[]): [number, number][] {
  const edges: [number, number][] = [];
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      if (nodes[i].position.distanceTo(nodes[j].position) < EDGE_DISTANCE) {
        edges.push([i, j]);
      }
    }
  }
  return edges;
}

function NetworkGraph() {
  const groupRef = useRef<THREE.Group>(null);
  const nodes = useRef<Node[]>(generateNodes());
  const edges = useMemo(() => computeEdges(nodes.current), []);
  const [hoveredNode, setHoveredNode] = useState<number | null>(null);

  const raycaster = useMemo(() => new THREE.Raycaster(), []);
  const pointer = useMemo(() => new THREE.Vector2(), []);
  const { camera, gl } = useThree();

  const handlePointerMove = useCallback(
    (e: { clientX: number; clientY: number }) => {
      pointer.x = (e.clientX / gl.domElement.clientWidth) * 2 - 1;
      pointer.y = -(e.clientY / gl.domElement.clientHeight) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const intersects = raycaster.intersectObjects(
        groupRef.current?.children.filter((c) => c.userData.isNode) ?? [],
      );
      setHoveredNode(
        intersects.length > 0 ? (intersects[0].object.userData.index as number) : null,
      );
    },
    [pointer, raycaster, camera, gl],
  );

  React.useEffect(() => {
    gl.domElement.addEventListener('pointermove', handlePointerMove);
    return () => gl.domElement.removeEventListener('pointermove', handlePointerMove);
  }, [gl, handlePointerMove]);

  useFrame((state, delta) => {
    if (!groupRef.current) return;

    const time = state.clock.elapsedTime;
    groupRef.current.rotation.y += delta * 0.08;
    groupRef.current.rotation.x = Math.sin(time * 0.02) * 0.05;

    for (let i = 0; i < nodes.current.length; i++) {
      const n = nodes.current[i];
      n.position.x += n.velocity.x * delta * 30;
      n.position.y += n.velocity.y * delta * 30;
      n.position.z += n.velocity.z * delta * 30;
      if (n.position.length() > 3) n.velocity.multiplyScalar(-1);
    }
  });

  const sphereGeom = useMemo(() => new THREE.SphereGeometry(0.08, 16, 16), []);

  return (
    <group ref={groupRef}>
      {edges.map(([i, j], idx) => {
        const n1 = nodes.current[i];
        const n2 = nodes.current[j];
        const isHovered = hoveredNode === i || hoveredNode === j;
        return (
          <Line
            key={`edge-${idx}`}
            points={[n1.position, n2.position]}
            color={isHovered ? GOLD : GOLD_DIM}
            lineWidth={isHovered ? 2 : 0.5}
            transparent
            opacity={isHovered ? 0.8 : 0.2}
          />
        );
      })}
      {nodes.current.map((n, i) => {
        const isHovered = hoveredNode === i;
        return (
          <mesh
            key={`node-${i}`}
            position={n.position}
            geometry={sphereGeom}
            userData={{ isNode: true, index: i }}
          >
            <meshBasicMaterial
              color={isHovered ? '#ffffff' : GOLD}
              transparent
              opacity={isHovered ? 1 : 0.6}
            />
          </mesh>
        );
      })}
      <ambientLight intensity={0.5} />
      <pointLight position={[5, 5, 5]} intensity={0.8} color={GOLD} />
    </group>
  );
}

const HERO_STYLES: Record<string, React.CSSProperties> = {
  wrapper: {
    position: 'relative',
    width: '100%',
    height: 400,
    overflow: 'hidden',
    borderRadius: 16,
    marginBottom: '2rem',
  },
};

export default function NeuralNetworkHero() {
  return (
    <div style={HERO_STYLES.wrapper}>
      <ThreeCanvas label="Interactive neural network visualization" cameraPos={[0, 0, 5]}>
        <NetworkGraph />
      </ThreeCanvas>
    </div>
  );
}
