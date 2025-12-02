import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import CoordinateService from '../services/coordinateService';
import './CoordinateAssignmentModal.css';

const CoordinateAssignmentModal = ({ image, project, onClose, onSave }) => {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markerRef = useRef(null);
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [zCoordinate, setZCoordinate] = useState('0');
  const [projectOrigin, setProjectOrigin] = useState(null);
  const [projectRotation, setProjectRotation] = useState(0);

  // Cargar configuración del proyecto
  useEffect(() => {
    if (project?.id) {
      // Intentar cargar desde localStorage primero
      const savedOrigin = localStorage.getItem(`project_origin_${project.id}`);
      const savedRotation = localStorage.getItem(`project_rotation_${project.id}`);

      if (savedOrigin) {
        setProjectOrigin(JSON.parse(savedOrigin));
      } else if (project.map_origin_lat && project.map_origin_lng) {
        setProjectOrigin([project.map_origin_lat, project.map_origin_lng]);
      }

      if (savedRotation) {
        setProjectRotation(parseFloat(savedRotation));
      } else if (project.map_rotation !== null && project.map_rotation !== undefined) {
        setProjectRotation(project.map_rotation);
      }
    }
  }, [project]);

  // Inicializar mapa
  useEffect(() => {
    // Pequeño delay para asegurar que el DOM esté listo
    const timer = setTimeout(() => {
      if (!mapRef.current || mapInstance.current) return;

      try {
        // Crear mapa centrado en el origen del proyecto o ubicación predeterminada
        const center = projectOrigin || [40.4168, -3.7038]; // Madrid como predeterminado
        const map = L.map(mapRef.current).setView(center, 18);

    // Capa satelital de Google
    L.tileLayer('http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
      maxZoom: 22,
      subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
      attribution: '© Google Maps'
    }).addTo(map);

    mapInstance.current = map;

    // Agregar evento de clic al mapa
    map.on('click', (e) => {
      const { lat, lng } = e.latlng;
      setSelectedPosition([lat, lng]);

      // Remover marcador anterior si existe
      if (markerRef.current) {
        map.removeLayer(markerRef.current);
      }

      // Crear nuevo marcador
      const marker = L.marker([lat, lng], {
        icon: L.divIcon({
          className: 'custom-marker-icon',
          html: `<div class="marker-pin assign-pin">
                   <div class="marker-content">
                     <img src="${image.url}" alt="${image.filename}" style="width: 30px; height: 30px; border-radius: 50%; object-fit: cover;" />
                   </div>
                 </div>`,
          iconSize: [40, 40],
          iconAnchor: [20, 40]
        }),
        draggable: true
      }).addTo(map);

      // Permitir arrastrar el marcador
      marker.on('dragend', (event) => {
        const newPos = event.target.getLatLng();
        setSelectedPosition([newPos.lat, newPos.lng]);
      });

      markerRef.current = marker;
    });
      } catch (error) {
        console.error('[MAP] Error inicializando mapa:', error);
      }
    }, 100);

    return () => {
      clearTimeout(timer);
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, [projectOrigin, image]);

  // Si la imagen ya tiene coordenadas, mostrarlas en el mapa
  useEffect(() => {
    if (mapInstance.current && image.geo_latitude && image.geo_longitude) {
      const existingPos = [image.geo_latitude, image.geo_longitude];
      setSelectedPosition(existingPos);
      setZCoordinate(image.project_z?.toString() || '0');

      // Centrar mapa en la posición existente
      mapInstance.current.setView(existingPos, 20);

      // Crear marcador en la posición existente
      if (markerRef.current) {
        mapInstance.current.removeLayer(markerRef.current);
      }

      const marker = L.marker(existingPos, {
        icon: L.divIcon({
          className: 'custom-marker-icon',
          html: `<div class="marker-pin assign-pin">
                   <div class="marker-content">
                     <img src="${image.url}" alt="${image.filename}" style="width: 30px; height: 30px; border-radius: 50%; object-fit: cover;" />
                   </div>
                 </div>`,
          iconSize: [40, 40],
          iconAnchor: [20, 40]
        }),
        draggable: true
      }).addTo(mapInstance.current);

      marker.on('dragend', (event) => {
        const newPos = event.target.getLatLng();
        setSelectedPosition([newPos.lat, newPos.lng]);
      });

      markerRef.current = marker;
    }
  }, [image, mapInstance.current]);

  const handleSave = () => {
    if (!selectedPosition) {
      alert('Por favor, haz clic en el mapa para seleccionar una posición');
      return;
    }

    const [lat, lng] = selectedPosition;

    // Calcular coordenadas UTM
    const utm = CoordinateService.wgs84ToUTM(lat, lng);

    // Calcular coordenadas del proyecto (locales)
    let project_x = null;
    let project_y = null;

    if (projectOrigin) {
      const [originLat, originLng] = projectOrigin;

      // Calcular diferencia en metros
      const latDiff = (lat - originLat) * 111320; // 1 grado ≈ 111.32 km
      const lngDiff = (lng - originLng) * 111320 * Math.cos(originLat * Math.PI / 180);

      // Aplicar rotación si existe
      const angle = -projectRotation * Math.PI / 180;
      project_x = lngDiff * Math.cos(angle) - latDiff * Math.sin(angle);
      project_y = lngDiff * Math.sin(angle) + latDiff * Math.cos(angle);
    }

    const coordinates = {
      geo_latitude: lat,
      geo_longitude: lng,
      utm_easting: utm?.easting,
      utm_northing: utm?.northing,
      utm_zone: utm?.zone,
      utm_hemisphere: utm?.hemisphere,
      utm_datum: utm?.datum || 'ETRS89',
      project_x,
      project_y,
      project_z: parseFloat(zCoordinate) || 0
    };

    console.log('[COORDS MODAL] Coordenadas calculadas:', coordinates);
    onSave(coordinates);
  };

  return (
    <div className="coordinate-assignment-overlay">
      <div className="coordinate-assignment-modal">
        <div className="modal-header">
          <h2>📍 Asignar Coordenadas</h2>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="modal-content">
          <div className="image-preview">
            <img src={image.url} alt={image.filename} />
            <p className="image-name">{image.filename}</p>
          </div>

          <div className="instructions">
            <p>Haz clic en el mapa para colocar la imagen en su ubicación real</p>
            {selectedPosition && (
              <div className="selected-coords">
                <strong>Posición seleccionada:</strong>
                <br />
                Lat: {selectedPosition[0].toFixed(8)}
                <br />
                Lng: {selectedPosition[1].toFixed(8)}
              </div>
            )}
          </div>

          <div className="map-container" ref={mapRef}></div>

          <div className="z-coordinate-input">
            <label htmlFor="z-coord">Coordenada Z (altura en metros):</label>
            <input
              id="z-coord"
              type="number"
              step="0.01"
              value={zCoordinate}
              onChange={(e) => setZCoordinate(e.target.value)}
              placeholder="0.00"
            />
          </div>

          {!projectOrigin && (
            <div className="warning-message">
              ⚠️ El proyecto no tiene un origen configurado. Las coordenadas locales (X, Y) no se calcularán.
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancelar
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={!selectedPosition}
          >
            Guardar Coordenadas
          </button>
        </div>
      </div>
    </div>
  );
};

export default CoordinateAssignmentModal;
