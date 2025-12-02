import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './ProfessionalMapView.css';
import CoordinateService from '../services/coordinateService';
import CoordinateAssignmentModal from './CoordinateAssignmentModal';
import api from '../config/axios';

// Fix para iconos de Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const ProfessionalMapView = ({ project, onClose }) => {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const markersRef = useRef([]);
  const layersRef = useRef({});
  const coordinateDisplayRef = useRef(null);

  const [userLocation, setUserLocation] = useState(null);
  const [photos360, setPhotos360] = useState([]);
  const [galleryImages, setGalleryImages] = useState([]);
  const [incidents, setIncidents] = useState([]);

  // Estados para captura
  const [captureMode, setCaptureMode] = useState(null); // '360', 'image', 'incident'
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [tempMarker, setTempMarker] = useState(null);

  // Estados para modales
  const [showPhotoModal, setShowPhotoModal] = useState(false);
  const [showImageModal, setShowImageModal] = useState(false);
  const [showIncidentModal, setShowIncidentModal] = useState(false);

  // Estados para formularios
  const [photoFile, setPhotoFile] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [incidentData, setIncidentData] = useState({
    title: '',
    description: '',
    type: 'defecto',
    severity: 'media'
  });
  const [zCoordinate, setZCoordinate] = useState('0');

  // Estados para capa de mapa
  const [currentLayer, setCurrentLayer] = useState('satellite'); // 'satellite', 'osm', 'hybrid'
  const [mouseCoords, setMouseCoords] = useState({ lat: 0, lng: 0, utm: null });

  // Estadísticas
  const [stats, setStats] = useState({
    total360: 0,
    totalImages: 0,
    totalIncidents: 0,
    withCoordinates: 0
  });

  // Cargar ubicación del usuario
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const coords = [position.coords.latitude, position.coords.longitude];
          setUserLocation(coords);
          if (mapInstance.current) {
            mapInstance.current.setView(coords, 18);
          }
        },
        (error) => console.error('Error obteniendo ubicación:', error)
      );
    }
  }, []);

  // Función para cambiar capa de mapa
  const changeMapLayer = useCallback((layerType) => {
    if (!mapInstance.current) return;

    // Remover capa actual
    if (layersRef.current.currentLayer) {
      mapInstance.current.removeLayer(layersRef.current.currentLayer);
    }

    let newLayer;
    switch (layerType) {
      case 'osm':
        newLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 22,
          attribution: '© OpenStreetMap contributors'
        });
        break;
      case 'hybrid':
        // Hybrid: Satellite + labels
        newLayer = L.tileLayer('http://{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', {
          maxZoom: 22,
          subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
          attribution: '© Google Maps'
        });
        break;
      case 'satellite':
      default:
        newLayer = L.tileLayer('http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
          maxZoom: 22,
          subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
          attribution: '© Google Maps'
        });
        break;
    }

    newLayer.addTo(mapInstance.current);
    layersRef.current.currentLayer = newLayer;
    setCurrentLayer(layerType);
  }, []);

  // Inicializar mapa
  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return;

    const timer = setTimeout(() => {
      try {
        const center = userLocation || [40.4168, -3.7038];
        const map = L.map(mapRef.current, {
          zoomControl: true,
          attributionControl: true
        }).setView(center, 18);

        // Capa satelital de Google (por defecto)
        const satelliteLayer = L.tileLayer('http://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
          maxZoom: 22,
          subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
          attribution: '© Google Maps'
        }).addTo(map);

        layersRef.current.currentLayer = satelliteLayer;

        // Control de escala
        L.control.scale({
          metric: true,
          imperial: false,
          position: 'bottomleft'
        }).addTo(map);

        mapInstance.current = map;

        console.log('[PROFESSIONAL MAP] Mapa inicializado correctamente');
      } catch (error) {
        console.error('[PROFESSIONAL MAP] Error inicializando:', error);
      }
    }, 200);

    return () => {
      clearTimeout(timer);
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, [userLocation]);

  // Registrar eventos del mapa después de inicialización
  useEffect(() => {
    if (!mapInstance.current) return;

    const map = mapInstance.current;

    // Evento de clic en el mapa
    const clickHandler = (e) => {
      handleMapClick(e);
    };

    // Evento de movimiento del mouse para mostrar coordenadas
    const mouseMoveHandler = (e) => {
      const { lat, lng } = e.latlng;
      const utm = CoordinateService.wgs84ToUTM(lat, lng);
      setMouseCoords({ lat, lng, utm });
    };

    map.on('click', clickHandler);
    map.on('mousemove', mouseMoveHandler);

    return () => {
      map.off('click', clickHandler);
      map.off('mousemove', mouseMoveHandler);
    };
  }, [captureMode, tempMarker]);

  // Cargar datos
  useEffect(() => {
    if (project?.id) {
      loadAllData();
    }
  }, [project]);

  // Renderizar marcadores cuando el mapa esté listo y tengamos datos
  useEffect(() => {
    if (mapInstance.current && (photos360.length > 0 || galleryImages.length > 0 || incidents.length > 0)) {
      console.log('[MAP READY] Rendering markers now');
      renderAllMarkers([...photos360, ...galleryImages, ...incidents]);
    }
  }, [mapInstance.current, photos360, galleryImages, incidents]);

  const loadAllData = async () => {
    try {
      // Cargar fotos 360
      const photos360Response = await api.get(`/projects/${project.id}/photos`);
      const all360 = photos360Response.data;
      setPhotos360(all360);
      console.log('[LOAD DATA] Loaded', all360.length, '360 photos');

      // Cargar imágenes de galería
      const galleryResponse = await api.get(`/projects/${project.id}/gallery`);
      const allGallery = galleryResponse.data;
      setGalleryImages(allGallery);
      console.log('[LOAD DATA] Loaded', allGallery.length, 'gallery images');

      // Cargar incidencias (puede no existir el endpoint aún)
      let allIncidents = [];
      try {
        const incidentsResponse = await api.get(`/projects/${project.id}/incidents`);
        allIncidents = incidentsResponse.data;
        setIncidents(allIncidents);
        console.log('[LOAD DATA] Loaded', allIncidents.length, 'incidents');
      } catch (incidentError) {
        console.warn('[LOAD DATA] No incidents endpoint or no incidents:', incidentError.message);
        setIncidents([]);
      }

      // Actualizar estadísticas
      setStats({
        total360: all360.length,
        totalImages: allGallery.length,
        totalIncidents: allIncidents.length,
        withCoordinates: [...all360, ...allGallery, ...allIncidents].filter(item =>
          item.geo_latitude && item.geo_longitude
        ).length
      });

      // Renderizar marcadores
      const allItems = [...all360, ...allGallery, ...allIncidents];
      console.log('[LOAD DATA] Total items to render:', allItems.length);
      renderAllMarkers(allItems);

    } catch (error) {
      console.error('[PROFESSIONAL MAP] Error cargando datos:', error);
    }
  };

  const handleMapClick = (e) => {
    console.log('[MAP CLICK] Clicked! Capture mode:', captureMode);

    if (!captureMode) {
      console.log('[MAP CLICK] No capture mode active, ignoring click');
      return;
    }

    const { lat, lng } = e.latlng;
    console.log('[MAP CLICK] Position:', lat, lng);
    setSelectedPosition([lat, lng]);

    // Remover marcador temporal anterior
    if (tempMarker) {
      mapInstance.current.removeLayer(tempMarker);
    }

    // Crear nuevo marcador temporal
    const icon = L.divIcon({
      className: 'custom-marker-temp',
      html: `<div style="background: #f59e0b; width: 40px; height: 40px; border-radius: 50%; border: 4px solid white; box-shadow: 0 6px 16px rgba(245, 158, 11, 0.6); display: flex; align-items: center; justify-content: center; font-size: 1.4rem;">
               ${captureMode === '360' ? '📸' : captureMode === 'image' ? '🖼️' : '⚠️'}
             </div>`,
      iconSize: [40, 40],
      iconAnchor: [20, 40]
    });

    const marker = L.marker([lat, lng], {
      icon,
      draggable: true
    }).addTo(mapInstance.current);

    marker.on('dragend', (event) => {
      const newPos = event.target.getLatLng();
      setSelectedPosition([newPos.lat, newPos.lng]);
    });

    setTempMarker(marker);

    // Abrir modal correspondiente
    console.log('[MAP CLICK] Opening modal for:', captureMode);
    if (captureMode === '360') {
      setShowPhotoModal(true);
    } else if (captureMode === 'image') {
      setShowImageModal(true);
    } else if (captureMode === 'incident') {
      setShowIncidentModal(true);
    }
  };

  const renderAllMarkers = (items) => {
    // Verificar que el mapa esté inicializado
    if (!mapInstance.current) {
      console.log('[RENDER MARKERS] Map not ready yet, skipping');
      return;
    }

    console.log('[RENDER MARKERS] Rendering', items.length, 'items');

    // Limpiar marcadores anteriores
    markersRef.current.forEach(marker => {
      mapInstance.current.removeLayer(marker);
    });
    markersRef.current = [];

    items.forEach((item, index) => {
      if (!item.geo_latitude || !item.geo_longitude) {
        console.log(`[RENDER MARKERS] Item ${index} skipped - no coordinates`, {
          filename: item.filename || item.title,
          id: item.id,
          hasGeoLat: !!item.geo_latitude,
          hasGeoLng: !!item.geo_longitude,
          url: item.url ? 'yes' : 'no'
        });
        return;
      }

      console.log(`[RENDER MARKERS] Rendering item ${index}:`, item.filename || item.title, 'at', item.geo_latitude, item.geo_longitude, {
        hasUrl: !!item.url,
        utmZone: item.utm_zone
      });

      const isPhoto360 = item.type === '360' || item.object_type === '360photo';
      const isImage = item.type === 'normal' || item.object_type === 'image';
      const isIncident = item.object_type === 'incident';

      let iconEmoji = '🖼️';
      let pinClass = 'image-pin';
      let itemType = 'Imagen Normal';

      if (isPhoto360) {
        iconEmoji = '📸';
        pinClass = 'photo-360-pin';
        itemType = 'Foto 360°';
      } else if (isIncident) {
        iconEmoji = '⚠️';
        pinClass = 'incident-pin';
        itemType = 'Incidencia';
      }

      const icon = L.divIcon({
        className: 'custom-marker',
        html: `<div class="marker-pin ${pinClass}">
                 <span class="marker-icon">${iconEmoji}</span>
               </div>`,
        iconSize: [36, 36],
        iconAnchor: [18, 36]
      });

      let popupContent = '';
      if (isIncident) {
        popupContent = `
          <div class="marker-popup">
            <h4>⚠️ ${item.title}</h4>
            <p style="margin: 5px 0;">${item.description || 'Sin descripción'}</p>
            <p style="margin: 5px 0;"><strong>Gravedad:</strong> <span style="color: ${item.severity === 'alta' || item.severity === 'critica' ? '#ef4444' : '#fbbf24'}">${item.severity}</span></p>
            <p style="margin: 5px 0;"><strong>Estado:</strong> ${item.status}</p>
            <div style="background: #f3f4f6; padding: 8px; border-radius: 6px; margin-top: 8px;">
              <p style="margin: 2px 0; font-size: 0.85rem;"><strong>UTM ETRS89 Zona ${item.utm_zone || 'N/A'}${item.utm_hemisphere || ''}</strong></p>
              <p style="margin: 2px 0; font-size: 0.85rem;">E: ${item.utm_easting?.toFixed(2) || 'N/A'} m</p>
              <p style="margin: 2px 0; font-size: 0.85rem;">N: ${item.utm_northing?.toFixed(2) || 'N/A'} m</p>
              <p style="margin: 2px 0; font-size: 0.85rem;">Z: ${item.project_z?.toFixed(2) || '0.00'} m</p>
            </div>
            <p style="font-size: 0.75rem; color: #6b7280; margin-top: 8px;">💡 Puedes arrastrar este marcador</p>
          </div>
        `;
      } else {
        // URL único para el elemento
        const elementUrl = isPhoto360
          ? `/project/${project.id}/viewer?photo=${item.id}`
          : item.url;

        popupContent = `
          <div class="marker-popup">
            <h4 style="margin: 0 0 10px 0;">${item.title || item.filename}</h4>
            ${item.url ? `
              <div style="position: relative; margin: 10px 0;">
                <img
                  src="${item.url}"
                  alt="${item.filename || item.title}"
                  style="width: 100%; max-width: 250px; height: auto; max-height: 180px; object-fit: cover; border-radius: 8px; cursor: pointer; display: block; margin: 0 auto;"
                  onclick="window.open('${item.url}', '_blank')"
                  onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22150%22%3E%3Crect fill=%22%23f3f4f6%22 width=%22200%22 height=%22150%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 dominant-baseline=%22middle%22 text-anchor=%22middle%22 fill=%22%236b7280%22%3EImagen no disponible%3C/text%3E%3C/svg%3E';"
                />
                <div style="position: absolute; top: 5px; right: 5px; background: rgba(0,0,0,0.6); color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.75rem;">
                  ${isPhoto360 ? '360°' : '📷'}
                </div>
              </div>
            ` : ''}
            <p style="margin: 5px 0;"><strong>Tipo:</strong> ${itemType}</p>
            <div style="background: #f3f4f6; padding: 8px; border-radius: 6px; margin-top: 8px;">
              <p style="margin: 2px 0; font-size: 0.85rem;"><strong>UTM ETRS89 Zona ${item.utm_zone || 'N/A'}${item.utm_hemisphere || ''}</strong></p>
              <p style="margin: 2px 0; font-size: 0.85rem;">E: ${item.utm_easting?.toFixed(2) || 'N/A'} m</p>
              <p style="margin: 2px 0; font-size: 0.85rem;">N: ${item.utm_northing?.toFixed(2) || 'N/A'} m</p>
            </div>
            <a href="${elementUrl}" target="_blank" style="display: inline-block; margin-top: 10px; padding: 6px 12px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px; font-size: 0.85rem;">
              ${isPhoto360 ? '🔄 Ver en Visor 360°' : '🔍 Ver imagen completa'}
            </a>
            <p style="font-size: 0.75rem; color: #6b7280; margin-top: 8px;">💡 Puedes arrastrar este marcador</p>
          </div>
        `;
      }

      const marker = L.marker([item.geo_latitude, item.geo_longitude], {
        icon,
        draggable: true  // Hacer marcadores arrastrables
      })
        .bindPopup(popupContent)
        .addTo(mapInstance.current);

      // Evento al arrastrar marcador - actualizar coordenadas
      marker.on('dragend', async (event) => {
        const newPos = event.target.getLatLng();
        const utm = CoordinateService.wgs84ToUTM(newPos.lat, newPos.lng);

        console.log(`[DRAG] Updating ${item.filename || item.title} to new position:`, newPos.lat, newPos.lng);

        try {
          // Actualizar según tipo de objeto
          if (isPhoto360) {
            await api.put(`/projects/${project.id}/photos/${item.id}/coordinates`, {
              geo_latitude: newPos.lat,
              geo_longitude: newPos.lng,
              utm_easting: utm.easting,
              utm_northing: utm.northing,
              utm_zone: utm.zone,
              utm_hemisphere: utm.hemisphere,
              utm_datum: utm.datum
            });
            console.log(`[DRAG] Photo360 ${item.id} coordinates updated`);
          } else if (isImage) {
            await api.put(`/projects/${project.id}/gallery/${item.id}/coordinates`, {
              geo_latitude: newPos.lat,
              geo_longitude: newPos.lng,
              utm_easting: utm.easting,
              utm_northing: utm.northing,
              utm_zone: utm.zone,
              utm_hemisphere: utm.hemisphere,
              utm_datum: utm.datum
            });
            console.log(`[DRAG] Image ${item.id} coordinates updated`);
          } else if (isIncident) {
            await api.put(`/projects/${project.id}/incidents/${item.id}`, {
              geo_latitude: newPos.lat,
              geo_longitude: newPos.lng,
              utm_easting: utm.easting,
              utm_northing: utm.northing,
              utm_zone: utm.zone,
              utm_hemisphere: utm.hemisphere,
              utm_datum: utm.datum
            });
            console.log(`[DRAG] Incident ${item.id} coordinates updated`);
          }

          // Actualizar el objeto en el estado
          item.geo_latitude = newPos.lat;
          item.geo_longitude = newPos.lng;
          item.utm_easting = utm.easting;
          item.utm_northing = utm.northing;
          item.utm_zone = utm.zone;
          item.utm_hemisphere = utm.hemisphere;

          // Actualizar popup con nuevas coordenadas
          const newPopup = isIncident ? `
            <div class="marker-popup">
              <h4>⚠️ ${item.title}</h4>
              <p>${item.description || 'Sin descripción'}</p>
              <p><strong>Gravedad:</strong> ${item.severity}</p>
              <p><strong>Coordenadas UTM ETRS89:</strong><br/>
                 Zona: ${utm.zone}${utm.hemisphere}<br/>
                 E: ${utm.easting.toFixed(2)}m<br/>
                 N: ${utm.northing.toFixed(2)}m<br/>
                 Z: ${item.project_z?.toFixed(2) || '0.00'}m</p>
              <p style="font-size: 0.8rem; color: #10b981;">✓ Coordenadas actualizadas</p>
            </div>
          ` : `
            <div class="marker-popup">
              <h4>${item.title || item.filename}</h4>
              <img src="${item.url}" alt="${item.filename || item.title}" style="max-width: 200px; max-height: 150px; border-radius: 6px; cursor: pointer;" onclick="window.open('${item.url}', '_blank')" />
              <p><strong>Tipo:</strong> ${itemType}</p>
              <p><strong>Coordenadas UTM ETRS89:</strong><br/>
                 Zona: ${utm.zone}${utm.hemisphere}<br/>
                 E: ${utm.easting.toFixed(2)}m<br/>
                 N: ${utm.northing.toFixed(2)}m</p>
              <p style="font-size: 0.8rem; color: #10b981;">✓ Coordenadas actualizadas</p>
              <a href="${item.url}" target="_blank" style="display: block; margin-top: 8px; color: #3b82f6;">🔗 Ver imagen completa</a>
            </div>
          `;

          marker.setPopupContent(newPopup);
          marker.openPopup();

        } catch (error) {
          console.error('[DRAG] Error updating coordinates:', error);
          alert('Error al actualizar coordenadas. Intenta de nuevo.');
          // Revertir posición del marcador
          marker.setLatLng([item.geo_latitude, item.geo_longitude]);
        }
      });

      // Evento al hacer click en el marcador - abrir elemento
      marker.on('click', () => {
        if (isPhoto360) {
          // Abrir visor 360 (necesitarás implementar esta función)
          console.log('[CLICK] Opening 360 viewer for photo', item.id);
          // TODO: Implementar navegación al visor 360
          // window.location.href = `/project/${project.id}/viewer?photo=${item.id}`;
        } else if (isImage) {
          // Abrir imagen en nueva pestaña
          console.log('[CLICK] Opening image', item.url);
          window.open(item.url, '_blank');
        } else if (isIncident) {
          // Mostrar detalles de incidencia
          console.log('[CLICK] Opening incident details', item.id);
          // TODO: Implementar modal de detalles de incidencia
        }
      });

      markersRef.current.push(marker);
    });
  };

  const handleSavePhoto360 = async () => {
    if (!photoFile || !selectedPosition) {
      alert('Por favor selecciona un archivo y una posición en el mapa');
      return;
    }

    try {
      const [lat, lng] = selectedPosition;
      const utm = CoordinateService.wgs84ToUTM(lat, lng);
      const z = parseFloat(zCoordinate) || 0;

      const formData = new FormData();
      formData.append('file', photoFile);
      formData.append('geo_latitude', lat.toString());
      formData.append('geo_longitude', lng.toString());
      formData.append('utm_easting', utm.easting.toString());
      formData.append('utm_northing', utm.northing.toString());
      formData.append('utm_zone', utm.zone.toString());
      formData.append('utm_hemisphere', utm.hemisphere);
      formData.append('utm_datum', utm.datum);
      formData.append('project_z', z.toString());

      await api.post(`/projects/${project.id}/photos/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      alert('Foto 360° guardada correctamente');
      resetCaptureMode();
      loadAllData();
    } catch (error) {
      console.error('[SAVE] Error:', error);
      alert('Error al guardar la foto 360°');
    }
  };

  const handleSaveImage = async () => {
    if (!imageFile || !selectedPosition) {
      alert('Por favor selecciona un archivo y una posición en el mapa');
      return;
    }

    try {
      const [lat, lng] = selectedPosition;
      const utm = CoordinateService.wgs84ToUTM(lat, lng);
      const z = parseFloat(zCoordinate) || 0;

      const formData = new FormData();
      formData.append('file', imageFile);
      formData.append('geo_latitude', lat.toString());
      formData.append('geo_longitude', lng.toString());
      formData.append('utm_easting', utm.easting.toString());
      formData.append('utm_northing', utm.northing.toString());
      formData.append('utm_zone', utm.zone.toString());
      formData.append('utm_hemisphere', utm.hemisphere);
      formData.append('utm_datum', utm.datum);
      formData.append('project_z', z.toString());

      await api.post(`/projects/${project.id}/gallery/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      alert('Imagen guardada correctamente');
      resetCaptureMode();
      loadAllData();
    } catch (error) {
      console.error('[SAVE] Error:', error);
      alert('Error al guardar la imagen');
    }
  };

  const handleSaveIncident = async () => {
    if (!selectedPosition || !incidentData.title) {
      alert('Por favor completa el título y selecciona una posición');
      return;
    }

    try {
      const [lat, lng] = selectedPosition;
      const utm = CoordinateService.wgs84ToUTM(lat, lng);
      const z = parseFloat(zCoordinate) || 0;

      // Crear URLSearchParams para enviar como application/x-www-form-urlencoded
      const params = new URLSearchParams();
      params.append('title', incidentData.title);
      params.append('description', incidentData.description || '');
      params.append('incident_type', incidentData.type);
      params.append('severity', incidentData.severity);
      params.append('geo_latitude', lat.toString());
      params.append('geo_longitude', lng.toString());
      params.append('utm_easting', utm.easting.toString());
      params.append('utm_northing', utm.northing.toString());
      params.append('utm_zone', utm.zone.toString());
      params.append('utm_hemisphere', utm.hemisphere);
      params.append('utm_datum', utm.datum);
      params.append('project_z', z.toString());

      await api.post(`/projects/${project.id}/incidents`, params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });

      alert('Incidencia guardada correctamente');
      resetCaptureMode();
      loadAllData();
    } catch (error) {
      console.error('[SAVE] Error:', error);
      alert('Error al guardar la incidencia');
    }
  };

  const resetCaptureMode = () => {
    setCaptureMode(null);
    setSelectedPosition(null);
    setPhotoFile(null);
    setImageFile(null);
    setIncidentData({ title: '', description: '', type: 'defecto', severity: 'media' });
    setZCoordinate('0');
    setShowPhotoModal(false);
    setShowImageModal(false);
    setShowIncidentModal(false);

    if (tempMarker) {
      mapInstance.current.removeLayer(tempMarker);
      setTempMarker(null);
    }
  };

  return (
    <div className="professional-map-container">
      {/* Header */}
      <div className="professional-map-header">
        <div className="header-left">
          <h1>🗺️ Mapa Profesional UTM</h1>
          <p>{project?.name || 'Proyecto'}</p>
        </div>
        <div className="header-stats">
          <div className="stat-item">
            <span className="stat-value">{stats.total360}</span>
            <span className="stat-label">360°</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.totalImages}</span>
            <span className="stat-label">Imágenes</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.totalIncidents}</span>
            <span className="stat-label">Incidencias</span>
          </div>
          <div className="stat-item">
            <span className="stat-value">{stats.withCoordinates}</span>
            <span className="stat-label">Con Coords</span>
          </div>
        </div>
        <button className="close-map-btn" onClick={onClose}>✕ Cerrar</button>
      </div>

      {/* Toolbar */}
      <div className="map-toolbar">
        {/* Botones de acción */}
        <div className="toolbar-section">
          <button
            className={`tool-btn ${captureMode === '360' ? 'active' : ''}`}
            onClick={() => setCaptureMode(captureMode === '360' ? null : '360')}
          >
            📸 Capturar Foto 360°
          </button>
          <button
            className={`tool-btn ${captureMode === 'image' ? 'active' : ''}`}
            onClick={() => setCaptureMode(captureMode === 'image' ? null : 'image')}
          >
            🖼️ Colocar Imagen
          </button>
          <button
            className={`tool-btn ${captureMode === 'incident' ? 'active' : ''}`}
            onClick={() => setCaptureMode(captureMode === 'incident' ? null : 'incident')}
          >
            ⚠️ Colocar Incidencia
          </button>
          {captureMode && (
            <button className="tool-btn cancel" onClick={resetCaptureMode}>
              ❌ Cancelar
            </button>
          )}
        </div>

        {/* Botones de capa */}
        <div className="toolbar-section layer-buttons">
          <button
            className={`layer-btn ${currentLayer === 'satellite' ? 'active' : ''}`}
            onClick={() => changeMapLayer('satellite')}
            title="Vista Satelital"
          >
            🛰️ Satélite
          </button>
          <button
            className={`layer-btn ${currentLayer === 'osm' ? 'active' : ''}`}
            onClick={() => changeMapLayer('osm')}
            title="OpenStreetMap"
          >
            🗺️ OSM
          </button>
          <button
            className={`layer-btn ${currentLayer === 'hybrid' ? 'active' : ''}`}
            onClick={() => changeMapLayer('hybrid')}
            title="Vista Híbrida"
          >
            🌍 Híbrido
          </button>
        </div>
      </div>

      {/* Coordenadas UTM en tiempo real */}
      <div className="utm-coordinates-display">
        <div className="coord-item">
          <span className="coord-label">Lat:</span>
          <span className="coord-value">{mouseCoords.lat.toFixed(6)}°</span>
        </div>
        <div className="coord-item">
          <span className="coord-label">Lng:</span>
          <span className="coord-value">{mouseCoords.lng.toFixed(6)}°</span>
        </div>
        {mouseCoords.utm && (
          <>
            <div className="coord-item">
              <span className="coord-label">UTM E:</span>
              <span className="coord-value">{mouseCoords.utm.easting.toFixed(2)}m</span>
            </div>
            <div className="coord-item">
              <span className="coord-label">UTM N:</span>
              <span className="coord-value">{mouseCoords.utm.northing.toFixed(2)}m</span>
            </div>
            <div className="coord-item">
              <span className="coord-label">Zona:</span>
              <span className="coord-value">{mouseCoords.utm.zone}{mouseCoords.utm.hemisphere}</span>
            </div>
          </>
        )}
      </div>

      {/* Instruction Banner */}
      {captureMode && (
        <div className="instruction-banner">
          {captureMode === '360' && '📸 Haz clic en el mapa para colocar una Foto 360°'}
          {captureMode === 'image' && '🖼️ Haz clic en el mapa para colocar una Imagen'}
          {captureMode === 'incident' && '⚠️ Haz clic en el mapa para colocar una Incidencia'}
        </div>
      )}

      {/* Map Container */}
      <div className="map-content">
        <div ref={mapRef} id="professional-map" className="professional-map"></div>
      </div>

      {/* Modal Foto 360° */}
      {showPhotoModal && (
        <div className="professional-modal-overlay">
          <div className="professional-modal">
            <div className="professional-modal-header">
              <h2>📸 Nueva Foto 360°</h2>
              <button className="modal-close-btn" onClick={resetCaptureMode}>✕</button>
            </div>
            <div className="professional-modal-body">
              <div className="form-group">
                <label>Archivo de Foto 360°:</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setPhotoFile(e.target.files[0])}
                />
              </div>
              <div className="form-group">
                <label>Altura Z (metros):</label>
                <input
                  type="number"
                  step="0.01"
                  value={zCoordinate}
                  onChange={(e) => setZCoordinate(e.target.value)}
                />
              </div>
              {selectedPosition && (
                <div className="coords-display">
                  <strong>Coordenadas seleccionadas:</strong>
                  <p>Lat: {selectedPosition[0].toFixed(6)}</p>
                  <p>Lng: {selectedPosition[1].toFixed(6)}</p>
                  <p>UTM: Zona {CoordinateService.wgs84ToUTM(selectedPosition[0], selectedPosition[1]).zone}</p>
                </div>
              )}
            </div>
            <div className="professional-modal-footer">
              <button className="btn-modal btn-modal-cancel" onClick={resetCaptureMode}>Cancelar</button>
              <button className="btn-modal btn-modal-save" onClick={handleSavePhoto360}>Guardar Foto 360°</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Imagen */}
      {showImageModal && (
        <div className="professional-modal-overlay">
          <div className="professional-modal">
            <div className="professional-modal-header">
              <h2>🖼️ Nueva Imagen</h2>
              <button className="modal-close-btn" onClick={resetCaptureMode}>✕</button>
            </div>
            <div className="professional-modal-body">
              <div className="form-group">
                <label>Archivo de Imagen:</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setImageFile(e.target.files[0])}
                />
              </div>
              <div className="form-group">
                <label>Altura Z (metros):</label>
                <input
                  type="number"
                  step="0.01"
                  value={zCoordinate}
                  onChange={(e) => setZCoordinate(e.target.value)}
                />
              </div>
              {selectedPosition && (
                <div className="coords-display">
                  <strong>Coordenadas seleccionadas:</strong>
                  <p>Lat: {selectedPosition[0].toFixed(6)}</p>
                  <p>Lng: {selectedPosition[1].toFixed(6)}</p>
                  <p>UTM: Zona {CoordinateService.wgs84ToUTM(selectedPosition[0], selectedPosition[1]).zone}</p>
                </div>
              )}
            </div>
            <div className="professional-modal-footer">
              <button className="btn-modal btn-modal-cancel" onClick={resetCaptureMode}>Cancelar</button>
              <button className="btn-modal btn-modal-save" onClick={handleSaveImage}>Guardar Imagen</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Incidencia */}
      {showIncidentModal && (
        <div className="professional-modal-overlay">
          <div className="professional-modal">
            <div className="professional-modal-header">
              <h2>⚠️ Nueva Incidencia</h2>
              <button className="modal-close-btn" onClick={resetCaptureMode}>✕</button>
            </div>
            <div className="professional-modal-body">
              <div className="form-group">
                <label>Título *:</label>
                <input
                  type="text"
                  value={incidentData.title}
                  onChange={(e) => setIncidentData({...incidentData, title: e.target.value})}
                  placeholder="Ej: Grieta en pared norte"
                />
              </div>
              <div className="form-group">
                <label>Descripción:</label>
                <textarea
                  value={incidentData.description}
                  onChange={(e) => setIncidentData({...incidentData, description: e.target.value})}
                  placeholder="Describe la incidencia..."
                  rows="4"
                />
              </div>
              <div className="form-group">
                <label>Tipo:</label>
                <select
                  value={incidentData.type}
                  onChange={(e) => setIncidentData({...incidentData, type: e.target.value})}
                >
                  <option value="defecto">Defecto</option>
                  <option value="dano">Daño</option>
                  <option value="observacion">Observación</option>
                  <option value="mejora">Mejora</option>
                </select>
              </div>
              <div className="form-group">
                <label>Gravedad:</label>
                <select
                  value={incidentData.severity}
                  onChange={(e) => setIncidentData({...incidentData, severity: e.target.value})}
                >
                  <option value="baja">Baja</option>
                  <option value="media">Media</option>
                  <option value="alta">Alta</option>
                  <option value="critica">Crítica</option>
                </select>
              </div>
              <div className="form-group">
                <label>Altura Z (metros):</label>
                <input
                  type="number"
                  step="0.01"
                  value={zCoordinate}
                  onChange={(e) => setZCoordinate(e.target.value)}
                />
              </div>
              {selectedPosition && (
                <div className="coords-display">
                  <strong>Coordenadas seleccionadas:</strong>
                  <p>Lat: {selectedPosition[0].toFixed(6)}</p>
                  <p>Lng: {selectedPosition[1].toFixed(6)}</p>
                  <p>UTM: Zona {CoordinateService.wgs84ToUTM(selectedPosition[0], selectedPosition[1]).zone}</p>
                </div>
              )}
            </div>
            <div className="professional-modal-footer">
              <button className="btn-modal btn-modal-cancel" onClick={resetCaptureMode}>Cancelar</button>
              <button className="btn-modal btn-modal-save" onClick={handleSaveIncident}>Guardar Incidencia</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProfessionalMapView;
