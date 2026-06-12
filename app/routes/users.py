from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User

# Blueprint para usuarios
users_bp = Blueprint('users', __name__)

# Decorador para restringir acceso a administradores
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            flash('Acceso restringido a administradores.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


# listar usuarios
@users_bp.route('/')
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.name).all()
    return render_template('users/list.html', users=users)


# crear nuevos usuarios
@users_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        if User.query.filter_by(email=email).first():
            flash('Ya existe un usuario con ese email.', 'danger')
        else:
            u = User(
                name=request.form['name'],
                email=email,
                role=request.form.get('role','user'),
                department=request.form.get('department',''),
            )
            u.set_password(request.form['password'])
            db.session.add(u)
            db.session.commit()
            flash(f'Usuario {u.name} creado.', 'success')
            return redirect(url_for('users.list_users'))

    return render_template('users/new.html')


# activar/desactivar usuarios
@users_bp.route('/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    u = User.query.get_or_404(user_id)
    if u.id == current_user.id:
        flash('No puedes desactivarte a ti mismo.', 'warning')
    else:
        u.active = not u.active
        db.session.commit()
        state = 'activado' if u.active else 'desactivado'
        flash(f'Usuario {u.name} {state}.', 'success')
    return redirect(url_for('users.list_users'))


# modificar usuarios
@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    u = User.query.get_or_404(user_id)

    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        # Comprobar que el email no lo usa otro usuario distinto
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != u.id:
            flash('Ya existe otro usuario con ese email.', 'danger')
        else:
            u.name       = request.form['name']
            u.email      = email
            u.role       = request.form.get('role', u.role)
            u.department = request.form.get('department', '')
            # Solo cambia la contraseña si se ha escrito algo
            new_password = request.form.get('password', '').strip()
            if new_password:
                u.set_password(new_password)
            db.session.commit()
            flash(f'Usuario {u.name} actualizado correctamente.', 'success')
            return redirect(url_for('users.list_users'))

    return render_template('users/edit.html', u=u)


# eliminar usuarios (solo si no tienen tickets asociados)
@users_bp.route('/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    u = User.query.get_or_404(user_id)
    if u.id == current_user.id:
        flash('No puedes eliminarte a ti mismo.', 'warning')
        return redirect(url_for('users.list_users'))
    # Seguridad: no eliminar si tiene tickets creados o asignados
    if u.tickets_creados.count() > 0 or u.tickets_asignados.count() > 0:
        flash(f'No se puede eliminar a {u.name} porque tiene tickets asociados. Desactívalo en su lugar.', 'warning')
        return redirect(url_for('users.list_users'))
    db.session.delete(u)
    db.session.commit()
    flash(f'Usuario {u.name} eliminado.', 'success')
    return redirect(url_for('users.list_users'))


# perfil de usuario (modificar datos propios y cambiar contraseña)
@users_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    u = current_user

    if request.method == 'POST':
        nombre_nuevo = request.form.get('name', '').strip()
        password_actual = request.form.get('current_password', '').strip()
        password_nueva  = request.form.get('new_password', '').strip()
        password_repetir = request.form.get('confirm_password', '').strip()

        if nombre_nuevo:
            u.name = nombre_nuevo

        # Solo cambiar contraseña si se han rellenado los campos
        if password_nueva:
            if not password_actual or not u.check_password(password_actual):
                flash('La contraseña actual no es correcta.', 'danger')
                return render_template('users/profile.html', u=u)

            if password_nueva != password_repetir:
                flash('Las contraseñas nuevas no coinciden.', 'danger')
                return render_template('users/profile.html', u=u)

            if len(password_nueva) < 6:
                flash('La nueva contraseña debe tener al menos 6 caracteres.', 'danger')
                return render_template('users/profile.html', u=u)

            u.set_password(password_nueva)
            flash('Contraseña actualizada correctamente.', 'success')

        db.session.commit()
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('users.profile'))

    return render_template('users/profile.html', u=u)