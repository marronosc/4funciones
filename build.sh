#!/bin/bash
set -e  # Salir si hay algún error

echo "=== INICIO DEL BUILD ==="
echo "Python version:"
python --version

echo "Pip version:"
pip --version

echo "=== VERIFICANDO REQUIREMENTS.TXT ==="
echo "Contenido de requirements.txt:"
cat requirements.txt
echo "---"

echo "¿Existe requirements.txt?"
ls -la requirements.txt

echo "=== INSTALANDO DEPENDENCIAS ==="
echo "Instalando desde requirements.txt..."
pip install -r requirements.txt

echo "=== VERIFICANDO INSTALACIONES ==="
echo "Packages installed:"
pip list

echo "=== VERIFICANDO PAQUETES ESPECÍFICOS ==="
python -c "import flask; print('Flask version:', flask.__version__)"
python -c "import google.ads; print('Google Ads package installed successfully')" || echo "Google Ads package not installed"

echo "=== ESTRUCTURA DE ARCHIVOS ==="
ls -la

echo "=== BUILD COMPLETADO EXITOSAMENTE ==="