from app import db
from datetime import datetime

class TicketAttachment(db.Model):
    __tablename__ = 'ticket_attachments'

    id         = db.Column(db.Integer, primary_key=True)
    ticket_id  = db.Column(db.String(20), db.ForeignKey('tickets.ticket_id'), nullable=False)
    filename   = db.Column(db.String(300), nullable=False)
    file_path  = db.Column(db.String(300), nullable=False)
    file_type  = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)