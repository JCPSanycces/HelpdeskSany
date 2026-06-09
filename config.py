import os
from dotenv import load_dotenv

load_dotenv() # Carga las variables del fichero .env

class Config:
    # Clave secreta para seguridad de formularios y sesiones
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-clave-provisional')
    # Ruta de la base de datos
    SQLALCHEMY_DATABASE_URI = os.environ.get(
    'DATABASE_URL', 'sqlite:///helpdesk.db'
    )
    # Desactiva avisos innecesarios de SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True # Muestra errores detallados

class ProductionConfig(Config):
    DEBUG = False