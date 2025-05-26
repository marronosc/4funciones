import os
import re
import requests
from urllib.parse import urlparse, parse_qs
import logging

def obtener_id_canal(url):
    logging.info(f"Procesando URL: {url}")
    
    # Normaliza la URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    parsed_url = urlparse(url)
    
    # Comprueba si es una URL de YouTube válida
    if 'youtube.com' not in parsed_url.netloc and 'youtu.be' not in parsed_url.netloc:
        logging.warning("URL no válida de YouTube")
        return None

    # Intenta extraer el ID del canal directamente de la URL
    path_parts = parsed_url.path.strip('/').split('/')
    logging.debug(f"Partes de la ruta: {path_parts}")

    if 'channel' in path_parts:
        channel_id = path_parts[path_parts.index('channel') + 1]
        logging.info(f"ID de canal encontrado en la URL: {channel_id}")
        return channel_id
    
    # Maneja URLs de usuario personalizado
    if path_parts and path_parts[0] in ['c', 'user'] or (path_parts and path_parts[0].startswith('@')):
        custom_name = path_parts[-1]
        logging.info(f"Nombre personalizado encontrado: {custom_name}")
        return obtener_id_desde_nombre_personalizado(custom_name)
    
    # Maneja URLs de vídeo
    if 'watch' in path_parts:
        video_id = parse_qs(parsed_url.query).get('v', [None])[0]
        if video_id:
            logging.info(f"ID de video encontrado: {video_id}")
            return obtener_id_desde_video(video_id)
    
    # Si todo lo demás falla, intenta obtener el ID de la página
    logging.info("Intentando obtener ID del contenido de la página")
    return obtener_id_desde_contenido_pagina(url)

def obtener_id_desde_nombre_personalizado(nombre):
    url = f'https://www.youtube.com/{nombre}'
    logging.info(f"Obteniendo ID desde nombre personalizado: {url}")
    return obtener_id_desde_contenido_pagina(url)

def obtener_id_desde_video(video_id):
    url = f'https://www.youtube.com/watch?v={video_id}'
    logging.info(f"Obteniendo ID desde video: {url}")
    return obtener_id_desde_contenido_pagina(url)

def obtener_id_desde_contenido_pagina(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        respuesta = requests.get(url, headers=headers)
        contenido = respuesta.text
        patron_id = r'"channelId":"(UC[a-zA-Z0-9_-]{22})"'
        coincidencia_id = re.search(patron_id, contenido)
        if coincidencia_id:
            channel_id = coincidencia_id.group(1)
            logging.info(f"ID de canal encontrado en el contenido de la página: {channel_id}")
            return channel_id
        else:
            logging.warning("No se encontró el ID del canal en el contenido de la página")
    except requests.RequestException as e:
        logging.error(f"Error al obtener el contenido de la página: {e}")
    return None