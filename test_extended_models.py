"""
Script de prueba para verificar que los nuevos modelos funcionan correctamente
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_extended import (
    ProjectExtended,
    ProjectObject,
    TableTemplate,
    ProjectStats
)

load_dotenv()

def get_engine():
    """Obtener engine de base de datos"""
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./photosite360.db")

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    if DATABASE_URL.startswith("postgresql://"):
        engine = create_engine(DATABASE_URL)
    else:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    return engine

def test_models():
    """Probar que los modelos funcionan correctamente"""

    print("\n" + "="*80)
    print("PRUEBA DE MODELOS EXTENDIDOS")
    print("="*80)

    engine = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Crear configuración de proyecto (edificación)
        print("\n1. Creando configuracion de proyecto (edificacion)...")
        config = ProjectExtended(
            project_id=999,  # ID de prueba
            project_type="edificacion",
            level_config={
                "levels": [
                    {"code": "S01", "name": "Sotano 1", "elevation": -3.0},
                    {"code": "P00", "name": "Planta Baja", "elevation": 0.0},
                    {"code": "P01", "name": "Planta 1", "elevation": 3.0}
                ],
                "default_height": 3.0
            }
        )
        session.add(config)
        session.commit()
        print("   [OK] Configuracion de proyecto creada con ID:", config.id)

        # 2. Crear objeto de prueba (foto 360)
        print("\n2. Creando objeto de prueba (foto 360)...")
        obj = ProjectObject(
            name="Foto de prueba",
            project_id=999,
            object_type="foto360",
            url="https://example.com/foto.jpg",
            description="Foto de prueba del sistema",

            # Coordenadas UTM
            utm_zone=30,
            utm_easting=500000.0,
            utm_northing=4500000.0,
            elevation=10.5,

            # Nivel (edificación)
            level="P00",

            # Campos personalizados
            attributes={
                "autor": "Sistema",
                "camara": "Test Camera",
                "calidad": "alta"
            },

            # Comentarios
            comments=[
                {
                    "text": "Primer comentario de prueba",
                    "user": "Admin",
                    "date": "2025-01-01",
                    "user_id": 1
                }
            ]
        )
        session.add(obj)
        session.commit()
        print("   [OK] Objeto creado con ID:", obj.id)

        # 3. Crear plantilla de tabla
        print("\n3. Creando plantilla de tabla...")
        template = TableTemplate(
            project_id=999,
            name="Incidencias por nivel",
            description="Tabla de incidencias agrupadas por nivel",
            config={
                "filters": {"object_type": "incidencia"},
                "columns": ["name", "level", "utm_easting", "utm_northing"],
                "export_format": "excel"
            },
            is_public=True,
            created_by=1
        )
        session.add(template)
        session.commit()
        print("   [OK] Plantilla creada con ID:", template.id)

        # 4. Crear estadísticas
        print("\n4. Creando estadisticas...")
        stats = ProjectStats(
            project_id=999,
            total_objects=1,
            total_fotos360=1,
            total_imagenes=0,
            total_incidencias=0,
            stats_by_level={
                "P00": {"fotos": 1, "imagenes": 0, "incidencias": 0}
            }
        )
        session.add(stats)
        session.commit()
        print("   [OK] Estadisticas creadas con ID:", stats.id)

        # 5. Verificar que podemos leer los datos
        print("\n5. Verificando lectura de datos...")

        # Leer configuración
        config_read = session.query(ProjectExtended).filter_by(project_id=999).first()
        print(f"   [OK] Config leida: tipo={config_read.project_type}, niveles={len(config_read.level_config['levels'])}")

        # Leer objeto
        obj_read = session.query(ProjectObject).filter_by(project_id=999).first()
        print(f"   [OK] Objeto leido: {obj_read.name} ({obj_read.object_type})")
        print(f"        UTM: {obj_read.utm_easting}, {obj_read.utm_northing}, Z={obj_read.elevation}")
        print(f"        Nivel: {obj_read.level}")
        print(f"        Atributos: {obj_read.attributes}")
        print(f"        Comentarios: {len(obj_read.comments)}")

        # 6. Limpiar datos de prueba
        print("\n6. Limpiando datos de prueba...")
        session.delete(stats)
        session.delete(template)
        session.delete(obj)
        session.delete(config)
        session.commit()
        print("   [OK] Datos de prueba eliminados")

        print("\n" + "="*80)
        print("TODAS LAS PRUEBAS PASARON CORRECTAMENTE")
        print("="*80)
        print("\nLos nuevos modelos estan listos para usar!")
        print("- ProjectExtended: Configuracion de proyectos")
        print("- ProjectObject: Objetos unificados con coordenadas UTM")
        print("- TableTemplate: Plantillas de tablas personalizadas")
        print("- ProjectStats: Estadisticas precalculadas")

    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] Fallo en las pruebas: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    test_models()
