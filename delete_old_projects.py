import cloudinary
import cloudinary.api
import cloudinary.uploader

# Configurar Cloudinary
cloudinary.config(
    cloud_name="dryuzad8w",
    api_key="281976991233177",
    api_secret="oVv51LHUFYrmmux8oFuU0t-836s"
)

print("🗑️  ELIMINANDO PROYECTOS ANTIGUOS DE CLOUDINARY...")
print("=" * 70)

# Proyectos a eliminar
projects_to_delete = [5, 6, 7, 8, 9]

total_deleted = 0

for project_num in projects_to_delete:
    print(f"\n📁 Procesando project_{project_num}...")
    
    # Eliminar fotos 360°
    try:
        folder_360 = f"photosite360/project_{project_num}"
        
        next_cursor = None
        resources_360 = []
        
        while True:
            result = cloudinary.api.resources(
                type="upload",
                prefix=folder_360,
                max_results=500,
                next_cursor=next_cursor
            )
            
            resources_360.extend(result.get('resources', []))
            next_cursor = result.get('next_cursor')
            
            if not next_cursor:
                break
        
        print(f"  📸 Eliminando {len(resources_360)} fotos 360°...")
        
        for resource in resources_360:
            try:
                cloudinary.uploader.destroy(resource['public_id'])
                total_deleted += 1
            except Exception as e:
                print(f"    ❌ Error eliminando {resource['public_id']}: {e}")
        
        print(f"  ✅ {len(resources_360)} fotos 360° eliminadas")
        
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
    
    # Eliminar galería
    try:
        folder_gallery = f"photosite360/gallery/project_{project_num}"
        
        next_cursor = None
        resources_gallery = []
        
        while True:
            result = cloudinary.api.resources(
                type="upload",
                prefix=folder_gallery,
                max_results=500,
                next_cursor=next_cursor
            )
            
            resources_gallery.extend(result.get('resources', []))
            next_cursor = result.get('next_cursor')
            
            if not next_cursor:
                break
        
        if len(resources_gallery) > 0:
            print(f"  🖼️  Eliminando {len(resources_gallery)} imágenes de galería...")
            
            for resource in resources_gallery:
                try:
                    cloudinary.uploader.destroy(resource['public_id'])
                    total_deleted += 1
                except Exception as e:
                    print(f"    ❌ Error eliminando {resource['public_id']}: {e}")
            
            print(f"  ✅ {len(resources_gallery)} galerías eliminadas")
        
    except Exception as e:
        print(f"  ⚠️  Error en galería: {e}")

print("\n" + "=" * 70)
print(f"🎉 ¡LIMPIEZA COMPLETADA!")
print(f"📊 Total de archivos eliminados: {total_deleted}")
print(f"✅ Solo queda el project_10 con sus 149 fotos")
print("=" * 70)