import sys
import os

# Añadir directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect

# Importar Base y engine desde main
from main import Base, engine

def create_tables():
    """
    Crea todas las tablas en la base de datos
    """
    print("=" * 60)
    print("🔧 CREANDO/ACTUALIZANDO TABLAS EN LA BASE DE DATOS")
    print("=" * 60)
    
    try:
        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)
        
        # Verificar qué tablas existen
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        print("\n✅ Proceso completado exitosamente\n")
        print("📊 Tablas en la base de datos:")
        print("-" * 60)
        
        expected_tables = [
            'users',
            'projects', 
            'photos',
            'gallery_images',
            'gallery_tags',
            'project_collaborators',  # Nueva
            'invitations'  # Nueva
        ]
        
        for table in expected_tables:
            if table in existing_tables:
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} (NO EXISTE)")
        
        print("-" * 60)
        print(f"\nTotal de tablas: {len(existing_tables)}")
        
        # Mostrar estructura de nuevas tablas
        if 'project_collaborators' in existing_tables:
            print("\n📋 Estructura de 'project_collaborators':")
            cols = inspector.get_columns('project_collaborators')
            for col in cols:
                print(f"  - {col['name']}: {col['type']}")
        
        if 'invitations' in existing_tables:
            print("\n📋 Estructura de 'invitations':")
            cols = inspector.get_columns('invitations')
            for col in cols:
                print(f"  - {col['name']}: {col['type']}")
        
        print("\n" + "=" * 60)
        print("🎉 ¡Base de datos lista para usar!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR creando tablas: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    create_tables()