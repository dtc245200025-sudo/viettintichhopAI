---
name: requirements-analysis
description: Analyze customer support system requirements and transform them into structured functional requirements, non-functional requirements, user stories, acceptance criteria, business rules, assumptions, ambiguities, and traceability information.
---

# Requirements Analysis Skill

## Objective

Analyze the VietinCare AI software requirements systematically and produce
a structured specification for architecture, database, implementation,
and testing.

## Inputs

Read:

- docs/customer-requirement.md
- existing requirements documentation
- object-oriented design documentation
- project constraints

## Process

### 1. Identify stakeholders

Identify all stakeholders relevant to the system.

### 2. Identify actors

Identify:

- Customer
- Support Staff / Agent
- Supervisor
- Admin
- AI Engine

### 3. Identify functional requirements

Convert only explicit business requirements into functional requirements.

Use IDs:

FR-001
FR-002
FR-003
...

### 4. Identify non-functional requirements

Identify:

- Performance
- Security
- Reliability
- Usability
- Maintainability
- Scalability

Use IDs:

NFR-001
NFR-002
...

### 5. Identify business rules

Only use rules explicitly stated in the project documents.

Do not invent business rules.

### 6. Identify assumptions

Clearly separate assumptions from actual requirements.

### 7. Identify ambiguities

Identify requirements that are:

- ambiguous
- incomplete
- contradictory
- not testable

### 8. Create user stories

Use:

As a <role>,
I want <capability>,
so that <benefit>.

### 9. Create acceptance criteria

Acceptance criteria must be testable.

### 10. Traceability

Every user story must trace to one or more functional requirements.

## Rules

- Do not write source code.
- Do not design the database.
- Do not design the architecture.
- Do not invent undocumented business rules.
- Clearly distinguish requirements from assumptions.
- Clearly identify missing information.

## Outputs

Create:

docs/requirements.md
docs/user-stories.md
docs/acceptance-criteria.md
docs/requirements-issues.md

## Verification

Before completing:

- all functional requirements have IDs
- all non-functional requirements have IDs
- user stories trace to requirements
- acceptance criteria are testable
- ambiguities are documented

# Requirements Analysis Skill

## Role
Bạn là chuyên gia phân tích yêu cầu phần mềm.

## Objective
Phân tích yêu cầu của hệ thống VietinBank Customer Support AI
(VietinCare AI) dựa trên tài liệu yêu cầu được cung cấp.

## Responsibilities
- Xác định stakeholders
- Xác định actors
- Phân tích functional requirements
- Phân tích non-functional requirements
- Xác định business rules
- Xác định assumptions
- Xác định ambiguities/issues
- Xây dựng user stories
- Xây dựng acceptance criteria
- Xây dựng traceability giữa requirements và use cases

## Important Rules
- Không tự ý thêm chức năng không có trong tài liệu.
- Phân biệt rõ yêu cầu đã có và giả định.
- Không viết code trong giai đoạn Requirements Engineering.
- Không bỏ qua các yêu cầu liên quan đến AI.
- Phải chú ý đến quyền của Customer, Agent, Supervisor và Admin.
- AI không được tự động gửi câu trả lời cuối cùng cho khách hàng.
- Agent phải kiểm tra và phê duyệt câu trả lời do AI đề xuất.
- Thông tin cá nhân không cần thiết phải được loại bỏ trước khi
  gửi dữ liệu hội thoại cho AI.

## Expected Outputs

Tạo các tài liệu:

docs/requirements.md
docs/user-stories.md
docs/acceptance-criteria.md
docs/requirements-issues.md