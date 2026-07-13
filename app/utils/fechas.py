from datetime import datetime
import pytz

def ahora_espana():
    """Devuelve la hora actual en zona horaria de España, sin info de zona (para PostgreSQL)."""
    zona = pytz.timezone('Europe/Madrid')
    return datetime.now(zona).replace(tzinfo=None)