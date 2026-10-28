from database.db import get_db

class CustomerService:
    @staticmethod
    def get_all_customers():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers ORDER BY full_name ASC")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_customer_by_id(customer_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def create_customer(full_name, email, phone, company, tier='Standard'):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO customers (full_name, email, phone, company, tier) VALUES (?, ?, ?, ?, ?)",
            (full_name, email, phone, company, tier)
        )
        conn.commit()
        customer_id = cursor.lastrowid
        conn.close()
        return customer_id

