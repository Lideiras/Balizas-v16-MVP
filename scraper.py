"""
Scraper para obtener incidencias de balizas activas desde la DGT

Las balizas activas se identifican como incidencias con descripción:
- "OBSTÁCULO FIJO"
- "OBSTÁCULO FIJO por ACCIDENTE"
"""

import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from typing import List, Optional
import re

DGT_BASE_URL = 'https://infocar.dgt.es/etraffic/Incidencias'
DGT_URL = f'{DGT_BASE_URL}?ca=&provIci=&caracter=acontecimiento&accion_consultar=Consultar&IncidenciasOTROS=IncidenciasOTROS&ordenacion=fechahora_ini-DESC'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
}

# IDs de la DGT para comunidades autónomas (para filtrar en la URL)
COMUNIDADES_IDS = {
    'ANDALUCÍA': '1', 'ANDALUCIA': '1',
    'ARAGÓN': '2', 'ARAGON': '2',
    'ASTURIAS': '3', 'PRINCIPADO DE ASTURIAS': '3',
    'ILLES BALEARS': '4', 'BALEARES': '4', 'ISLAS BALEARES': '4',
    'CANARIAS': '5',
    'CANTABRIA': '6',
    'CASTILLA Y LEÓN': '7', 'CASTILLA Y LEON': '7',
    'CASTILLA-LA MANCHA': '8', 'CASTILLA LA MANCHA': '8',
    'CATALUÑA': '9', 'CATALUNA': '9', 'CATALUNYA': '9',
    'COMUNIDAD VALENCIANA': '10', 'COMUNITAT VALENCIANA': '10', 'VALENCIA': '10',
    'EXTREMADURA': '11',
    'GALICIA': '12',
    'COMUNIDAD DE MADRID': '13', 'MADRID': '13',
    'REGIÓN DE MURCIA': '14', 'MURCIA': '14',
    'NAVARRA': '15', 'COMUNIDAD FORAL DE NAVARRA': '15',
    'PAÍS VASCO': '16', 'PAIS VASCO': '16', 'EUSKADI': '16',
    'LA RIOJA': '17', 'RIOJA': '17',
    'CEUTA': '18',
    'MELILLA': '19'
}

# IDs de la DGT para provincias (para filtrar en la URL)
PROVINCIAS_IDS = {
    # Andalucía
    'ALMERÍA': '4', 'ALMERIA': '4',
    'CÁDIZ': '11', 'CADIZ': '11',
    'CÓRDOBA': '14', 'CORDOBA': '14',
    'GRANADA': '18',
    'HUELVA': '21',
    'JAÉN': '23', 'JAEN': '23',
    'MÁLAGA': '29', 'MALAGA': '29',
    'SEVILLA': '41',
    # Aragón
    'HUESCA': '22',
    'TERUEL': '44',
    'ZARAGOZA': '50',
    # Asturias
    'ASTURIAS': '33',
    # Baleares
    'BALEARS, ILLES': '7', 'BALEARES': '7', 'ILLES BALEARS': '7',
    # Canarias
    'LAS PALMAS': '35', 'PALMAS, LAS': '35',
    'SANTA CRUZ DE TENERIFE': '38', 'S.C.TENERIFE': '38', 'TENERIFE': '38',
    # Cantabria
    'CANTABRIA': '39',
    # Castilla-La Mancha
    'ALBACETE': '2',
    'CIUDAD REAL': '13',
    'CUENCA': '16',
    'GUADALAJARA': '19',
    'TOLEDO': '45',
    # Castilla y León
    'ÁVILA': '5', 'AVILA': '5',
    'BURGOS': '9',
    'LEÓN': '24', 'LEON': '24',
    'PALENCIA': '34',
    'SALAMANCA': '37',
    'SEGOVIA': '40',
    'SORIA': '42',
    'VALLADOLID': '47',
    'ZAMORA': '49',
    # Cataluña
    'BARCELONA': '8',
    'GIRONA': '17', 'GERONA': '17',
    'LLEIDA': '25', 'LÉRIDA': '25', 'LERIDA': '25',
    'TARRAGONA': '43',
    # Comunidad Valenciana
    'ALICANTE': '3', 'ALACANT': '3',
    'CASTELLÓN': '12', 'CASTELLÓ': '12', 'CASTELLON': '12',
    'VALENCIA': '46', 'VALÈNCIA': '46',
    # Extremadura
    'BADAJOZ': '6',
    'CÁCERES': '10', 'CACERES': '10',
    # Galicia
    'A CORUÑA': '15', 'CORUÑA, A': '15', 'LA CORUÑA': '15', 'CORUÑA': '15',
    'LUGO': '27',
    'OURENSE': '32', 'ORENSE': '32',
    'PONTEVEDRA': '36',
    # Madrid
    'MADRID': '28',
    # Murcia
    'MURCIA': '30',
    # Navarra
    'NAVARRA': '31',
    # País Vasco
    'ÁLAVA': '1', 'ALAVA': '1', 'ARABA': '1',
    'BIZKAIA': '48', 'VIZCAYA': '48',
    'GIPUZKOA': '20', 'GUIPÚZCOA': '20', 'GUIPUZCOA': '20',
    # La Rioja
    'LA RIOJA': '26', 'RIOJA, LA': '26',
    # Ceuta y Melilla
    'CEUTA': '51',
    'MELILLA': '52'
}

