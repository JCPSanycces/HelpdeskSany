from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.user import User
from app.models.ticket_participant import TicketParticipant
from app.utils.email import (
    enviar_notificacion_asignacion,
    enviar_notificacion_comentario,
    enviar_notificacion_cambio_estado,
)

tickets_bp = Blueprint('tickets', __name__)


def _añadir_participante(ticket_id, user_id):
    """Añade un participante al ticket si no existe ya."""
    existe = TicketParticipant.query.filter_by(
        ticket_id=ticket_id, user_id=user_id
    ).first()
    if not existe:
        db.session.add(TicketParticipant(ticket_id=ticket_id, user_id=user_id))


def _get_participantes(ticket_id):
    return TicketParticipant.query.filter_by(ticket_id=ticket_id).all()


@tickets_bp.route('/')
@login_required
def list_tickets():
    status   = request.args.get('status', '')
    priority = request.args.get('priority', '')
    query    = Ticket.query
    if not current_user.is_agent():
        query = query.filter_by(created_by=current_user.id)
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    tickets = query.order_by(Ticket.created_at.desc()).all()
    return render_template('tickets/list.html', tickets=tickets,
                           status=status, priority=priority)


@tickets_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_ticket():
    agents = User.query.filter(
        User.role.in_(['admin', 'agent'])).filter_by(active=True).all()

    if request.method == 'POST':
        assigned_id = request.form.get('assigned_to') or None
        t = Ticket(
            title=request.form['title'],
            description=request.form['description'],
            priority=request.form.get('priority', 'medium'),
            category=request.form.get('category', ''),
            created_by=current_user.id,
            assigned_to=assigned_id,
        )
        db.session.add(t)
        db.session.flush()  # Para tener t.id antes del commit

        # Registrar participantes iniciales
        _añadir_participante(t.id, current_user.id)
        if assigned_id:
            _añadir_participante(t.id, int(assigned_id))

        db.session.commit()

        # Notificar al agente asignado
        if assigned_id:
            agente = User.query.get(int(assigned_id))
            if agente:
                enviar_notificacion_asignacion(agente, t)

        flash(f'Ticket #{t.id} creado correctamente.', 'success')
        return redirect(url_for('tickets.detail', ticket_id=t.id))

    return render_template('tickets/new.html', agents=agents)


@tickets_bp.route('/<int:ticket_id>')
@login_required
def detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    agents = User.query.filter(
        User.role.in_(['admin', 'agent'])).filter_by(active=True).all()
    return render_template('tickets/detail.html', ticket=ticket, agents=agents)


@tickets_bp.route('/<int:ticket_id>/update', methods=['POST'])
@login_required
def update_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not current_user.is_agent():
        flash('No tienes permiso para hacer eso.', 'danger')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    nuevo_agente_id = request.form.get('assigned_to') or None
    agente_anterior_id = ticket.assigned_to
    estado_anterior = ticket.status
    nuevo_estado = request.form.get('status', ticket.status)

    ticket.status     = nuevo_estado
    ticket.priority   = request.form.get('priority', ticket.priority)
    ticket.assigned_to = nuevo_agente_id

    # Añadir nuevo agente como participante si ha cambiado
    if nuevo_agente_id:
        _añadir_participante(ticket_id, int(nuevo_agente_id))

    db.session.commit()
    participantes = _get_participantes(ticket_id)

    # Email si el agente ha cambiado
    if nuevo_agente_id and str(nuevo_agente_id) != str(agente_anterior_id):
        agente = User.query.get(int(nuevo_agente_id))
        if agente:
            enviar_notificacion_asignacion(agente, ticket)

    # Email si el estado ha cambiado
    if nuevo_estado != estado_anterior:
        enviar_notificacion_cambio_estado(ticket, estado_anterior, participantes)

    flash('Ticket actualizado.', 'success')
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))


@tickets_bp.route('/<int:ticket_id>/comment', methods=['POST'])
@login_required
def add_comment(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    body   = request.form.get('body', '').strip()

    if body:
        c = Comment(body=body, ticket_id=ticket_id, user_id=current_user.id)
        db.session.add(c)

        # Registrar al comentarista como participante
        _añadir_participante(ticket_id, current_user.id)
        db.session.commit()

        participantes = _get_participantes(ticket_id)
        enviar_notificacion_comentario(current_user, ticket, c, participantes)

    return redirect(url_for('tickets.detail', ticket_id=ticket_id))