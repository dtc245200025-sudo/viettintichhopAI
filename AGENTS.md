# Quy tắc làm việc trong VietinCare AI

## Theo dõi tiến độ theo yêu cầu của người dùng

- Trước mỗi tác vụ trong project, đọc `PROJECT_CHECKLIST.md` và các file liên quan để nắm trạng thái hiện tại. Không chỉ dựa vào lịch sử trò chuyện.
- Sau mỗi đợt thay đổi mã nguồn, SQL, cấu hình hoặc tài liệu, tự cập nhật `PROJECT_CHECKLIST.md` trong cùng tác vụ, không cần hỏi lại người dùng.
- Ghi ngày cập nhật, ID công việc, thay đổi thực tế, file liên quan, cách kiểm tra và kết quả. Ghi rõ nếu chưa kiểm tra, còn lỗi hoặc bị chặn.
- Chỉ đánh dấu `[x]` khi tiêu chí hoàn thành của công việc đã đạt. Giao diện demo không tương đương backend hoạt động; kiểm tra XML không tương đương kiểm tra bố cục Word; tạo bảng thành công không tương đương toàn bộ nghiệp vụ đã được kiểm thử.
- Nếu phát hiện việc mới hoặc thay đổi phạm vi, thêm mục có ID ổn định và mức ưu tiên; không xóa lịch sử hoặc đổi ID cũ. Nếu một mục đã hoàn thành bị lỗi lại, mở lại mục đó và ghi lý do.
- Kết thúc câu trả lời sau khi sửa đổi bằng lời nhắc ngắn: checklist đã cập nhật, phần chưa kiểm chứng/đang bị chặn (nếu có), và 1–3 việc ưu tiên tiếp theo. Liên kết đến checklist khi hữu ích.
- Với yêu cầu chỉ đọc hoặc tư vấn, không tự đánh dấu công việc triển khai là hoàn thành. Chỉ ghi thêm phát hiện khi có thông tin mới ảnh hưởng tiến độ.
- Không tự triển khai toàn bộ backlog chỉ vì có mục chưa hoàn thành; thực hiện theo phạm vi yêu cầu hiện tại của người dùng.
- Việc cập nhật và nhắc nhở diễn ra trong các phiên làm việc có truy cập project này; không hứa theo dõi nền hoặc thông báo tự động ngoài phiên.

## Quyết định đã thống nhất

- Hệ quản trị duy nhất: MySQL Community Server 8.0.46, InnoDB, utf8mb4. Không thêm hệ quản trị khác nếu người dùng chưa thay đổi yêu cầu.
- `SQLQuery1.sql` là script khởi tạo; database có dữ liệu cần migration riêng, không tự xóa để chạy lại.
- Dữ liệu RAG lưu trong MySQL (`KnowledgeBase`, `KnowledgeChunk`); backend tạo embedding và tính độ tương đồng cho quy mô đồ án.
- Giữ đồng bộ nội dung tiếng Việt/tiếng Anh khi thay đổi tính năng chung.
- Không ghi nhận kết quả Pass cho chức năng chưa thực sự kiểm thử. Không lưu mật khẩu hoặc khóa API thật vào project/checklist.
