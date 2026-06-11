import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename

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

def guardar_adjunto(file):
    """Guarda un fichero y devuelve (file_path, file_type, filename_original) o None."""
    if not file or file.filename == '':
        return None

    ext = get_extension(file.filename)
    if ext not in ALLOWED_ALL:
        return None

    original_name = secure_filename(file.filename)
    stored_name   = f"{uuid.uuid4().hex}.{ext}"
    upload_folder = os.path.join(
        current_app.config['UPLOAD_FOLDER']
    )
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, stored_name))

    return {
        'file_path': f"uploads/comments/{stored_name}",
        'file_type': get_file_type(file.filename),
        'filename':  original_name,
    }