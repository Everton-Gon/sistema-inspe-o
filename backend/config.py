import os
from datetime import timedelta

class Config:
    """Configuração base"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # Banco de dados
    MYSQL_HOST = os.getenv('DB_HOST', 'localhost')
    MYSQL_USER = os.getenv('DB_USER', 'root')
    MYSQL_PASSWORD = os.getenv('DB_PASSWORD', '')
    MYSQL_DB = os.getenv('DB_NAME', 'sistema_mallory')
    MYSQL_PORT = int(os.getenv('DB_PORT', 3306))
    
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_timeout': 20,
        'pool_recycle': 3600,
        'max_overflow': 5,
        'pool_pre_ping': True
    }
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Paginação
    POSTS_PER_PAGE = 50
    MAX_POSTS_PER_PAGE = 100

class DevelopmentConfig(Config):
    """Configuração para desenvolvimento"""
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """Configuração para produção"""
    DEBUG = False
    
    # Segurança adicional em produção
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Logs mais detalhados
    SQLALCHEMY_ENGINE_OPTIONS = {
        **Config.SQLALCHEMY_ENGINE_OPTIONS,
        'echo': False
    }

class TestingConfig(Config):
    """Configuração para testes"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Dicionário de configurações
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}