| Relationship | Cardinality | Description |
|---|---:|---|
| Role – User Account | 1 – n | Một vai trò có thể được gán cho nhiều tài khoản người dùng. |
| User Account – Customer | 1 – 0..1 | Một tài khoản khách hàng có tối đa một hồ sơ khách hàng. |
| User Account – Audit Log | 1 – n | Một tài khoản người dùng có thể phát sinh nhiều bản ghi nhật ký thao tác. |
| Customer – Chat Session | 1 – n | Một khách hàng có thể khởi tạo nhiều phiên trò chuyện. |
| User Account – Chat Session | 1 – n | Một nhân viên hỗ trợ có thể phụ trách nhiều phiên trò chuyện. |
| Chat Session – Message | 1 – n | Một phiên trò chuyện có thể chứa nhiều tin nhắn. |
| User Account – Message | 1 – n | Một tài khoản người dùng có thể gửi nhiều tin nhắn. |
| Message – Sentiment Analysis | 1 – 0..n | Một tin nhắn có thể chưa được phân tích hoặc có nhiều kết quả phân tích cảm xúc. |
| Message – AI Reply Suggestion | 1 – 0..n | Một tin nhắn có thể không có hoặc sinh ra nhiều gợi ý trả lời từ AI. |
| Chat Session – Handover | 1 – 0..n | Một phiên trò chuyện có thể không chuyển giao hoặc phát sinh nhiều lần chuyển cho nhân viên hỗ trợ. |
| User Account – Handover | 1 – n | Một nhân viên hỗ trợ có thể tiếp nhận nhiều lần chuyển giao. |
| Customer – Support Ticket | 1 – n | Một khách hàng có thể tạo nhiều yêu cầu hỗ trợ. |
| Chat Session – Support Ticket | 1 – 0..n | Một phiên trò chuyện có thể không tạo hoặc phát sinh nhiều yêu cầu hỗ trợ. |
| Ticket Category – Support Ticket | 1 – n | Một danh mục yêu cầu có thể được sử dụng cho nhiều yêu cầu hỗ trợ. |
| Customer – Support Evaluation | 1 – n | Một khách hàng có thể gửi nhiều đánh giá cho các trường hợp hỗ trợ khác nhau. |
| Chat Session – Support Evaluation | 1 – 0..1 | Một phiên trò chuyện đã kết thúc có tối đa một đánh giá. |
| Support Ticket – Support Evaluation | 1 – 0..1 | Một yêu cầu hỗ trợ đã đóng có tối đa một đánh giá. |
| User Account – Knowledge Document | 1 – n | Một người dùng có quyền có thể quản lý nhiều tài liệu tri thức. |
| Knowledge Document – Knowledge Chunk | 1 – n | Một tài liệu tri thức được chia thành nhiều đoạn để truy xuất bằng RAG. |
