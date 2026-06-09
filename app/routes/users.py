from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User

users_bp = Blueprint('users', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            flash('Acceso restringido a administradores.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated

@users_bp.route('/')
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.name).all()
    return render_template('users/list.html', users=users)

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