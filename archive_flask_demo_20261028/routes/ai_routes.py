from flask import Blueprint, request, jsonify, session
from services.ai_support_service import AISupportService
from services.ticket_service import TicketService

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

@ai_bp.route('/classify', methods=['POST'])
def classify():
    data = request.get_json() or {}
    title = data.get('title', '')
    description = data.get('description', '')

    if not title:
        return jsonify({"error": "Tiêu đề không được để trống"}), 400

    result = AISupportService.classify_ticket(title, description)
    return jsonify(result)

@ai_bp.route('/suggest', methods=['POST'])
def suggest():
    data = request.get_json() or {}
    ticket_id = data.get('ticket_id')

    if not ticket_id:
        return jsonify({"error": "ticket_id là bắt buộc"}), 400

    ticket = TicketService.get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({"error": "Không tìm thấy ticket"}), 404

    comments = TicketService.get_comments(ticket_id)
    result = AISupportService.suggest_response(ticket, comments)
    return jsonify(result)

@ai_bp.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json() or {}
    ticket_id = data.get('ticket_id')

    if not ticket_id:
        return jsonify({"error": "ticket_id là bắt buộc"}), 400

    ticket = TicketService.get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({"error": "Không tìm thấy ticket"}), 404

    comments = TicketService.get_comments(ticket_id)
    result = AISupportService.summarize_history(ticket, comments)
    return jsonify(result)

@ai_bp.route('/approve-and-send', methods=['POST'])
def approve_and_send():
    """
    HUMAN GATE: Nhân viên xem xét, chỉnh sửa và bấm Duyệt gửi phản hồi của AI.
    """
    if 'user_id' not in session:
        return jsonify({"error": "Chưa đăng nhập"}), 401

    data = request.get_json() or {}
    ticket_id = data.get('ticket_id')
    approved_content = data.get('content', '').strip()

    if not ticket_id or not approved_content:
        return jsonify({"error": "Thiếu dữ liệu ticket_id hoặc nội dung duyệt"}), 400

    ticket = TicketService.get_ticket_by_id(ticket_id)
    if not ticket:
        return jsonify({"error": "Không tìm thấy ticket"}), 404

    # 1. Thêm vào bảng ticket_comments
    comment_id = TicketService.add_comment(
        ticket_id=ticket_id,
        user_id=session.get('user_id'),
        author_role='agent',
        author_name=session.get('full_name', 'Nhân viên hỗ trợ'),
        content=approved_content,
        is_internal=False
    )

    # 2. Cập nhật trạng thái ticket sang 'Waiting Customer' nếu đang là New hoặc In Progress
    if ticket['status'] in ['New', 'In Progress']:
        TicketService.update_ticket_status(ticket_id, 'Waiting Customer')

    # 3. Ghi nhận log kiểm toán duyệt AI
    AISupportService.log_ai_action(
        ticket_id=ticket_id,
        action_type='suggest_response',
        input_context=f"Ticket #{ticket_id}",
        raw_ai_output="[Approved from UI]",
        approved_output=approved_content,
        is_approved=True,
        agent_id=session.get('user_id'),
        latency_ms=0
    )

    return jsonify({
        "success": True,
        "message": "Đã duyệt và gửi phản hồi thành công cho khách hàng!",
        "comment_id": comment_id
    })

@ai_bp.route('/apply-classification', methods=['POST'])
def apply_classification():
    data = request.get_json() or {}
    ticket_id = data.get('ticket_id')
    category = data.get('category')
    priority = data.get('priority')

    if not ticket_id or not category or not priority:
        return jsonify({"error": "Thiếu thông tin phân loại"}), 400

    TicketService.update_ticket_classification(ticket_id, category, priority)
    return jsonify({"success": True, "message": "Đã cập nhật phân loại và mức ưu tiên theo đề xuất AI!"})

