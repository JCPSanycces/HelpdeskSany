from app import db
from datetime import datetime

class TicketParticipant(db.Model):
    __tablename__ = 'ticket_participants'

    id         = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(20), db.ForeignKey('tickets.ticket_id'), nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    joined_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # Evita duplicados
    __table_args__ = (db.UniqueConstraint('ticket_id', 'user_id'),)

    user = db.relationship('User', backref='participaciones')