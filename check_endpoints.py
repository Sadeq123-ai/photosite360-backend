from main import app

print("🔍 VERIFICANDO ENDPOINTS DE GALERÍA:")
print("=" * 60)

# Buscar específicamente el endpoint de gallery/upload
gallery_upload_found = False

for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        path_str = str(route.path)
        methods = route.methods
        
        if '/gallery/upload' in path_str:
            print(f"✅ ENCONTRADO: {path_str}")
            print(f"   Métodos: {methods}")
            gallery_upload_found = True
        
        elif '/gallery' in path_str:
            print(f"📍 GALERÍA: {path_str}")
            print(f"   Métodos: {methods}")

if not gallery_upload_found:
    print("❌ NO SE ENCONTRÓ: /api/projects/{project_id}/gallery/upload")

print("\n📋 TODOS LOS ENDPOINTS DE UPLOAD:")
print("=" * 40)
for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        if 'upload' in str(route.path):
            methods = list(route.methods) if route.methods else ['GET']
            print(f"{methods[0]:<6} {route.path}")

print("\n🔧 VERIFICANDO ORDEN DE RUTAS:")
print("=" * 40)
routes_list = []
for route in app.routes:
    if hasattr(route, 'path'):
        routes_list.append(str(route.path))

# Mostrar rutas que contengan "gallery" o "upload"
for route in sorted(routes_list):
    if 'gallery' in route or 'upload' in route:
        print(f"  {route}")