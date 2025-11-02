from functools import wraps
from flask import request, jsonify, current_app
import logging
import os
from datetime import datetime

def create_response(success=True, message="", data=None, errors=None, status_code=200):
    """Criar resposta padronizada da API"""
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response["data"] = data
        
    if errors is not None:
        response["errors"] = errors
    
    return jsonify(response), status_code

def validate_json(f):
    """Decorator para validar se request tem JSON válido"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return create_response(
                success=False,
                message="Content-Type deve ser application/json",
                status_code=400
            )
        return f(*args, **kwargs)
    return decorated_function

def setup_logging(app):
    """Configurar sistema de logs"""
    if not app.debug and not app.testing:
        # Criar diretório de logs
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Configurar handler de arquivo
        file_handler = logging.FileHandler('logs/sistema_mallory.log')
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # Configurar nível de log
        app.logger.setLevel(logging.INFO)
        app.logger.info('Sistema Mallory Flask iniciado')