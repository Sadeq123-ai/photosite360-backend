import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import CameraMap3D from '../components/CameraMap3D';
import EnhancedMapView from '../components/EnhancedMapView';
import api from '../config/axios';
import toast from 'react-hot-toast';
import { 
  ArrowLeft, 
  Upload, 
  Image as ImageIcon, 
  Eye, 
  Maximize2, 
  Link2, 
  Download, 
  Trash2, 
  Map 
} from 'lucide-react';
import './ProjectDetail.css';

const ProjectDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [normalImages, setNormalImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [show3DMapFullscreen, setShow3DMapFullscreen] = useState(false);
  const [showEnhancedMap, setShowEnhancedMap] = useState(false);
  const [showFileImport, setShowFileImport] = useState(false);

  useEffect(() => {
    fetchProject();
    fetchPhotos();
    fetchNormalImages();
  }, [id]);

  const fetchProject = async () => {
    try {
      const response = await api.get(`/projects/${id}`);
      setProject(response.data);
    } catch (error) {
      console.error('Error fetching project:', error);
      toast.error('Error al cargar proyecto');
      navigate('/projects');
    } finally {
      setLoading(false);
    }
  };

  const fetchPhotos = async () => {
    try {
      const response = await api.get(`/projects/${id}/photos`);
      setPhotos(response.data);
    } catch (error) {
      console.error('Error fetching photos:', error);
    }
  };

  const fetchNormalImages = async () => {
    try {
      const response = await api.get(`/projects/${id}/gallery`);
      setNormalImages(response.data);
    } catch (error) {
      console.error('Error fetching normal images:', error);
    }
  };

  // ✅ FUNCIÓN: Subir fotos 360° + archivos TXT
  const handle360Upload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);

    const images = [];
    const txtFiles = {};

    // Separar imágenes y archivos TXT
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileName = file.name;
      const baseName = fileName.substring(0, fileName.lastIndexOf('.')) || fileName;
      const extension = fileName.split('.').pop().toLowerCase();

      if (extension === 'txt') {
        txtFiles[baseName] = file;
      } else if (['jpg', 'jpeg', 'png', 'gif'].includes(extension)) {
        images.push({ file, baseName });
      }
    }

    const uploadedPhotos = [];
    
    try {
      // Subir imágenes primero
      for (const { file, baseName } of images) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', file.name);
        formData.append('type', '360');

        const response = await api.post(`/projects/${id}/photos/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        
        toast.success(`Foto 360° "${file.name}" subida`);
        
        uploadedPhotos.push({
          id: response.data.id,
          baseName: baseName
        });
      }

      // Subir coordenadas TXT después
      for (const photoData of uploadedPhotos) {
        if (txtFiles[photoData.baseName]) {
          const txtFormData = new FormData();
          txtFormData.append('file', txtFiles[photoData.baseName]);
          
          await api.post(`/projects/${id}/photos/${photoData.id}/coordinates`, txtFormData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          });
          toast.success(`Coordenadas de "${photoData.baseName}" actualizadas`);
        }
      }

    } catch (error) {
      console.error('Error uploading photo:', error);
      toast.error('Error al subir archivos');
    }

    setUploading(false);
    await fetchPhotos();
  };

  // ✅ FUNCIÓN: Subir imágenes normales
  const handleNormalImageUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', file.name);
        formData.append('type', 'normal');

        await api.post(`/projects/${id}/gallery/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        
        toast.success(`Imagen normal "${file.name}" subida a galería`);
      }
    } catch (error) {
      console.error('Error uploading normal image:', error);
      toast.error('Error al subir imágenes normales');
    }

    setUploading(false);
    await fetchNormalImages();
  };

  const handlePhotoClick = (photo) => {
    if (photo.type === 'normal') {
      window.open(photo.url, '_blank');
    } else {
      navigate(`/projects/${id}/view/${photo.id}`);
    }
  };

  const handleDeletePhoto = async (photoId, photoTitle) => {
    if (!confirm(`¿Estás seguro de eliminar "${photoTitle}"?`)) return;

    try {
      await api.delete(`/projects/${id}/photos/${photoId}`);
      setPhotos(photos.filter(p => p.id !== photoId));
      toast.success('Foto eliminada');
    } catch (error) {
      console.error('Error deleting photo:', error);
      toast.error('Error al eliminar foto');
    }
  };

  const copyPhotoURL = (photo) => {
    const url = photo.type === 'normal' 
      ? photo.url
      : `https://photosite360-frontend.onrender.com/projects/${id}/view/${photo.id}`;
    
    navigator.clipboard.writeText(url);
    toast.success('URL copiada al portapapeles');
  };

  const exportToCSV = () => {
    const photosWithCoords = photos.filter(p => p.latitude && p.longitude);
    if (photosWithCoords.length === 0) {
      toast.error('No hay fotos con coordenadas para exportar');
      return;
    }
    
    let csv = 'Nombre de Imagen;X;Y;Z;URL Imagen\n';
    
    photosWithCoords.forEach(photo => {
      const x = (parseFloat(photo.latitude) / 1) || 0;
      const y = (parseFloat(photo.longitude) / 1) || 0;
      
      let z = 0;
      const zMatch = photo.description?.match(/z:\s*([-\d.,]+)/i);
      if (zMatch) {
        z = (parseFloat(zMatch[1]) / 1) || 0;
      }
      
      const url = `https://photosite360-frontend.onrender.com/projects/${id}/view/${photo.id}`;
      csv += `"${photo.title}";${x};${y};${z};"${url}"\n`;
    });
    
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const downloadUrl = URL.createObjectURL(blob);
    link.setAttribute('href', downloadUrl);
    link.setAttribute('download', `${project.name}_Coordenadas.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    toast.success('Archivo CSV exportado');
  };

  // ✅ FUNCIÓN: Manejar captura de imágenes desde el mapa
  const handlePhotoCapture = async (photoData) => {
    try {
      console.log('📸 Captura móvil:', photoData);

      const formData = new FormData();
      formData.append('file', photoData.file);
      formData.append('title', photoData.title || `Imagen ${new Date().toLocaleString()}`);
      formData.append('type', 'normal');
      formData.append('level', photoData.level || '');
      formData.append('room', photoData.room || '');
      formData.append('pk', photoData.pk || '');
      formData.append('comment', photoData.comment || '');

      // ✅ Coordenadas geográficas WGS84
      if (photoData.geo_latitude !== undefined && photoData.geo_longitude !== undefined) {
        formData.append('geo_latitude', photoData.geo_latitude.toString());
        formData.append('geo_longitude', photoData.geo_longitude.toString());
      } else if (photoData.latitude && photoData.longitude) {
        // Backward compatibility
        formData.append('latitude', photoData.latitude.toString());
        formData.append('longitude', photoData.longitude.toString());
      }

      // ✅ Coordenadas UTM
      if (photoData.utm_easting !== undefined) {
        formData.append('utm_easting', photoData.utm_easting.toString());
      }
      if (photoData.utm_northing !== undefined) {
        formData.append('utm_northing', photoData.utm_northing.toString());
      }
      if (photoData.utm_zone !== undefined) {
        formData.append('utm_zone', photoData.utm_zone.toString());
      }
      if (photoData.utm_hemisphere) {
        formData.append('utm_hemisphere', photoData.utm_hemisphere);
      }
      if (photoData.utm_datum) {
        formData.append('utm_datum', photoData.utm_datum);
      }

      // ✅ Coordenadas del proyecto (locales X,Y,Z)
      if (photoData.project_x !== undefined) {
        formData.append('project_x', photoData.project_x.toString());
      } else if (photoData.projectX !== undefined) {
        formData.append('project_x', photoData.projectX.toString());
      }

      if (photoData.project_y !== undefined) {
        formData.append('project_y', photoData.project_y.toString());
      } else if (photoData.projectY !== undefined) {
        formData.append('project_y', photoData.projectY.toString());
      }

      if (photoData.project_z !== undefined) {
        formData.append('project_z', photoData.project_z.toString());
      } else if (photoData.projectZ !== undefined) {
        formData.append('project_z', photoData.projectZ.toString());
      }

      await api.post(`/projects/${id}/gallery/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      toast.success('✅ Imagen guardada en galería normal');
      await fetchNormalImages();
      
    } catch (error) {
      console.error('❌ Error en captura móvil:', error);
      toast.error('Error al guardar la imagen capturada');
    }
  };

  // ✅ FUNCIÓN: Sincronizar coordenadas de fotos 360° existentes
  const handleSync360Coordinates = async () => {
    if (!confirm('¿Deseas sincronizar las coordenadas de las fotos 360° existentes? Esto calculará coordenadas reales (WGS84, UTM) basándose en la posición del mapa.')) {
      return;
    }

    try {
      toast.loading('Sincronizando coordenadas...', { id: 'sync-coords' });

      const response = await api.post(`/projects/${id}/sync-360-coordinates`);

      toast.success(
        `✅ ${response.data.message}\n${response.data.synced_count} fotos actualizadas`,
        { id: 'sync-coords', duration: 4000 }
      );

      // Recargar fotos para ver los cambios
      await fetchPhotos();

    } catch (error) {
      console.error('❌ Error sincronizando coordenadas:', error);
      const errorMsg = error.response?.data?.detail || 'Error al sincronizar coordenadas';
      toast.error(errorMsg, { id: 'sync-coords' });
    }
  };

  // ✅ FUNCIÓN: Combinar todas las fotos para el mapa
  const getAllPhotosForMap = () => {
    const photos360 = photos.map(photo => ({ ...photo, type: '360' }));
    const normalPhotos = normalImages.map(img => ({ ...img, type: 'normal' }));
    return [...photos360, ...normalPhotos];
  };

  // ✅ FILTRAR TODAS LAS FOTOS/IMÁGENES CON COORDENADAS (360° + NORMALES)
  const allPhotosForMap = getAllPhotosForMap();
  const photosWithCoords = allPhotosForMap.filter(p => {
    // Tiene coordenadas del proyecto (nuevo sistema)
    const hasProjectCoords = p.project_x !== undefined && p.project_x !== null && p.project_y !== undefined && p.project_y !== null;
    // Tiene coordenadas legacy (fotos 360 antiguas) - verificar que no sean null, undefined o strings vacíos
    const hasLegacyCoords = (p.latitude !== undefined && p.latitude !== null && p.latitude !== '' &&
                             p.longitude !== undefined && p.longitude !== null && p.longitude !== '');
    // Tiene coordenadas geo (nuevo sistema)
    const hasGeoCoords = p.geo_latitude !== undefined && p.geo_latitude !== null &&
                         p.geo_longitude !== undefined && p.geo_longitude !== null;
    return hasProjectCoords || hasLegacyCoords || hasGeoCoords;
  });

  if (loading) {
    return (
      <div className="page">
        <Navbar />
        <div className="loading">Cargando proyecto...</div>
      </div>
    );
  }

  return (
    <div className="page">
      <Navbar />
      
      <div className="container project-detail-content">
        {/* Botón volver */}
        <button className="btn-back" onClick={() => navigate('/projects')}>
          <ArrowLeft size={20} />
          Volver a proyectos
        </button>

        {/* Header del proyecto */}
        <div className="project-detail-header">
          <div>
            <h1>{project?.name}</h1>
            {project?.description && <p className="project-desc">{project.description}</p>}
            {project?.location && <p className="project-loc">📍 {project.location}</p>}
          </div>

          {/* Botones de acción */}
          <div className="project-actions">
            {photosWithCoords.length > 0 && (
              <>
                <button className="btn btn-secondary" onClick={exportToCSV}>
                  <Download size={20} />
                  Exportar CSV
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => setShowEnhancedMap(true)}
                >
                  <Map size={20} />
                  Mapa Avanzado
                </button>
              </>
            )}

            {/* Botón sincronizar coordenadas 360° */}
            {photos.length > 0 && (
              <button
                className="btn btn-warning"
                onClick={handleSync360Coordinates}
                title="Sincronizar coordenadas de fotos 360° existentes"
              >
                🔄 Sincronizar Coordenadas 360°
              </button>
            )}

            {/* Botón importar GIS/CAD */}
            <button 
              className="btn btn-secondary"
              onClick={() => setShowFileImport(true)}
            >
              🗂️ Importar GIS/CAD
            </button>
            
            {/* Botón subir imágenes normales */}
            <label className="btn btn-success upload-btn">
              <ImageIcon size={20} />
              {uploading ? 'Subiendo...' : '🖼️ Subir Imágenes Normales'}
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleNormalImageUpload}
                disabled={uploading}
                style={{ display: 'none' }}
              />
            </label>

            {/* Botón ver galería */}
            <button 
              className="btn btn-info"
              onClick={() => navigate(`/projects/${id}/gallery`)}
            >
              <Eye size={20} />
              Ver Galería Imágenes
            </button>
          </div>
        </div>

        {/* Estadísticas */}
        <div className="project-stats">
          <div className="stat-card">
            <div className="stat-number">{photos.length}</div>
            <div className="stat-label">Fotos 360°</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{normalImages.length}</div>
            <div className="stat-label">Imágenes Normales</div>
          </div>
          <div className="stat-card">
            <div className="stat-number">{photosWithCoords.length}</div>
            <div className="stat-label">Con Coordenadas</div>
          </div>
        </div>

        {/* Vista 3D - Solo si hay fotos con coordenadas */}
        {photosWithCoords.length > 0 && (
          <div className="viewer-3d-section">
            <div className="viewer-3d-header">
              <h2>Vista 3D - Navegación por Coordenadas</h2>
              <button 
                className="btn-expand"
                onClick={() => setShow3DMapFullscreen(true)}
                title="Ver en pantalla completa"
              >
                <Maximize2 size={20} />
                <span>Expandir</span>
              </button>
            </div>
            <div className="viewer-3d-container">
              <CameraMap3D
                photos={getAllPhotosForMap()}
                onPhotoClick={handlePhotoClick}
                embedded={true}
              />
            </div>
          </div>
        )}

        {/* Lista de fotos 360° */}
        <div className="photos-section">
          <h2>Fotos 360° del Proyecto ({photos.length})</h2>
          
          {photos.length > 0 ? (
            <div className="photos-grid">
              {photos.map(photo => (
                <div key={photo.id} className="photo-card">
                  {/* Botón eliminar */}
                  <button
                    className="btn-delete-photo"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeletePhoto(photo.id, photo.title)
                    }}
                    title="Eliminar foto"
                  >
                    <Trash2 size={18} />
                  </button>
                  
                  {/* Imagen con overlay */}
                  <div className="photo-image-container" onClick={() => handlePhotoClick(photo)}>
                    <img 
                      src={photo.url.startsWith('http') ? photo.url : `http://localhost:8001${photo.url}`}
                      alt={photo.title}
                      className="photo-image"
                    />
                    <div className="photo-overlay">
                      <Eye size={32} />
                      <span>Ver en 360°</span>
                    </div>
                  </div>
                  
                  {/* Información de la foto */}
                  <div className="photo-info">
                    <h4>{photo.title}</h4>
                    {photo.latitude && photo.longitude && (
                      <span className="photo-coords">
                        📍 X:{photo.latitude}, Y:{photo.longitude}
                      </span>
                    )}
                    <button 
                      className="btn-copy-url"
                      onClick={() => copyPhotoURL(photo)}
                      title="Copiar URL pública"
                    >
                      <Link2 size={16} />
                      Copiar URL
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-photos">
              <ImageIcon size={64} color="#cbd5e0" />
              <h3>No hay fotos 360° aún</h3>
              <p>Sube la primera foto 360° de este proyecto</p>
              <label className="btn btn-primary">
                <Upload size={20} />
                Subir Primera Foto 360°
                <input
                  type="file"
                  multiple
                  accept="image/*,.txt"
                  onChange={handle360Upload}
                  style={{ display: 'none' }}
                />
              </label>
            </div>
          )}
        </div>
      </div>

      {/* Modal mapa 3D en pantalla completa */}
      {show3DMapFullscreen && (
        <CameraMap3D
          photos={getAllPhotosForMap()}
          onPhotoClick={handlePhotoClick}
          onClose={() => setShow3DMapFullscreen(false)}
        />
      )}

      {/* Modal mapa avanzado */}
      {showEnhancedMap && (
        <EnhancedMapView
          photos={getAllPhotosForMap()}
          project={project}
          onClose={() => setShowEnhancedMap(false)}
          onPhotoCapture={handlePhotoCapture}
        />
      )}

      {/* Modal importar GIS/CAD */}
      {showFileImport && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>🗂️ Importar Archivos GIS/CAD</h3>
              <button className="close-btn" onClick={() => setShowFileImport(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p>Funcionalidad en desarrollo...</p>
              <p>Próximamente podrás importar:</p>
              <ul>
                <li>📁 KML/KMZ - Datos de Google Earth</li>
                <li>📐 DWG - Planos de AutoCAD</li>
                <li>🗺️ Shapefile - Datos GIS profesionales</li>
              </ul>
              <button 
                className="btn btn-primary"
                onClick={() => setShowFileImport(false)}
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectDetail;