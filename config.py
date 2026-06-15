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

    # Configuración de correo
    MAIL_SERVER   = os.environ.get('MAIL_SERVER', 'smtp-relay.brevo.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # Subida de ficheros
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'app', 'static', 'uploads', 'comments')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB máximo por petición
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Ruta base para las subidas de archivos
    UPLOAD_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads')

class DevelopmentConfig(Config):
    DEBUG = True # Muestra errores detallados

class ProductionConfig(Config):
    DEBUG = False