import os
from flask import Flask, render_template, redirect, url_for
from dotenv import load_dotenv

# Nạp cấu hình biến môi trường
load_dotenv()

from database.db import init_db
from routes.auth_routes import auth_bp
from routes.ticket_routes import ticket_bp
from routes.customer_routes import customer_bp
from routes.ai_routes import ai_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'viettincare-super-secret-key-2026')

    # Khởi tạo CSDL nếu chưa có
    init_db()

    # Đăng ký Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(ticket_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(ai_bp)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return {"error": "Lỗi máy chủ nội bộ. Vui lòng liên hệ quản trị viên."}, 500

    return app

if __name__ == '__main__':
    app = create_app()
    print("=================================================================")
    print("   ViettinCare - AI Customer Support Ticket Management System    ")
    print("   Running on http://127.0.0.1:5000                              ")
    print("=================================================================")
    app.run(debug=True, port=5000)

