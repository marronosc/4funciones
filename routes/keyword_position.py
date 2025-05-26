from flask import Blueprint, request, render_template, redirect, url_for
from services.keyword_position import search_channel_position, format_number, format_date

keyword_position_bp = Blueprint('keyword_position', __name__, url_prefix='/keyword-position')

@keyword_position_bp.route('/', methods=['GET', 'POST'])
def keyword_position():
    if request.method == 'POST':
        keyword = request.form['keyword'].strip()
        channel_id = request.form['channel_id'].strip()
        max_results = int(request.form.get('max_results', 100))
        
        # Validar que el channel_id tenga el formato correcto
        if not channel_id.startswith('UC') or len(channel_id) != 24:
            return render_template('keyword_position/index.html', 
                                 error="El ID del canal debe tener el formato correcto (UC seguido de 22 caracteres)")
        
        return redirect(url_for('keyword_position.generate_report', 
                              keyword=keyword, 
                              channel_id=channel_id, 
                              max_results=max_results))
    
    return render_template('keyword_position/index.html')

@keyword_position_bp.route('/report/<keyword>/<channel_id>')
@keyword_position_bp.route('/report/<keyword>/<channel_id>/<int:max_results>')
def generate_report(keyword, channel_id, max_results=100):
    try:
        result = search_channel_position(keyword, channel_id, max_results)
        
        return render_template('keyword_position/report.html',
                             result=result,
                             format_number=format_number,
                             format_date=format_date)
                             
    except Exception as e:
        error_message = f"Error al generar el informe: {str(e)}"
        return render_template('keyword_position/error.html', 
                             error=error_message, 
                             keyword=keyword, 
                             channel_id=channel_id)