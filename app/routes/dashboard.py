from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app import db
from app.models.ticket import Ticket
from app.models.ticket_participant import TicketParticipant

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    if current_user.is_admin():
        base_query = Ticket.query
    else:
        tickets_participante = db.session.query(TicketParticipant.ticket_id)\
            .filter_by(user_id=current_user.id).subquery()
        base_query = Ticket.query.filter(
            db.or_(
                Ticket.created_by == current_user.id,
                Ticket.ticket_id.in_(tickets_participante)
            )
        )

    total_open     = base_query.filter_by(status='open').count()
    total_progress = base_query.filter_by(status='in_progress').count()
    total_resolved = base_query.filter_by(status='resolved').count()
    total_closed   = base_query.filter_by(status='closed').count()

    recent_tickets = base_query.order_by(Ticket.created_at.desc()).limit(10).all()

    return render_template('dashboard.html',
        total_open=total_open,
        total_progress=total_progress,
        total_resolved=total_resolved,
        total_closed=total_closed,
        recent_tickets=recent_tickets,
    )