import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import ImageUploader from '../components/ImageUploader'
import TagManager from '../components/TagManager'
import TagSelector from '../components/TagSelector'
import CoordinateAssignmentModal from '../components/CoordinateAssignmentModal'
import api from '../config/axios'
import './ImageGallery.css'

const ImageGallery = () => {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [images, setImages] = useState([])
  const [showUploader, setShowUploader] = useState(false)
  const [showTagManager, setShowTagManager] = useState(false)
  const [tags, setTags] = useState([])
  const [imageTags, setImageTags] = useState({})
  const [selectedImage, setSelectedImage] = useState(null)
  const [showImageModal, setShowImageModal] = useState(false)
  const [showCoordinateModal, setShowCoordinateModal] = useState(false)
  const [imageForCoordinates, setImageForCoordinates] = useState(null)

  // ✅ ETIQUETAS PREDEFINIDAS
  const predefinedTags = [
    { id: 'p00', name: 'P00', color: '#3b82f6', predefined: true, category: 'Planta' },
    { id: 'p01', name: 'P01', color: '#3b82f6', predefined: true, category: 'Planta' },
    { id: 'p02', name: 'P02', color: '#3b82f6', predefined: true, category: 'Planta' },
    { id: 'p03', name: 'P03', color: '#3b82f6', predefined: true, category: 'Planta' },
    { id: 'p04', name: 'P04', color: '#3b82f6', predefined: true, category: 'Planta' },
    { id: 's01', name: 'S01', color: '#10b981', predefined: true, category: 'Sección' },
    { id: 's02', name: 'S02', color: '#10b981', predefined: true, category: 'Sección' },
    { id: 's03', name: 'S03', color: '#10b981', predefined: true, category: 'Sección' },
    { id: 'salon', name: 'Salon', color: '#f59e0b', predefined: true, category: 'Espacio' },
    { id: 'cocina', name: 'Cocina', color: '#f59e0b', predefined: true, category: 'Espacio' },
    { id: 'baño', name: 'Baño', color: '#f59e0b', predefined: true, category: 'Espacio' },
    { id: 'dormitorio', name: 'Dormitorio', color: '#f59e0b', predefined: true, category: 'Espacio' },
    { id: 'oficina', name: 'Oficina', color: '#f59e0b', predefined: true, category: 'Espacio' },
    { id: 'terraza', name: 'Terraza', color: '#f59e0b', predefined: true, category: 'Espacio' },
    { id: 'garaje', name: 'Garaje', color: '#f59e0b', predefined: true, category: 'Espacio' },
    { id: 'fachada', name: 'Fachada', color: '#ef4444', predefined: true, category: 'Exterior' },
    { id: 'jardin', name: 'Jardin', color: '#ef4444', predefined: true, category: 'Exterior' },
    { id: 'piscina', name: 'Piscina', color: '#ef4444', predefined: true, category: 'Exterior' },
  ]

  useEffect(() => {
    fetchProject()
    fetchImages()
    loadTags()
  }, [id])

  // ✅ CARGAR ETIQUETAS DEL LOCALSTORAGE
  const loadTags = () => {
    try {
      const savedTags = JSON.parse(localStorage.getItem(`project_${id}_tags`) || '[]')
      setTags([...predefinedTags, ...savedTags])
    } catch (error) {
      console.error('Error cargando etiquetas:', error)
      setTags(predefinedTags)
    }
  }

  const fetchProject = async () => {
    try {
      const response = await api.get(`/projects/${id}`)
      setProject(response.data)
    } catch (error) {
      console.error('Error cargando proyecto:', error)
    } finally {
      setLoading(false)
    }
  }

  // ✅ FUNCIÓN MEJORADA: Eliminar imagen
  const deleteImage = async (imageId) => {
    if (!window.confirm('¿Estás seguro de que quieres eliminar esta imagen?')) {
      return
    }

    try {
      console.log(`🗑️ Eliminando imagen ${imageId}...`)
      await api.delete(`/projects/${id}/gallery/${imageId}`)
      
      const updatedImages = images.filter(img => img.id !== imageId)
      setImages(updatedImages)
      
      const updatedImageTags = { ...imageTags }
      delete updatedImageTags[imageId]
      setImageTags(updatedImageTags)
      
      console.log('✅ Imagen eliminada correctamente')
      alert('Imagen eliminada correctamente')
      
    } catch (error) {
      console.error('Error eliminando imagen:', error)
      alert('Error al eliminar la imagen. Por favor, intenta nuevamente.')
    }
  }

  const fetchImages = async () => {
    try {
      console.log(`🔄 Cargando imágenes desde API para proyecto ${id}...`)
      const response = await api.get(`/projects/${id}/gallery`)
      setImages(response.data)
      console.log(`✅ ${response.data.length} imágenes cargadas desde API`)
      
      const initialImageTags = {}
      response.data.forEach(image => {
        initialImageTags[image.id] = []
      })
      setImageTags(initialImageTags)
      
    } catch (error) {
      console.error('Error cargando imágenes desde API:', error)
      try {
        const savedImages = JSON.parse(localStorage.getItem(`project_${id}_gallery`) || '[]')
        if (savedImages.length > 0) {
          setImages(savedImages)
          console.log('📸 Imágenes cargadas desde localStorage como respaldo')
        }
      } catch (localError) {
        console.error('Error cargando desde localStorage:', localError)
      }
    }
  }

  const handleUploadComplete = (newImages) => {
    const updatedImages = [...images, ...newImages]
    setImages(updatedImages)
    setShowUploader(false)
    
    const newImageTags = { ...imageTags }
    newImages.forEach(image => {
      newImageTags[image.id] = []
    })
    setImageTags(newImageTags)
    
    console.log('✅ Nuevas imágenes añadidas:', newImages)
  }

  // ✅ MANEJAR ACTUALIZACIÓN DE ETIQUETAS
  const handleTagsUpdate = (updatedTags) => {
    setTags(updatedTags)
    const updatedImageTags = { ...imageTags }
    Object.keys(updatedImageTags).forEach(imageId => {
      updatedImageTags[imageId] = updatedImageTags[imageId].filter(tag => 
        updatedTags.find(t => t.id === tag.id)
      )
    })
    setImageTags(updatedImageTags)
  }

  // ✅ NUEVA FUNCIÓN: Abrir imagen en modal
  const openImageModal = (image) => {
    setSelectedImage(image)
    setShowImageModal(true)
  }

  // ✅ NUEVA FUNCIÓN: Copiar URL única
  const copyUniqueUrl = (image) => {
    const uniqueUrl = image.unique_url || image.url
    navigator.clipboard.writeText(uniqueUrl)
    alert('URL única copiada al portapapeles')
  }

  // ✅ NUEVA FUNCIÓN: Abrir modal de asignación de coordenadas
  const openCoordinateAssignment = (image) => {
    setImageForCoordinates(image)
    setShowCoordinateModal(true)
  }

  // ✅ NUEVA FUNCIÓN: Guardar coordenadas asignadas
  const handleCoordinatesSave = async (coordinates) => {
    try {
      console.log('[COORDS] Guardando coordenadas para imagen:', imageForCoordinates.id, coordinates)

      await api.put(`/projects/${id}/gallery/${imageForCoordinates.id}/coordinates`, coordinates)

      // Actualizar la imagen en el estado local
      setImages(prevImages =>
        prevImages.map(img =>
          img.id === imageForCoordinates.id
            ? { ...img, ...coordinates }
            : img
        )
      )

      setShowCoordinateModal(false)
      setImageForCoordinates(null)
      alert('Coordenadas asignadas correctamente. Las imágenes ahora aparecerán en el mapa avanzado.')

      // Recargar imágenes para asegurar sincronización
      fetchImages()

    } catch (error) {
      console.error('[COORDS] Error guardando coordenadas:', error)
      alert('Error al guardar las coordenadas. Por favor, intenta nuevamente.')
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Cargando galería...</p>
      </div>
    )
  }

  return (
    <div className="image-gallery-page">
      <Navbar />
      
      <div className="gallery-container">
        <div className="gallery-header">
          <button 
            className="btn-back"
            onClick={() => navigate(`/projects/${id}`)}
          >
            ← Volver al Proyecto
          </button>
          
          <div className="gallery-title">
            <h1>🖼️ Galería de Imágenes Normales</h1>
            <p>{project?.name} - Imágenes con etiquetas y coordenadas opcionales</p>
          </div>

          <div className="gallery-actions">
            <button 
              className="btn btn-secondary"
              onClick={() => setShowTagManager(!showTagManager)}
            >
              🏷️ Gestionar Etiquetas
            </button>
            <button 
              className="btn btn-primary"
              onClick={() => setShowUploader(!showUploader)}
            >
              {showUploader ? '← Cancelar' : '📤 Subir Imágenes'}
            </button>
          </div>
        </div>

        <div className="gallery-content">
          {showUploader ? (
            <div className="upload-section">
              <ImageUploader 
                projectId={id}
                onUploadComplete={handleUploadComplete}
              />
            </div>
          ) : showTagManager ? (
            <div className="tag-manager-section">
              <TagManager 
                projectId={id}
                onTagsUpdate={handleTagsUpdate}
              />
            </div>
          ) : (
            <>
              {/* Estadísticas mejoradas */}
              <div className="gallery-stats">
                <div className="stat-card">
                  <div className="stat-number">{images.length}</div>
                  <div className="stat-label">Imágenes Totales</div>
                </div>
                <div className="stat-card">
                  <div className="stat-number">
                    {images.filter(img => !imageTags[img.id] || imageTags[img.id].length === 0).length}
                  </div>
                  <div className="stat-label">Sin Etiquetar</div>
                </div>
                <div className="stat-card">
                  <div className="stat-number">{tags.length}</div>
                  <div className="stat-label">Etiquetas Creadas</div>
                </div>
                <div className="stat-card">
                  <div className="stat-number">
                    {images.filter(img => (img.geo_latitude && img.geo_longitude) || (img.latitude && img.longitude)).length}
                  </div>
                  <div className="stat-label">Con Coordenadas</div>
                </div>
              </div>

              {/* Galería de imágenes */}
              {images.length > 0 ? (
                <div className="images-grid">
                  <div className="images-header">
                    <h3>Tus Imágenes ({images.length})</h3>
                    <button 
                      className="btn btn-secondary"
                      onClick={() => setShowUploader(true)}
                    >
                      📤 Subir Más
                    </button>
                  </div>
                  
                  <div className="images-grid-content">
                    {images.map((image, index) => (
                      <div key={index} className="image-card">
                        <div className="image-container">
                          <img 
                            src={image.url} 
                            alt={image.filename}
                            onClick={() => openImageModal(image)}
                          />
                          {/* Indicador de coordenadas */}
                          {((image.geo_latitude && image.geo_longitude) || (image.latitude && image.longitude)) && (
                            <div className="coordinates-badge" title="Tiene coordenadas en el mapa">
                              📍
                            </div>
                          )}
                        </div>
                        
                        <div className="image-info">
                          <span className="image-filename">{image.filename}</span>
                          <span className="image-url">ID: {image.unique_url}</span>
                          
                          {/* Información de coordenadas */}
                          {((image.geo_latitude && image.geo_longitude) || (image.latitude && image.longitude)) && (
                            <div className="coordinates-info">
                              <small>📍 X: {image.project_x?.toFixed(2) || image.latitude}, Y: {image.project_y?.toFixed(2) || image.longitude}</small>
                              {image.project_z !== null && image.project_z !== undefined && (
                                <small>, Z: {image.project_z.toFixed(2)}m</small>
                              )}
                            </div>
                          )}

                          {/* Selector de etiquetas */}
                          <div className="image-tags-section">
                            <label className="tags-label">Etiquetas:</label>
                            <TagSelector
                              projectId={id}
                              selectedTags={imageTags[image.id] || []}
                              onTagsChange={(newTags) => {
                                setImageTags(prev => ({
                                  ...prev,
                                  [image.id]: newTags
                                }))
                              }}
                              availableTags={tags}
                              maxHeight={150}
                            />
                          </div>

                          <div className="image-actions">
                            <button
                              className="btn-action"
                              onClick={() => copyUniqueUrl(image)}
                              title="Copiar URL único"
                            >
                              📋
                            </button>
                            <button
                              className="btn-action"
                              onClick={() => openCoordinateAssignment(image)}
                              title={image.geo_latitude ? "Actualizar coordenadas" : "Asignar coordenadas"}
                            >
                              📍
                            </button>
                            <button
                              className="btn-action"
                              onClick={() => {
                                const link = document.createElement('a')
                                link.href = image.url
                                link.download = image.filename
                                link.click()
                              }}
                              title="Descargar"
                            >
                              ⬇️
                            </button>
                            <button
                              className="btn-action btn-delete"
                              onClick={() => deleteImage(image.id)}
                              title="Eliminar imagen"
                            >
                              🗑️
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="empty-gallery">
                  <div className="empty-icon">🖼️</div>
                  <h3>Galería Vacía</h3>
                  <p>No hay imágenes normales en la galería todavía.</p>
                  <button 
                    className="btn btn-primary"
                    onClick={() => setShowUploader(true)}
                  >
                    📤 Subir Primera Imagen
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Modal para ver imagen */}
      {showImageModal && selectedImage && (
        <div className="image-modal-overlay" onClick={() => setShowImageModal(false)}>
          <div className="image-modal-content" onClick={(e) => e.stopPropagation()}>
            <button
              className="modal-close"
              onClick={() => setShowImageModal(false)}
            >
              ✕
            </button>
            <img src={selectedImage.url} alt={selectedImage.filename} />
            <div className="image-modal-info">
              <h3>{selectedImage.filename}</h3>
              <p>ID: {selectedImage.unique_url}</p>
              {((selectedImage.geo_latitude && selectedImage.geo_longitude) || (selectedImage.latitude && selectedImage.longitude)) && (
                <p>📍 Coordenadas: X: {selectedImage.project_x?.toFixed(2) || selectedImage.latitude}, Y: {selectedImage.project_y?.toFixed(2) || selectedImage.longitude}
                {selectedImage.project_z !== null && selectedImage.project_z !== undefined && (
                  <span>, Z: {selectedImage.project_z.toFixed(2)}m</span>
                )}
                </p>
              )}
              <button
                className="btn btn-secondary"
                onClick={() => copyUniqueUrl(selectedImage)}
              >
                📋 Copiar URL
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal para asignar coordenadas */}
      {showCoordinateModal && imageForCoordinates && (
        <CoordinateAssignmentModal
          image={imageForCoordinates}
          project={project}
          onClose={() => {
            setShowCoordinateModal(false)
            setImageForCoordinates(null)
          }}
          onSave={handleCoordinatesSave}
        />
      )}
    </div>
  )
}

export default ImageGallery