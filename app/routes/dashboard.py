from flask import Blueprint, render_template, current_app, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app.models.app_setting import AppSetting
from app import db
from app.models.ticket import Ticket
from app.models.ticket_participant import TicketParticipant
from datetime import datetime, timedelta
from sqlalchemy import func
import json

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

    # Use global data for dashboard totals and charts so everyone sees complete stats
    global_query = Ticket.query
    total_open     = global_query.filter_by(status='open').count()
    total_progress = global_query.filter_by(status='in_progress').count()
    total_pending  = global_query.filter_by(status='pending').count()
    total_resolved = global_query.filter_by(status='resolved').count()
    total_closed   = global_query.filter_by(status='closed').count()

    # recent_tickets remains scoped to the user (unless admin)
    recent_tickets = base_query.order_by(Ticket.created_at.desc()).limit(10).all()

    # ── Datos para gráficos ──────────────────────────────
    hoy = datetime.utcnow()
    meses_labels = []
    meses_abiertos = []
    meses_resueltos = []
    meses_cerrados  = []

    for i in range(5, -1, -1):
        # Primer y último día del mes
        primer_dia = (hoy.replace(day=1) - timedelta(days=1)).replace(day=1) \
            if i == 0 else \
            (hoy - timedelta(days=30 * i)).replace(day=1)
        # Calcular mes/año correctamente
        mes = hoy.month - i
        año = hoy.year
        while mes <= 0:
            mes += 12
            año -= 1
        primer_dia = datetime(año, mes, 1)
        if mes == 12:
            ultimo_dia = datetime(año + 1, 1, 1)
        else:
            ultimo_dia = datetime(año, mes + 1, 1)

        meses_labels.append(primer_dia.strftime('%b %Y'))

        q = global_query.filter(
            Ticket.created_at >= primer_dia,
            Ticket.created_at < ultimo_dia
        )
        meses_abiertos.append(q.filter_by(status='open').count())
        meses_resueltos.append(q.filter_by(status='resolved').count())
        meses_cerrados.append(q.filter_by(status='closed').count())

    # Distribución por prioridad
    prioridades = {}
    for pri in ['low', 'medium', 'high', 'critical']:
        prioridades[pri] = global_query.filter_by(priority=pri).count()

    # Tickets por estado (totales para donut)
    estados = {
        'open':        total_open,
        'in_progress': total_progress,
        'resolved':    total_resolved,
        'closed':      total_closed,
    }


    # Distribución por categoría
    categorias = {}
    for cat in ['Sage X3', 'Software', 'Hardware', 'Redes e internet', 'EDI', 'Analisis de datos/PowerBI']:
        categorias[cat] = global_query.filter_by(category=cat).count()
    sin_categoria = global_query.filter(
        db.or_(Ticket.category == None, Ticket.category == '')
    ).count()
    if sin_categoria:
        categorias['Sin categoría'] = sin_categoria



    # Read persistent flag directly so UI always reflects DB
    disable_flag = AppSetting.get_bool('disable_email_notifications', default=current_app.config.get('DISABLE_EMAIL_NOTIFICATIONS', False))
    current_app.logger.debug(f'dashboard: disable_email_notifications={disable_flag}')

    return render_template('dashboard.html',
        total_open=total_open,
        total_pending=total_pending,
        total_progress=total_progress,
        total_resolved=total_resolved,
        total_closed=total_closed,
        recent_tickets=recent_tickets,
        meses_labels=json.dumps(meses_labels),
        meses_abiertos=json.dumps(meses_abiertos),
        meses_resueltos=json.dumps(meses_resueltos),
        meses_cerrados=json.dumps(meses_cerrados),
        prioridades=json.dumps(prioridades),
        estados=json.dumps(estados),
        categorias=json.dumps(categorias),
        disable_email_notifications=disable_flag,
    )


@dashboard_bp.route('/toggle-email-notifications', methods=['POST'])
@login_required
def toggle_email_notifications():
    if not current_user.is_admin():
        flash('No tienes permiso para realizar esta acción.', 'danger')
        return redirect(url_for('dashboard.index'))
    # Read current persisted value from DB to avoid mismatch with app.config
    cur = AppSetting.get_bool('disable_email_notifications', default=current_app.config.get('DISABLE_EMAIL_NOTIFICATIONS', False))
    new_val = not cur
    try:
        # persist in DB
        AppSetting.set('disable_email_notifications', 'True' if new_val else 'False')
        db.session.commit()
        current_app.config['DISABLE_EMAIL_NOTIFICATIONS'] = new_val
        state = 'desactivadas' if new_val else 'activadas'
        current_app.logger.info(f'Email notifications toggled: {cur} -> {new_val}')
        flash(f'Notificaciones por correo {state}.', 'success')
    except Exception as e:
        current_app.logger.error(f'Error guardando setting: {e}')
        db.session.rollback()
        flash('No se pudo guardar la configuración.', 'danger')
    return redirect(url_for('dashboard.index'))