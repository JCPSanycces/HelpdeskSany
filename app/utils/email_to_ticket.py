import requests
import msal
import re
from flask import current_app, url_for
import re
from app import db
from app.models.ticket import Ticket
from app.models.ticket_attachment import TicketAttachment
from app.models.comment import Comment
from app.models.comment_attachment import CommentAttachment
from app.models.ticket_participant import TicketParticipant
from app.models.user import User
from app.utils.ticket_id import generar_ticket_id
from app.utils.uploads import guardar_adjunto_bytes
from app.utils.email import enviar_notificacion_comentario

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


def _obtener_token():
    app = msal.ConfidentialClientApplication(
        current_app.config['GRAPH_CLIENT_ID'],
        authority=f"https://login.microsoftonline.com/{current_app.config['GRAPH_TENANT_ID']}",
        client_credential=current_app.config['GRAPH_CLIENT_SECRET'],
    )
    result = app.acquire_token_for_client(scopes=GRAPH_SCOPE)
    if 'access_token' not in result:
        raise Exception(f"Error obteniendo token: {result.get('error_description')}")
    return result['access_token']


def _añadir_participante(ticket_id, user_id):
    existe = TicketParticipant.query.filter_by(
        ticket_id=ticket_id, user_id=user_id).first()
    if not existe:
        db.session.add(TicketParticipant(ticket_id=ticket_id, user_id=user_id))


def _obtener_participantes(ticket_id):
    return TicketParticipant.query.filter_by(ticket_id=ticket_id).all()


def _obtener_o_crear_usuario(email, nombre):
    email = email.strip().lower()
    usuario = User.query.filter_by(email=email).first()
    if usuario:
        return usuario
    usuario = User(name=nombre or email.split('@')[0], email=email, role='user', department='')
    # Crear con contraseña por defecto '1234' y forzar cambio en primer inicio
    usuario.set_password('1234')
    usuario.must_change_password = True
    db.session.add(usuario)
    db.session.flush()
    return usuario


def _obtener_adjuntos_mensaje(headers, mailbox, msg_id):
    """Devuelve la lista de adjuntos (incluye los inline embebidos en el cuerpo)."""
    url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages/{msg_id}/attachments"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        current_app.logger.error(f'Error obteniendo adjuntos de {msg_id}: {resp.text}')
        return []
    return resp.json().get('value', [])


def _procesar_adjuntos(headers, mailbox, msg_id, cuerpo_html, ticket_id=None, comment_id=None):
    """Descarga los adjuntos del correo. Las imágenes inline se insertan en el cuerpo
    en sustitución del cid:..., el resto se guarda como adjunto del ticket o comentario."""
    adjuntos = _obtener_adjuntos_mensaje(headers, mailbox, msg_id)
    cuerpo_final = cuerpo_html

    for adj in adjuntos:
        if adj.get('@odata.type') != '#microsoft.graph.fileAttachment':
            continue  # ignoramos adjuntos de tipo item/referencia

        nombre = adj.get('name', 'adjunto')
        content_bytes = adj.get('contentBytes')
        is_inline = adj.get('isInline', False)
        content_id = adj.get('contentId', '')

        if not content_bytes:
            continue

        guardado = guardar_adjunto_bytes(content_bytes, nombre, subfolder='tickets')
        if not guardado:
            continue

        if is_inline and content_id:
            # Sustituir cid:xxxx por la URL real del fichero guardado en static/
            url_publica = f"/static/{guardado['file_path']}"
            patron = re.compile(re.escape(f'cid:{content_id}'), re.IGNORECASE)
            cuerpo_final = patron.sub(url_publica, cuerpo_final)
        else:
            # Adjunto real (documento, o imagen no incrustada): lo asociamos al ticket o comentario
            if ticket_id:
                db.session.add(TicketAttachment(
                    ticket_id=ticket_id,
                    filename=guardado['filename'],
                    file_path=guardado['file_path'],
                    file_type=guardado['file_type'],
                ))
            elif comment_id:
                db.session.add(CommentAttachment(
                    comment_id=comment_id,
                    filename=guardado['filename'],
                    file_path=guardado['file_path'],
                    file_type=guardado['file_type'],
                ))

    return cuerpo_final


