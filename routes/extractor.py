from flask import Blueprint, request, render_template
from services.channel_extractor import obtener_id_canal
import io
import logging

# Configurar logging para esta funcionalidad
log_stream = io.StringIO()
logging.basicConfig(stream=log_stream, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

extractor_bp = Blueprint('extractor', __name__, url_prefix='/extractor')

@extractor_bp.route('/', methods=['GET', 'POST'])
def extractor():
    result = None
    debug_info = None
    
    if request.method == 'POST':
        url = request.form['url']
        log_stream.seek(0)
        log_stream.truncate(0)
        result = obtener_id_canal(url)
        debug_info = log_stream.getvalue()
    
    return render_template('extractor/index.html', result=result, debug_info=debug_info)