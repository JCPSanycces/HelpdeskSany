import requests
import msal
import re
from flask import current_app
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
from bs4 import BeautifulSoup

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]

# Función auxiliar para obtener un token de acceso a Microsoft Graph
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

# Funciones auxiliares para manejar participantes de tickets y usuarios
def _añadir_participante(ticket_id, user_id):
    existe = TicketParticipant.query.filter_by(
        ticket_id=ticket_id, user_id=user_id
    ).first()
    if not existe:
        db.session.add(TicketParticipant(ticket_id=ticket_id, user_id=user_id))

# Función auxiliar para obtener los participantes de un ticket
def _obtener_participantes(ticket_id):
    return TicketParticipant.query.filter_by(ticket_id=ticket_id).all()

# Función auxiliar para obtener o crear un usuario a partir de un correo electrónico
def _obtener_o_crear_usuario(email, nombre):
    email = email.strip().lower()
    usuario = User.query.filter_by(email=email).first()
    if usuario:
        return usuario

    usuario = User(
        name=nombre or email.split('@')[0],
        email=email,
        role='user',
        department=''
    )
    # Crear con contraseña por defecto '1234' y forzar cambio en primer inicio
    usuario.set_password('1234')
    usuario.must_change_password = True
    db.session.add(usuario)
    db.session.flush()
    return usuario

# Obtiene los adjuntos del mensaje de correo, incluidas las imágenes inline.
def _obtener_adjuntos_mensaje(headers, mailbox, msg_id):
    """Devuelve la lista de adjuntos (incluye los inline embebidos en el cuerpo)."""
    url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages/{msg_id}/attachments"
    resp = requests.get(url, headers=headers)

    if resp.status_code != 200:
        current_app.logger.error(f'Error obteniendo adjuntos de {msg_id}: {resp.text}')
        return []
    try:
        data = resp.json()
        return data.get('value', [])
    except Exception as e:
        current_app.logger.error(f'Error interpretando adjuntos de {msg_id}: {e}')
        return []

# Sustituye las referencias cid: de las imágenes inline por sus URLs públicas.
def _reemplazar_cid_en_html(cuerpo_html, content_id, url_publica):
    """Reemplaza referencias cid en el HTML del correo."""
    if not cuerpo_html or not content_id:
        return cuerpo_html

    # Reemplaza src="cid:xxxx" o src='cid:xxxx'
    cuerpo_html = re.sub(
        r'src\s*=\s*[\'"]cid:' + re.escape(content_id) + r'[\'"]',
        f'src="{url_publica}"',
        cuerpo_html,
        flags=re.IGNORECASE
    )

    # Reemplaza cualquier referencia cid:xxxx suelta
    cuerpo_html = re.sub(
        re.escape(f'cid:{content_id}'),
        url_publica,
        cuerpo_html,
        flags=re.IGNORECASE
    )

    return cuerpo_html

# Descarga y procesa los adjuntos del correo, asociándolos al ticket o comentario.
def _procesar_adjuntos(headers, mailbox, msg_id, cuerpo_html, ticket_id=None, comment_id=None):
    """Descarga los adjuntos del correo.

    Las imágenes inline se insertan en el cuerpo en sustitución del cid:...,
    el resto se guarda como adjunto del ticket o comentario.
    """
    adjuntos = _obtener_adjuntos_mensaje(headers, mailbox, msg_id)
    cuerpo_final = cuerpo_html

    # Extraemos todos los CID que aparezcan en el HTML
    cids_en_html = set(re.findall(r'cid:([^"\'>\s]+)', cuerpo_html or '', flags=re.IGNORECASE))

    for adj in adjuntos:
        if adj.get('@odata.type') != '#microsoft.graph.fileAttachment':
            continue  # ignoramos adjuntos de tipo item/referencia

        nombre = adj.get('name', 'adjunto')
        content_bytes = adj.get('contentBytes')
        is_inline = adj.get('isInline', False)
        content_id = adj.get('contentId', '') or ''

        if not content_bytes:
            continue

        guardado = guardar_adjunto_bytes(content_bytes, nombre, subfolder='tickets')
        if not guardado:
            continue

        url_publica = f"/static/{guardado['file_path']}"

        # Si es inline, intentamos sustituir la referencia cid del HTML
        if is_inline and content_id:
            cuerpo_final = _reemplazar_cid_en_html(cuerpo_final, content_id, url_publica)

            # A veces el contentId no coincide exactamente, pero el nombre sí aparece en el HTML
            # o el correo usa el CID sin algunos caracteres. Probamos también con coincidencias parciales.
            for cid_html in list(cids_en_html):
                if cid_html.lower() == content_id.lower():
                    cuerpo_final = _reemplazar_cid_en_html(cuerpo_final, cid_html, url_publica)

            continue

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

