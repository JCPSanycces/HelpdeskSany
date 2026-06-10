from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.user import User
from app.utils.email import enviar_notificacion_asignacion

tickets_bp = Blueprint('tickets', __name__)

# Rutas para gestionar tickets
@tickets_bp.route('/')
@login_required
def list_tickets():
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    query = Ticket.query

    # Los usuarios normales solo ven sus tickets
    if not current_user.is_agent():
        query = query.filter_by(created_by=current_user.id)

    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return render_template('tickets/list.html', tickets=tickets, status=status, priority=priority)


# Ruta para crear un nuevo ticket
@tickets_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_ticket():
    agents = User.query.filter(User.role.in_(['admin','agent'])).filter_by(active=True).all()

    if request.method == 'POST':
        t = Ticket(
            title=request.form['title'],
            description=request.form['description'],
            priority=request.form.get('priority','medium'),
            category=request.form.get('category',''),
            created_by=current_user.id,
            assigned_to=request.form.get('assigned_to') or None,
        )
        db.session.add(t)
        db.session.commit()

        # Enviar email si se ha asignado a alguien
        if t.assigned_to:
            agente = User.query.get(int(t.assigned_to))
            if agente:
                enviar_notificacion_asignacion(agente, t)
                
        flash(f'Ticket #{t.id} creado correctamente.', 'success')
        return redirect(url_for('tickets.detail', ticket_id=t.id))

    return render_template('tickets/new.html', agents=agents)


# Ruta para ver el detalle de un ticket
@tickets_bp.route('/<int:ticket_id>')
@login_required
def detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    agents = User.query.filter(User.role.in_(['admin','agent'])).filter_by(active=True).all()
    return render_template('tickets/detail.html', ticket=ticket, agents=agents)


# Ruta para actualizar el estado, prioridad o asignación de un ticket
@tickets_bp.route('/<int:ticket_id>/update', methods=['POST'])
@login_required
def update_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not current_user.is_agent():
        flash('No tienes permiso para hacer eso.', 'danger')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))
    
    nuevo_agente_id = request.form.get('assigned_to') or None
    agente_anterior = ticket.assigned_to
    
    ticket.status = request.form.get('status', ticket.status)
    ticket.priority = request.form.get('priority', ticket.priority)
    ticket.assigned_to = nuevo_agente_id

    db.session.commit()

    # Enviar email solo si el agente ha cambiado
    if nuevo_agente_id and str(nuevo_agente_id) != str(agente_anterior):
        agente = User.query.get(int(nuevo_agente_id))
        if agente:
            enviar_notificacion_asignacion(agente, ticket)

    flash('Ticket actualizado.', 'success')
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))


# Ruta para añadir un comentario a un ticket
@tickets_bp.route('/<int:ticket_id>/comment', methods=['POST'])
@login_required
def add_comment(ticket_id):
    body = request.form.get('body', '').strip()
    if body:
        c = Comment(body=body, ticket_id=ticket_id, user_id=current_user.id)
        db.session.add(c)
        db.session.commit()
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))