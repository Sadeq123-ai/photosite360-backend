import cloudinary
import cloudinary.api
from main import SessionLocal, User, Project, Photo
from datetime import datetime

# Configurar Cloudinary
cloudinary.config(
    cloud_name="dryuzad8w",
    api_key="281976991233177",
    api_secret="oVv51LHUFYrmmux8oFuU0t-836s"
)

db = SessionLocal()

print("🔄 RECUPERANDO PROYECTO 10 DE CLOUDINARY...")
print("=" * 70)

try:
    # Buscar tu usuario
    user = db.query(User).filter(User.email == "ASCH360@aschinfraestructuras.com").first()
    if not user:
        print("❌ Usuario ASCH360 no encontrado")
        exit(1)
    
    print(f"👤 Usuario: {user.email} (ID: {user.id})")
    
    # Obtener fotos del project_10
    print("\n📥 Obteniendo fotos del project_10...")
    
    next_cursor = None
    project_10_resources = []
    
    while True:
        result = cloudinary.api.resources(
            type="upload",
            prefix="photosite360/project_10/",
            max_results=500,
            next_cursor=next_cursor
        )
        
        project_10_resources.extend(result.get('resources', []))
        next_cursor = result.get('next_cursor')
        
        if not next_cursor:
            break
    
    print(f"✅ {len(project_10_resources)} fotos encontradas en project_10")
    
    # Verificar si el proyecto 10 ya existe
    existing_project = db.query(Project).filter(Project.id == 10).first()
    
    if existing_project:
        print(f"\n⚠️  Ya existe un proyecto con ID 10:")
        print(f"   Nombre: {existing_project.name}")
        print(f"   Owner: {existing_project.owner_id}")
        
        response = input("\n¿Deseas SOBRESCRIBIR este proyecto? (S/N): ")
        
        if response.upper() != 'S':
            print("❌ Operación cancelada")
            exit(0)
        
        # Eliminar fotos antiguas
        db.query(Photo).filter(Photo.project_id == 10).delete()
        
        # Actualizar proyecto
        existing_project.name = "Proyecto ASCH - Ayto Écija"
        existing_project.description = f"Proyecto recuperado con {len(project_10_resources)} fotos 360°"
        existing_project.location = "Ayuntamiento de Écija"
        existing_project.owner_id = user.id
        existing_project.is_public = 0
        
        project = existing_project
        print("✅ Proyecto 10 actualizado")
        
    else:
        # Crear proyecto con ID específico
        # Primero crear proyecto temporal para obtener ID
        temp_project = Project(
            name="temp",
            owner_id=user.id
        )
        db.add(temp_project)
        db.flush()
        
        # Si el ID asignado no es 10, ajustar
        if temp_project.id != 10:
            db.delete(temp_project)
            db.flush()
            
            # Insertar directamente con ID 10 usando SQLAlchemy text
            from sqlalchemy import text
            db.execute(
                text("INSERT INTO projects (id, name, description, location, is_public, owner_id, created_at) VALUES (:id, :name, :desc, :loc, :pub, :owner, :created)"),
                {
                    "id": 10,
                    "name": "Proyecto ASCH - Ayto Écija",
                    "desc": f"Proyecto recuperado con {len(project_10_resources)} fotos 360°",
                    "loc": "Ayuntamiento de Écija",
                    "pub": 0,
                    "owner": user.id,
                    "created": datetime.utcnow()
                }
            )
            db.commit()
            project = db.query(Project).filter(Project.id == 10).first()
        else:
            temp_project.name = "Proyecto ASCH - Ayto Écija"
            temp_project.description = f"Proyecto recuperado con {len(project_10_resources)} fotos 360°"
            temp_project.location = "Ayuntamiento de Écija"
            temp_project.is_public = 0
            project = temp_project
        
        print(f"✅ Proyecto 10 creado: {project.name}")
    
    # Importar fotos
    print(f"\n📸 Importando {len(project_10_resources)} fotos...")
    
    photos_imported = 0
    for i, resource in enumerate(project_10_resources, 1):
        # Extraer nombre del archivo
        filename = resource['public_id'].split('/')[-1]
        title = filename.split('_')[-1].replace('.jpg', '').replace('.png', '')
        
        # Crear foto
        photo = Photo(
            title=title,
            description="Foto 360° Ayuntamiento de Écija",
            url=resource['secure_url'],
            latitude=None,
            longitude=None,
            project_id=10
        )
        db.add(photo)
        
        if i % 10 == 0:
            print(f"  ... {i}/{len(project_10_resources)} fotos procesadas")
        
        photos_imported += 1
    
    db.commit()
    
    print("\n" + "=" * 70)
    print("🎉 ¡RECUPERACIÓN COMPLETADA!")
    print("=" * 70)
    print(f"\n📊 RESUMEN:")
    print(f"  • Proyecto ID: 10")
    print(f"  • Nombre: {project.name}")
    print(f"  • Fotos importadas: {photos_imported}")
    print(f"  • Propietario: {user.email}")
    print(f"\n✅ Las URLs contienen '/project_10/' como requerías")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()

finally:
    db.close()