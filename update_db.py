import sqlite3

# Conectar a la base de datos
conn = sqlite3.connect('photosite360.db')
cursor = conn.cursor()

try:
    # Agregar columna is_public si no existe
    cursor.execute("ALTER TABLE projects ADD COLUMN is_public INTEGER DEFAULT 0")
    print("✓ Columna 'is_public' agregada exitosamente")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("✓ Columna 'is_public' ya existe")
    else:
        print(f"✗ Error: {e}")

conn.commit()
conn.close()
print("✓ Base de datos actualizada")