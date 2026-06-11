from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.ticket import Ticket
from app.models.comment import Comment
from app.models.user import User
from app.models.ticket_participant import TicketParticipant
from app.utils.ticket_id import generar_ticket_id
from app.utils.email import (
    enviar_notificacion_asignacion,
    enviar_notificacion_comentario,
    enviar_notificacion_cambio_estado,
)
from app.utils.uploads import guardar_adjunto
from app.models.comment_attachment import CommentAttachment

tickets_bp = Blueprint('tickets', __name__)


# Funciones auxiliares para manejar participantes del ticket
def _añadir_participante(ticket_id, user_id):
    """Añade un participante al ticket si no existe ya."""
    existe = TicketParticipant.query.filter_by(
        ticket_id=ticket_id, user_id=user_id
    ).first()
    if not existe:
        db.session.add(TicketParticipant(ticket_id=ticket_id, user_id=user_id))


# Obtener participantes del ticket para notificaciones
def _get_participantes(ticket_id):
    return TicketParticipant.query.filter_by(ticket_id=ticket_id).all()


# Listado de tickets con filtros
@tickets_bp.route('/')
@login_required
def list_tickets():
    status   = request.args.get('status', '')
    priority = request.args.get('priority', '')
    category = request.args.get('category', '')

    if current_user.is_admin():
        query = Ticket.query
    else:
        tickets_participante = db.session.query(TicketParticipant.ticket_id)\
            .filter_by(user_id=current_user.id).subquery()
        query = Ticket.query.filter(
            db.or_(
                Ticket.created_by == current_user.id,
                Ticket.ticket_id.in_(tickets_participante)
            )
        )

    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if category:
        query = query.filter_by(category=category)

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return render_template('tickets/list.html', tickets=tickets,
                           status=status, priority=priority, category=category)


# Crear nuevo ticket con opción de asignar a un agente
@tickets_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_ticket():
    agents = User.query.filter(
        User.role.in_(['admin', 'agent'])).filter_by(active=True).all()

    if request.method == 'POST':
        assigned_id = request.form.get('assigned_to') or None
        t = Ticket(
            ticket_id=generar_ticket_id(),
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
        _añadir_participante(t.ticket_id, current_user.id)
        if assigned_id:
            _añadir_participante(t.ticket_id, int(assigned_id))

        db.session.commit()

        # Notificar al agente asignado
        if assigned_id:
            agente = User.query.get(int(assigned_id))
            if agente:
                enviar_notificacion_asignacion(agente, t)

        flash(f'Ticket {t.ticket_id} creado correctamente.', 'success')
        return redirect(url_for('tickets.detail', ticket_id=t.ticket_id))

    return render_template('tickets/new.html', agents=agents)


# Notificar al agente asignado
@tickets_bp.route('/<string:ticket_id>')
@login_required
def detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    agents = User.query.filter(
        User.role.in_(['admin', 'agent'])).filter_by(active=True).all()

    participantes     = TicketParticipant.query.filter_by(ticket_id=ticket_id).all()
    ids_participantes = {p.user_id for p in participantes}
    todos_usuarios    = User.query.filter_by(active=True).order_by(User.name).all()
    usuarios_disponibles = User.query.filter(
        User.active == True,
        ~User.id.in_(ids_participantes)
    ).order_by(User.name).all()

    return render_template('tickets/detail.html',
        ticket=ticket,
        agents=agents,
        participantes=participantes,
        ids_participantes=ids_participantes,
        todos_usuarios=todos_usuarios,
        usuarios_disponibles=usuarios_disponibles,
    )


# actualizar estado, prioridad, asignación y usuarios añadidos
@tickets_bp.route('/<string:ticket_id>/update', methods=['POST'])
@login_required
def update_ticket(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not current_user.is_agent():
        flash('No tienes permiso para hacer eso.', 'danger')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    nuevo_agente_id    = request.form.get('assigned_to') or None
    agente_anterior_id = ticket.assigned_to
    estado_anterior    = ticket.status
    nuevo_estado       = request.form.get('status', ticket.status)

    ticket.status      = nuevo_estado
    ticket.priority    = request.form.get('priority', ticket.priority)
    ticket.assigned_to = nuevo_agente_id
    ticket.category    = request.form.get('category', ticket.category)

    # Gestionar participantes del selector múltiple
    ids_seleccionados = set(
        int(i) for i in request.form.getlist('participantes_ids')
    )
    ids_actuales = {
        p.user_id for p in TicketParticipant.query.filter_by(ticket_id=ticket_id).all()
    }

    # El creador nunca se puede eliminar
    protegidos = {ticket.created_by}
    a_eliminar = ids_actuales - ids_seleccionados - protegidos

    for uid in a_eliminar:
        TicketParticipant.query.filter_by(
            ticket_id=ticket_id, user_id=uid).delete()

    nuevos_ids = ids_seleccionados - ids_actuales
    for uid in nuevos_ids:
        _añadir_participante(ticket_id, uid)

    # Forzar que creador y agente asignado siempre estén como participantes
    _añadir_participante(ticket_id, ticket.created_by)
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

    # Email a nuevos participantes añadidos
    if nuevos_ids:
        from app.utils.email import _enviar, _base_html
        for uid in nuevos_ids:
            nuevo = User.query.get(uid)
            if nuevo:
                html = _base_html(
                    f'📋 Añadido al ticket {ticket_id}',
                    f"""
                    <p>Hola <strong>{nuevo.name}</strong>,</p>
                    <p>Has sido añadido como participante en el ticket
                       <strong>{ticket_id}: {ticket.title}</strong>.</p>
                    <p>A partir de ahora recibirás notificaciones de todas las
                       interacciones de este ticket.</p>
                    <p style="color:#666; font-size:13px;">
                        Estado: <strong>{ticket.status_label()}</strong> ·
                        Prioridad: <strong>{ticket.priority_label()}</strong>
                    </p>
                    """
                )
                _enviar(
                    [nuevo.email],
                    f'[HelpDesk] Añadido al ticket {ticket_id}',
                    html,
                    thread_id=ticket.email_thread_id
                )

    flash('Ticket actualizado.', 'success')
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))


