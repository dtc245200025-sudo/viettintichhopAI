import os
import sqlite3
import logging
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

# Paths
DB_DIR = os.path.dirname(__file__)
SQLITE_DB_PATH = os.path.join(DB_DIR, 'viettincare.db')
SCHEMA_SQLITE_PATH = os.path.join(DB_DIR, 'schema.sql')
SCHEMA_MYSQL_PATH = os.path.join(DB_DIR, 'schema_mysql.sql')

# MySQL Wrapper classes to unify SQLite and MySQL execution
class RowDict(dict):
    """
    Hỗ trợ truy cập cả theo tên cột (row['col']) và theo chỉ số số nguyên (row[0])
    để tương thích 100% với hành vi của sqlite3.Row.
    """
    def __getitem__(self, item):
        if isinstance(item, int):
            return list(self.values())[item]
        return super().__getitem__(item)

class MySQLCursorWrapper:
    def __init__(self, raw_cursor):
        self.raw_cursor = raw_cursor

    def _convert_query(self, query):
        if not query:
            return query
        # SQLite uses '?' while MySQL uses '%s'
        return query.replace('?', '%s')

    def execute(self, query, params=None):
        converted = self._convert_query(query)
        if params is None:
            return self.raw_cursor.execute(converted)
        return self.raw_cursor.execute(converted, params)

    def executemany(self, query, seq_of_params):
        converted = self._convert_query(query)
        return self.raw_cursor.executemany(converted, seq_of_params)

    def fetchone(self):
        row = self.raw_cursor.fetchone()
        return RowDict(row) if row is not None else None

    def fetchall(self):
        rows = self.raw_cursor.fetchall()
        return [RowDict(r) for r in rows] if rows else []

    @property
    def lastrowid(self):
        return self.raw_cursor.lastrowid

    @property
    def rowcount(self):
        return self.raw_cursor.rowcount

    def close(self):
        try:
            self.raw_cursor.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

class MySQLConnectionWrapper:
    def __init__(self, raw_conn):
        self.raw_conn = raw_conn

    def cursor(self):
        return MySQLCursorWrapper(self.raw_conn.cursor(dictionary=True))

    def commit(self):
        return self.raw_conn.commit()

    def rollback(self):
        return self.raw_conn.rollback()

    def close(self):
        try:
            self.raw_conn.close()
        except Exception:
            pass

def get_db_type() -> str:
    return os.getenv('DB_TYPE', 'sqlite').strip().lower()

def get_mysql_connection():
    try:
        import mysql.connector
    except ImportError:
        logger.warning("mysql-connector-python not installed; falling back to SQLite.")
        return None

    host = os.getenv('MYSQL_HOST', '127.0.0.1')
    port = int(os.getenv('MYSQL_PORT', '3306'))
    user = os.getenv('MYSQL_USER', 'vietincare_app')
    password = os.getenv('MYSQL_PASSWORD', 'vietincare_pass_2026')
    database = os.getenv('MYSQL_DATABASE', 'vietincare_db')

    try:
        raw_conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            autocommit=False
        )
        return MySQLConnectionWrapper(raw_conn)
    except Exception as e:
        logger.error(f"Failed to connect to MySQL database '{database}' on {host}:{port}: {e}")
        return None

