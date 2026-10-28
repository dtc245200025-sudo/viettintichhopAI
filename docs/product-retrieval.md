# Đặc tả Kỹ thuật Truy xuất Dữ liệu Nghiệp vụ Ngân hàng (Banking Retrieval Specification) - Đề tài 10

## 1. Bối cảnh nghiệp vụ CSKH Ngân hàng số ViettinCare
Hệ thống chăm sóc khách hàng ngân hàng số ViettinCare quản lý các yêu cầu hỗ trợ và khiếu nại giao dịch của khách hàng:
- **Tài khoản & Đăng nhập**: Quên mật khẩu, khóa tài khoản do nhập sai mã PIN/mật khẩu, đổi số điện thoại nhận biến động số dư.
- **Thanh toán & Chuyển tiền**: Chuyển tiền nhanh 24/7 bị trừ tiền nhưng người nhận chưa có tiền, quét mã QR thanh toán thất bại, giao dịch thẻ ghi nợ/tín dụng bị tính phí sai.
- **Bảo mật & Smart OTP**: Kích hoạt ứng dụng trên thiết bị mới, đồng bộ mã xác thực Smart OTP, cảnh báo rò rỉ mã OTP.
- **Biểu phí & Sản phẩm Ngân hàng**: Biểu phí duy trì tài khoản, lãi suất tiết kiệm trực tuyến, điều kiện nâng cấp tài khoản VIP.

## 2. Quy trình truy xuất dữ liệu (Retrieval Pipeline)
```
Khách hàng phản ánh sự cố -> Question Analyzer -> Structured Banking Intent -> Parameterized SQL -> Cơ sở tri thức Ngân hàng -> Giải pháp chuẩn
```

## 3. Câu lệnh SQL tham số hóa an toàn
```python
def retrieve_banking_faqs(intent):
    category = intent.get("category")
    keywords = intent.get("keywords", [])

    # Truy vấn theo danh mục nghiệp vụ ngân hàng
    query = "SELECT * FROM faqs WHERE category = ?"
    params = [category]

    if keywords:
        kw_conditions = " OR ".join(["keywords LIKE ?" for _ in keywords])
        query = f"SELECT * FROM faqs WHERE category = ? OR ({kw_conditions}) LIMIT 3"
        params = [category] + [f"%{k}%" for k in keywords]

    return execute_query(query, params)
```

## 4. An ninh & Bảo vệ Dữ liệu Tài chính Khách hàng
- Không lưu số thẻ đầy đủ hoặc mã CVV trong câu lệnh truy vấn hay bảng FAQ.
- Toàn bộ tham số được ràng buộc kiểu dữ liệu chặt chẽ để phòng chống SQL Injection.
