"""
API de Balizas Activas - DGT

Servidor Flask que expone endpoints para consultar
las balizas activas (obstáculos fijos) de la DGT
"""

from flask import Flask, jsonify
from flask_cors import CORS
from scraper import fetch_balizas_activas, filtrar_activas
from geocoding import geocodificar_baliza
from datetime import datetime
import time

app = Flask(__name__)
CORS(app)

# Cache de incidencias para no sobrecargar la DGT
cache = {
    'data': [],
    'last_update': None,
    'ttl': 60  # 1 minuto de cache
}


def get_incidencias_con_cache():
    """Obtiene las incidencias, usando cache si está disponible"""
    now = time.time()
    
    if cache['last_update'] and (now - cache['last_update']) < cache['ttl']:
        return cache['data']
    
    try:
        incidencias = fetch_balizas_activas()
        cache['data'] = incidencias
        cache['last_update'] = now
        return incidencias
    except Exception as e:
        # Si falla, devolver cache anterior si existe
        if cache['data']:
            print(f"Error al actualizar, usando cache anterior: {e}")
            return cache['data']
        raise


# ==================== ENDPOINTS ====================

@app.route('/')
def home():
    """Ruta raíz con información de la API"""
    return jsonify({
        'name': 'API Balizas Activas DGT',
        'version': '1.1.0',
        'description': 'API para consultar balizas activas (obstáculos fijos) de la DGT con geocodificación',
        'source': 'https://infocar.dgt.es/etraffic/Incidencias',
        'endpoints': {
            '/api/balizas': 'Obtener todas las balizas activas',
            '/api/balizas/<id>': 'Obtener baliza específica por ID',
            '/api/balizas/<id>/ubicacion': 'Obtener baliza con coordenadas GPS',
            '/api/balizas/mapa': 'Obtener todas las balizas con coordenadas (para mapa)',
            '/api/balizas/todas': 'Obtener todas las incidencias (activas e inactivas)',
            '/api/balizas/comunidad/<comunidad>': 'Filtrar por comunidad autónoma',
            '/api/balizas/provincia/<provincia>': 'Filtrar por provincia',
            '/api/balizas/tipo/<tipo>': 'Filtrar por tipo (accidente o fijo)',
            '/api/status': 'Estado del servicio y estadísticas'
        }
    })


@app.route('/api/balizas')
def get_balizas():
    """Obtiene todas las balizas activas (obstáculos fijos)"""
    try:
        incidencias = get_incidencias_con_cache()
        activas = filtrar_activas(incidencias)
        
        return jsonify({
            'success': True,
            'total': len(activas),
            'last_update': datetime.fromtimestamp(cache['last_update']).isoformat() if cache['last_update'] else None,
            'data': [inc.to_dict() for inc in activas]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al obtener las balizas activas: {str(e)}'
        }), 500


@app.route('/api/balizas/<id>')
def get_baliza_por_id(id):
    """Obtiene una baliza específica por su ID (inciCodigo de la DGT)"""
    try:
        incidencias = get_incidencias_con_cache()
        
        # Buscar la incidencia por ID
        baliza = next((inc for inc in incidencias if inc.id == id), None)
        
        if baliza:
            return jsonify({
                'success': True,
                'data': baliza.to_dict()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'No se encontró la baliza con ID {id}'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al obtener la baliza: {str(e)}'
        }), 500


@app.route('/api/balizas/<id>/ubicacion')
def get_baliza_ubicacion(id):
    """Obtiene una baliza con sus coordenadas GPS geocodificadas"""
    try:
        incidencias = get_incidencias_con_cache()
        baliza = next((inc for inc in incidencias if inc.id == id), None)
        
        if not baliza:
            return jsonify({
                'success': False,
                'error': f'No se encontró la baliza con ID {id}'
            }), 404
        
        # Geocodificar si no tiene coordenadas
        if baliza.latitud is None:
            coords = geocodificar_baliza(
                baliza.carretera, 
                baliza.pk, 
                baliza.provincia, 
                baliza.poblacion,
                baliza.comunidad
            )
            if coords:
                baliza.latitud = coords.latitud
                baliza.longitud = coords.longitud
                baliza.precision_geo = coords.precision
        
        return jsonify({
            'success': True,
            'data': baliza.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al obtener la ubicación: {str(e)}'
        }), 500


