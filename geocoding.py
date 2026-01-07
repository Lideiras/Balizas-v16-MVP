"""
Módulo de geocodificación para obtener coordenadas GPS
a partir de carretera + punto kilométrico

Usa Nominatim (OpenStreetMap) como servicio gratuito de geocodificación
"""

import requests
import time
from typing import Optional, Tuple
from dataclasses import dataclass

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'

# Headers requeridos por Nominatim (requieren User-Agent identificativo)
HEADERS = {
    'User-Agent': 'BalizasActivasDGT/1.0 (API de monitorización de balizas)',
    'Accept': 'application/json'
}

# Cache de geocodificación para evitar peticiones repetidas
_geocode_cache = {}

# Control de rate limiting (Nominatim permite 1 petición/segundo)
_last_request_time = 0


@dataclass
class Coordenadas:
    """Coordenadas GPS"""
    latitud: float
    longitud: float
    precision: str  # 'alta', 'media', 'baja', 'estimada'
    fuente: str     # Descripción de cómo se obtuvo


def _rate_limit():
    """Espera si es necesario para respetar el rate limit de Nominatim"""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_request_time = time.time()


def geocodificar_nominatim(query: str) -> Optional[Tuple[float, float]]:
    """
    Geocodifica una consulta usando Nominatim
    
    Args:
        query: Texto a geocodificar (ej: "A-1 km 23, Madrid, España")
        
    Returns:
        Tupla (latitud, longitud) o None si no se encuentra
    """
    # Verificar cache
    if query in _geocode_cache:
        return _geocode_cache[query]
    
    _rate_limit()
    
    try:
        params = {
            'q': query,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'es'
        }
        
        response = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        results = response.json()
        
        if results:
            lat = float(results[0]['lat'])
            lon = float(results[0]['lon'])
            _geocode_cache[query] = (lat, lon)
            return (lat, lon)
        
        _geocode_cache[query] = None
        return None
        
    except Exception as e:
        print(f"Error geocodificando '{query}': {e}")
        return None


def geocodificar_baliza(carretera: str, pk: str, provincia: str, poblacion: str = "", comunidad: str = "") -> Optional[Coordenadas]:
    """
    Intenta geocodificar una baliza usando múltiples estrategias con TODOS los datos disponibles
    
    Args:
        carretera: Nombre de la carretera (ej: "A-1", "M-50")
        pk: Punto kilométrico (ej: "23,5")
        provincia: Provincia
        poblacion: Población (opcional)
        comunidad: Comunidad autónoma (opcional)
        
    Returns:
        Objeto Coordenadas o None
    """
    # Normalizar PK (cambiar coma por punto)
    pk_normalizado = pk.replace(',', '.') if pk else ''
    
    # Limpiar población (quitar paréntesis como "(O)" de "OUTEIRO (O)")
    poblacion_limpia = poblacion.split('(')[0].strip() if poblacion else ''
    
    # Estrategia 1: Carretera + PK + Población + Provincia (MÁXIMA precisión)
    if carretera and pk_normalizado and poblacion_limpia:
        query = f"{carretera} km {pk_normalizado}, {poblacion_limpia}, {provincia}, España"
        coords = geocodificar_nominatim(query)
        if coords:
            return Coordenadas(
                latitud=coords[0],
                longitud=coords[1],
                precision='muy_alta',
                fuente=f'Nominatim: {query}'
            )
    
    # Estrategia 2: Población + Carretera + Provincia (sin PK pero con contexto)
    if poblacion_limpia and carretera:
        query = f"{poblacion_limpia}, {carretera}, {provincia}, España"
        coords = geocodificar_nominatim(query)
        if coords:
            return Coordenadas(
                latitud=coords[0],
                longitud=coords[1],
                precision='alta',
                fuente=f'Nominatim: {query}'
            )
    
    # Estrategia 3: Carretera + PK + Provincia
    if carretera and pk_normalizado:
        query = f"{carretera} kilómetro {pk_normalizado}, {provincia}, España"
        coords = geocodificar_nominatim(query)
        if coords:
            return Coordenadas(
                latitud=coords[0],
                longitud=coords[1],
                precision='alta',
                fuente=f'Nominatim: {query}'
            )
    
    # Estrategia 4: Carretera + PK solo
    if carretera and pk_normalizado:
        query = f"{carretera} km {pk_normalizado}, España"
        coords = geocodificar_nominatim(query)
        if coords:
            return Coordenadas(
                latitud=coords[0],
                longitud=coords[1],
                precision='media',
                fuente=f'Nominatim: {query}'
            )
    
    # Estrategia 5: Población + Provincia (muy común que funcione)
    if poblacion_limpia:
        query = f"{poblacion_limpia}, {provincia}, España"
        coords = geocodificar_nominatim(query)
        if coords:
            return Coordenadas(
                latitud=coords[0],
                longitud=coords[1],
                precision='media',
                fuente=f'Nominatim (población): {query}'
            )
    
    # Estrategia 6: Carretera + Provincia
    if carretera:
        query = f"carretera {carretera}, {provincia}, España"
        coords = geocodificar_nominatim(query)
        if coords:
            return Coordenadas(
                latitud=coords[0],
                longitud=coords[1],
                precision='baja',
                fuente=f'Nominatim: {query}'
            )
    
    # Estrategia 7: Solo provincia (último recurso)
    query = f"{provincia}, España"
    coords = geocodificar_nominatim(query)
    if coords:
        return Coordenadas(
            latitud=coords[0],
            longitud=coords[1],
            precision='estimada',
            fuente=f'Nominatim (provincia): {query}'
        )
    
    return None


def limpiar_cache():
    """Limpia el cache de geocodificación"""
    global _geocode_cache
    _geocode_cache = {}


if __name__ == '__main__':
    # Test
    print("🗺️  Probando geocodificación...")
    
    # Test con carretera nacional
    result = geocodificar_baliza("A-1", "23", "MADRID", "Alcobendas")
    if result:
        print(f"\n✅ A-1 km 23:")
        print(f"   Lat: {result.latitud}, Lon: {result.longitud}")
        print(f"   Precisión: {result.precision}")
        print(f"   Fuente: {result.fuente}")
    
    # Test con carretera autonómica
    result2 = geocodificar_baliza("M-50", "15", "MADRID")
    if result2:
        print(f"\n✅ M-50 km 15:")
        print(f"   Lat: {result2.latitud}, Lon: {result2.longitud}")
        print(f"   Precisión: {result2.precision}")
