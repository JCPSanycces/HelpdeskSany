from flask_mail import Message
from app import mail
from flask import current_app

def enviar_notificacion_asignacion(agente, ticket):
    try:
        msg = Message(
            subject=f'[HelpDesk] Ticket #{ticket.id} asignado a ti',
            recipients=[agente.email],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #185FA5; padding: 20px; border-radius: 8px 8px 0 0;">
                    <h2 style="color: white; margin: 0;">Nuevo ticket asignado</h2>
                </div>
                <div style="background: #f8f9fa; padding: 24px; border-radius: 0 0 8px 8px;">
                    <p>Hola <strong>{agente.name}</strong>,</p>
                    <p>Se te ha asignado el siguiente ticket de soporte:</p>
                    <table style="width:100%; border-collapse: collapse; margin: 16px 0;">
                        <tr>
                            <td style="padding: 8px; font-weight: bold; width: 120px;">Ticket:</td>
                            <td style="padding: 8px;">#{ticket.id}</td>
                        </tr>
                        <tr style="background: white;">
                            <td style="padding: 8px; font-weight: bold;">Asunto:</td>
                            <td style="padding: 8px;">{ticket.title}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Prioridad:</td>
                            <td style="padding: 8px;">{ticket.priority_label()}</td>
                        </tr>
                        <tr style="background: white;">
                            <td style="padding: 8px; font-weight: bold;">Solicitante:</td>
                            <td style="padding: 8px;">{ticket.solicitante.name if ticket.solicitante else '-'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; vertical-align: top;">Descripción:</td>
                            <td style="padding: 8px;">{ticket.description or '-'}</td>
                        </tr>
                    </table>
                    <p style="color: #666; font-size: 13px; margin-top: 24px;">
                        Mensaje automático del sistema HelpDesk de Sanycces.
                    </p>
                </div>
            </div>
            """
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Error enviando email a {agente.email}: {e}')
