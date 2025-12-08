"""
Utilidades para transformaciones de coordenadas entre diferentes sistemas

Sistemas soportados:
- Local (proyecto): X, Y, Z relativos a un origen arbitrario
- UTM ETRS89: Easting, Northing, Zona (coordenadas proyectadas)
- WGS84 Geográficas: Latitud, Longitud (grados decimales)
"""

import math
from typing import Dict, Tuple, Optional
from pyproj import Transformer, CRS


class CoordinateTransformer:
    """Transforma coordenadas entre diferentes sistemas"""

    def __init__(self):
        # Transformadores pre-configurados para España (zonas UTM 28-31)
        self.transformers = {}

        # WGS84 (EPSG:4326) a UTM ETRS89 para zonas de España
        for zone in range(28, 32):  # Zonas 28N, 29N, 30N, 31N
            utm_epsg = 25800 + zone  # EPSG:25828, 25829, 25830, 25831
            self.transformers[zone] = {
                'to_utm': Transformer.from_crs("EPSG:4326", f"EPSG:{utm_epsg}", always_xy=True),
                'to_geo': Transformer.from_crs(f"EPSG:{utm_epsg}", "EPSG:4326", always_xy=True)
            }

    def geo_to_utm(self, latitude: float, longitude: float, zone: Optional[int] = None) -> Dict:
        """
        Convierte coordenadas geográficas (WGS84) a UTM ETRS89

        Args:
            latitude: Latitud en grados decimales
            longitude: Longitud en grados decimales
            zone: Zona UTM (28-31). Si no se proporciona, se calcula automáticamente

        Returns:
            Dict con easting, northing, zone, hemisphere, datum
        """
        # Calcular zona UTM si no se proporciona
        if zone is None:
            zone = self._calculate_utm_zone(longitude)

        # Asegurar que la zona está en el rango de España
        if zone not in range(28, 32):
            zone = 30  # Zona por defecto para España central

        transformer = self.transformers[zone]['to_utm']
        easting, northing = transformer.transform(longitude, latitude)

        return {
            'utm_easting': round(easting, 3),
            'utm_northing': round(northing, 3),
            'utm_zone': zone,
            'utm_hemisphere': 'N',  # España siempre hemisferio norte
            'utm_datum': 'ETRS89'
        }

    def utm_to_geo(self, easting: float, northing: float, zone: int) -> Dict:
        """
        Convierte coordenadas UTM ETRS89 a geográficas (WGS84)

        Args:
            easting: Coordenada Este en metros
            northing: Coordenada Norte en metros
            zone: Zona UTM (28-31)

        Returns:
            Dict con geo_latitude, geo_longitude
        """
        if zone not in range(28, 32):
            raise ValueError(f"Zona UTM {zone} no válida para España. Use 28-31")

        transformer = self.transformers[zone]['to_geo']
        longitude, latitude = transformer.transform(easting, northing)

        return {
            'geo_latitude': round(latitude, 8),
            'geo_longitude': round(longitude, 8)
        }

    def local_to_utm(
        self,
        project_x: float,
        project_y: float,
        project_z: float,
        origin_lat: float,
        origin_lng: float,
        rotation: float = 0.0
    ) -> Dict:
        """
        Convierte coordenadas locales del proyecto a UTM

        Args:
            project_x: Coordenada X local
            project_y: Coordenada Y local
            project_z: Coordenada Z local (altura)
            origin_lat: Latitud del origen del proyecto
            origin_lng: Longitud del origen del proyecto
            rotation: Rotación del proyecto en grados (0 = norte arriba)

        Returns:
            Dict con coordenadas UTM
        """
        # 1. Convertir origen a UTM
        origin_utm = self.geo_to_utm(origin_lat, origin_lng)
        origin_easting = origin_utm['utm_easting']
        origin_northing = origin_utm['utm_northing']
        zone = origin_utm['utm_zone']

        # 2. Aplicar rotación a las coordenadas locales
        rotation_rad = math.radians(rotation)
        cos_r = math.cos(rotation_rad)
        sin_r = math.sin(rotation_rad)

        # Rotar punto
        x_rotated = project_x * cos_r - project_y * sin_r
        y_rotated = project_x * sin_r + project_y * cos_r

        # 3. Sumar al origen UTM
        final_easting = origin_easting + x_rotated
        final_northing = origin_northing + y_rotated

        return {
            'utm_easting': round(final_easting, 3),
            'utm_northing': round(final_northing, 3),
            'utm_zone': zone,
            'utm_hemisphere': 'N',
            'utm_datum': 'ETRS89'
        }

    def utm_to_local(
        self,
        easting: float,
        northing: float,
        origin_lat: float,
        origin_lng: float,
        rotation: float = 0.0
    ) -> Dict:
        """
        Convierte coordenadas UTM a locales del proyecto

        Args:
            easting: Coordenada Este UTM
            northing: Coordenada Norte UTM
            origin_lat: Latitud del origen del proyecto
            origin_lng: Longitud del origen del proyecto
            rotation: Rotación del proyecto en grados

        Returns:
            Dict con project_x, project_y
        """
        # 1. Convertir origen a UTM
        origin_utm = self.geo_to_utm(origin_lat, origin_lng)
        origin_easting = origin_utm['utm_easting']
        origin_northing = origin_utm['utm_northing']

        # 2. Restar origen
        delta_x = easting - origin_easting
        delta_y = northing - origin_northing

        # 3. Aplicar rotación inversa
        rotation_rad = math.radians(-rotation)  # Rotación inversa
        cos_r = math.cos(rotation_rad)
        sin_r = math.sin(rotation_rad)

        project_x = delta_x * cos_r - delta_y * sin_r
        project_y = delta_x * sin_r + delta_y * cos_r

        return {
            'project_x': round(project_x, 6),
            'project_y': round(project_y, 6)
        }

    def _calculate_utm_zone(self, longitude: float) -> int:
        """
        Calcula la zona UTM basándose en la longitud

        Para España:
        - Zona 28: Canarias occidental
        - Zona 29: Canarias oriental, Galicia
        - Zona 30: Casi toda España peninsular
        - Zona 31: Cataluña, Valencia, Baleares
        """
        # Fórmula estándar para zona UTM
        zone = int((longitude + 180) / 6) + 1

        # Limitar a zonas de España
        if zone < 28:
            zone = 28
        elif zone > 31:
            zone = 31

        return zone

    def batch_transform(
        self,
        items: list,
        transform_type: str,
        origin_lat: Optional[float] = None,
        origin_lng: Optional[float] = None,
        rotation: float = 0.0
    ) -> list:
        """
        Transforma múltiples elementos en lote

        Args:
            items: Lista de diccionarios con coordenadas
            transform_type: 'local_to_utm', 'utm_to_local', 'geo_to_utm', 'utm_to_geo'
            origin_lat, origin_lng: Origen del proyecto (si aplica)
            rotation: Rotación del proyecto

        Returns:
            Lista de items con coordenadas transformadas
        """
        results = []

        for item in items:
            result = item.copy()

            try:
                if transform_type == 'local_to_utm' and origin_lat and origin_lng:
                    if item.get('project_x') is not None and item.get('project_y') is not None:
                        utm = self.local_to_utm(
                            item['project_x'],
                            item['project_y'],
                            item.get('project_z', 0),
                            origin_lat,
                            origin_lng,
                            rotation
                        )
                        result.update(utm)

                elif transform_type == 'utm_to_local' and origin_lat and origin_lng:
                    if item.get('utm_easting') is not None and item.get('utm_northing') is not None:
                        local = self.utm_to_local(
                            item['utm_easting'],
                            item['utm_northing'],
                            origin_lat,
                            origin_lng,
                            rotation
                        )
                        result.update(local)

                elif transform_type == 'geo_to_utm':
                    if item.get('geo_latitude') is not None and item.get('geo_longitude') is not None:
                        utm = self.geo_to_utm(
                            item['geo_latitude'],
                            item['geo_longitude'],
                            item.get('utm_zone')
                        )
                        result.update(utm)

                elif transform_type == 'utm_to_geo':
                    if item.get('utm_easting') is not None and item.get('utm_northing') is not None:
                        zone = item.get('utm_zone', 30)
                        geo = self.utm_to_geo(
                            item['utm_easting'],
                            item['utm_northing'],
                            zone
                        )
                        result.update(geo)

            except Exception as e:
                result['_transform_error'] = str(e)

            results.append(result)

        return results
