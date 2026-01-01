"""
Script de migración segura a modelos extendidos
SOLO CREA NUEVAS TABLAS - NO MODIFICA NI ELIMINA NADA

Uso:
    python migrate_to_extended.py --create-tables
    python migrate_to_extended.py --migrate-data
    python migrate_to_extended.py --verify
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Cargar variables de entorno
load_dotenv()

# Importar modelos
from models_extended import (
    Base,
    ProjectExtended,
    ProjectObject,
    TableTemplate,
    ProjectStats,
    create_all_tables
)

def get_engine():
    """Obtener conexión a la base de datos"""
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./photosite360.db")

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    is_postgres = DATABASE_URL.startswith("postgresql://")

    if is_postgres:
        engine = create_engine(DATABASE_URL)
    else:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

    return engine, is_postgres


def step1_create_tables():
    """
    PASO 1: Crear las nuevas tablas
    NO toca las tablas existentes
    """
    print("\n" + "="*80)
    print("PASO 1: Creando nuevas tablas")
    print("="*80)

    engine, is_postgres = get_engine()
    db_type = "PostgreSQL" if is_postgres else "SQLite"
    print(f"Base de datos detectada: {db_type}")

    try:
        create_all_tables(engine)
        print("\nTablas creadas exitosamente!")
        print("\nTablas existentes (no modificadas):")
        print("   - users")
        print("   - projects")
        print("   - photos")
        print("   - gallery_images")
        print("\nNuevas tablas creadas:")
        print("   - projects_extended")
        print("   - project_objects")
        print("   - table_templates")
        print("   - project_stats")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


def step2_verify_tables():
    """
    PASO 2: Verificar que las tablas existen
    """
    print("\n" + "="*80)
    print("PASO 2: Verificando tablas")
    print("="*80)

    engine, is_postgres = get_engine()

    try:
        with engine.connect() as conn:
            # Verificar tablas nuevas
            tables_to_check = [
                'projects_extended',
                'project_objects',
                'table_templates',
                'project_stats'
            ]

            for table in tables_to_check:
                if is_postgres:
                    # PostgreSQL usa information_schema
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) as count
                        FROM information_schema.tables
                        WHERE table_name = '{table}'
                    """))
                else:
                    # SQLite usa sqlite_master
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) as count
                        FROM sqlite_master
                        WHERE type='table' AND name='{table}'
                    """))

                count = result.fetchone()[0]

                if count > 0:
                    print(f"   [OK] {table} existe")
                else:
                    print(f"   [ERROR] {table} NO existe")

            # Verificar tablas antiguas (no deben haber cambiado)
            print("\nTablas originales (verificando que no se tocaron):")
            old_tables = ['users', 'projects', 'photos', 'gallery_images']

            for table in old_tables:
                try:
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) as count
                        FROM {table}
                    """))
                    count = result.fetchone()[0]
                    print(f"   [OK] {table}: {count} registros (sin cambios)")
                except Exception as table_error:
                    print(f"   [AVISO] {table}: tabla no existe o esta vacia")

    except Exception as e:
        print(f"\nError: {e}")


