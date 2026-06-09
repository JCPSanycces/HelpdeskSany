from flask import Blueprint, render_template
from flask_login import login_required
from app.models.ticket import Ticket
from app.models.user import User

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():

    # Contamos tickets por estado
    total_open = Ticket.query.filter_by(status='open').count()
    total_progress = Ticket.query.filter_by(status='in_progress').count()
    total_resolved = Ticket.query.filter_by(status='resolved').count()
    total_closed = Ticket.query.filter_by(status='closed').count()

    # Ultimos 10 tickets para mostrar en la tabla
    recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(10).all()

    return render_template('dashboard.html',
    total_open=total_open,
    total_progress=total_progress,
    total_resolved=total_resolved,
    total_closed=total_closed,
    recent_tickets=recent_tickets,
)