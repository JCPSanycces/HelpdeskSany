from app import db
from app.models.ticket_counter import TicketCounter
from datetime import datetime

def generar_ticket_id():
    """Genera el próximo ID de ticket en formato YYYY-NNNNN."""
    year = datetime.utcnow().year

    # Busca o crea el contador para este año
    contador = TicketCounter.query.filter_by(year=year).with_for_update().first()
    if not contador:
        contador = TicketCounter(year=year, counter=0)
        db.session.add(contador)

    contador.counter += 1
    db.session.flush()  # Guarda el incremento antes de usarlo

    return f"{year}-{contador.counter:05d}"