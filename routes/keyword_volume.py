from flask import Blueprint, request, render_template, redirect, url_for, jsonify
from services.keyword_volume import (
    get_keyword_search_volume, 
    get_keyword_suggestions,
    format_volume,
    calculate_youtube_opportunity_score
)
import os

keyword_volume_bp = Blueprint('keyword_volume', __name__, url_prefix='/keyword-volume')

@keyword_volume_bp.route('/', methods=['GET', 'POST'])
def keyword_volume():
    if request.method == 'POST':
        keywords = request.form.get('keywords', '').strip()
        if not keywords:
            return render_template('keyword_volume/index.html', 
                                 error="Por favor ingresa al menos una palabra clave")
        
        # Convertir las palabras clave en una lista
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]
        
        # Obtener parámetros opcionales
        language_id = request.form.get('language_id', '1003')  # Español por defecto
        location_id = request.form.get('location_id', '2724')  # España por defecto
        customer_id = request.form.get('customer_id', '').strip() or None
        
        return redirect(url_for('keyword_volume.generate_report', 
                              keywords=','.join(keyword_list),
                              language_id=language_id,
                              location_id=location_id,
                              customer_id=customer_id or 'default'))
    
    return render_template('keyword_volume/index.html')

@keyword_volume_bp.route('/report')
def generate_report():
    keywords = request.args.get('keywords', '').split(',')
    language_id = request.args.get('language_id', '1003')
    location_id = request.args.get('location_id', '2724')
    customer_id = request.args.get('customer_id')
    
    if customer_id == 'default':
        customer_id = None
    
    if not keywords or not keywords[0]:
        return redirect(url_for('keyword_volume.keyword_volume'))
    
    try:
        # Obtener volúmenes de búsqueda
        result = get_keyword_search_volume(
            keywords, 
            customer_id=customer_id,
            language_id=language_id,
            location_ids=[location_id]
        )
        
        if result['status'] == 'error':
            return render_template('keyword_volume/error.html', 
                                 error=result.get('error', 'Error desconocido'),
                                 details=result.get('details', []))
        
        # Calcular scores de oportunidad
        for keyword_data in result['data']:
            keyword_data['opportunity_score'] = calculate_youtube_opportunity_score(keyword_data)
            keyword_data['formatted_google_volume'] = format_volume(keyword_data['google_total_volume'])
            keyword_data['formatted_youtube_volume'] = format_volume(keyword_data['youtube_estimated_volume'])
        
        # Ordenar por score de oportunidad
        result['data'] = sorted(result['data'], key=lambda x: x['opportunity_score'], reverse=True)
        
        # Obtener nombres de ubicación y idioma
        location_names = {
            '2724': 'España',
            '2840': 'Estados Unidos',
            '2484': 'México',
            '2032': 'Argentina',
            '2152': 'Chile',
            '2170': 'Colombia',
            '2604': 'Perú'
        }
        
        language_names = {
            '1003': 'Español',
            '1000': 'Inglés',
            '1014': 'Portugués'
        }
        
        return render_template('keyword_volume/report.html',
                             result=result,
                             keywords=keywords,
                             location_name=location_names.get(location_id, location_id),
                             language_name=language_names.get(language_id, language_id))
                             
    except Exception as e:
        error_message = f"Error al generar el informe: {str(e)}"
        return render_template('keyword_volume/error.html', 
                             error=error_message,
                             details=[])

@keyword_volume_bp.route('/api/suggestions', methods=['POST'])
def api_suggestions():
    """Endpoint API para obtener sugerencias de palabras clave"""
    data = request.get_json()
    seed_keyword = data.get('keyword', '').strip()
    
    if not seed_keyword:
        return jsonify({'status': 'error', 'error': 'Se requiere una palabra clave'}), 400
    
    try:
        result = get_keyword_suggestions(
            seed_keyword,
            customer_id=data.get('customer_id'),
            language_id=data.get('language_id', '1003'),
            location_ids=[data.get('location_id', '2724')],
            max_suggestions=data.get('max_suggestions', 20)
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@keyword_volume_bp.route('/check-config')
def check_config():
    """Verifica la configuración de Google Ads"""
    config_status = {
        'developer_token': bool(os.environ.get('GOOGLE_ADS_DEVELOPER_TOKEN')),
        'refresh_token': bool(os.environ.get('GOOGLE_ADS_REFRESH_TOKEN')),
        'client_id': bool(os.environ.get('GOOGLE_ADS_CLIENT_ID')),
        'client_secret': bool(os.environ.get('GOOGLE_ADS_CLIENT_SECRET')),
        'customer_id': bool(os.environ.get('GOOGLE_ADS_CUSTOMER_ID')),
        'login_customer_id': bool(os.environ.get('GOOGLE_ADS_LOGIN_CUSTOMER_ID'))
    }
    
    all_configured = all(config_status.values())
    
    return render_template('keyword_volume/config_check.html',
                         config_status=config_status,
                         all_configured=all_configured)