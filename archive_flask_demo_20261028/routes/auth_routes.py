from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form.get('username')
        password = request.form.get('password')

        user = AuthService.authenticate(username_or_email, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash(f"Đăng nhập thành công! Chào mừng {user['full_name']}", "success")
            return redirect(url_for('tickets.dashboard'))
        else:
            flash("Tên đăng nhập hoặc mật khẩu không chính xác!", "danger")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Bạn đã đăng xuất an toàn.", "info")
    return redirect(url_for('auth.login'))