@app.route('/api/balizas/mapa')
def get_balizas_mapa():
    """
    Obtiene todas las balizas activas con coordenadas GPS para mostrar en mapa.
    NOTA: Este endpoint puede ser lento la primera vez debido al rate limiting de Nominatim (1 req/seg)
    """
    try:
        incidencias = get_incidencias_con_cache()
        activas = filtrar_activas(incidencias)
        
        balizas_con_coords = []
        for baliza in activas:
            # Geocodificar si no tiene coordenadas
            if baliza.latitud is None:
                coords = geocodificar_baliza(
                    baliza.carretera, 
                    baliza.pk, 
                    baliza.provincia, 
                    baliza.poblacion,
                    baliza.comunidad
                )
                if coords:
                    baliza.latitud = coords.latitud
                    baliza.longitud = coords.longitud
                    baliza.precision_geo = coords.precision
            
            # Solo incluir si tiene coordenadas
            if baliza.latitud is not None:
                balizas_con_coords.append(baliza.to_dict())
        
        return jsonify({
            'success': True,
            'total': len(balizas_con_coords),
            'geocodificadas': len(balizas_con_coords),
            'sin_geocodificar': len(activas) - len(balizas_con_coords),
            'data': balizas_con_coords
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al obtener balizas para mapa: {str(e)}'
        }), 500


@app.route('/api/balizas/todas')
def get_todas():
    """Obtiene todas las incidencias de obstáculos fijos (activas e inactivas)"""
    try:
        incidencias = get_incidencias_con_cache()
        
        return jsonify({
            'success': True,
            'total': len(incidencias),
            'last_update': datetime.fromtimestamp(cache['last_update']).isoformat() if cache['last_update'] else None,
            'data': [inc.to_dict() for inc in incidencias]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al obtener las incidencias: {str(e)}'
        }), 500


@app.route('/api/balizas/provincia/<provincia>')
def get_por_provincia(provincia):
    """Obtiene las balizas activas filtradas por provincia (filtra en origen)"""
    try:
        # Filtra directamente en la DGT usando el parámetro de URL
        incidencias = fetch_balizas_activas(provincia=provincia)
        activas = filtrar_activas(incidencias)
        
        return jsonify({
            'success': True,
            'provincia': provincia,
            'total': len(activas),
            'data': [inc.to_dict() for inc in activas]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al obtener las balizas por provincia: {str(e)}'
        }), 500


@app.route('/api/balizas/comunidad/<comunidad>')
def get_por_comunidad(comunidad):
    """Obtiene las balizas activas filtradas por comunidad autónoma (filtra en origen)"""
    try:
        # Filtra directamente en la DGT usando el parámetro de URL
        incidencias = fetch_balizas_activas(comunidad=comunidad)
        activas = filtrar_activas(incidencias)
        
        return jsonify({
            'success': True,
            'comunidad': comunidad,
            'total': len(activas),
            'data': [inc.to_dict() for inc in activas]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al obtener las balizas por comunidad: {str(e)}'
        }), 500


@app.route('/api/balizas/tipo/<tipo>')
def get_por_tipo(tipo):
    """
    Obtiene las balizas activas filtradas por tipo
    Tipos válidos: "accidente" o "fijo"
    """
    try:
        incidencias = get_incidencias_con_cache()
        activas = filtrar_activas(incidencias)
        
        if tipo.lower() == 'accidente':
            filtradas = [inc for inc in activas if 'ACCIDENTE' in inc.tipo]
        elif tipo.lower() == 'fijo':
            filtradas = [inc for inc in activas if 'ACCIDENTE' not in inc.tipo]
        else:
            return jsonify({
                'success': False,
                'error': 'Tipo no válido. Use "accidente" o "fijo"'
            }), 400
        
        return jsonify({
            'success': True,
            'tipo': tipo,
            'total': len(filtradas),
            'last_update': datetime.fromtimestamp(cache['last_update']).isoformat() if cache['last_update'] else None,
            'data': [inc.to_dict() for inc in filtradas]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error al obtener las balizas por tipo: {str(e)}'
        }), 500


@app.route('/api/status')
def get_status():
    """Estado del servicio y estadísticas"""
    try:
        incidencias = get_incidencias_con_cache()
        activas = filtrar_activas(incidencias)
        
        return jsonify({
            'success': True,
            'status': 'online',
            'cache': {
                'last_update': datetime.fromtimestamp(cache['last_update']).isoformat() if cache['last_update'] else None,
                'ttl_seconds': cache['ttl']
            },
            'stats': {
                'total_incidencias': len(incidencias),
                'balizas_activas': len(activas),
                'por_accidente': len([i for i in activas if 'ACCIDENTE' in i.tipo]),
                'obstaculos_fijos': len([i for i in activas if 'ACCIDENTE' not in i.tipo])
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("🚧 API Balizas Activas DGT")
    print("📊 Status: http://localhost:5000/api/status")
    print("🔍 Balizas: http://localhost:5000/api/balizas")
    app.run(debug=True, port=5000)