def procesar_correos_nuevos():
    token = _obtener_token()
    mailbox = current_app.config['HELPDESK_MAILBOX']
    headers = {'Authorization': f'Bearer {token}'}

    url = (
        f"https://graph.microsoft.com/v1.0/users/{mailbox}/mailFolders/inbox/messages"
        f"?$filter=isRead eq false"
        f"&$select=id,subject,body,from,conversationId,hasAttachments,receivedDateTime&$top=25"
    )

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        current_app.logger.error(f'Error consultando Graph API: {response.status_code} {response.text}')
        return 0

    mensajes = response.json().get('value', [])
    procesados = 0

    for msg in mensajes:
        msg_id = msg['id']
        asunto = msg.get('subject') or '(Sin asunto)'

        # --- Ignorar por asunto (configurable) ---
        ignored_cfg = current_app.config.get('IGNORED_EMAIL_SUBJECTS', '')
        skip_msg = False
        if ignored_cfg:
            parts = [p.strip().lower() for p in re.split(r'[;,|\n]+', ignored_cfg) if p.strip()]
            subj_lower = (asunto or '').lower()
            for part in parts:
                if part and part in subj_lower:
                    _marcar_leido(headers, mailbox, msg_id)
                    skip_msg = True
                    break
        if skip_msg:
            continue

        cuerpo = msg.get('body', {}).get('content', '')
        conversation_id = msg.get('conversationId')
        tiene_adjuntos = msg.get('hasAttachments', False)
        from_info = msg.get('from', {}).get('emailAddress', {})
        remitente_email = from_info.get('address', '').strip().lower()
        remitente_nombre = from_info.get('name', '')

        if not remitente_email:
            continue
        if remitente_email == mailbox.strip().lower():
            _marcar_leido(headers, mailbox, msg_id)
            continue

        # --- Ignorar por remitente (configurable) ---
        ignored_senders_cfg = current_app.config.get('IGNORED_EMAIL_SENDERS', '')
        if ignored_senders_cfg:
            send_parts = [p.strip().lower() for p in re.split(r'[;,|\n]+', ignored_senders_cfg) if p.strip()]
            sender_lower = remitente_email.lower()
            skip_sender = False
            for part in send_parts:
                if part and part in sender_lower:
                    _marcar_leido(headers, mailbox, msg_id)
                    skip_sender = True
                    break
            if skip_sender:
                continue

        try:
            remitente = _obtener_o_crear_usuario(remitente_email, remitente_nombre)

            ticket_existente = None
            if conversation_id:
                ticket_existente = Ticket.query.filter_by(
                    graph_conversation_id=conversation_id).first()

            if ticket_existente:
                # Crear primero el comentario para tener su id, procesar adjuntos después
                c = Comment(body=cuerpo, ticket_id=ticket_existente.ticket_id, user_id=remitente.id)
                db.session.add(c)
                db.session.flush()

                if tiene_adjuntos:
                    cuerpo_procesado = _procesar_adjuntos(
                        headers, mailbox, msg_id, cuerpo, comment_id=c.id)
                    c.body = cuerpo_procesado

                _añadir_participante(ticket_existente.ticket_id, remitente.id)
                db.session.commit()

                participantes = _obtener_participantes(ticket_existente.ticket_id)
                enviar_notificacion_comentario(remitente, ticket_existente, c, participantes)

                current_app.logger.info(
                    f'Comentario añadido al ticket {ticket_existente.ticket_id} desde correo de {remitente_email}')
            else:
                ticket_id_nuevo = generar_ticket_id()

                if tiene_adjuntos:
                    cuerpo = _procesar_adjuntos(
                        headers, mailbox, msg_id, cuerpo, ticket_id=ticket_id_nuevo)

                t = Ticket(
                    ticket_id=ticket_id_nuevo,
                    title=asunto,
                    description=cuerpo,
                    priority='medium',
                    category='SAGE X3',
                    created_by=remitente.id,
                    assigned_to=None,
                    graph_conversation_id=conversation_id,
                )
                db.session.add(t)
                db.session.flush()
                _añadir_participante(t.ticket_id, remitente.id)
                db.session.commit()

                current_app.logger.info(f'Ticket {t.ticket_id} creado desde correo de {remitente_email}')

            procesados += 1

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error procesando correo {msg_id}: {e}')
            continue

        _marcar_leido(headers, mailbox, msg_id)

    return procesados


def _marcar_leido(headers, mailbox, msg_id):
    marcar_url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages/{msg_id}"
    resp = requests.patch(marcar_url, headers=headers, json={'isRead': True})
    if resp.status_code not in (200, 202):
        current_app.logger.error(
            f'No se pudo marcar como leído el correo {msg_id}: {resp.status_code} {resp.text}')