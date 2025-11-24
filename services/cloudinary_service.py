import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class CloudinaryService:
    """Servicio para gestión de archivos en Cloudinary"""
    
    @staticmethod
    def delete_project_folder(project_id: int) -> Dict:
        """
        Elimina TODA la carpeta del proyecto en Cloudinary
        
        Args:
            project_id: ID del proyecto
        
        Returns:
            Dict con resultado de la eliminación
        """
        try:
            folder_prefix = f"photosite360/project_{project_id}"
            gallery_folder = f"photosite360/gallery/project_{project_id}"
            
            deleted_count = 0
            failed_count = 0
            
            print(f"🗑️ Eliminando carpeta del proyecto {project_id}...")
            
            # 1. Eliminar fotos 360°
            resources_360 = CloudinaryService._get_all_resources_in_folder(folder_prefix)
            for resource in resources_360:
                if CloudinaryService.delete_photo(resource['public_id']):
                    deleted_count += 1
                else:
                    failed_count += 1
            
            # 2. Eliminar galería
            resources_gallery = CloudinaryService._get_all_resources_in_folder(gallery_folder)
            for resource in resources_gallery:
                if CloudinaryService.delete_photo(resource['public_id']):
                    deleted_count += 1
                else:
                    failed_count += 1
            
            # 3. Eliminar carpetas vacías
            try:
                cloudinary.api.delete_folder(folder_prefix)
            except:
                pass
            
            try:
                cloudinary.api.delete_folder(gallery_folder)
            except:
                pass
            
            print(f"✅ Carpeta eliminada: {deleted_count} archivos")
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'failed_count': failed_count,
                'message': f'Eliminados {deleted_count} archivos del proyecto {project_id}'
            }
            
        except Exception as e:
            print(f"❌ Error eliminando carpeta: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'deleted_count': 0,
                'failed_count': 0
            }
    
    @staticmethod
    def delete_photo(public_id: str) -> bool:
        """
        Elimina una foto específica de Cloudinary
        
        Args:
            public_id: ID público de la foto en Cloudinary
        
        Returns:
            True si se eliminó correctamente
        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            
            if result.get('result') == 'ok':
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Error eliminando foto {public_id}: {str(e)}")
            return False
    
    @staticmethod
    def _get_all_resources_in_folder(folder_prefix: str) -> List[Dict]:
        """
        Obtiene todos los recursos en una carpeta
        
        Args:
            folder_prefix: prefijo de la carpeta
        
        Returns:
            Lista de recursos
        """
        all_resources = []
        next_cursor = None
        
        try:
            while True:
                result = cloudinary.api.resources(
                    type="upload",
                    prefix=folder_prefix,
                    max_results=500,
                    next_cursor=next_cursor
                )
                
                all_resources.extend(result.get('resources', []))
                
                next_cursor = result.get('next_cursor')
                if not next_cursor:
                    break
            
            print(f"📊 Encontrados {len(all_resources)} recursos en {folder_prefix}")
            return all_resources
            
        except Exception as e:
            print(f"❌ Error obteniendo recursos: {str(e)}")
            return []
    
    @staticmethod
    def get_project_storage_info(project_id: int) -> Dict:
        """
        Obtiene información de almacenamiento del proyecto
        """
        try:
            folder_360 = f"photosite360/project_{project_id}"
            folder_gallery = f"photosite360/gallery/project_{project_id}"
            
            resources_360 = CloudinaryService._get_all_resources_in_folder(folder_360)
            resources_gallery = CloudinaryService._get_all_resources_in_folder(folder_gallery)
            
            all_resources = resources_360 + resources_gallery
            total_size = sum(r.get('bytes', 0) for r in all_resources)
            
            return {
                'project_id': project_id,
                'total_files': len(all_resources),
                'photos_360': len(resources_360),
                'gallery_images': len(resources_gallery),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo info: {str(e)}")
            return {}