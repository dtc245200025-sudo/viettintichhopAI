# Vấn đề và điểm mơ hồ của yêu cầu

Nguồn: [`requirements/source-topic-10.md`](requirements/source-topic-10.md).

| ID | Điểm chưa rõ | Trạng thái hiện hành |
|---|---|---|
| RI-001 | “File đính kèm ở mức mô tả” không xác định upload, URL hay mô tả văn bản. | Chưa có upload/bảng metadata; cần xác nhận nếu attachment riêng là bắt buộc. |
| RI-002 | Đề tài không quy định Customer hay Agent đóng ticket. | Chỉ Agent được giao đóng sau khi phản hồi; Customer đánh giá sau khi đóng. |
| RI-003 | Không quy định phân công tự động hay thủ công. | Người dùng chọn tự động ngày 29/10: Agent heartbeat/phiên hợp lệ, ít Ticket mở nhất; vẫn giữ phân công tay. Đây là cân bằng tải demo, không phải định tuyến chuyên môn ngân hàng. |
| RI-004 | “Dựa trên mô tả và lịch sử” không bắt buộc ticket-assist dùng RAG. | Yêu cầu mới có tri thức cho nháp; đã bổ sung nguồn xuất bản cho ticket-assist. |
| RI-005 | Không có ngưỡng hiệu năng/độ chính xác AI kiểm thử được trong đề tài gốc. | Không cam kết số liệu khi chưa đo trên provider và dữ liệu thật. |
| RI-006 | Yêu cầu mới vừa đặt p95 ≤5 giây, vừa nêu AI dưới 2 giây và uptime 99,9%. | Đo 50 câu/5 phiên/1.000 chunk; không khẳng định SLA Gemini thật hoặc uptime. |
| RI-007 | Phần đầu có 3 nhãn cảm xúc, UC005 thêm bức xúc cao. | Người dùng chọn bổ sung tự động/cảnh báo; hỗ trợ 4 nhãn bằng migration mới. |
| RI-008 | Một số đoạn nhắc Đã giải quyết nhưng phần chính quy định 4 trạng thái. | Giữ Mới/Đang xử lý/Chờ khách hàng/Đã đóng; không tái thêm trạng thái đã loại. |
| RI-009 | Một đoạn yêu cầu chứng nhận/tuân thủ, đoạn khác chỉ rõ demo và không tuyên bố chứng nhận. | Không dùng kiểm thử đồ án để khẳng định chứng nhận/tuân thủ pháp lý hoặc an toàn ngân hàng. |

## Không được suy diễn

- Không tự động hoàn tiền, thực hiện giao dịch ngân hàng hoặc hứa chính sách ngoài nguồn.
- Không tự gửi câu trả lời AI cho Customer.
- Không coi UI demo, unit test hoặc health check là bằng chứng end-to-end đầy đủ.
