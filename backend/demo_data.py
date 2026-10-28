"""Idempotent synthetic data loader; never resets existing accounts or deletes rows."""

import argparse
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.config import Settings
from backend.db import Database
from backend.security import hash_password

DEMO_MODEL = "vietincare-demo-embedding-v1"
DEMO_DIMENSIONS = 768


def seed(
    database: Database, password: str, *, chunk_count: int = 1000
) -> dict[str, Any]:
    if not 12 <= len(password) <= 128 or not 1 <= chunk_count <= 1000:
        raise ValueError("Use a 12–128 character demo password and at most 1000 chunks")
    prefix = "VC-DEMO-20261029"
    with database.transaction() as tx:
        marker = tx.fetch_one(
            "SELECT MaLog FROM AuditLog WHERE HanhDong='DEMO_SEED' AND DoiTuong=? LIMIT 1",
            (prefix,),
        )
        if marker:
            return {"status": "already_seeded", "marker": prefix}
        roles = {
            row["TenRole"]: row["MaRole"]
            for row in tx.fetch_all("SELECT MaRole,TenRole FROM Role")
        }
        identities = [(f"customer{i}", "Customer") for i in range(1, 6)] + [
            ("agent1", "Agent"),
            ("agent2", "Agent"),
            ("supervisor", "Supervisor"),
            ("admin", "Admin"),
        ]
        ids = {}
        customers = {}
        hashed = hash_password(password)
        for label, role in identities:
            email = f"{label}@demo.invalid"
            if tx.fetch_one(
                "SELECT MaUser FROM UserAccount WHERE EmailNormalized=?", (email,)
            ):
                raise ValueError(
                    "Demo email collision; existing account was not modified"
                )
            user_id = tx.execute(
                "INSERT INTO UserAccount(MaRole,HoTen,Username,PasswordHash,Email,SoDienThoai,TrangThai) VALUES(?,?,?,?,?,?,?)",
                (
                    roles[role],
                    f"Demo {role} {label}",
                    f"vc_demo_{label}",
                    hashed,
                    email,
                    "+84000000000",
                    0 if label == "customer5" else 1,
                ),
            )
            ids[label] = user_id
            if role == "Customer":
                customers[label] = tx.execute(
                    "INSERT INTO Customer(MaUser,HoTen,Email,SoDienThoai,LoaiKhachHang,TrangThai) VALUES(?,?,?,?,?,?)",
                    (
                        user_id,
                        f"Khách hàng Demo {label}",
                        email,
                        "+84000000000",
                        "VIP" if label == "customer1" else "Standard",
                        0 if label == "customer5" else 1,
                    ),
                )
        category_ids = []
        for label in ["Tài khoản", "Thanh toán", "Lỗi kỹ thuật", "Tư vấn"]:
            row = tx.fetch_one(
                "SELECT MaCategory FROM TicketCategory WHERE TenCategory=? ORDER BY MaCategory LIMIT 1",
                (label,),
            )
            category_ids.append(
                row["MaCategory"]
                if row
                else tx.execute(
                    "INSERT INTO TicketCategory(TenCategory,MoTa) VALUES(?,?)",
                    (label, "Dữ liệu giả lập nghiệm thu"),
                )
            )
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        ticket_ids = []
        stages = ["Mới", "Đang xử lý", "Chờ khách hàng", "Đã đóng"]
        priorities = ["Thấp", "Trung bình", "Cao", "Khẩn cấp"]
        for i in range(48):
            owner = f"customer{(i // 4 + i % 4) % 4 + 1}"
            status = stages[i % 4]
            created = now - timedelta(days=i % 24, hours=5)
            agent = None if status == "Mới" else ids[f"agent{(i // 4) % 2 + 1}"]
            closed = created + timedelta(hours=2) if status == "Đã đóng" else None
            tid = tx.execute(
                "INSERT INTO Ticket(MaKH,MaAgent,MaCategory,TieuDe,NoiDung,MucDoUuTien,TrangThai,NgayTao,NgayCapNhat,NgayDong) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    customers[owner],
                    agent,
                    category_ids[i % 4],
                    f"[{prefix}] Ticket {i+1:02d}",
                    "Dữ liệu giả lập: cần hỗ trợ đăng nhập; không truy vấn tài khoản ngân hàng thật.",
                    priorities[(i // 4) % 4],
                    status,
                    created,
                    created,
                    closed,
                ),
            )
            ticket_ids.append(tid)
            tx.execute(
                "INSERT INTO TicketAutomation(MaTicket,State,Category,Priority,Sentiment) VALUES(?,?,?,?,?)",
                (
                    tid,
                    "Failed" if status == "Mới" else "Done",
                    (
                        "Cần kiểm tra"
                        if status == "Mới"
                        else ["Tài khoản", "Thanh toán", "Lỗi kỹ thuật", "Tư vấn"][
                            i % 4
                        ]
                    ),
                    priorities[(i // 4) % 4],
                    "Bức xúc cao" if i == 0 else "Trung tính",
                ),
            )
            if i == 0:
                tx.execute(
                    "INSERT INTO SupervisorAlert(SourceType,SourceId,Sentiment) VALUES('Ticket',?,'Bức xúc cao')",
                    (tid,),
                )
            if i in (1, 5, 9):
                review = ["Pending", "Selected", "Dismissed"][(i - 1) // 4]
                tx.execute(
                    "INSERT INTO TicketAIAnalysis(MaTicket,MaUser,RequestKey,RequestHash,CategorySuggestion,PrioritySuggestion,SentimentSuggestion,DraftReply,Summary,Provider,Model,ReviewStatus,CreatedAt,ReviewedBy,ReviewedAt) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        tid,
                        agent,
                        str(uuid.uuid4()),
                        "0" * 64,
                        "Tài khoản",
                        "Trung bình",
                        "Trung tính",
                        "[SIMULATION] Bản nháp cần nhân viên kiểm tra; không tự động gửi.",
                        "[SIMULATION] Khách cần hỗ trợ đăng nhập.",
                        "simulation",
                        "vietincare-demo-chat-v1",
                        review,
                        created,
                        agent if review != "Pending" else None,
                        (
                            created + timedelta(minutes=20)
                            if review != "Pending"
                            else None
                        ),
                    ),
                )
            tx.execute(
                "INSERT INTO TicketStatusHistory(MaTicket,TrangThaiCu,TrangThaiMoi,MaUser,ThoiGian) VALUES(?,NULL,?,?,?)",
                (tid, status, ids[owner], created),
            )
            if agent:
                tx.execute(
                    "INSERT INTO TicketAssignmentHistory(MaTicket,MaAgentCu,MaAgentMoi,MaNguoiThucHien,ThoiGian) VALUES(?,NULL,?,?,?)",
                    (tid, agent, ids["supervisor"], created),
                )
                tx.execute(
                    "INSERT INTO TicketReply(MaTicket,MaUser,NoiDung,ThoiGian) VALUES(?,?,?,?)",
                    (
                        tid,
                        agent,
                        "Phản hồi mẫu: nhân viên đã xem xét nội dung và hướng dẫn kiểm tra kết nối.",
                        created + timedelta(minutes=30),
                    ),
                )
            if closed:
                tx.execute(
                    "INSERT INTO Evaluation(MaKH,MaTicket,SoSao,NhanXet,NgayDanhGia) VALUES(?,?,?,?,?)",
                    (
                        customers[owner],
                        tid,
                        (i // 4) % 5 + 1,
                        "Nhận xét giả lập cho CSAT",
                        closed,
                    ),
                )
        documents = []
        chunks = []
        texts = [
            (
                "Hướng dẫn đăng nhập demo",
                "Đăng nhập VietinCare bằng email và mật khẩu đã đăng ký. Khi quên thông tin, gặp nhân viên hỗ trợ. Không cung cấp OTP hoặc CVV.",
            ),
            (
                "Quy trình Ticket demo",
                "Ticket có bốn trạng thái: Mới, Đang xử lý, Chờ khách hàng, Đã đóng. Khách hàng có thể bổ sung thông tin và đánh giá sau khi hỗ trợ kết thúc.",
            ),
            (
                "An toàn thông tin demo",
                "Không gửi mật khẩu, OTP, CVV hoặc số CCCD trong hội thoại. VietinCare không truy vấn số dư hay lịch sử giao dịch ngân hàng thật.",
            ),
            (
                "Chuyển giao hỗ trợ demo",
                "Khách hàng chọn gặp nhân viên khi câu hỏi thiếu nguồn. Nếu nhân viên chưa trực tuyến, khách có thể để lại lời nhắn hoặc tạo Ticket.",
            ),
        ]
        for title, content in texts:
            documents.append(
                tx.execute(
                    "INSERT INTO KnowledgeBase(MaUser,TieuDe,NoiDung,TrangThai) VALUES(?,?,?,'Đã xuất bản')",
                    (ids["admin"], f"[{prefix}] {title}", content),
                )
            )
        vector = json.dumps([1.0] + [0.0] * (DEMO_DIMENSIONS - 1))
        for i in range(chunk_count):
            document = i % len(documents)
            chunks.append(
                tx.execute(
                    "INSERT INTO KnowledgeChunk(MaKB,ThuTu,NoiDung,Embedding,TenMoHinh,SoChieu) VALUES(?,?,?,?,?,?)",
                    (
                        documents[document],
                        i // len(documents),
                        texts[document][1],
                        vector,
                        DEMO_MODEL,
                        DEMO_DIMENSIONS,
                    ),
                )
            )
        import hashlib

        for i in range(8):
            owner = f"customer{i%4+1}"
            closed = i % 2 == 1
            sid = tx.execute(
                "INSERT INTO ChatSession(MaKH,TieuDe,KenhChat,TrangThai,ThoiGianBatDau,ThoiGianKetThuc) VALUES(?,?,'Web',?,?,?)",
                (
                    customers[owner],
                    f"[{prefix}] Hội thoại {i+1}",
                    "Đã kết thúc" if closed else "Đang hoạt động",
                    now - timedelta(hours=1),
                    now if closed else None,
                ),
            )
            mid = tx.execute(
                "INSERT INTO Message(MaSession,NguoiGui,MaUser,NoiDung) VALUES(?,'Customer',?,?)",
                (sid, ids[owner], "Tôi muốn được hướng dẫn sử dụng hệ thống demo."),
            )
            aid = tx.execute(
                "INSERT INTO Message(MaSession,NguoiGui,NoiDung,ReplyTo,AnswerStatus) VALUES(?,'AI',?,?,'answered')",
                (sid, texts[0][1], mid),
            )
            tx.execute(
                "INSERT INTO MessageSource(MaMessage,MaChunk,TieuDeNguon,NoiDungNguon,SourceHash) VALUES(?,?,?,?,?)",
                (
                    aid,
                    chunks[0],
                    texts[0][0],
                    texts[0][1],
                    hashlib.sha256(texts[0][1].encode()).hexdigest(),
                ),
            )
            sentiment = ["Tích cực", "Trung tính", "Tiêu cực", "Bức xúc cao"][i % 4]
            tx.execute(
                "INSERT INTO SentimentAnalysis(MaMessage,CamXuc) VALUES(?,?)",
                (mid, sentiment),
            )
            tx.execute(
                "INSERT INTO MessageAutomation(MaMessage,State,Sentiment) VALUES(?,'Done',?)",
                (mid, sentiment),
            )
            if sentiment == "Bức xúc cao":
                tx.execute(
                    "INSERT INTO SupervisorAlert(SourceType,SourceId,Sentiment) VALUES('Message',?,'Bức xúc cao')",
                    (mid,),
                )
            if i % 3 == 0:
                tx.execute(
                    "INSERT INTO Handover(MaSession,MaAgent,LyDo,TrangThai,ThoiGian,ThoiGianTiepNhan,ThoiGianKetThuc,TomTat) VALUES(?,?,?, ?,?,?,?,?)",
                    (
                        sid,
                        ids["agent1"] if closed else None,
                        "Khách cần hỗ trợ thêm",
                        "Đã kết thúc" if closed else "Chờ tiếp nhận",
                        now - timedelta(minutes=10),
                        now if closed else None,
                        now if closed else None,
                        "Tóm tắt giả lập; không chứa giao dịch thật.",
                    ),
                )
            if closed:
                tx.execute(
                    "INSERT INTO ConversationSummary(MaSession,NoiDungTomTat) VALUES(?,?)",
                    (sid, "Khách đã được hướng dẫn sử dụng hệ thống demo."),
                )
                tx.execute(
                    "INSERT INTO Evaluation(MaKH,MaSession,SoSao,NhanXet) VALUES(?,?,?,?)",
                    (customers[owner], sid, i % 5 + 1, "Đánh giá chat giả lập"),
                )
        tx.execute(
            "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,ChiTiet) VALUES(?,'DEMO_SEED',?,?)",
            (
                ids["admin"],
                prefix,
                json.dumps(
                    {
                        "users": len(ids),
                        "tickets": 48,
                        "chats": 8,
                        "chunks": chunk_count,
                    }
                ),
            ),
        )
    return {
        "status": "seeded",
        "marker": prefix,
        "users": len(ids),
        "customers": len(customers),
        "tickets": 48,
        "chats": 8,
        "documents": 4,
        "chunks": chunk_count,
        "ai_analyses": 3,
        "supervisor_alerts": 3,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-demo-data", action="store_true", required=True)
    parser.add_argument("--chunks", type=int, default=1000)
    args = parser.parse_args()
    password = os.environ.get("VC_DEMO_PASSWORD", "")
    if not password:
        import getpass

        password = getpass.getpass(
            "Mat khau chi danh cho tai khoan demo / Demo-only password: "
        )
    print(
        json.dumps(
            seed(
                Database(Settings.from_env().database),
                password,
                chunk_count=args.chunks,
            ),
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
