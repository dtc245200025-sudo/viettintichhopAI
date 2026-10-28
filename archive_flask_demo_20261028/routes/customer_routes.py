from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from services.customer_service import CustomerService

customer_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customer_bp.route('/')
def list_customers():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    customers = CustomerService.get_all_customers()
    return render_template('customers.html', customers=customers)

@customer_bp.route('/create', methods=['POST'])
def create_customer():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    full_name = request.form.get('full_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    company = request.form.get('company')
    tier = request.form.get('tier', 'Standard')

    if not full_name or not email:
        flash("Họ tên và email khách hàng là bắt buộc!", "danger")
        return redirect(url_for('customers.list_customers'))

    try:
        CustomerService.create_customer(full_name, email, phone, company, tier)
        flash(f"Khách hàng {full_name} đã được thêm thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi thêm khách hàng: {str(e)}", "danger")

    return redirect(url_for('customers.list_customers'))

