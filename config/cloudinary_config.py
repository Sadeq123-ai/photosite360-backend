import cloudinary
import cloudinary.uploader
import cloudinary.api

# Configuración de Cloudinary
cloudinary.config(
    cloud_name="dryuzad8w",
    api_key="281976991233177",
    api_secret="oVv51LHUFYrmmux8oFuU0t-836s",
    secure=True
)

def get_cloudinary_config():
    """Retorna la configuración de Cloudinary"""
    return {
        'cloud_name': "dryuzad8w",
        'api_key': "281976991233177",
        'api_secret': "oVv51LHUFYrmmux8oFuU0t-836s"
    }