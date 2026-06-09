from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash= db.Column(db.String(256))
    role = db.Column(db.String(20), default='user') # admin/agent/user
    department = db.Column(db.String(100), default='')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones con tickets
    tickets_creados = db.relationship('Ticket',
        foreign_keys='Ticket.created_by', backref='solicitante', lazy='dynamic')
    tickets_asignados = db.relationship('Ticket',
        foreign_keys='Ticket.assigned_to', backref='agente', lazy='dynamic')

    def set_password(self, password):
        # Guarda la contrasena de forma segura (nunca en texto plano)
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # Comprueba si la contrasena introducida es correcta
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_agent(self):
        return self.role in ('admin', 'agent')

    def __repr__(self):
        return f'<User {self.email}>'
    
# Flask-Login necesita esta funcion para cargar un usuario por su ID
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))