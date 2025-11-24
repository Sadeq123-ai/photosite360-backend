import sqlite3
from main import SessionLocal, User, Project, Photo, pwd_context

# Conectar a la base antigua
old_db = sqlite3.connect('photosite360_persistent.db')
old_cursor = old_db.cursor()

# Conectar a la base nueva
new_db = SessionLocal()

print("🔄 INICIANDO MIGRACIÓN DE DATOS...")
print("=" * 60)

try:
    # 1. MIGRAR USUARIOS
    print("\n👥 Migrando usuarios...")
    old_cursor.execute("SELECT id, email, full_name, hashed_password, created_at FROM users")
    old_users = old_cursor.fetchall()
    
    user_map = {}  # Mapeo de IDs antiguos a nuevos
    
    for old_id, email, full_name, hashed_password, created_at in old_users:
        # Crear username a partir del email
        username = email.split('@')[0]
        
        # Verificar si ya existe
        existing = new_db.query(User).filter(User.email == email).first()
        if existing:
            print(f"  ⚠️  Usuario ya existe: {email}")
            user_map[old_id] = existing.id
            continue
        
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            hashed_password=hashed_password
        )
        new_db.add(user)
        new_db.flush()
        user_map[old_id] = user.id
        print(f"  ✅ Migrado: {email}")
    
    new_db.commit()
    print(f"\n✅ {len(user_map)} usuarios migrados")
    
    # 2. MIGRAR PROYECTOS
    print("\n📁 Migrando proyectos...")
    old_cursor.execute("SELECT id, name, description, location, is_public, owner_id, created_at FROM projects")
    old_projects = old_cursor.fetchall()
    
    project_map = {}
    
    for old_id, name, description, location, is_public, owner_id, created_at in old_projects:
        new_owner_id = user_map.get(owner_id)
        if not new_owner_id:
            print(f"  ⚠️  Proyecto '{name}' sin propietario válido, omitiendo...")
            continue
        
        project = Project(
            name=name,
            description=description,
            location=location,
            is_public=is_public,
            owner_id=new_owner_id
        )
        new_db.add(project)
        new_db.flush()
        project_map[old_id] = project.id
        print(f"  ✅ Migrado: {name}")
    
    new_db.commit()
    print(f"\n✅ {len(project_map)} proyectos migrados")
    
    # 3. MIGRAR FOTOS
    print("\n📸 Migrando fotos...")
    old_cursor.execute("SELECT id, title, description, url, latitude, longitude, project_id, created_at FROM photos")
    old_photos = old_cursor.fetchall()
    
    photos_count = 0
    
    for old_id, title, description, url, latitude, longitude, project_id, created_at in old_photos:
        new_project_id = project_map.get(project_id)
        if not new_project_id:
            print(f"  ⚠️  Foto '{title}' sin proyecto válido, omitiendo...")
            continue
        
        photo = Photo(
            title=title,
            description=description,
            url=url,
            latitude=latitude,
            longitude=longitude,
            project_id=new_project_id
        )
        new_db.add(photo)
        photos_count += 1
        print(f"  ✅ Migrado: {title}")
    
    new_db.commit()
    print(f"\n✅ {photos_count} fotos migradas")
    
    print("\n" + "=" * 60)
    print("🎉 ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    new_db.rollback()

finally:
    old_db.close()
    new_db.close()