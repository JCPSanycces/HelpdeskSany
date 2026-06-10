from flask_mail import Message
from app import mail
from flask import current_app

def _base_html(titulo, cuerpo_html):
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #185FA5; padding: 20px; border-radius: 8px 8px 0 0;">
            <h2 style="color: white; margin: 0;">{titulo}</h2>
        </div>
        <div style="background: #f8f9fa; padding: 24px; border-radius: 0 0 8px 8px;">
            {cuerpo_html}
            <p style="color: #999; font-size: 12px; margin-top: 24px; border-top: 1px solid #ddd; padding-top: 12px;">
                Mensaje automático del sistema HelpDesk de Sanycces.
            </p>
        </div>
    </div>
    """

def _enviar(destinatarios, subject, html, thread_id=None):
    """Envía un email. Si se pasa thread_id, lo encadena al hilo."""
    try:
        msg = Message(subject=subject, recipients=destinatarios, html=html)
        # Cabeceras para encadenar en el mismo hilo de correo
        if thread_id:
            msg.extra_headers = {
                'References': thread_id,
                'In-Reply-To': thread_id,
            }
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Error enviando email a {destinatarios}: {e}')


def enviar_notificacion_asignacion(agente, ticket):
    """Avisa al agente cuando se le asigna el ticket."""
    html = _base_html(
        '🎫 Nuevo ticket asignado',
        f"""
        <p>Hola <strong>{agente.name}</strong>,</p>
        <p>Se te ha asignado el siguiente ticket:</p>
        <table style="width:100%; border-collapse:collapse; margin:16px 0;">
            <tr><td style="padding:8px; font-weight:bold; width:120px;">Ticket:</td>
                <td style="padding:8px;">#{ticket.ticket_id}</td></tr>
            <tr style="background:white;"><td style="padding:8px; font-weight:bold;">Asunto:</td>
                <td style="padding:8px;">{ticket.title}</td></tr>
            <tr><td style="padding:8px; font-weight:bold;">Prioridad:</td>
                <td style="padding:8px;">{ticket.priority_label()}</td></tr>
            <tr style="background:white;"><td style="padding:8px; font-weight:bold;">Solicitante:</td>
                <td style="padding:8px;">{ticket.solicitante.name if ticket.solicitante else '-'}</td></tr>
            <tr><td style="padding:8px; font-weight:bold; vertical-align:top;">Descripción:</td>
                <td style="padding:8px;">{ticket.description or '-'}</td></tr>
        </table>
        """
    )
    _enviar(
        [agente.email],
        f'[HelpDesk] Ticket #{ticket.ticket_id} asignado a ti',
        html,
        thread_id=ticket.email_thread_id
    )


def enviar_notificacion_comentario(autor, ticket, comentario, participantes):
    """Avisa a todos los participantes del ticket excepto al autor del comentario."""
    destinatarios = [
        p.user.email for p in participantes
        if p.user.email != autor.email and p.user.active
    ]
    if not destinatarios:
        return

    html = _base_html(
        f'💬 Nuevo comentario en Ticket #{ticket.ticket_id}',
        f"""
        <p><strong>{autor.name}</strong> ha añadido un comentario en el ticket
           <strong>#{ticket.ticket_id}: {ticket.title}</strong>:</p>
        <div style="background:white; border-left:4px solid #185FA5;
                    padding:12px 16px; margin:16px 0; border-radius:0 4px 4px 0;">
            {comentario.body}
        </div>
        <p style="color:#666; font-size:13px;">
            Estado actual: <strong>{ticket.status_label()}</strong> ·
            Prioridad: <strong>{ticket.priority_label()}</strong>
        </p>
        """
    )
    _enviar(
        destinatarios,
        f'[HelpDesk] Comentarios Ticket #{ticket.ticket_id}',
        html,
        thread_id=ticket.email_thread_id
    )


def enviar_notificacion_cambio_estado(ticket, estado_anterior, participantes):
    """Avisa a todos los participantes cuando cambia el estado del ticket."""
    destinatarios = [p.user.email for p in participantes if p.user.active]
    if not destinatarios:
        return

    html = _base_html(
        f'🔄 Cambio de estado en Ticket #{ticket.ticket_id}',
        f"""
        <p>El ticket <strong>#{ticket.ticket_id}: {ticket.title}</strong>
           ha cambiado de estado:</p>
        <div style="display:flex; align-items:center; gap:12px; margin:16px 0;">
            <span style="background:#e0e0e0; padding:6px 14px; border-radius:20px;">
                {ticket.STATUS_LABELS.get(estado_anterior, estado_anterior)}
            </span>
            <span style="font-size:20px;">→</span>
            <span style="background:#185FA5; color:white; padding:6px 14px; border-radius:20px;">
                {ticket.status_label()}
            </span>
        </div>
        <p style="color:#666; font-size:13px;">
            Prioridad: <strong>{ticket.priority_label()}</strong> ·
            Asignado a: <strong>{ticket.agente.name if ticket.agente else 'Sin asignar'}</strong>
        </p>
        """
    )
    _enviar(
        destinatarios,
        f'[HelpDesk] Cambio de estado Ticket #{ticket.ticket_id}',
        html,
        thread_id=ticket.email_thread_id
    )