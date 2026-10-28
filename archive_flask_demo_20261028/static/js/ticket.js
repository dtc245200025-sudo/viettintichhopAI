// ViettinCare - Frontend JavaScript Logic for AI Support & Human Gate

function toggleModal(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    if (modal.style.display === 'none' || modal.style.display === '') {
        modal.style.display = 'flex';
    } else {
        modal.style.display = 'none';
    }
}

function switchAITab(tabId) {
    document.querySelectorAll('.ai-tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.ai-tab-btn').forEach(el => el.classList.remove('active'));

    const targetTab = document.getElementById(tabId);
    if (targetTab) targetTab.classList.add('active');

    event.currentTarget.classList.add('active');
}

// 1. Phân loại AI khi tạo ticket mới
async function triggerAIClassify() {
    const title = document.getElementById('ticket_title').value;
    const desc = document.getElementById('ticket_description').value;
    const statusSpan = document.getElementById('ai-classify-status');

    if (!title) {
        alert('Vui lòng nhập tiêu đề sự cố trước khi chạy AI phân tích!');
        return;
    }

    statusSpan.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AI đang phân tích nội dung...';

    try {
        const res = await fetch('/api/ai/classify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title, description: desc })
        });
        const data = await res.json();

        if (data.category) {
            document.getElementById('ticket_category').value = data.category;
            document.getElementById('ticket_priority').value = data.suggested_priority;
            statusSpan.innerHTML = `<span style="color: #10b981;"><i class="fa-solid fa-check"></i> Đề xuất: ${data.category} (${data.suggested_priority})</span>`;
        } else {
            statusSpan.innerText = 'Không thể phân loại';
        }
    } catch (err) {
        statusSpan.innerText = 'Lỗi kết nối AI';
    }
}

// 2. Sinh câu trả lời nháp (Draft Response Suggester)
async function generateAIDraft(ticketId) {
    const btn = document.getElementById('btnGenerateDraft');
    const container = document.getElementById('aiDraftContainer');
    const editor = document.getElementById('aiDraftText');
    const latencyEl = document.getElementById('aiDraftLatency');
    const matchedEl = document.getElementById('aiDraftMatched');

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AI đang tra cứu FAQ và soạn nháp...';

    try {
        const res = await fetch('/api/ai/suggest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticket_id: ticketId })
        });
        const data = await res.json();

        if (data.draft_response) {
            editor.value = data.draft_response;
            container.style.display = 'block';
            latencyEl.innerHTML = `<i class="fa-solid fa-bolt"></i> Thời gian: ${data.latency_ms}ms`;
            matchedEl.innerHTML = `<i class="fa-solid fa-book"></i> FAQ khớp: ${data.matched_faqs}`;
        } else {
            alert('Không thể tạo câu trả lời: ' + (data.error || 'Lỗi không xác định'));
        }
    } catch (err) {
        alert('Lỗi kết nối tới AI Service: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> AI Soạn thảo lại Câu trả lời Nháp';
    }
}

// 3. HUMAN GATE: Phê duyệt câu trả lời nháp và gửi cho khách hàng
async function approveAndSendDraft(ticketId) {
    const editor = document.getElementById('aiDraftText');
    const btn = document.getElementById('btnApproveDraft');
    const approvedContent = editor.value.trim();

    if (!approvedContent) {
        alert('Nội dung phản hồi không được để trống!');
        return;
    }

    if (!confirm('Bạn có chắc chắn muốn PHÊ DUYỆT và gửi phản hồi này đến khách hàng?')) {
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang duyệt và gửi...';

    try {
        const res = await fetch('/api/ai/approve-and-send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticket_id: ticketId, content: approvedContent })
        });
        const data = await res.json();

        if (data.success) {
            alert(data.message);
            window.location.reload();
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể lưu phản hồi'));
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-check-double"></i> Phê duyệt & Gửi cho Khách hàng';
        }
    } catch (err) {
        alert('Lỗi kết nối khi gửi: ' + err.message);
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-check-double"></i> Phê duyệt & Gửi cho Khách hàng';
    }
}

// 4. Tóm tắt lịch sử trao đổi
async function summarizeTicketHistory(ticketId) {
    const btn = document.getElementById('btnSummarize');
    const box = document.getElementById('summaryResultBox');
    const content = document.getElementById('summaryText');
    const latencyEl = document.getElementById('summaryLatency');

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tóm tắt...';

    try {
        const res = await fetch('/api/ai/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticket_id: ticketId })
        });
        const data = await res.json();

        if (data.summary) {
            content.innerHTML = data.summary.replace(/\n/g, '<br>');
            latencyEl.innerText = `Thời gian xử lý AI: ${data.latency_ms}ms`;
            box.style.display = 'block';
        } else {
            alert('Không thể tạo tóm tắt');
        }
    } catch (err) {
        alert('Lỗi kết nối AI: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-bolt"></i> Tạo Tóm tắt bằng AI';
    }
}

// 5. Phân loại trong chi tiết ticket
let currentSuggestedCategory = '';
let currentSuggestedPriority = '';

async function classifyTicketTab(ticketId, title, desc) {
    const btn = document.getElementById('btnClassifyTab');
    const box = document.getElementById('classifyResultBox');

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang phân tích...';

    try {
        const res = await fetch('/api/ai/classify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: title, description: desc })
        });
        const data = await res.json();

        if (data.category) {
            currentSuggestedCategory = data.category;
            currentSuggestedPriority = data.suggested_priority;

            document.getElementById('aiSuggestedCategory').innerText = data.category;
            document.getElementById('aiSuggestedPriority').innerText = data.suggested_priority;
            document.getElementById('aiSuggestedKeywords').innerText = data.keywords.join(', ') || 'Không';

            box.style.display = 'block';
        }
    } catch (err) {
        alert('Lỗi khi phân tích: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-magnifying-glass-chart"></i> Phân tích lại với AI';
    }
}

async function applySuggestedClassification(ticketId) {
    if (!currentSuggestedCategory || !currentSuggestedPriority) return;

    try {
        const res = await fetch('/api/ai/apply-classification', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ticket_id: ticketId,
                category: currentSuggestedCategory,
                priority: currentSuggestedPriority
            })
        });
        const data = await res.json();
        if (data.success) {
            alert('Đã cập nhật danh mục và mức ưu tiên!');
            window.location.reload();
        }
    } catch (err) {
        alert('Lỗi khi áp dụng: ' + err.message);
    }
}

