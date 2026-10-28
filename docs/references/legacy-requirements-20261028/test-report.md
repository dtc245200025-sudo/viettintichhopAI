# Báo cáo kết quả kiểm thử (Test Execution Report) - Đề tài 10

## 1. Thông tin chung
- **Hệ thống**: ViettinCare - Customer Support Management System with AI.
- **Môi trường thực thi hiện hành**: Python 3.13.1 / Pytest 8.4.2 / Windows.
- **Ngày thực thi**: 2026-10-28.

## 2. Kết quả thực thi Test Suite

```
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
rootdir: F:\ViettinCare
collected 13 items

tests/test_ai_support.py::test_pii_sanitization PASSED                   [ 12%]
tests/test_ai_support.py::test_ai_ticket_classification PASSED           [ 25%]
tests/test_ai_support.py::test_faq_retrieval PASSED                      [ 37%]
tests/test_ai_support.py::test_ai_suggest_response_fallback_and_guardrail PASSED [ 50%]
tests/test_auth.py::test_auth_success PASSED                             [ 62%]
tests/test_auth.py::test_auth_failure PASSED                             [ 75%]
tests/test_auth.py::test_login_route_get PASSED                          [ 87%]
tests/test_tickets.py::test_ticket_crud_and_status PASSED                [100%]

============================== 13 passed ==============================
```

## 3. Đánh giá độ bao phủ yêu cầu (Requirements Coverage)
| Mã yêu cầu | Test Case tương ứng | Trạng thái |
|---|---|---|
| FR-001 (xác thực cơ bản; chưa đủ RBAC) | `test_auth_success`, `test_auth_failure`, `test_login_route_get` | **PASSED trong phạm vi test** |
| FR-003, FR-004, FR-005 (Ticket CRUD, lifecycle, filter, statistics) | `test_tickets.py`, `test_routes.py` | **PASSED trong phạm vi test** |
| FR-008 (AI Phân loại) | `test_ai_ticket_classification` | **PASSED với engine test/fallback** |
| FR-009 (AI Gợi ý trả lời RAG) | `test_faq_retrieval`, `test_ai_suggest_response_fallback_and_guardrail` | **PASSED với provider giả/fallback** |
| FR-010 (Human Gate Review) | Luồng route trong `test_routes.py` | **PASSED trong môi trường test cục bộ** |
| NFR-003 (PII Sanitization) | `test_pii_sanitization` | **PASSED với mẫu PII đã định nghĩa** |

## 4. Kết luận
Sau khi khôi phục FastAPI làm backend chính, lệnh `.venv-1\\Scripts\\python.exe -m pytest -q` ngày 2026-10-28 đạt **110 passed, 1 skipped**; test bị skip là MySQL integration có điều kiện. `compileall backend tests` và kiểm tra cú pháp JavaScript đạt. Chưa chạy migration trên database người dùng, kiểm thử trình duyệt, SMS hoặc Gemini/OpenAI thật; vì vậy chưa đủ bằng chứng phát hành.

