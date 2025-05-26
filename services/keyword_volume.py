import os
import logging
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from datetime import datetime, timedelta
import pandas as pd

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración del cliente de Google Ads
def get_google_ads_client():
    """Inicializa y retorna el cliente de Google Ads"""
    # Configuración del cliente usando variables de entorno
    credentials = {
        "developer_token": os.environ.get('GOOGLE_ADS_DEVELOPER_TOKEN', 'rBAFQh1gt1UIM43xYbTIqQ'),
        "refresh_token": os.environ.get('GOOGLE_ADS_REFRESH_TOKEN'),
        "client_id": os.environ.get('GOOGLE_ADS_CLIENT_ID'),
        "client_secret": os.environ.get('GOOGLE_ADS_CLIENT_SECRET'),
        "login_customer_id": os.environ.get('GOOGLE_ADS_LOGIN_CUSTOMER_ID'),
    }
    
    # Validar que todas las credenciales necesarias estén presentes
    missing_credentials = [key for key, value in credentials.items() if not value and key != 'login_customer_id']
    if missing_credentials:
        logger.warning(f"Faltan las siguientes credenciales: {', '.join(missing_credentials)}")
        logger.warning("Por favor, configura todas las variables de entorno necesarias para Google Ads")
        return None
    
    try:
        # Crear configuración YAML programáticamente
        yaml_str = f"""
developer_token: {credentials['developer_token']}
refresh_token: {credentials['refresh_token']}
client_id: {credentials['client_id']}
client_secret: {credentials['client_secret']}
"""
        if credentials['login_customer_id']:
            yaml_str += f"login_customer_id: {credentials['login_customer_id']}\n"
        
        client = GoogleAdsClient.load_from_string(yaml_str)
        return client
    except Exception as e:
        logger.error(f"Error al inicializar cliente de Google Ads: {str(e)}")
        return None

def get_keyword_search_volume(keywords, customer_id=None, language_id='1003', location_ids=['2840']):
    """
    Obtiene el volumen de búsqueda para las palabras clave especificadas
    
    Args:
        keywords (list): Lista de palabras clave a analizar
        customer_id (str): ID de la cuenta de Google Ads (opcional)
        language_id (str): ID del idioma (1003 = Español)
        location_ids (list): Lista de IDs de ubicación (2840 = Estados Unidos)
    
    Returns:
        dict: Información del volumen de búsqueda con estimaciones de YouTube
    """
    client = get_google_ads_client()
    if not client:
        raise Exception("No se pudo inicializar el cliente de Google Ads. Verifica las credenciales.")
    
    # Si no se proporciona customer_id, intentar usar el de las variables de entorno
    if not customer_id:
        customer_id = os.environ.get('GOOGLE_ADS_CUSTOMER_ID')
        if not customer_id:
            raise Exception("Se requiere un customer_id. Configura GOOGLE_ADS_CUSTOMER_ID en las variables de entorno.")
    
    # Remover guiones del customer_id si los tiene
    customer_id = customer_id.replace('-', '')
    
    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
    keyword_competition_level_enum = client.enums.KeywordPlanCompetitionLevelEnum
    keyword_plan_network = client.enums.KeywordPlanNetworkEnum.KeywordPlanNetwork.GOOGLE_SEARCH_AND_PARTNERS
    
    # Convertir language_id y location_ids a los recursos apropiados
    language_rn = client.get_service("GoogleAdsService").language_constant_path(language_id)
    location_rns = [client.get_service("GoogleAdsService").geo_target_constant_path(location_id) 
                    for location_id in location_ids]
    
    # Construir la solicitud
    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = customer_id
    request.language = language_rn
    request.geo_target_constants.extend(location_rns)
    request.include_adult_keywords = False
    request.keyword_plan_network = keyword_plan_network
    
    # Configurar las palabras clave
    request.keyword_seed.keywords.extend(keywords)
    
    # Configurar el rango de fechas histórico (últimos 12 meses)
    # Esto es importante para obtener datos más precisos
    request.historical_metrics_options.year_month_range.start.year = datetime.now().year - 1
    request.historical_metrics_options.year_month_range.start.month = datetime.now().month
    request.historical_metrics_options.year_month_range.end.year = datetime.now().year
    request.historical_metrics_options.year_month_range.end.month = datetime.now().month - 1
    
    try:
        keyword_ideas = keyword_plan_idea_service.generate_keyword_ideas(request=request)
        
        results = []
        for idea in keyword_ideas:
            keyword_idea_metrics = idea.keyword_idea_metrics
            
            # Obtener volúmenes para Google y para Google + Partners
            google_search_volume = keyword_idea_metrics.avg_monthly_searches
            
            # Hacer una segunda llamada con GOOGLE_SEARCH para obtener solo Google
            request_google_only = request
            request_google_only.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.KeywordPlanNetwork.GOOGLE_SEARCH
            
            try:
                google_only_ideas = keyword_plan_idea_service.generate_keyword_ideas(request=request_google_only)
                google_only_volume = 0
                for google_idea in google_only_ideas:
                    if google_idea.text == idea.text:
                        google_only_volume = google_idea.keyword_idea_metrics.avg_monthly_searches
                        break
            except:
                google_only_volume = int(google_search_volume * 0.85)  # Estimación si falla
            
            # Estimar búsquedas en YouTube (diferencia entre total y solo Google)
            youtube_estimated_volume = max(0, google_search_volume - google_only_volume)
            
            # Si la diferencia es muy pequeña, aplicar un factor de estimación basado en estudios
            # YouTube representa aproximadamente 15-20% del volumen total de búsquedas
            if youtube_estimated_volume < google_search_volume * 0.1:
                youtube_estimated_volume = int(google_search_volume * 0.15)
            
            competition_value = keyword_idea_metrics.competition
            if competition_value == keyword_competition_level_enum.UNSPECIFIED:
                competition = "UNSPECIFIED"
            elif competition_value == keyword_competition_level_enum.UNKNOWN:
                competition = "UNKNOWN"
            elif competition_value == keyword_competition_level_enum.LOW:
                competition = "BAJO"
            elif competition_value == keyword_competition_level_enum.MEDIUM:
                competition = "MEDIO"
            elif competition_value == keyword_competition_level_enum.HIGH:
                competition = "ALTO"
            
            results.append({
                'keyword': idea.text,
                'google_total_volume': google_search_volume,
                'google_only_volume': google_only_volume,
                'youtube_estimated_volume': youtube_estimated_volume,
                'competition': competition,
                'competition_index': keyword_idea_metrics.competition_index if keyword_idea_metrics.HasField('competition_index') else None,
                'low_top_of_page_bid': keyword_idea_metrics.low_top_of_page_bid_micros / 1000000 if keyword_idea_metrics.HasField('low_top_of_page_bid_micros') else None,
                'high_top_of_page_bid': keyword_idea_metrics.high_top_of_page_bid_micros / 1000000 if keyword_idea_metrics.HasField('high_top_of_page_bid_micros') else None,
                'monthly_search_volumes': [
                    {
                        'year': month.year,
                        'month': month.month,
                        'volume': month.monthly_searches
                    }
                    for month in keyword_idea_metrics.monthly_search_volumes
                ] if keyword_idea_metrics.monthly_search_volumes else []
            })
        
        return {
            'status': 'success',
            'data': results,
            'summary': {
                'total_keywords': len(results),
                'total_google_volume': sum(r['google_total_volume'] for r in results),
                'total_youtube_estimated': sum(r['youtube_estimated_volume'] for r in results),
                'location': location_ids,
                'language': language_id
            }
        }
        
    except GoogleAdsException as ex:
        logger.error(f"Request failed with status {ex.error.code().name}")
        logger.error(f"Failure message: {ex.failure}")
        
        error_messages = []
        for error in ex.failure.errors:
            error_messages.append(f"{error.error_code}: {error.message}")
        
        return {
            'status': 'error',
            'error': 'Error al obtener datos de Google Ads',
            'details': error_messages
        }
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }

