import { useRef, useState, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera, Text } from '@react-three/drei'
import { X } from 'lucide-react'
import * as THREE from 'three'
import './CameraMap3D.css'

// Convertir cuaternión a ángulos Euler
const quaternionToEuler = (qx, qy, qz, qw) => {
  const sinr_cosp = 2 * (qw * qx + qy * qz)
  const cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
  const roll = Math.atan2(sinr_cosp, cosr_cosp)

  const sinp = 2 * (qw * qy - qz * qx)
  const pitch = Math.abs(sinp) >= 1 ? Math.sign(sinp) * Math.PI / 2 : Math.asin(sinp)

  const siny_cosp = 2 * (qw * qz + qx * qy)
  const cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
  const yaw = Math.atan2(siny_cosp, cosy_cosp)

  return { yaw, pitch, roll }
}

// Extraer orientación del description
const getOrientation = (photo) => {
  if (!photo.description) return null
  
  const orientMatch = photo.description.match(/orientation:\[([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+),([-\d.eE+]+)\]/)
  if (orientMatch) {
    const qx = parseFloat(orientMatch[1])
    const qy = parseFloat(orientMatch[2])
    const qz = parseFloat(orientMatch[3])
    const qw = parseFloat(orientMatch[4])
    
    return quaternionToEuler(qx, qy, qz, qw)
  }
  return null
}

const CameraMarker = ({ photo, onClick, isActive }) => {
  const meshRef = useRef()
  const arrowRef = useRef()
  const [hovered, setHovered] = useState(false)

  // ✅ DETECTAR TIPO DE FOTO Y COORDENADAS
  const isNormalImage = photo.type === 'normal' || photo.object_type === 'image'

  // Priorizar project_x, project_y, project_z (nuevo sistema)
  let x, y, z
  if (photo.project_x !== undefined && photo.project_y !== undefined) {
    x = parseFloat(photo.project_x) || 0
    y = parseFloat(photo.project_y) || 0
    z = parseFloat(photo.project_z) || 0
  } else {
    // Legacy: usar latitude/longitude para fotos 360
    x = parseFloat(photo.latitude) || 0
    y = parseFloat(photo.longitude) || 0
    z = parseFloat(photo.description?.match(/z:([-\d.]+)/)?.[1] || 0)
  }

  // Obtener orientación (solo para fotos 360°)
  const orientation = isNormalImage ? null : getOrientation(photo)

  useFrame(() => {
    if (meshRef.current && hovered) {
      meshRef.current.rotation.y += 0.02
    }
  })

  return (
    <group position={[x, z, y]}>
      {/* Marcador diferente según tipo */}
      <mesh
        ref={meshRef}
        onClick={(e) => {
          e.stopPropagation()
          onClick(photo)
        }}
        onPointerOver={(e) => {
          e.stopPropagation()
          setHovered(true)
        }}
        onPointerOut={(e) => {
          e.stopPropagation()
          setHovered(false)
        }}
        rotation={orientation ? [orientation.pitch, orientation.yaw, orientation.roll] : [0, 0, 0]}
      >
        {/* ✅ Foto 360: Cono (cámara) | Imagen normal: Esfera */}
        {isNormalImage ? (
          <sphereGeometry args={[0.6, 16, 16]} />
        ) : (
          <coneGeometry args={[0.5, 1.5, 4]} />
        )}
        <meshStandardMaterial
          color={isActive ? '#10b981' : hovered ? '#667eea' : isNormalImage ? '#f59e0b' : '#4a5568'}
          emissive={isActive ? '#10b981' : hovered ? '#667eea' : '#000000'}
          emissiveIntensity={0.5}
        />
      </mesh>

      {/* Flecha que indica dirección */}
      {orientation && (
        <group rotation={[0, orientation.yaw, 0]}>
          <mesh ref={arrowRef} position={[0, 0.5, 1]}>
            <coneGeometry args={[0.3, 0.8, 3]} />
            <meshStandardMaterial 
              color={isActive ? '#10b981' : hovered ? '#667eea' : '#f59e0b'}
              emissive={isActive ? '#10b981' : hovered ? '#667eea' : '#f59e0b'}
              emissiveIntensity={0.3}
            />
          </mesh>
        </group>
      )}
      
      {hovered && (
        <Text
          position={[0, 3, 0]}
          fontSize={0.5}
          color="white"
          anchorX="center"
          anchorY="middle"
        >
          {photo.title}
        </Text>
      )}
    </group>
  )
}

const Ground = () => {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]} receiveShadow>
      <planeGeometry args={[200, 200]} />
      <meshStandardMaterial color="#1a1a1a" roughness={0.8} metalness={0.2} />
    </mesh>
  )
}