# Procesa los correos no leídos de la bandeja de entrada y crea o actualiza tickets.
def procesar_correos_nuevos():
    token = _obtener_token()
    mailbox = current_app.config['HELPDESK_MAILBOX']
    headers = {'Authorization': f'Bearer {token}'}

    url = (
        f"https://graph.microsoft.com/v1.0/users/{mailbox}/mailFolders/inbox/messages"
        f"?$filter=isRead eq false"
        f"&$select=id,subject,body,from,conversationId,hasAttachments,receivedDateTime"
        f"&$top=25"
    )

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        current_app.logger.error(
            f'Error consultando Graph API: {response.status_code} {response.text}'
        )
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
        from_info = msg.get('from', {}).get('emailAddress', {})
        remitente_email = from_info.get('address', '').strip().lower()
        remitente_nombre = from_info.get('name', '')

        if not remitente_email:
            continue

        # Marcamos si el mensaje viene del propio buzón del helpdesk
        es_helpdesk = remitente_email == mailbox.strip().lower()

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
                    graph_conversation_id=conversation_id
                ).first()

            # Si el correo viene del propio helpdesk y no pertenece a un ticket,
            # lo ignoramos para evitar bucles o ecos de notificaciones.
            if es_helpdesk and not ticket_existente:
                _marcar_leido(headers, mailbox, msg_id)
                continue

            if ticket_existente:

                respuesta_nueva = _extraer_respuesta_nueva(cuerpo)

                if not respuesta_nueva.strip():
                    current_app.logger.info(
                        f'Correo {msg_id} descartado: no contiene respuesta nueva utilizable.'
                    )
                    _marcar_leido(headers, mailbox, msg_id)
                    continue

                c = Comment(
                    body=respuesta_nueva,
                    ticket_id=ticket_existente.ticket_id,
                    user_id=remitente.id
                )
                db.session.add(c)
                db.session.flush()
                cuerpo_procesado = _procesar_adjuntos(
                    headers, mailbox, msg_id, respuesta_nueva, comment_id=c.id
                )
                c.body = cuerpo_procesado

                _añadir_participante(ticket_existente.ticket_id, remitente.id)
                db.session.commit()

                participantes = _obtener_participantes(ticket_existente.ticket_id)
                enviar_notificacion_comentario(remitente, ticket_existente, c, participantes)

                current_app.logger.info(
                    f'Comentario añadido al ticket {ticket_existente.ticket_id} desde correo de {remitente_email}'
                )

            else:
                ticket_id_nuevo = generar_ticket_id()

                # Procesa también las imágenes inline aunque el mensaje no indique adjuntos.
                cuerpo = _procesar_adjuntos(
                    headers, mailbox, msg_id, cuerpo, ticket_id=ticket_id_nuevo
                )

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

                current_app.logger.info(
                    f'Ticket {t.ticket_id} creado desde correo de {remitente_email}'
                )

            procesados += 1

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error procesando correo {msg_id}: {e}')
            continue

        _marcar_leido(headers, mailbox, msg_id)

    return procesados



# Marca un correo como leído en Microsoft Graph.
def _marcar_leido(headers, mailbox, msg_id):
    marcar_url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages/{msg_id}"
    resp = requests.patch(marcar_url, headers=headers, json={'isRead': True})
    if resp.status_code not in (200, 202):
        current_app.logger.error(
            f'No se pudo marcar como leído el correo {msg_id}: {resp.status_code} {resp.text}'
        )

# Extrae únicamente la respuesta nueva del correo, eliminando el hilo citado.
def _extraer_respuesta_nueva(html):
    """Extrae la respuesta nueva y elimina el hilo anterior de Outlook.

    Outlook suele insertar el mensaje anterior después de una cabecera
    visual separada mediante una línea superior. Se localiza esa cabecera
    buscando "De:" o "From:" y el DIV que contiene el estilo "border-top".
    Todo el contenido a partir de ese punto se elimina, conservando la
    respuesta nueva, su firma y las imágenes inline.
    """

    if not html:
        return ''

    soup = BeautifulSoup(html, 'html.parser')
    cabecera_hilo = None

    # Buscar la cabecera "De:" / "From:" que marca el inicio
    # del correo anterior.
    for elemento in soup.find_all(string=True):
        if elemento.strip() in ('De:', 'From:'):
            padre = elemento.parent

            # Subimos por la estructura HTML hasta localizar el DIV
            # que contiene la línea horizontal de separación del hilo.
            for _ in range(10):
                if padre is None:
                    break

                estilo = padre.get('style', '')

                if (
                    padre.name == 'div'
                    and 'border-top' in estilo.lower()
                ):
                    cabecera_hilo = padre
                    break

                padre = padre.parent

        if cabecera_hilo:
            break

    if cabecera_hilo:
        # Eliminar todo lo que aparece después de la cabecera
        # del mensaje anterior.
        for elemento in list(cabecera_hilo.find_all_next()):
            elemento.decompose()

        # Eliminar también la propia cabecera del mensaje anterior.
        cabecera_hilo.decompose()

    return str(soup).strip()