def get_keyword_suggestions(seed_keyword, customer_id=None, language_id='1003', location_ids=['2840'], max_suggestions=20):
    """
    Obtiene sugerencias de palabras clave relacionadas con volúmenes estimados
    
    Args:
        seed_keyword (str): Palabra clave semilla
        customer_id (str): ID de la cuenta de Google Ads
        language_id (str): ID del idioma
        location_ids (list): Lista de IDs de ubicación
        max_suggestions (int): Número máximo de sugerencias
    
    Returns:
        dict: Sugerencias de palabras clave con volúmenes
    """
    # Primero obtenemos las ideas de palabras clave
    keywords_to_analyze = [seed_keyword]
    
    # Obtener sugerencias adicionales
    result = get_keyword_search_volume(keywords_to_analyze, customer_id, language_id, location_ids)
    
    if result['status'] == 'success' and result['data']:
        # Ordenar por volumen estimado de YouTube
        sorted_keywords = sorted(
            result['data'], 
            key=lambda x: x['youtube_estimated_volume'], 
            reverse=True
        )[:max_suggestions]
        
        return {
            'status': 'success',
            'seed_keyword': seed_keyword,
            'suggestions': sorted_keywords,
            'total_found': len(result['data'])
        }
    
    return result

def format_volume(volume):
    """Formatea el volumen de búsqueda para mostrar"""
    if volume >= 1000000:
        return f"{volume/1000000:.1f}M"
    elif volume >= 1000:
        return f"{volume/1000:.1f}K"
    else:
        return str(volume)

def calculate_youtube_opportunity_score(keyword_data):
    """
    Calcula un score de oportunidad para YouTube basado en volumen y competencia
    
    Args:
        keyword_data (dict): Datos de la palabra clave
    
    Returns:
        float: Score de 0 a 100
    """
    youtube_volume = keyword_data.get('youtube_estimated_volume', 0)
    competition = keyword_data.get('competition', 'UNKNOWN')
    
    # Factor de volumen (0-50 puntos)
    if youtube_volume >= 10000:
        volume_score = 50
    elif youtube_volume >= 5000:
        volume_score = 40
    elif youtube_volume >= 1000:
        volume_score = 30
    elif youtube_volume >= 500:
        volume_score = 20
    elif youtube_volume >= 100:
        volume_score = 10
    else:
        volume_score = 5
    
    # Factor de competencia (0-50 puntos)
    competition_scores = {
        'BAJO': 50,
        'MEDIO': 30,
        'ALTO': 10,
        'UNKNOWN': 25,
        'UNSPECIFIED': 25
    }
    competition_score = competition_scores.get(competition, 25)
    
    return volume_score + competition_score