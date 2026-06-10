from app import db
from datetime import datetime

class Comment(db.Model):

    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    ticket_id  = db.Column(db.String(20), db.ForeignKey('tickets.ticket_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.relationship('User', backref='comments')
    def __repr__(self):
        return f'<Comment by user {self.user_id} on ticket {self.ticket_id}>'