# Mapeo de provincias a comunidades autónomas
PROVINCIAS_COMUNIDADES = {
    # Andalucía
    'ALMERÍA': 'ANDALUCÍA', 'CÁDIZ': 'ANDALUCÍA', 'CÓRDOBA': 'ANDALUCÍA',
    'GRANADA': 'ANDALUCÍA', 'HUELVA': 'ANDALUCÍA', 'JAÉN': 'ANDALUCÍA',
    'MÁLAGA': 'ANDALUCÍA', 'SEVILLA': 'ANDALUCÍA',
    # Aragón
    'HUESCA': 'ARAGÓN', 'TERUEL': 'ARAGÓN', 'ZARAGOZA': 'ARAGÓN',
    # Asturias
    'ASTURIAS': 'ASTURIAS',
    # Baleares
    'BALEARS, ILLES': 'ILLES BALEARS', 'BALEARES': 'ILLES BALEARS',
    # Canarias
    'LAS PALMAS': 'CANARIAS', 'SANTA CRUZ DE TENERIFE': 'CANARIAS',
    'PALMAS, LAS': 'CANARIAS', 'S.C.TENERIFE': 'CANARIAS',
    # Cantabria
    'CANTABRIA': 'CANTABRIA',
    # Castilla-La Mancha
    'ALBACETE': 'CASTILLA-LA MANCHA', 'CIUDAD REAL': 'CASTILLA-LA MANCHA',
    'CUENCA': 'CASTILLA-LA MANCHA', 'GUADALAJARA': 'CASTILLA-LA MANCHA',
    'TOLEDO': 'CASTILLA-LA MANCHA',
    # Castilla y León
    'ÁVILA': 'CASTILLA Y LEÓN', 'BURGOS': 'CASTILLA Y LEÓN',
    'LEÓN': 'CASTILLA Y LEÓN', 'PALENCIA': 'CASTILLA Y LEÓN',
    'SALAMANCA': 'CASTILLA Y LEÓN', 'SEGOVIA': 'CASTILLA Y LEÓN',
    'SORIA': 'CASTILLA Y LEÓN', 'VALLADOLID': 'CASTILLA Y LEÓN',
    'ZAMORA': 'CASTILLA Y LEÓN',
    # Cataluña
    'BARCELONA': 'CATALUÑA', 'GIRONA': 'CATALUÑA',
    'LLEIDA': 'CATALUÑA', 'TARRAGONA': 'CATALUÑA',
    # Comunidad Valenciana
    'ALICANTE': 'COMUNIDAD VALENCIANA', 'ALACANT': 'COMUNIDAD VALENCIANA',
    'CASTELLÓN': 'COMUNIDAD VALENCIANA', 'CASTELLÓ': 'COMUNIDAD VALENCIANA',
    'VALENCIA': 'COMUNIDAD VALENCIANA', 'VALÈNCIA': 'COMUNIDAD VALENCIANA',
    # Extremadura
    'BADAJOZ': 'EXTREMADURA', 'CÁCERES': 'EXTREMADURA',
    # Galicia
    'CORUÑA, A': 'GALICIA', 'A CORUÑA': 'GALICIA', 'LA CORUÑA': 'GALICIA',
    'LUGO': 'GALICIA', 'OURENSE': 'GALICIA', 'PONTEVEDRA': 'GALICIA',
    # Madrid
    'MADRID': 'COMUNIDAD DE MADRID',
    # Murcia
    'MURCIA': 'REGIÓN DE MURCIA',
    # Navarra
    'NAVARRA': 'NAVARRA',
    # País Vasco
    'ÁLAVA': 'PAÍS VASCO', 'ARABA': 'PAÍS VASCO',
    'BIZKAIA': 'PAÍS VASCO', 'VIZCAYA': 'PAÍS VASCO',
    'GIPUZKOA': 'PAÍS VASCO', 'GUIPÚZCOA': 'PAÍS VASCO',
    # La Rioja
    'LA RIOJA': 'LA RIOJA', 'RIOJA, LA': 'LA RIOJA',
    # Ceuta y Melilla
    'CEUTA': 'CEUTA', 'MELILLA': 'MELILLA'
}