def get_db():
    """
    Trả về đối tượng kết nối CSDL hợp nhất.
    Tự động hỗ trợ cả MySQL Community Server 8.0.46 (khi DB_TYPE=mysql)
    hoặc SQLite (khi DB_TYPE=sqlite hoặc khi MySQL không khả dụng).
    """
    db_type = get_db_type()
    if db_type == 'mysql':
        mysql_conn = get_mysql_connection()
        if mysql_conn is not None:
            return mysql_conn
        logger.warning("MySQL connection failed. Falling back to SQLite database.")

    # Mặc định / fallback: SQLite
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """
    Khởi tạo bảng và nạp dữ liệu mẫu ban đầu.
    Hỗ trợ cả MySQL và SQLite.
    """
    db_type = get_db_type()
    if db_type == 'mysql':
        conn = get_mysql_connection()
        if conn is not None:
            init_mysql_db(conn)
            return

    # SQLite initialization
    conn = get_db()
    with open(SCHEMA_SQLITE_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    seed_initial_data(conn)
    conn.close()

def init_mysql_db(conn):
    cursor = conn.cursor()
    with open(SCHEMA_MYSQL_PATH, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Tách và chạy từng câu lệnh DDL
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
    for stmt in statements:
        if stmt:
            cursor.execute(stmt)
    conn.commit()
    seed_initial_data(conn)
    conn.close()

def seed_initial_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count_row = cursor.fetchone()
    # Hỗ trợ cả Row, dict, hoặc tuple
    user_count = 0
    if count_row:
        if isinstance(count_row, dict):
            user_count = list(count_row.values())[0]
        else:
            user_count = count_row[0]

    if user_count == 0:
        # Seed users
        users = [
            ('admin', 'admin@viettincare.vn', generate_password_hash('Admin@123'), 'Quản Trị Viên', 'admin'),
            ('lead_tuan', 'tuan.lead@viettincare.vn', generate_password_hash('Lead@123'), 'Trần Anh Tuấn (Team Lead)', 'lead'),
            ('agent_lan', 'lan.agent@viettincare.vn', generate_password_hash('Agent@123'), 'Nguyễn Mai Lan (Support Agent)', 'agent'),
            ('agent_huy', 'huy.agent@viettincare.vn', generate_password_hash('Agent@123'), 'Lê Quang Huy (Support Agent)', 'agent'),
        ]
        cursor.executemany(
            "INSERT INTO users (username, email, password_hash, full_name, role) VALUES (?, ?, ?, ?, ?)",
            users
        )

        # Seed customers
        customers = [
            ('Phạm Minh Hoàng', 'hoang.pm@gmail.com', '0912345678', 'Tập đoàn An Phát', 'VIP'),
            ('Đỗ Bích Phương', 'phuong.db@techcorp.vn', '0987654321', 'TechCorp JSC', 'Standard'),
            ('Lê Văn Nam', 'nam.le@startup.io', '0903112233', 'V-Solutions', 'Standard'),
        ]
        cursor.executemany(
            "INSERT INTO customers (full_name, email, phone, company, tier) VALUES (?, ?, ?, ?, ?)",
            customers
        )

        # Seed FAQs (Cơ sở tri thức CSKH Ngân hàng số cho RAG)
        faqs = [
            (
                'Tài khoản & Đăng nhập',
                'Khách hàng không nhận được email/SMS mã xác nhận kích hoạt ứng dụng Ngân hàng số hoặc reset mật khẩu?',
                'Hướng dẫn khách kiểm tra hòm thư Rác (Spam/Junk) và kiểm tra tín hiệu mạng điện thoại. Nếu sau 3 phút vẫn chưa nhận được, nhân viên CSKH hướng dẫn xác thực khuôn mặt (eKYC) trên ứng dụng hoặc cấp mã kích hoạt lại qua kênh xác thực tổng đài bảo mật.',
                'đổi mật khẩu reset pass quên mật khẩu không nhận email kích hoạt otp ngân hàng số'
            ),
            (
                'Thanh toán & Hóa đơn',
                'Khách hàng chuyển khoản nhanh 24/7 hoặc thanh toán QR bị trừ tiền tài khoản nhưng bên nhận chưa nhận được?',
                'Đây là tình trạng trễ lệnh đối soát liên ngân hàng (Napas). Hệ thống ngân hàng tự động tra soát và hoàn tiền hoặc ghi có cho người thụ hưởng trong vòng 24h làm việc. Nhân viên CSKH cần xin Mã tham chiếu giao dịch (Transaction ID) và gửi yêu cầu tra soát liên ngân hàng. Tuyệt đối không tự ý cam kết hoàn tiền mặt ngay lập tức.',
                'chuyển tiền napas trừ tiền hai lần giao dịch hoàn tiền tra soát lỗi ngân hàng qr pay'
            ),
            (
                'Lỗi kỹ thuật & Phần mềm',
                'Ứng dụng Ngân hàng số báo lỗi không kết nối máy chủ hoặc lỗi xác thực sinh trắc học FaceID/Vân tay?',
                'Yêu cầu khách hàng kiểm tra kết nối mạng 4G/Wifi, cập nhật phiên bản mới nhất của ứng dụng trên App Store/Google Play hoặc khởi động lại thiết bị. Nếu lỗi liên quan đến sinh trắc học theo Quyết định 2345/QĐ-NHNN, hướng dẫn khách mang Căn cước công dân gắn chip tới quầy giao dịch gần nhất để cập nhật dữ liệu NFC.',
                'lỗi ứng dụng crash sinh trắc học faceid căn cước cccd nfc sập hệ thống'
            ),
            (
                'Tư vấn & Hướng dẫn sử dụng',
                'Điều kiện nâng cấp tài khoản thanh toán lên phân hạng Khách hàng Ưu tiên (Priority/VIP) và hạn mức giao dịch?',
                'Khách hàng duy trì số dư bình quân từ 200 triệu VNĐ trong 3 tháng gần nhất hoặc có gói tiền gửi tiết kiệm từ 1 tỷ VNĐ. Quyền lợi bao gồm: Miễn phí toàn bộ phí chuyển tiền và phí quản lý tài khoản, nâng hạn mức chuyển tiền trực tuyến lên tới 5 tỷ VNĐ/ngày, và có chuyên viên tư vấn tài chính riêng 24/7.',
                'nâng cấp vip priority hạn mức chuyển tiền biểu phí lãi suất tiết kiệm thẻ tín dụng'
            )
        ]
        cursor.executemany(
            "INSERT INTO faqs (category, question, answer, keywords) VALUES (?, ?, ?, ?)",
            faqs
        )

        # Seed sample tickets
        tickets = [
            (
                'TCK-1001', 1,
                'Không đăng nhập được sau khi đổi mật khẩu, đã thử reset nhưng chưa nhận email',
                'Tôi vừa thực hiện đổi mật khẩu lúc 9h sáng nay. Sau đó đăng xuất thì không vào lại được. Đã bấm quên mật khẩu nhiều lần nhưng hòm thư hoang.pm@gmail.com vẫn không thấy email gửi về. Công việc đang gấp, nhờ xử lý sớm giúp!',
                'Tài khoản & Đăng nhập', 'High', 'New', 3
            ),
            (
                'TCK-1002', 2,
                'Giao dịch thanh toán gia hạn gói dịch vụ báo lỗi nhưng tài khoản ngân hàng đã bị trừ 500k',
                'Sáng nay tôi thanh toán gói dịch vụ qua quét mã QR VNPay. Ứng dụng báo lỗi kết nối cổng thanh toán, tuy nhiên tiền trong tài khoản VCB của tôi đã bị trừ 500.000đ. Hệ thống vẫn báo tài khoản hết hạn.',
                'Thanh toán & Hóa đơn', 'Urgent', 'In Progress', 3
            ),
            (
                'TCK-1003', 3,
                'Cần tư vấn thủ tục nâng cấp tài khoản công ty lên gói Doanh nghiệp VIP',
                'Công ty chúng tôi sắp mở rộng thêm 20 nhân viên nên muốn tìm hiểu chính sách ưu đãi khi nâng cấp gói dịch vụ Standard lên VIP.',
                'Tư vấn & Hướng dẫn sử dụng', 'Medium', 'Closed', 4
            )
        ]
        cursor.executemany(
            "INSERT INTO tickets (ticket_number, customer_id, title, description, category, priority, status, assigned_to) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            tickets
        )

        # Seed comments
        comments = [
            (1, 1, 'customer', 'Phạm Minh Hoàng', 'Tôi đã kiểm tra kỹ cả hòm thư Spam nhưng vẫn hoàn toàn không có email.', 0),
            (2, 3, 'agent', 'Nguyễn Mai Lan', 'Chào chị Phương, em đã tiếp nhận thông tin. Chị vui lòng gửi giúp em mã tham chiếu giao dịch trừ tiền trên app VCB để em gửi sang kế toán đối soát nhé ạ.', 0),
            (3, 4, 'agent', 'Lê Quang Huy', 'Chào anh Nam, tư vấn viên đã gửi tài liệu báo giá qua email cho anh. Hợp đồng nâng cấp đã hoàn tất.', 0)
        ]
        cursor.executemany(
            "INSERT INTO ticket_comments (ticket_id, user_id, author_role, author_name, content, is_internal) VALUES (?, ?, ?, ?, ?, ?)",
            comments
        )

        conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
