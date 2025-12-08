-- Migración: Agregar campo coordinate_source a tablas photos y gallery_images
-- Fecha: 2025-12-09
-- Descripción: Agrega el campo coordinate_source para rastrear el origen de las coordenadas

-- Agregar columna a photos si no existe
ALTER TABLE photos
ADD COLUMN IF NOT EXISTS coordinate_source VARCHAR DEFAULT 'manual';

-- Agregar columna a gallery_images si no existe
ALTER TABLE gallery_images
ADD COLUMN IF NOT EXISTS coordinate_source VARCHAR DEFAULT 'manual';

-- Verificar que se agregaron correctamente
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name IN ('photos', 'gallery_images')
  AND column_name = 'coordinate_source';