def get_comunidad(provincia: str) -> str:
    """Obtiene la comunidad autónoma a partir de la provincia"""
    provincia_upper = provincia.upper().strip()
    return PROVINCIAS_COMUNIDADES.get(provincia_upper, 'DESCONOCIDA')


@dataclass
class Incidencia:
    """Representa una incidencia de baliza activa"""
    id: str  # inciCodigo de la DGT
    tipo: str
    fecha_inicio: str
    hora_inicio: str
    fecha_fin: Optional[str]
    hora_fin: Optional[str]
    nivel: str
    comunidad: str  # Comunidad autónoma
    provincia: str
    poblacion: str
    carretera: str
    pk: str
    sentido: str
    descripcion: str
    activa: bool
    # Coordenadas GPS (opcionales, se obtienen por geocodificación)
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    precision_geo: Optional[str] = None  # 'alta', 'media', 'baja', 'estimada'
    
    def to_dict(self):
        return asdict(self)


def parse_incidencias(html: str) -> List[Incidencia]:
    """
    Parsea el HTML de la tabla de incidencias de la DGT
    
    Args:
        html: HTML de la página
        
    Returns:
        Lista de incidencias de balizas activas
    """
    soup = BeautifulSoup(html, 'html.parser')
    incidencias = []
    
    # Buscar todas las filas de la tabla
    rows = soup.find_all('tr')
    
    for row in rows:
        # Verificar si contiene "OBSTÁCULO FIJO"
        row_text = row.get_text().upper()
        if 'OBSTÁCULO FIJO' not in row_text:
            continue
        
        cells = row.find_all('td')
        if len(cells) < 6:
            continue
        
        try:
            # Extraer ID (inciCodigo) de la fila
            row_id = extract_id(row)
            incidencia = parse_row(cells, row_id)
            if incidencia:
                incidencias.append(incidencia)
        except Exception as e:
            print(f"Error parsing row: {e}")
            continue
    
    return incidencias


def extract_id(row) -> str:
    """
    Extrae el ID (inciCodigo) de una fila de incidencia.
    Lo busca en el atributo onclick de los enlaces o en el alt de la imagen.
    
    Args:
        row: Elemento BeautifulSoup de la fila
        
    Returns:
        ID de la incidencia o cadena vacía
    """
    # Buscar en onclick de cualquier enlace
    for link in row.find_all('a'):
        onclick = link.get('onclick', '')
        match = re.search(r'inciCodigo=(\d+)', onclick)
        if match:
            return match.group(1)
    
    # Buscar en el alt de la imagen de nivel
    for img in row.find_all('img'):
        alt = img.get('alt', '')
        match = re.search(r'/(\d+)$', alt)
        if match:
            return match.group(1)
    
    return ""