const GridHelper = () => {
  return (
    <gridHelper args={[200, 20, '#4a5568', '#2d3748']} />
  )
}

const SkyGradient = () => {
  const mesh = useRef()
  
  const gradientTexture = useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 2
    canvas.height = 256
    const ctx = canvas.getContext('2d')
    
    const gradient = ctx.createLinearGradient(0, 0, 0, 256)
    gradient.addColorStop(0, '#2d3748')
    gradient.addColorStop(0.3, '#4a5568')
    gradient.addColorStop(0.6, '#5a7a9e')
    gradient.addColorStop(1, '#87ceeb')
    
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, 2, 256)
    
    const texture = new THREE.CanvasTexture(canvas)
    return texture
  }, [])

  return (
    <mesh ref={mesh}>
      <sphereGeometry args={[150, 32, 32]} />
      <meshBasicMaterial map={gradientTexture} side={THREE.BackSide} />
    </mesh>
  )
}

const Scene = ({ photos, onPhotoClick, activePhotoId }) => {
  return (
    <>
      <PerspectiveCamera makeDefault position={[20, 20, 20]} />
      <OrbitControls 
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        minDistance={5}
        maxDistance={100}
      />
      
      <ambientLight intensity={0.6} />
      <directionalLight position={[10, 20, 10]} intensity={1} castShadow />
      <pointLight position={[-10, 10, -10]} intensity={0.5} />
      
      <SkyGradient />
      <Ground />
      <GridHelper />
      
      {photos.map(photo => (
        <CameraMarker 
          key={photo.id} 
          photo={photo} 
          onClick={onPhotoClick}
          isActive={photo.id === activePhotoId}
        />
      ))}
    </>
  )
}

const CameraMap3D = ({ photos, onPhotoClick, activePhotoId, onClose, embedded = false }) => {
  // ✅ FILTRAR FOTOS CON COORDENADAS (LEGACY O NUEVO SISTEMA)
  const photosWithCoords = photos.filter(p => {
    // Tiene coordenadas del proyecto (nuevo sistema)
    const hasProjectCoords = p.project_x !== undefined && p.project_y !== undefined
    // Tiene coordenadas legacy (fotos 360 antiguas)
    const hasLegacyCoords = p.latitude !== undefined && p.longitude !== undefined
    return hasProjectCoords || hasLegacyCoords
  })

  if (embedded) {
    return (
      <div className="camera-map-embedded">
        <Canvas>
          <Scene 
            photos={photosWithCoords} 
            onPhotoClick={onPhotoClick}
            activePhotoId={activePhotoId}
          />
        </Canvas>
        <div className="camera-map-info-embedded">
          <span>🖱️ Arrastrar: Rotar | Rueda: Zoom | Click derecho: Mover | 🎯 Flechas amarillas = Dirección de la foto</span>
        </div>
      </div>
    )
  }

  return (
    <div className="camera-map-overlay">
      <div className="camera-map-header">
        <div>
          <h3>Vista 3D del Proyecto</h3>
          <p>{photosWithCoords.length} fotos con coordenadas</p>
        </div>
        <button className="camera-map-close" onClick={onClose}>
          <X size={24} />
        </button>
      </div>

      <div className="camera-map-container">
        <Canvas>
          <Scene 
            photos={photosWithCoords} 
            onPhotoClick={onPhotoClick}
            activePhotoId={activePhotoId}
          />
        </Canvas>
      </div>

      <div className="camera-map-legend">
        <div className="legend-item">
          <div className="legend-icon" style={{background: '#4a5568'}}></div>
          <span>Foto 360° (Cono)</span>
        </div>
        <div className="legend-item">
          <div className="legend-icon" style={{background: '#f59e0b'}}></div>
          <span>Imagen Normal (Esfera)</span>
        </div>
        <div className="legend-item">
          <div className="legend-icon" style={{background: '#667eea'}}></div>
          <span>Hover</span>
        </div>
        <div className="legend-item">
          <div className="legend-icon" style={{background: '#10b981'}}></div>
          <span>Activa</span>
        </div>
      </div>

      <div className="camera-map-controls-info">
        <p>🖱️ Click izquierdo: Rotar | Rueda: Zoom | Click derecho: Mover | 🎯 Flechas naranjas indican hacia dónde mira cada cámara</p>
      </div>
    </div>
  )
}

export default CameraMap3D
