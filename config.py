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

    # Configuración de correo para enviar notificaciones
    MAIL_SERVER   = os.environ.get('MAIL_SERVER', 'smtp-relay.brevo.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS  = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # Configuración de Microsoft Graph API para recepción de correos y creación de tickets
    GRAPH_TENANT_ID     = os.environ.get('GRAPH_TENANT_ID')
    GRAPH_CLIENT_ID     = os.environ.get('GRAPH_CLIENT_ID')
    GRAPH_CLIENT_SECRET = os.environ.get('GRAPH_CLIENT_SECRET')
    HELPDESK_MAILBOX    = os.environ.get('HELPDESK_MAILBOX')

    # Subida de ficheros
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'app', 'static', 'uploads', 'comments')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB máximo por petición
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Ruta base para las subidas de archivos
    UPLOAD_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads')

    # Asuntos de correo que deben ignorarse (separados por coma, ; o |). Ejemplo:
    # IGNORED_EMAIL_SUBJECTS='No ticket,Auto-reply'
    IGNORED_EMAIL_SUBJECTS = os.environ.get('IGNORED_EMAIL_SUBJECTS', '')

    # Direcciones de remitente que deben ignorarse (separadas por coma, ; o |).
    # Permite dominios o partes del email. Ejemplo:
    # IGNORED_EMAIL_SENDERS='no-reply@,@example.com,lista@dominio.com'
    IGNORED_EMAIL_SENDERS = os.environ.get('IGNORED_EMAIL_SENDERS', '')

    # Desactivar envío de notificaciones por correo (usar 'True' para desactivar)
    # Útil para mantenimiento o pruebas en entorno en vivo.
    DISABLE_EMAIL_NOTIFICATIONS = os.environ.get('DISABLE_EMAIL_NOTIFICATIONS', 'False') == 'True'

class DevelopmentConfig(Config):
    DEBUG = True # Muestra errores detallados

class ProductionConfig(Config):
    DEBUG = False