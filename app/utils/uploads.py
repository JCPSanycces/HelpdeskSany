import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename
import base64

ALLOWED_IMAGES = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_DOCS   = {'txt', 'docx', 'pptx', 'xlsx', 'pdf'}
ALLOWED_ALL    = ALLOWED_IMAGES | ALLOWED_DOCS

def get_extension(filename):
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[1].lower()

def allowed_file(filename):
    return get_extension(filename) in ALLOWED_ALL

def get_file_type(filename):
    return 'imagen' if get_extension(filename) in ALLOWED_IMAGES else 'documento'

def guardar_adjunto(file, subfolder='comments'):
    """Guarda un fichero en static/uploads/<subfolder>/ y devuelve sus datos o None."""
    if not file or file.filename == '':
        return None

    ext = get_extension(file.filename)
    if ext not in ALLOWED_ALL:
        return None

    original_name = secure_filename(file.filename)
    stored_name   = f"{uuid.uuid4().hex}.{ext}"

    upload_folder = os.path.join(current_app.config['UPLOAD_BASE'], subfolder)
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, stored_name))

    return {
        'file_path': f"uploads/{subfolder}/{stored_name}",
        'file_type': get_file_type(file.filename),
        'filename':  original_name,
    }

# Eliminar un adjunto implica eliminar su registro en la base de datos y el fichero físico.
def eliminar_adjunto_fichero(file_path):
    """Elimina el fichero físico dentro de static/<file_path>."""
    full_path = os.path.join(current_app.root_path, 'static', file_path)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except OSError:
            pass

# Guardar un adjunto a partir de contenido en base64 (usado para adjuntos de Graph API)
def guardar_adjunto_bytes(contenido_base64, filename_original, subfolder='tickets'):
    """Guarda un fichero a partir de contenido en base64 (usado para adjuntos de Graph API)."""
    ext = get_extension(filename_original)
    if ext not in ALLOWED_ALL:
        return None

    try:
        contenido = base64.b64decode(contenido_base64)
    except Exception:
        return None

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    upload_folder = os.path.join(current_app.config['UPLOAD_BASE'], subfolder)
    os.makedirs(upload_folder, exist_ok=True)

    with open(os.path.join(upload_folder, stored_name), 'wb') as f:
        f.write(contenido)

    return {
        'file_path': f"uploads/{subfolder}/{stored_name}",
        'file_type': get_file_type(filename_original),
        'filename':  secure_filename(filename_original),
    }