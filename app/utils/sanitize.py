import re
import bleach

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's',
    'ol', 'ul', 'li', 'a', 'img', 'h1', 'h2', 'h3', 'blockquote'
]

ALLOWED_ATTRS = {
    'a': ['href', 'target', 'rel'],
    'img': ['src', 'alt'],
}

def limpiar_html(html):
    if not html:
        return ''

    # Normaliza entidades frecuentes de Office/Outlook
    html = html.replace('\xa0', ' ')
    html = html.replace('&nbsp;', ' ')

    # Elimina comentarios HTML
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    # Convierte divs en párrafos para evitar estructuras raras
    html = re.sub(r'<\s*div[^>]*>', '<p>', html, flags=re.IGNORECASE)
    html = re.sub(r'<\s*/\s*div\s*>', '</p>', html, flags=re.IGNORECASE)

    # Reduce múltiples saltos
    html = re.sub(r'(<br\s*/?>\s*){3,}', '<br><br>', html, flags=re.IGNORECASE)
    html = re.sub(r'(</p>\s*<p[^>]*>\s*){2,}', '</p><p>', html, flags=re.IGNORECASE)

    # Elimina párrafos vacíos repetidos
    html = re.sub(r'(<p>\s*</p>\s*){2,}', '<p></p>', html, flags=re.IGNORECASE)

    # Elimina atributos peligrosos o innecesarios antes de bleach
    html = re.sub(r'\s+(style|class|lang|dir|face|size|color|width|height|id|title)=["\'].*?["\']', '', html, flags=re.IGNORECASE)

    # Sanitiza manteniendo solo las etiquetas seguras
    html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)

    # Limpieza final de saltos excesivos que puedan quedar tras bleach
    html = re.sub(r'(<br\s*/?>\s*){3,}', '<br><br>', html, flags=re.IGNORECASE)
    html = re.sub(r'(</p>\s*<p[^>]*>\s*){2,}', '</p><p>', html, flags=re.IGNORECASE)

    return html.strip()
