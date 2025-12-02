import React, { useState, useEffect } from 'react';
import './MobileCaptureModal.css';
import CoordinateService from '../services/coordinateService';

const MobileCaptureModal = ({ position, onSave, onClose, selectedImage, levels = [] }) => {
    const [capturedImage, setCapturedImage] = useState(selectedImage || null);
    const [level, setLevel] = useState('');
    const [room, setRoom] = useState('');
    const [pk, setPk] = useState('');
    const [comment, setComment] = useState('');
    const [availableLevels, setAvailableLevels] = useState([]);
    const [availableRooms, setAvailableRooms] = useState([]);
    
    // ✅ NUEVOS ESTADOS PARA SISTEMA Z
    const [zType, setZType] = useState('absolute'); // 'absolute' o 'relative'
    const [customZ, setCustomZ] = useState('');
    const [showLevelManager, setShowLevelManager] = useState(false);

    // ✅ CARGAR ETIQUETAS EXISTENTES
    useEffect(() => {
        loadAvailableTags();
    }, []);

    const loadAvailableTags = () => {
        try {
            // Si tenemos niveles desde props, usarlos, sino usar predefinidos
            if (levels && levels.length > 0) {
                const levelNames = ['', ...levels.map(l => l.name)];
                setAvailableLevels(levelNames);
            } else {
                // Etiquetas predefinidas fijas
                const defaultLevels = ['', 'P00', 'P01', 'P02', 'P03', 'P04', 'S01', 'S02', 'S03'];
                setAvailableLevels(defaultLevels);
            }
            
            const rooms = ['', 'Salon', 'Cocina', 'Baño', 'Dormitorio', 'Oficina', 'Terraza', 'Garaje', 'Fachada', 'Jardin', 'Piscina'];
            setAvailableRooms(rooms);
            
        } catch (error) {
            console.error('Error cargando etiquetas:', error);
            setAvailableLevels(['', 'P00', 'P01', 'P02']);
            setAvailableRooms(['', 'Salon', 'Cocina', 'Baño']);
        }
    };

    // ✅ Obtener altura Z basada en nivel seleccionado
    const getZFromLevel = () => {
        if (!level) return 0;
        
        // Buscar en niveles prop
        if (levels && levels.length > 0) {
            const levelConfig = levels.find(l => l.name === level);
            return levelConfig ? levelConfig.height : 0;
        }
        
        // Valores predefinidos por defecto
        const predefinedZ = {
            'P00': 0, 'P01': 3, 'P02': 6, 'P03': 9, 'P04': 12,
            'S01': -3, 'S02': -6, 'S03': -9
        };
        
        return predefinedZ[level] || 0;
    };

    // ✅ Calcular Z final
    const calculateFinalZ = () => {
        if (zType === 'absolute') {
            return parseFloat(customZ) || 0;
        } else {
            const baseZ = getZFromLevel();
            const relativeZ = parseFloat(customZ) || 0;
            return baseZ + relativeZ;
        }
    };

    // ✅ ABRIR CÁMARA SOLO EN MÓVIL
    const openNativeCamera = () => {
        // Solo en móvil
        if (!/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
            alert('Esta función solo está disponible en dispositivos móviles');
            return;
        }

        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.capture = 'environment';
        input.style.display = 'none';
        
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                setCapturedImage(file);
            }
        };
        
        document.body.appendChild(input);
        input.click();
    };

    // ✅ GUARDAR CON ETIQUETAS Y COORDENADAS Z
    const handleSave = async () => {
        if (!capturedImage && !selectedImage) {
            alert('Primero selecciona o captura una imagen');
            return;
        }

        const imageFile = capturedImage || selectedImage;
        if (!imageFile) return;

        // ✅ CALCULAR Z FINAL
        const finalZ = calculateFinalZ();

        // ✅ CALCULAR COORDENADAS COMPLETAS (WGS84, UTM, PROYECTO)
        const geoLat = position.lat;
        const geoLng = position.lng;

        // Calcular coordenadas UTM
        const utmCoords = CoordinateService.wgs84ToUTM(geoLat, geoLng);
        const zoneInfo = CoordinateService.detectUTMZone(geoLat, geoLng);

        // Preparar datos para guardar (el backend subirá a Cloudinary)
        const imageData = {
            file: imageFile,
            latitude: geoLat,
            longitude: geoLng,
            // ✅ COORDENADAS GEOGRÁFICAS WGS84
            geo_latitude: geoLat,
            geo_longitude: geoLng,
            // ✅ COORDENADAS UTM
            utm_easting: utmCoords?.easting,
            utm_northing: utmCoords?.northing,
            utm_zone: utmCoords?.zone,
            utm_hemisphere: zoneInfo?.hemisphere,
            utm_datum: utmCoords?.datum || 'ETRS89',
            // ✅ COORDENADAS DEL PROYECTO (se calcularán en ProjectDetail)
            // project_x, project_y se calcularán en handleMobileCaptureSubmit
            project_z: finalZ,
            // Metadatos
            level: level,
            room: room,
            pk: pk,
            comment: comment,
            filename: imageFile.name,
            uploaded_at: new Date().toISOString(),
            title: `Imagen ${new Date().toLocaleString()}`,
            tags: [level, room, pk].filter(Boolean).join(', '),
            type: 'normal',
            object_type: 'image',
            // ✅ CAMPOS ADICIONALES PARA Z
            finalZ: finalZ,
            zType: zType,
            customZ: customZ,
            // ✅ INDICAR QUE ES EDITABLE/MOVIBLE
            editable: true
        };

        // Llamar función padre para guardar (envía al backend)
        onSave(imageData);
    };

    return (
        <div className="mobile-modal-overlay">
            <div className="mobile-modal-content">
                {/* Header */}
                <div className="modal-header">
                    <h3>📸 {selectedImage ? 'Colocar Imagen en Mapa' : 'Capturar Imagen'}</h3>
                    <button className="close-btn" onClick={onClose}>✕</button>
                </div>

                {/* ✅ BOTÓN DE CÁMARA SOLO SI NO HAY IMAGEN SELECCIONADA */}
                {!capturedImage && !selectedImage && (
                    <div className="camera-section">
                        <button className="camera-btn" onClick={openNativeCamera}>
                            📷 Abrir Cámara
                        </button>
                        <p className="help-text">Toca para abrir la cámara de tu móvil</p>
                    </div>
                )}

                {/* ✅ PREVIEW DE IMAGEN */}
                {(capturedImage || selectedImage) && (
                    <div className="image-preview">
                        <img 
                            src={URL.createObjectURL(capturedImage || selectedImage)} 
                            alt="Imagen seleccionada" 
                        />
                        <p className="image-size">
                            ✅ Imagen lista para guardar con etiquetas
                        </p>
                    </div>
                )}

                {/* ✅ FORMULARIO DE ETIQUETAS (SIEMPRE VISIBLE) */}
                <div className="tagging-form">
                    <h4>🏷️ Información de la Imagen</h4>
                    
                    <div className="form-group">
                        <label>🏗️ Nivel</label>
                        <select 
                            value={level} 
                            onChange={(e) => setLevel(e.target.value)}
                            className="touch-select"
                        >
                            {availableLevels.map((lvl, index) => (
                                <option key={index} value={lvl}>
                                    {lvl || 'Seleccionar nivel'}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* ✅ NUEVO: SISTEMA DE COORDENADA Z */}
                    <div className="form-group">
                        <label>📐 Sistema de Coordenada Z</label>
                        <div className="z-controls">
                            <select 
                                value={zType} 
                                onChange={(e) => setZType(e.target.value)}
                                className="touch-select"
                            >
                                <option value="absolute">Cota Absoluta</option>
                                <option value="relative">Cota Relativa al Nivel</option>
                            </select>
                            
                            {zType === 'absolute' ? (
                                <input
                                    type="number"
                                    step="0.01"
                                    value={customZ}
                                    onChange={(e) => setCustomZ(e.target.value)}
                                    placeholder="Z absoluto (metros)"
                                    className="touch-input"
                                />
                            ) : (
                                <div className="relative-z-controls">
                                    <div className="z-info">
                                        <span>Nivel {level}: {getZFromLevel()}m + </span>
                                        <input
                                            type="number"
                                            step="0.01"
                                            value={customZ}
                                            onChange={(e) => setCustomZ(e.target.value)}
                                            placeholder="ΔZ adicional"
                                            className="touch-input small"
                                        />
                                        <span> = {calculateFinalZ().toFixed(2)}m</span>
                                    </div>
                                </div>
                            )}
                        </div>
                        <button 
                            type="button"
                            className="btn-link"
                            onClick={() => setShowLevelManager(true)}
                        >
                            ⚙️ Gestionar Niveles
                        </button>
                    </div>

                    <div className="form-group">
                        <label>🚪 Habitación/Zona</label>
                        <select 
                            value={room} 
                            onChange={(e) => setRoom(e.target.value)}
                            className="touch-select"
                        >
                            {availableRooms.map((rm, index) => (
                                <option key={index} value={rm}>
                                    {rm || 'Seleccionar zona'}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label>📏 PK (Obra Lineal)</label>
                        <input
                            type="text"
                            value={pk}
                            onChange={(e) => setPk(e.target.value)}
                            placeholder="Ej: 0+250, 1+500"
                            className="touch-input"
                        />
                    </div>

                    <div className="form-group">
                        <label>💬 Comentario</label>
                        <textarea
                            value={comment}
                            onChange={(e) => setComment(e.target.value)}
                            placeholder="Describe lo que se ve en la imagen..."
                            rows="3"
                        />
                    </div>
                </div>

                {/* ✅ INFORMACIÓN DE UBICACIÓN CON UTM */}
                <div className="location-info">
                    <h4>📍 Ubicación Seleccionada</h4>
                    <div className="coords-display">
                        <p><strong>WGS84:</strong></p>
                        <p>Lat: {position?.lat.toFixed(6)}</p>
                        <p>Lng: {position?.lng.toFixed(6)}</p>

                        {position && (() => {
                            const utm = CoordinateService.wgs84ToUTM(position.lat, position.lng);
                            return utm && (
                                <>
                                    <p style={{marginTop: '8px'}}><strong>UTM ({utm.datum} Zone {utm.zone}{utm.hemisphere}):</strong></p>
                                    <p>Easting: {utm.easting.toFixed(2)}m</p>
                                    <p>Northing: {utm.northing.toFixed(2)}m</p>
                                </>
                            );
                        })()}

                        <p style={{marginTop: '8px'}}><strong>Coordenada Z:</strong> {calculateFinalZ().toFixed(2)}m</p>
                    </div>
                </div>

                {/* ✅ BOTONES DE ACCIÓN */}
                <div className="action-buttons">
                    <button className="btn-cancel" onClick={onClose}>
                        Cancelar
                    </button>
                    <button 
                        className="btn-save" 
                        onClick={handleSave}
                        disabled={!capturedImage && !selectedImage}
                    >
                        ✅ Guardar en Mapa
                    </button>
                </div>
            </div>
        </div>
    );
};

export default MobileCaptureModal;