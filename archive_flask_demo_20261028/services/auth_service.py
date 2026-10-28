from database.db import get_db
from werkzeug.security import check_password_hash, generate_password_hash

class AuthService:
    @staticmethod
    def authenticate(username_or_email, password):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE username = ? OR email = ?",
            (username_or_email, username_or_email)
        )
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            return dict(user)
        return None

    @staticmethod
    def get_user_by_id(user_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, full_name, role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    @staticmethod
    def list_agents():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, full_name, role FROM users WHERE role IN ('agent', 'lead') ORDER BY full_name")
        agents = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return agents

