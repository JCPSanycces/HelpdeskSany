from app import db

class TicketCounter(db.Model):
    __tablename__ = 'ticket_counters'

    year    = db.Column(db.Integer, primary_key=True)
    counter = db.Column(db.Integer, default=0, nullable=False)