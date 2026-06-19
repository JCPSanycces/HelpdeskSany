from app import db
from datetime import datetime
import uuid

class Ticket(db.Model):

    __tablename__ = 'tickets'

    ticket_id = db.Column(db.String(20), primary_key=True)
    # id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(30), default='open')
    priority = db.Column(db.String(20), default='medium')       # Valores: open / in_progress / pending / resolved / closed
    category = db.Column(db.String(100), default='')            # Valores: low / medium / high / critical
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
    onupdate=datetime.utcnow)
    comments = db.relationship('Comment', backref='ticket', lazy='dynamic',
    cascade='all, delete-orphan')
    participantes = db.relationship('TicketParticipant', backref='ticket',
                                    lazy='dynamic', cascade='all, delete-orphan')

    # comunicación por email
    email_thread_id = db.Column(db.String(200), default=lambda: f"<ticket-{uuid.uuid4()}@sanycces.es>")

    # Para integración con Microsoft Graph API (recepción de correos)
    graph_conversation_id = db.Column(db.String(300), nullable=True, index=True)

    # Relación con TicketAttachment (archivos adjuntos al ticket que se crean desde el correo)
    attachments = db.relationship('TicketAttachment', backref='ticket',
                              lazy='dynamic', cascade='all, delete-orphan')

    STATUS_LABELS = {
    'open': 'Abierto',
    'in_progress': 'En progreso',
    'pending': 'Pendiente',
    'validation': 'Validación',
    'blocked': 'Bloqueado',
    'resolved': 'Resuelto',
    'closed': 'Cerrado',
    }

    PRIORITY_LABELS = {
    'low': 'Baja',
    'medium': 'Media',
    'high': 'Alta',
    'critical': 'Crítica',
    }


    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    def priority_label(self):
        return self.PRIORITY_LABELS.get(self.priority, self.priority)

    def __repr__(self):
        return f'<Ticket {self.ticket_id}>'