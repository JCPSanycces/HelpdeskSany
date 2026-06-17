from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import user
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

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
            # Si debe cambiar la contraseña, redirigir al perfil para forzar cambio
            if getattr(user, 'must_change_password', False):
                return redirect(url_for('users.profile', force=1))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Email o contrasena incorrectos.', 'danger')
            return render_template('auth/login.html')
    # GET
    return render_template('auth/login.html')
    
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesion correctamente.', 'info')
    return redirect(url_for('auth.login'))