"""
Modelos extendidos para sistema GIS/BIM profesional
NUEVOS modelos que convivirán con los actuales hasta migración completa
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import os

Base = declarative_base()

# Detectar si estamos usando PostgreSQL o SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./photosite360.db")
IS_POSTGRES = DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")

# Usar JSONB para PostgreSQL, JSON para SQLite
JSONType = JSONB if IS_POSTGRES else JSON

# ============================================================================
# MODELO: ProjectExtended (Configuración ampliada de proyectos)
# ============================================================================

class ProjectExtended(Base):
    """
    Extensión de configuración para proyectos
    Se vincula con la tabla 'projects' existente
    """
    __tablename__ = "projects_extended"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, unique=True, index=True)  # FK a projects.id

    # 🏢 TIPO DE PROYECTO
    project_type = Column(String, default="edificacion")
    # Valores: "edificacion" o "obra_lineal"

    # 📐 CONFIGURACIÓN DE NIVELES (EDIFICACIÓN)
    level_config = Column(JSONType, default={
        "levels": [
            {"code": "S01", "name": "Sótano 1", "elevation": -3.0},
            {"code": "P00", "name": "Planta Baja", "elevation": 0.0},
            {"code": "P01", "name": "Planta 1", "elevation": 3.0},
            {"code": "P02", "name": "Planta 2", "elevation": 6.0}
        ],
        "default_height": 3.0
    })

    # 🛣️ CONFIGURACIÓN DE PKs (OBRA LINEAL)
    pk_config = Column(JSONType, default={
        "pk_start": 0.0,
        "pk_end": 1000.0,
        "interval": 20.0,
        "axis_name": "Eje 1"
    })

    # 🔗 Integración BIM/CAD
    revit_file_id = Column(String, nullable=True)
    civil3d_file_path = Column(String, nullable=True)
    ifc_file_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


# ============================================================================
# MODELO: ProjectObject (Objetos unificados con soporte GIS)
# ============================================================================

class ProjectObject(Base):
    """
    Modelo unificado para todos los objetos del proyecto
    Reemplazará gradualmente a Photo y GalleryImage
    """
    __tablename__ = "project_objects"

    # 🆔 Identificación
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, index=True)  # FK a projects.id
    name = Column(String)

    # 📸 TIPO DE OBJETO
    object_type = Column(String, index=True)
    # Valores: "foto360", "imagen", "incidencia", "punto_control", "elemento_bim"

    # 🏷️ Clasificación y organización
    group_name = Column(String, nullable=True, index=True)
    tags = Column(JSONType, default=[])  # Array de tags

    # 📐 COORDENADAS UTM ETRS89 (SIEMPRE PRESENTES)
    utm_zone = Column(Integer, default=30)  # 28, 29, 30, 31
    utm_easting = Column(Float, nullable=False, default=0.0)   # X
    utm_northing = Column(Float, nullable=False, default=0.0)  # Y
    elevation = Column(Float, nullable=False, default=0.0)      # Z

    # 🏢 EDIFICACIÓN - Nivel
    level = Column(String, nullable=True, index=True)
    # Valores: "S01", "P00", "P01", "P02", etc.
    level_elevation = Column(Float, nullable=True)

    # 🛣️ OBRA LINEAL - PK
    pk = Column(Float, nullable=True, index=True)
    pk_offset = Column(Float, default=0.0)  # Desplazamiento lateral
    axis = Column(String, nullable=True)     # Nombre del eje

    # 📝 Información general
    description = Column(Text, nullable=True)
    url = Column(String, nullable=True)  # Cloudinary URL

    # 💬 COMENTARIOS (Array de objetos)
    comments = Column(JSONType, default=[])
    # Formato: [{"text": "...", "user": "...", "date": "...", "user_id": 1}]

    # 🎨 CAMPOS PERSONALIZADOS (Totalmente flexible)
    attributes = Column(JSONType, default={})
    # Ejemplos:
    # {"severidad": "crítico", "responsable": "Juan", "temperatura": 25.5}

    # 🔗 INTEGRACIÓN BIM/GIS
    ifc_guid = Column(String, nullable=True, index=True)
    revit_element_id = Column(String, nullable=True)
    civil3d_handle = Column(String, nullable=True)
    cloudcompare_id = Column(String, nullable=True)

    # 📅 Auditoría
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    created_by = Column(Integer, nullable=True)  # FK a users.id

    # 📊 Índices compuestos para queries rápidos
    __table_args__ = (
        Index('idx_project_type', 'project_id', 'object_type'),
        Index('idx_project_level', 'project_id', 'level'),
        Index('idx_project_pk', 'project_id', 'pk'),
        Index('idx_project_date', 'project_id', 'created_at'),
        Index('idx_project_group', 'project_id', 'group_name'),
    )


# ============================================================================
# MODELO: TableTemplate (Plantillas de tablas personalizadas)
# ============================================================================

class TableTemplate(Base):
    """
    Plantillas guardadas para exportación de tablas personalizadas
    """
    __tablename__ = "table_templates"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, index=True)
    name = Column(String)
    description = Column(Text, nullable=True)

    # Configuración de la tabla
    config = Column(JSONType)
    # {
    #   "filters": {"object_type": "incidencia", "level": "P01"},
    #   "columns": ["name", "utm_easting", "utm_northing", "elevation"],
    #   "export_format": "excel",
    #   "options": {"include_charts": true}
    # }

    is_public = Column(Boolean, default=False)
    created_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# MODELO: ProjectStats (Estadísticas precalculadas para charts)
# ============================================================================

class ProjectStats(Base):
    """
    Estadísticas precalculadas para mejorar performance de charts
    Se actualiza cada vez que cambian los objetos del proyecto
    """
    __tablename__ = "project_stats"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, unique=True, index=True)

    # Contadores generales
    total_objects = Column(Integer, default=0)
    total_fotos360 = Column(Integer, default=0)
    total_imagenes = Column(Integer, default=0)
    total_incidencias = Column(Integer, default=0)

    # Incidencias por severidad
    incidencias_criticas = Column(Integer, default=0)
    incidencias_moderadas = Column(Integer, default=0)
    incidencias_leves = Column(Integer, default=0)

    # Por nivel (JSONB para flexibilidad)
    stats_by_level = Column(JSONType, default={})
    # {"P00": {"incidencias": 5, "fotos": 10}, "P01": {...}}

    # Por PK (obra lineal)
    stats_by_pk_range = Column(JSONType, default={})
    # {"0-100": {"incidencias": 3}, "100-200": {...}}

    # Última actualización
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# FUNCIONES DE UTILIDAD
# ============================================================================

def create_all_tables(engine):
    """
    Crear todas las nuevas tablas
    NO afecta a las tablas existentes (photos, gallery_images)
    """
    Base.metadata.create_all(bind=engine)
    print("Nuevas tablas creadas:")
    print("   - projects_extended")
    print("   - project_objects")
    print("   - table_templates")
    print("   - project_stats")


def get_project_type(project_extended) -> str:
    """Obtener tipo de proyecto"""
    return project_extended.project_type if project_extended else "edificacion"


def get_levels(project_extended) -> list:
    """Obtener configuración de niveles"""
    if not project_extended or not project_extended.level_config:
        return [
            {"code": "P00", "name": "Planta Baja", "elevation": 0.0},
            {"code": "P01", "name": "Planta 1", "elevation": 3.0}
        ]
    return project_extended.level_config.get("levels", [])


def format_pk(pk_value: float) -> str:
    """
    Formatear PK al formato estándar: X+XXX.XX
    Ejemplo: 125.50 → "0+125.50"
    """
    km = int(pk_value / 1000)
    metros = pk_value % 1000
    return f"{km}+{metros:06.2f}"
