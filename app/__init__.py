from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Creamos los objetos globales (sin app todavia)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.DevelopmentConfig')

    # Conectamos los modulos a la app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
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
    return app