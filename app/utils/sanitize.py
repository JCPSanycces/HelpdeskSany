import bleach

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's',
    'ol', 'ul', 'li', 'a', 'img', 'h1', 'h2', 'h3', 'blockquote'
]
ALLOWED_ATTRS = {
    'a':   ['href', 'target', 'rel'],
    'img': ['src', 'alt'],
}

def limpiar_html(html):
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)