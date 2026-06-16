from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler

# Creamos los objetos globales (sin app todavia)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
scheduler = BackgroundScheduler()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.DevelopmentConfig')

    # Conectamos los modulos a la app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesion para acceder.'
    login_manager.login_message_category = 'warning'

    # Registramos los blueprints (grupos de rutas)
    from .routes.auth import auth_bp
    from .routes.tickets import tickets_bp
    from .routes.users import users_bp
    from .routes.dashboard import dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(tickets_bp, url_prefix='/tickets')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(dashboard_bp)

    # Tarea programada: revisar el buzón cada 3 minutos
    if not scheduler.running:
        from app.utils.email_to_ticket import procesar_correos_nuevos

        def job_revisar_correo():
            with app.app_context():
                try:
                    n = procesar_correos_nuevos()
                    if n:
                        app.logger.info(f'{n} ticket(s) creados desde correo.')
                except Exception as e:
                    app.logger.error(f'Error procesando correos: {e}')

        scheduler.add_job(job_revisar_correo, 'interval', minutes=1, id='revisar_correo')
        scheduler.start()

    return app