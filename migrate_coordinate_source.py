import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    print("Please set it in your .env file or Render environment variables")
    exit(1)

# Render uses postgres:// but psycopg2 needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"Connecting to database: {DATABASE_URL[:50]}...")

try:
    # Connect to PostgreSQL
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    print("✅ Connected to database successfully!")

    # Read and execute migration SQL
    with open('migrate_add_coordinate_source.sql', 'r', encoding='utf-8') as f:
        migration_sql = f.read()

    print("\nExecuting migration to add coordinate_source field...")

    # Execute migration (split by semicolons for multiple statements)
    statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]

    for statement in statements:
        if statement:
            print(f"Executing: {statement[:80]}...")
            cursor.execute(statement)

    conn.commit()

    print("✅ Migration completed successfully!")

    # Verify column was added to photos
    cursor.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'photos'
        AND column_name = 'coordinate_source';
    """)

    photos_result = cursor.fetchone()
    if photos_result:
        print(f"\n✅ Column added to 'photos' table: {photos_result}")
    else:
        print("\n⚠️  Column 'coordinate_source' not found in 'photos' table")

    # Verify column was added to gallery_images
    cursor.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'gallery_images'
        AND column_name = 'coordinate_source';
    """)

    gallery_result = cursor.fetchone()
    if gallery_result:
        print(f"✅ Column added to 'gallery_images' table: {gallery_result}")
    else:
        print("⚠️  Column 'coordinate_source' not found in 'gallery_images' table")

    cursor.close()
    conn.close()

    print("\n✅ All done! The database schema is updated.")
    print("You can now deploy your application with the new coordinate_source field.")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
