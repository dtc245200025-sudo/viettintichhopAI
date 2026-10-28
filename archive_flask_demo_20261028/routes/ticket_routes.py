from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from services.ticket_service import TicketService
from services.customer_service import CustomerService
from services.auth_service import AuthService

ticket_bp = Blueprint('tickets', __name__)

@ticket_bp.route('/')
@ticket_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    stats = TicketService.get_statistics()
    recent_tickets = TicketService.get_tickets()[:5]
    return render_template('dashboard.html', stats=stats, recent_tickets=recent_tickets)

@ticket_bp.route('/tickets')
def list_tickets():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    status = request.args.get('status')
    priority = request.args.get('priority')
    search = request.args.get('search')
    assigned_to = request.args.get('assigned_to')

    tickets = TicketService.get_tickets(status=status, priority=priority, search=search, assigned_to=assigned_to)
    customers = CustomerService.get_all_customers()
    agents = AuthService.list_agents()

    return render_template('tickets.html', tickets=tickets, customers=customers, agents=agents,
                           curr_status=status, curr_priority=priority, curr_search=search)

@ticket_bp.route('/tickets/create', methods=['POST'])
def create_ticket():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    customer_id = request.form.get('customer_id')
    title = request.form.get('title')
    description = request.form.get('description')
    category = request.form.get('category', 'Chưa phân loại')
    priority = request.form.get('priority', 'Medium')
    assigned_to = request.form.get('assigned_to') or None

    if not title or not description:
        flash("Tiêu đề và mô tả không được để trống!", "danger")
        return redirect(url_for('tickets.list_tickets'))

    ticket_id = TicketService.create_ticket(customer_id, title, description, category, priority, assigned_to)
    flash("Ticket hỗ trợ mới đã được tạo thành công!", "success")
    return redirect(url_for('tickets.ticket_detail', ticket_id=ticket_id))

@ticket_bp.route('/tickets/<int:ticket_id>')
def ticket_detail(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    ticket = TicketService.get_ticket_by_id(ticket_id)
    if not ticket:
        flash("Không tìm thấy ticket yêu cầu!", "danger")
        return redirect(url_for('tickets.list_tickets'))

    comments = TicketService.get_comments(ticket_id)
    agents = AuthService.list_agents()

    return render_template('ticket_detail.html', ticket=ticket, comments=comments, agents=agents)

@ticket_bp.route('/tickets/<int:ticket_id>/status', methods=['POST'])
def update_status(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    new_status = request.form.get('status')
    TicketService.update_ticket_status(ticket_id, new_status)
    flash(f"Trạng thái ticket đã được cập nhật thành '{new_status}'!", "success")
    return redirect(url_for('tickets.ticket_detail', ticket_id=ticket_id))

@ticket_bp.route('/tickets/<int:ticket_id>/assign', methods=['POST'])
def assign_agent(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    agent_id = request.form.get('assigned_to')
    TicketService.assign_ticket(ticket_id, agent_id if agent_id else None)
    flash("Đã cập nhật nhân viên phụ trách!", "success")
    return redirect(url_for('tickets.ticket_detail', ticket_id=ticket_id))

@ticket_bp.route('/tickets/<int:ticket_id>/comment', methods=['POST'])
def add_comment(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    content = request.form.get('content')
    is_internal = bool(request.form.get('is_internal'))

    if not content:
        flash("Nội dung trao đổi không được để trống!", "danger")
        return redirect(url_for('tickets.ticket_detail', ticket_id=ticket_id))

    TicketService.add_comment(
        ticket_id=ticket_id,
        user_id=session.get('user_id'),
        author_role=session.get('role', 'agent'),
        author_name=session.get('full_name', 'Nhân viên hỗ trợ'),
        content=content,
        is_internal=is_internal
    )
    flash("Đã gửi phản hồi thành công!", "success")
    return redirect(url_for('tickets.ticket_detail', ticket_id=ticket_id))