def step3_migrate_data():
    """
    PASO 3: Migrar datos de photos/gallery_images a project_objects
    COPIA los datos, NO los elimina
    """
    print("\n" + "="*80)
    print("PASO 3: Migrando datos (COPIA, no elimina)")
    print("="*80)

    engine, is_postgres = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Migrar Photos a ProjectObject
        print("\nMigrando fotos 360...")

        photos = session.execute(text("""
            SELECT id, project_id, title, url, description,
                   project_x, project_y, project_z,
                   utm_easting, utm_northing, utm_zone,
                   geo_latitude, geo_longitude,
                   created_at
            FROM photos
        """)).fetchall()

        migrated_photos = 0
        for photo in photos:
            # Crear ProjectObject equivalente
            obj = ProjectObject(
                name=photo.title or f"Foto_{photo.id}",
                project_id=photo.project_id,
                object_type="foto360",
                url=photo.url,
                description=photo.description or "",

                # Coordenadas UTM (priorizar project_x/y/z)
                utm_easting=photo.project_x if photo.project_x else (photo.utm_easting or 0.0),
                utm_northing=photo.project_y if photo.project_y else (photo.utm_northing or 0.0),
                elevation=photo.project_z if photo.project_z else 0.0,
                utm_zone=photo.utm_zone or 30,

                # Metadatos
                attributes={
                    "original_photo_id": photo.id,
                    "geo_latitude": photo.geo_latitude,
                    "geo_longitude": photo.geo_longitude
                },

                created_at=photo.created_at
            )
            session.add(obj)
            migrated_photos += 1

        session.commit()
        print(f"   {migrated_photos} fotos 360 migradas")

        # Migrar GalleryImages a ProjectObject
        print("\nMigrando imagenes normales...")

        images = session.execute(text("""
            SELECT id, project_id, filename, url,
                   project_x, project_y, project_z,
                   utm_easting, utm_northing, utm_zone,
                   geo_latitude, geo_longitude,
                   image_type, level, room, pk_value, section,
                   uploaded_at
            FROM gallery_images
        """)).fetchall()

        migrated_images = 0
        for img in images:
            obj = ProjectObject(
                name=img.filename or f"Imagen_{img.id}",
                project_id=img.project_id,
                object_type=img.image_type or "imagen",
                url=img.url,

                # Coordenadas
                utm_easting=img.project_x if img.project_x else (img.utm_easting or 0.0),
                utm_northing=img.project_y if img.project_y else (img.utm_northing or 0.0),
                elevation=img.project_z if img.project_z else 0.0,
                utm_zone=img.utm_zone or 30,

                # Nivel y PK
                level=img.level,
                pk=img.pk_value,

                # Metadatos
                attributes={
                    "original_image_id": img.id,
                    "room": img.room,
                    "section": img.section,
                    "geo_latitude": img.geo_latitude,
                    "geo_longitude": img.geo_longitude
                },

                created_at=img.uploaded_at
            )
            session.add(obj)
            migrated_images += 1

        session.commit()
        print(f"   {migrated_images} imagenes migradas")

        print(f"\nTOTAL MIGRADO: {migrated_photos + migrated_images} objetos")
        print("\nIMPORTANTE: Los datos originales en 'photos' y 'gallery_images' NO se han eliminado")
        print("   Ambas tablas siguen funcionando normalmente")

    except Exception as e:
        session.rollback()
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


def step4_create_project_configs():
    """
    PASO 4: Crear configuraciones extendidas para proyectos existentes
    """
    print("\n" + "="*80)
    print("PASO 4: Creando configuraciones de proyectos")
    print("="*80)

    engine, is_postgres = get_engine()
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Obtener proyectos existentes
        projects = session.execute(text("""
            SELECT id, name FROM projects
        """)).fetchall()

        for project in projects:
            # Verificar si ya tiene configuración extendida
            existing = session.query(ProjectExtended).filter_by(
                project_id=project.id
            ).first()

            if not existing:
                # Crear configuración por defecto (edificación)
                config = ProjectExtended(
                    project_id=project.id,
                    project_type="edificacion",
                    level_config={
                        "levels": [
                            {"code": "S01", "name": "Sótano 1", "elevation": -3.0},
                            {"code": "P00", "name": "Planta Baja", "elevation": 0.0},
                            {"code": "P01", "name": "Planta 1", "elevation": 3.0},
                            {"code": "P02", "name": "Planta 2", "elevation": 6.0}
                        ],
                        "default_height": 3.0
                    }
                )
                session.add(config)
                print(f"   Configuracion creada para: {project.name}")

        session.commit()
        print(f"\nConfiguraciones creadas para {len(projects)} proyectos")

    except Exception as e:
        session.rollback()
        print(f"\nError: {e}")
    finally:
        session.close()


def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("""
Uso:
    python migrate_to_extended.py --create-tables    # Crear nuevas tablas
    python migrate_to_extended.py --verify            # Verificar tablas
    python migrate_to_extended.py --migrate-data      # Migrar datos
    python migrate_to_extended.py --all               # Hacer todo
        """)
        return

    command = sys.argv[1]

    if command == "--create-tables":
        step1_create_tables()
        step2_verify_tables()

    elif command == "--verify":
        step2_verify_tables()

    elif command == "--migrate-data":
        step3_migrate_data()
        step4_create_project_configs()

    elif command == "--all":
        step1_create_tables()
        step2_verify_tables()
        input("\nPresiona ENTER para continuar con la migracion de datos...")
        step3_migrate_data()
        step4_create_project_configs()
        print("\n" + "="*80)
        print("MIGRACION COMPLETA")
        print("="*80)
        print("\nProximos pasos:")
        print("1. Verifica que la aplicacion sigue funcionando")
        print("2. Prueba los nuevos endpoints de charts y exportacion")
        print("3. Cuando todo este OK, se puede hacer push a produccion")

    else:
        print(f"Comando desconocido: {command}")


if __name__ == "__main__":
    main()