def parse_row(cells, row_id: str = "") -> Optional[Incidencia]:
    """
    Parsea una fila individual de la tabla
    
    Args:
        cells: Lista de celdas <td> de la fila
        
    Returns:
        Objeto Incidencia o None
    """
    # Cell 0: INICIO (fecha y hora)
    cell_inicio = cells[0]
    hora_inicio = ""
    fecha_inicio = ""
    
    span = cell_inicio.find('span')
    if span:
        hora_inicio = span.get_text().strip()
    
    link = cell_inicio.find('a')
    if link:
        fecha_inicio = link.get_text().strip()
    
    # Cell 1: FIN (puede estar vacío)
    cell_fin = cells[1]
    hora_fin = None
    fecha_fin = None
    
    span_fin = cell_fin.find('span')
    if span_fin and span_fin.get_text().strip():
        hora_fin = span_fin.get_text().strip()
        # Buscar fecha después del span
        text = cell_fin.get_text()
        fecha_match = re.search(r'\d{2}/\d{2}/\d{4}', text)
        if fecha_match:
            fecha_fin = fecha_match.group()
    
    # Cell 2: TIPO/NIVEL (imagen de nivel)
    cell_nivel = cells[2]
    nivel = "desconocido"
    img = cell_nivel.find('img')
    if img and img.get('src'):
        nivel_match = re.search(r'nivel_(\w+)\.gif', img.get('src', ''))
        if nivel_match:
            nivel = nivel_match.group(1)
    
    # Cell 3: PROVINCIA / POBLACIÓN
    cell_provincia = cells[3]
    provincia = ""
    poblacion = ""
    
    bold = cell_provincia.find('b')
    if bold:
        provincia = bold.get_text().strip()
    
    # La población está fuera del <b>
    full_text = cell_provincia.get_text().strip()
    if provincia and provincia in full_text:
        poblacion = full_text.replace(provincia, '').strip()
    
    # Cell 4: CARRETERA
    cell_carretera = cells[4]
    carretera = ""
    pk = ""
    
    bold_carr = cell_carretera.find('b')
    if bold_carr:
        carretera = bold_carr.get_text().strip()
    
    # El PK NO está en la celda de carretera, hay que buscarlo en la descripción
    pk = ""
    
    # Cell 5: DESCRIPCIÓN
    cell_desc = cells[5]
    descripcion_texto = cell_desc.get_text().strip()
    descripcion_texto = re.sub(r'\s+', ' ', descripcion_texto)
    
    # Extraer PK de la descripción (formato: "km 342.55" o "km 1.259")
    pk_match = re.search(r'km\s*([\d.,]+)', descripcion_texto, re.IGNORECASE)
    if pk_match:
        pk = pk_match.group(1)
    
    # Determinar tipo de incidencia
    upper_desc = descripcion_texto.upper()
    if 'OBSTÁCULO FIJO' in upper_desc and 'ACCIDENTE' in upper_desc:
        tipo = 'OBSTÁCULO FIJO POR ACCIDENTE'
    else:
        tipo = 'OBSTÁCULO FIJO'
    
    # Extraer sentido
    sentido = ""
    sentido_match = re.search(r'sentido\s+(\w+)', descripcion_texto, re.IGNORECASE)
    if sentido_match:
        sentido = sentido_match.group(1)
    else:
        # Buscar en el HTML con <b>
        sentido_bold = cell_desc.find_all('b')
        for b in sentido_bold:
            prev_text = b.previous_sibling
            if prev_text and 'sentido' in str(prev_text).lower():
                sentido = b.get_text().strip()
                break
    
    return Incidencia(
        id=row_id,
        tipo=tipo,
        fecha_inicio=fecha_inicio,
        hora_inicio=hora_inicio,
        fecha_fin=fecha_fin,
        hora_fin=hora_fin,
        nivel=nivel,
        comunidad=get_comunidad(provincia),
        provincia=provincia,
        poblacion=poblacion,
        carretera=carretera,
        pk=pk,
        sentido=sentido,
        descripcion=descripcion_texto,
        activa=fecha_fin is None
    )


def build_url(comunidad: Optional[str] = None, provincia: Optional[str] = None) -> str:
    """
    Construye la URL de la DGT con los filtros especificados
    
    Args:
        comunidad: Nombre de la comunidad autónoma (opcional)
        provincia: Nombre de la provincia (opcional)
        
    Returns:
        URL con los parámetros de filtro
    """
    ca_id = ''
    prov_id = ''
    
    if comunidad:
        ca_id = COMUNIDADES_IDS.get(comunidad.upper(), '')
    
    if provincia:
        prov_id = PROVINCIAS_IDS.get(provincia.upper(), '')
    
    return f'{DGT_BASE_URL}?ca={ca_id}&provIci={prov_id}&caracter=acontecimiento&accion_consultar=Consultar&IncidenciasOTROS=IncidenciasOTROS&ordenacion=fechahora_ini-DESC'


def fetch_balizas_activas(comunidad: Optional[str] = None, provincia: Optional[str] = None) -> List[Incidencia]:
    """
    Obtiene las incidencias de balizas activas desde la DGT
    
    Args:
        comunidad: Filtrar por comunidad autónoma (opcional)
        provincia: Filtrar por provincia (opcional)
    
    Returns:
        Lista de incidencias
    """
    url = build_url(comunidad, provincia)
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = 'utf-8'
    
    return parse_incidencias(response.text)


def filtrar_activas(incidencias: List[Incidencia]) -> List[Incidencia]:
    """
    Filtra solo las balizas que están actualmente activas
    
    Args:
        incidencias: Lista de incidencias
        
    Returns:
        Lista de incidencias activas
    """
    return [inc for inc in incidencias if inc.activa]


if __name__ == '__main__':
    # Test rápido
    print("🔍 Probando scraper...")
    incidencias = fetch_balizas_activas()
    print(f"✅ Total incidencias obstáculo fijo: {len(incidencias)}")
    
    activas = filtrar_activas(incidencias)
    print(f"🚧 Balizas activas: {len(activas)}")
    
    for inc in activas[:3]:
        print(f"\n  🆔 {inc.id}")
        print(f"  📍 {inc.provincia} - {inc.carretera}")
        print(f"     {inc.tipo}")
