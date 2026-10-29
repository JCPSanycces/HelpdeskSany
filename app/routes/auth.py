from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash
from app.models.user import User
from app import db, mail
from flask_mail import Message

auth_bp = Blueprint('auth', __name__)

# -------------------------------------------------
# Helpers para generar/validar tokens de reset
# -------------------------------------------------
def _get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

def _generate_reset_token(user):
    s = _get_serializer()
    return s.dumps(user.email, salt='password-reset-salt')

def _confirm_reset_token(token, max_age=None):
    s = _get_serializer()
    if max_age is None:
        max_age = current_app.config.get('PASSWORD_RESET_TOKEN_EXPIRES', 3600)
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=max_age)
        return email
    except SignatureExpired:
        return None
    except BadSignature:
        return None

def _send_reset_email(user):
    token = _generate_reset_token(user)
    reset_url = url_for('auth.reset_password_token', token=token, _external=True)

    msg = Message(
        subject='[HelpDesk] Restablecer contraseña',
        recipients=[user.email]
    )
    msg.html = render_template('auth/reset_password_email.html', user=user, reset_url=reset_url)
    mail.send(msg)

# -------------------------------------------------
# Login
# -------------------------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        user = User.query.filter_by(email=email).first()
        if user and user.active and user.check_password(password):
            login_user(user, remember=remember)
            if getattr(user, 'must_change_password', False):
                return redirect(url_for('users.profile', force=1))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Email o contrasena incorrectos.', 'danger')
            return render_template('auth/login.html')

    return render_template('auth/login.html')

# -------------------------------------------------
# Logout
# -------------------------------------------------
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesion correctamente.', 'info')
    return redirect(url_for('auth.login'))

# -------------------------------------------------
# Solicitar restablecimiento de contraseña
# -------------------------------------------------
@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email, active=True).first()

        # Mensaje neutro por seguridad (no revelar si existe o no)
        if user:
            _send_reset_email(user)

        flash('Si el email existe en el sistema, recibirás un enlace para restablecer la contraseña.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password_request.html')

# -------------------------------------------------
# Establecer nueva contraseña desde token
# -------------------------------------------------
@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    email = _confirm_reset_token(token)
    if not email:
        flash('El enlace no es válido o ha expirado.', 'danger')
        return redirect(url_for('auth.reset_password_request'))

    user = User.query.filter_by(email=email, active=True).first()
    if not user:
        flash('El enlace no es válido o ha expirado.', 'danger')
        return redirect(url_for('auth.reset_password_request'))

    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        password2 = request.form.get('password2', '').strip()

        if not password or len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'warning')
            return render_template('auth/reset_password_form.html', token=token, user=user)

        if password != password2:
            flash('Las contraseñas no coinciden.', 'warning')
            return render_template('auth/reset_password_form.html', token=token, user=user)

        user.set_password(password)
        user.must_change_password = False
        db.session.commit()

        flash('Contraseña actualizada correctamente. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password_form.html', token=token, user=user)
