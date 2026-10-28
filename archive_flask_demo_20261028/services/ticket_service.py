from database.db import get_db
import random
import string
from datetime import datetime

class TicketService:
    @staticmethod
    def generate_ticket_number():
        suffix = ''.join(random.choices(string.digits, k=4))
        return f"TCK-{suffix}"

    @staticmethod
    def get_tickets(status=None, priority=None, search=None, assigned_to=None):
        conn = get_db()
        cursor = conn.cursor()

        query = """
            SELECT t.*, c.full_name as customer_name, c.email as customer_email, c.tier as customer_tier,
                   u.full_name as assigned_name
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            LEFT JOIN users u ON t.assigned_to = u.id
            WHERE 1=1
        """
        params = []

        if status:
            query += " AND t.status = ?"
            params.append(status)
        if priority:
            query += " AND t.priority = ?"
            params.append(priority)
        if assigned_to:
            query += " AND t.assigned_to = ?"
            params.append(assigned_to)
        if search:
            query += " AND (t.title LIKE ? OR t.ticket_number LIKE ? OR t.description LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])

        query += " ORDER BY CASE t.priority WHEN 'Urgent' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, t.created_at DESC"

        cursor.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_ticket_by_id(ticket_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, c.full_name as customer_name, c.email as customer_email, c.phone as customer_phone,
                   c.company as customer_company, c.tier as customer_tier,
                   u.full_name as assigned_name, u.role as assigned_role
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            LEFT JOIN users u ON t.assigned_to = u.id
            WHERE t.id = ?
        """, (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def create_ticket(customer_id, title, description, category='Chưa phân loại', priority='Medium', assigned_to=None):
        conn = get_db()
        cursor = conn.cursor()
        ticket_number = TicketService.generate_ticket_number()
        cursor.execute("""
            INSERT INTO tickets (ticket_number, customer_id, title, description, category, priority, status, assigned_to)
            VALUES (?, ?, ?, ?, ?, ?, 'New', ?)
        """, (ticket_number, customer_id, title, description, category, priority, assigned_to))
        conn.commit()
        ticket_id = cursor.lastrowid
        conn.close()
        return ticket_id

    @staticmethod
    def update_ticket_status(ticket_id, new_status):
        conn = get_db()
        cursor = conn.cursor()
        resolved_at = datetime.now() if new_status == 'Closed' else None
        cursor.execute("""
            UPDATE tickets
            SET status = ?, updated_at = CURRENT_TIMESTAMP, resolved_at = COALESCE(?, resolved_at)
            WHERE id = ?
        """, (new_status, resolved_at, ticket_id))
        conn.commit()
        conn.close()

    @staticmethod
    def update_ticket_classification(ticket_id, category, priority):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tickets
            SET category = ?, priority = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (category, priority, ticket_id))
        conn.commit()
        conn.close()

    @staticmethod
    def assign_ticket(ticket_id, user_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tickets
            SET assigned_to = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id, ticket_id))
        conn.commit()
        conn.close()

    @staticmethod
    def get_comments(ticket_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM ticket_comments
            WHERE ticket_id = ?
            ORDER BY created_at ASC
        """, (ticket_id,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def add_comment(ticket_id, user_id, author_role, author_name, content, is_internal=False):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ticket_comments (ticket_id, user_id, author_role, author_name, content, is_internal)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticket_id, user_id, author_role, author_name, content, 1 if is_internal else 0))
        # Cập nhật updated_at của ticket
        cursor.execute("UPDATE tickets SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (ticket_id,))
        conn.commit()
        comment_id = cursor.lastrowid
        conn.close()
        return comment_id

    @staticmethod
    def get_statistics():
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status")
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

        cursor.execute("SELECT priority, COUNT(*) as count FROM tickets GROUP BY priority")
        priority_counts = {row['priority']: row['count'] for row in cursor.fetchall()}

        cursor.execute("SELECT category, COUNT(*) as count FROM tickets GROUP BY category")
        category_counts = {row['category']: row['count'] for row in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) FROM tickets")
        row_tickets = cursor.fetchone()
        total_tickets = row_tickets[0] if row_tickets else 0

        cursor.execute("SELECT COUNT(*) FROM customers")
        row_cust = cursor.fetchone()
        total_customers = row_cust[0] if row_cust else 0

        conn.close()
        return {
            'total_tickets': total_tickets,
            'total_customers': total_customers,
            'status_counts': status_counts,
            'priority_counts': priority_counts,
            'category_counts': category_counts
        }