# Añadir comentario al ticket
@tickets_bp.route('/<string:ticket_id>/comment', methods=['POST'])
@login_required
def add_comment(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    body   = request.form.get('body', '').strip()

    if body:
        c = Comment(body=body, ticket_id=ticket_id, user_id=current_user.id)
        db.session.add(c)
        db.session.flush()  # Para tener c.id antes del commit

        # Guardar todos los ficheros adjuntos
        ficheros = request.files.getlist('adjuntos')
        for file in ficheros:
            resultado = guardar_adjunto(file)
            if resultado:
                adjunto = CommentAttachment(
                    comment_id=c.id,
                    filename=resultado['filename'],
                    file_path=resultado['file_path'],
                    file_type=resultado['file_type'],
                )
                db.session.add(adjunto)

        _añadir_participante(ticket_id, current_user.id)
        db.session.commit()

        participantes = _get_participantes(ticket_id)
        enviar_notificacion_comentario(current_user, ticket, c, participantes)

    return redirect(url_for('tickets.detail', ticket_id=ticket_id))


# Solo los admins pueden eliminar tickets
@tickets_bp.route('/<string:ticket_id>/delete', methods=['POST'])
@login_required
def delete_ticket(ticket_id):
    if not current_user.is_admin():
        flash('No tienes permiso para eliminar tickets.', 'danger')
        return redirect(url_for('tickets.list_tickets'))

    ticket = Ticket.query.get_or_404(ticket_id)

    # Eliminar comentarios y participantes asociados (por si cascade no está activo)
    Comment.query.filter_by(ticket_id=ticket_id).delete()
    TicketParticipant.query.filter_by(ticket_id=ticket_id).delete()
    db.session.delete(ticket)
    db.session.commit()

    flash(f'Ticket {ticket_id} eliminado correctamente.', 'success')
    return redirect(url_for('tickets.list_tickets'))


@tickets_bp.route('/<string:ticket_id>/add_participant', methods=['POST'])
@login_required
def add_participant(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)

    # Solo admin o participantes actuales pueden añadir
    es_participante = TicketParticipant.query.filter_by(
        ticket_id=ticket_id, user_id=current_user.id).first()
    if not current_user.is_admin() and not es_participante:
        flash('No tienes permiso para añadir participantes.', 'danger')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    user_id = request.form.get('user_id')
    if not user_id:
        flash('Selecciona un usuario.', 'warning')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    user_id = int(user_id)
    existe = TicketParticipant.query.filter_by(
        ticket_id=ticket_id, user_id=user_id).first()
    if existe:
        flash('Ese usuario ya es participante del ticket.', 'warning')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    _añadir_participante(ticket_id, user_id)
    db.session.commit()

    nuevo = User.query.get(user_id)
    # Notificar al nuevo participante
    from app.utils.email import _enviar, _base_html
    html = _base_html(
        f'📋 Añadido al ticket #{ticket_id}',
        f"""
        <p>Hola <strong>{nuevo.name}</strong>,</p>
        <p>Has sido añadido como participante en el ticket
           <strong>{ticket_id}: {ticket.title}</strong>.</p>
        <p>A partir de ahora recibirás notificaciones de todas las
           interacciones de este ticket.</p>
        <p style="color:#666; font-size:13px;">
            Estado: <strong>{ticket.status_label()}</strong> ·
            Prioridad: <strong>{ticket.priority_label()}</strong>
        </p>
        """
    )
    _enviar(
        [nuevo.email],
        f'[HelpDesk] Añadido al ticket {ticket_id}',
        html,
        thread_id=ticket.email_thread_id
    )

    flash(f'{nuevo.name} añadido como participante.', 'success')
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))