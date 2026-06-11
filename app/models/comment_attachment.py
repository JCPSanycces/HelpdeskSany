from app import db
from datetime import datetime

class CommentAttachment(db.Model):
    __tablename__ = 'comment_attachments'

    id         = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    filename   = db.Column(db.String(300), nullable=False)  # nombre original
    file_path  = db.Column(db.String(300), nullable=False)  # ruta relativa a static/
    file_type  = db.Column(db.String(10), nullable=False)   # imagen / documento
    created_at = db.Column(db.DateTime, default=datetime.utcnow)