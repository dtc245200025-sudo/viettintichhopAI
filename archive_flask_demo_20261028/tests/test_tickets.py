import pytest
from app import create_app
from services.ticket_service import TicketService
from database.db import init_db

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_ticket_crud_and_status():
    init_db()
    # 1. Tạo ticket mới
    ticket_id = TicketService.create_ticket(
        customer_id=1,
        title="Lỗi không thể xuất file Excel",
        description="Khi bấm nút xuất báo cáo hệ thống quay tròn.",
        category="Lỗi kỹ thuật & Phần mềm",
        priority="High"
    )
    assert ticket_id > 0

    # 2. Đọc ticket
    ticket = TicketService.get_ticket_by_id(ticket_id)
    assert ticket is not None
    assert ticket['title'] == "Lỗi không thể xuất file Excel"
    assert ticket['status'] == "New"

    # 3. Chuyển trạng thái sang In Progress
    TicketService.update_ticket_status(ticket_id, "In Progress")
    updated = TicketService.get_ticket_by_id(ticket_id)
    assert updated['status'] == "In Progress"

    # 4. Thêm bình luận
    comment_id = TicketService.add_comment(
        ticket_id=ticket_id,
        user_id=1,
        author_role="agent",
        author_name="Kỹ thuật viên",
        content="Đang kiểm tra log trên máy chủ."
    )
    assert comment_id > 0
    comments = TicketService.get_comments(ticket_id)
    assert len(comments) >= 1

def test_ticket_statistics():
    init_db()
    stats = TicketService.get_statistics()
    assert stats['total_tickets'] >= 3
    assert stats['total_customers'] >= 3
    assert 'New' in stats['status_counts'] or 'In Progress' in stats['status_counts']

def test_ticket_search_and_filter():
    init_db()
    # Lọc theo trạng thái
    tickets_new = TicketService.get_tickets(status='New')
    assert all(t['status'] == 'New' for t in tickets_new)

    # Tìm kiếm theo từ khóa
    tickets_search = TicketService.get_tickets(search='mật khẩu')
    assert len(tickets_search) > 0

