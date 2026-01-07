"""
Generador de mapa interactivo de balizas activas

Genera un archivo HTML con un mapa de España usando Leaflet.js
que muestra todas las balizas activas con sus ubicaciones geocodificadas.
No requiere servidor - todo se ejecuta localmente.
"""

import webbrowser
import os
import json
from scraper import fetch_balizas_activas, filtrar_activas
from geocoding import geocodificar_baliza

# Centro de España aproximado
CENTRO_ESPANA = [40.4168, -3.7038]  # Madrid
ZOOM_INICIAL = 6


def generar_html_mapa(balizas_data: list) -> str:
    """
    Genera el HTML del mapa con Leaflet.js
    
    Args:
        balizas_data: Lista de diccionarios con datos de balizas geocodificadas
        
    Returns:
        HTML completo del mapa
    """
    balizas_json = json.dumps(balizas_data, ensure_ascii=False)
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Balizas Activas - Mapa</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        #map {{
            height: 100vh;
            width: 100%;
        }}
        .baliza-popup {{
            min-width: 280px;
        }}
        .baliza-popup h3 {{
            color: #c0392b;
            margin-bottom: 8px;
            font-size: 14px;
            border-bottom: 2px solid #e74c3c;
            padding-bottom: 4px;
        }}
        .baliza-popup .info-row {{
            display: flex;
            margin: 4px 0;
            font-size: 13px;
        }}
        .baliza-popup .label {{
            font-weight: 600;
            color: #555;
            min-width: 90px;
        }}
        .baliza-popup .value {{
            color: #222;
        }}
        .baliza-popup .ubicacion {{
            background: #f8f9fa;
            padding: 8px;
            border-radius: 4px;
            margin-top: 8px;
        }}
        .baliza-popup .precision {{
            font-size: 11px;
            color: #888;
            margin-top: 6px;
        }}
        .header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(135deg, #c0392b, #e74c3c);
            color: white;
            padding: 12px 20px;
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }}
        .header h1 {{
            font-size: 18px;
            font-weight: 600;
        }}
        .header .stats {{
            font-size: 14px;
            opacity: 0.9;
        }}
        #map {{
            margin-top: 50px;
            height: calc(100vh - 50px);
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Balizas Activas DGT</h1>
        <div class="stats" id="stats">Cargando...</div>
    </div>
    <div id="map"></div>
    
    <script>
        const balizas = {balizas_json};
        
        // Inicializar mapa centrado en España
        const map = L.map('map').setView({CENTRO_ESPANA}, {ZOOM_INICIAL});
        
        // Capa de OpenStreetMap
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors | Datos: DGT'
        }}).addTo(map);
        
        // Icono personalizado para balizas
        const balizaIcon = L.divIcon({{
            className: 'baliza-marker',
            html: '<div style="background: #e74c3c; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: bold;">⚠</div>',
            iconSize: [24, 24],
            iconAnchor: [12, 12],
            popupAnchor: [0, -12]
        }});
        
        // Añadir marcadores
        let count = 0;
        balizas.forEach(b => {{
            if (b.latitud && b.longitud) {{
                const popup = `
                    <div class="baliza-popup">
                        <h3>🚧 ${{b.tipo}}</h3>
                        <div class="info-row">
                            <span class="label">📍 Carretera: </span>
                            <span class="value">${{b.carretera}} km ${{b.pk || 'N/A'}}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">🏛️ Comunidad: </span>
                            <span class="value">${{b.comunidad}}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">🏘️ Provincia: </span>
                            <span class="value">${{b.provincia}}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">🏠 Población: </span>
                            <span class="value">${{b.poblacion || 'N/A'}}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">➡️ Sentido: </span>
                            <span class="value">${{b.sentido || 'N/A'}}</span>
                        </div>
                        <div class="info-row">
                            <span class="label">🕐 Inicio: </span>
                            <span class="value">${{b.fecha_inicio}} ${{b.hora_inicio}}</span>
                        </div>
                        <div class="ubicacion">
                            <div class="info-row">
                                <span class="label">🌍 Lat: </span>
                                <span class="value">${{b.latitud.toFixed(6)}}</span>
                            </div>
                            <div class="info-row">
                                <span class="label">🌍 Lon: </span>
                                <span class="value">${{b.longitud.toFixed(6)}}</span>
                            </div>
                            <div class="precision">Precisión: ${{b.precision_geo || 'N/A'}}</div>
                        </div>
                    </div>
                `;
                
                L.marker([b.latitud, b.longitud], {{icon: balizaIcon}})
                    .bindPopup(popup)
                    .addTo(map);
                count++;
            }}
        }});
        
        document.getElementById('stats').textContent = `${{count}} balizas en el mapa`;
    </script>
</body>
</html>'''
    
    return html


def obtener_balizas_geocodificadas(limite: int = None) -> list:
    """
    Obtiene las balizas activas y las geocodifica
    
    Args:
        limite: Número máximo de balizas a procesar (None = todas)
        
    Returns:
        Lista de balizas con coordenadas
    """
    print("🔍 Obteniendo balizas activas de la DGT...")
    incidencias = fetch_balizas_activas()
    activas = filtrar_activas(incidencias)
    print(f"   ✅ {len(activas)} balizas activas encontradas")
    
    if limite:
        activas = activas[:limite]
        print(f"   ⚠️  Limitando a {limite} balizas para prueba")
    
    print("\n🗺️  Geocodificando balizas (esto puede tardar)...")
    balizas_data = []
    
    for i, baliza in enumerate(activas, 1):
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
            balizas_data.append(baliza.to_dict())
            print(f"   [{i}/{len(activas)}] ✅ {baliza.carretera} km {baliza.pk} → ({coords.latitud:.4f}, {coords.longitud:.4f})")
        else:
            print(f"   [{i}/{len(activas)}] ❌ {baliza.carretera} km {baliza.pk} - No geocodificado")
    
    print(f"\n📊 Resultado: {len(balizas_data)}/{len(activas)} balizas geocodificadas")
    return balizas_data


def main():
    """Función principal"""
    print("=" * 50)
    print("GENERADOR DE MAPA DE BALIZAS ACTIVAS")
    print("=" * 50)
    
    # Obtener y geocodificar balizas (limitar a 20 para prueba rápida)
    # Cambiar a None para procesar todas (puede tardar ~5 min)
    balizas = obtener_balizas_geocodificadas(limite=20)
    
    if not balizas:
        print("\n❌ No se encontraron balizas geocodificadas")
        return
    
    # Generar HTML
    print("\n📝 Generando mapa HTML...")
    html = generar_html_mapa(balizas)
    
    # Guardar archivo
    output_path = os.path.join(os.path.dirname(__file__), 'mapa_balizas.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"   ✅ Guardado en: {output_path}")
    
    # Abrir en navegador
    print("\n🌐 Abriendo mapa en el navegador...")
    webbrowser.open(f'file://{output_path}')
    
    print("\n✅ ¡Listo! El mapa debería abrirse automáticamente.")


if __name__ == '__main__':
    main()
