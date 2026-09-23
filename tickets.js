const english = document.documentElement.lang === 'en';
const t = (vi, en) => english ? en : vi;
const $ = id => document.getElementById(id);
const labels = { 'Mới':'New', 'Đang xử lý':'In progress', 'Đã giải quyết':'Resolved', 'Đã đóng':'Closed', 'Thấp':'Low', 'Trung bình':'Normal', 'Cao':'High', 'Khẩn cấp':'Urgent' };
const label = value => english ? (labels[value] || value) : value;
const errors = {
  INVALID_INPUT: ['Nhập đủ nội dung, tiêu đề tối đa 200 ký tự, nội dung tối đa 3.000 ký tự.', 'Complete the fields: subject up to 200 characters, message up to 3,000 characters.'],
  TICKET_NOT_FOUND: ['Không tìm thấy yêu cầu hoặc bạn không có quyền xem.', 'Ticket not found or access unavailable.'],
  TICKET_ALREADY_CLAIMED: ['Yêu cầu đã được nhận. Hãy làm mới danh sách.', 'This ticket has already been claimed. Refresh the list.'],
  CLAIM_REQUIRED: ['Hãy nhận yêu cầu trước khi xử lý.', 'Claim the ticket before processing it.'],
  REPLY_REQUIRED: ['Cần gửi phản hồi trước khi đánh dấu đã giải quyết.', 'Send a reply before marking the ticket resolved.'],
  INVALID_TRANSITION: ['Trạng thái đã thay đổi hoặc bước chuyển không hợp lệ. Hãy làm mới.', 'The status changed or this transition is invalid. Refresh the ticket.'],
  TICKET_READ_ONLY: ['Yêu cầu đã giải quyết/đóng, không nhận thêm phản hồi.', 'Resolved or closed tickets cannot receive more replies.'],
  FORBIDDEN: ['Vai trò của bạn không được thực hiện thao tác này.', 'Your role cannot perform this action.'],
  ORIGIN_REJECTED: ['Hãy mở trang tại http://localhost:3000.', 'Open this page at http://localhost:3000.'],
  REQUEST_KEY_CONFLICT: ['Yêu cầu thử lại không khớp. Hãy làm mới trang.', 'The retry does not match. Refresh the page.']
};
let user, nextPage = null, selected = null, busy = false, detailSequence = 0, listSequence = 0;
const keys = new Map();
function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  if (className === 'badge') el.dataset.status = Object.keys(labels).find(key => label(key) === text) || text;
  return el;
}
function notice(message, error = false) { $('notice').textContent = message; $('notice').classList.toggle('error', error); }
function fail(error) { notice((errors[error.message] || [ 'Dịch vụ tạm thời không phản hồi. Bạn có thể thử lại; hệ thống chống gửi trùng.', 'Service unavailable. You can retry; duplicate submissions are prevented.' ])[english ? 1 : 0], true); }
function date(value) { return value ? new Intl.DateTimeFormat(english ? 'en-GB' : 'vi-VN', { timeZone:'Asia/Ho_Chi_Minh', dateStyle:'short', timeStyle:'short' }).format(new Date(value)) : ''; }
async function api(path, body) {
  let storageKey, requestKey;
  if (body !== undefined) {
    const bytes = new TextEncoder().encode(JSON.stringify([user.id, path, body]));
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(v => v.toString(16).padStart(2,'0')).join('');
    storageKey = `vietincare-ticket-${hash}`;
    try { requestKey = sessionStorage.getItem(storageKey); } catch { /* In-memory retry if storage is disabled. */ }
    requestKey ||= keys.get(storageKey) || crypto.randomUUID();
    keys.set(storageKey, requestKey);
    try { sessionStorage.setItem(storageKey, requestKey); } catch { /* No ticket text is stored. */ }
  }
  const response = await fetch(path, { credentials:'same-origin', cache:'no-store', ...(body !== undefined ? { method:'POST', headers:{'Content-Type':'application/json','X-Vietincare-Request':'1','Idempotency-Key':requestKey}, body:JSON.stringify(body) } : {}) });
  if (response.status === 401) { location.replace(`login-${english ? 'en':'vi'}.html`); throw new Error('UNAUTHENTICATED'); }
  const data = await response.json();
  if (storageKey && (response.ok || response.status < 500)) {
    keys.delete(storageKey); try { sessionStorage.removeItem(storageKey); } catch { /* optional storage */ }
  }
  if (!response.ok) throw new Error(data.error || 'SERVICE_UNAVAILABLE');
  return data;
}
async function action(work) {
  if (busy) return;
  busy = true;
  document.querySelectorAll('button').forEach(b => b.disabled = true);
  notice(t('Đang lưu…', 'Saving…'));
  try { await work(); } catch (e) { fail(e); }
  finally { busy = false; document.querySelectorAll('button').forEach(b => b.disabled = false); }
}
async function loadList(append = false) {
  const sequence = ++listSequence;
  $('listStatus').textContent = t('Đang tải…','Loading…');
  const params = new URLSearchParams();
  if ($('filter').value) params.set('status',$('filter').value);
  if (append && nextPage) params.set('before',nextPage);
  try {
    const data = await api(`/api/tickets?${params}`);
    if (sequence !== listSequence) return;
    if (!append) $('ticketList').replaceChildren();
    for (const ticket of data.tickets) {
      const li = node('li'), link = node('a', undefined, 'ticket-link');
      link.href = `#${ticket.id}`; link.dataset.id = ticket.id;
      link.setAttribute('aria-current', String(ticket.id === selected));
      link.append(node('span', ticket.code, 'meta'),node('strong', ticket.title),node('span',label(ticket.status),'badge'),node('span',date(ticket.createdAt),'meta'));
      li.append(link); $('ticketList').append(li);
    }
    nextPage = data.next; $('more').hidden = !nextPage;
    $('listStatus').textContent = $('ticketList').children.length ? '' : t('Chưa có yêu cầu trong danh sách này.', 'No tickets in this list.');
  } catch(e) { if (sequence === listSequence) { $('listStatus').textContent = t('Chưa tải được danh sách. Nhấn Làm mới.', 'Could not load tickets. Select Refresh.'); throw e; } }
}
function button(text, work, secondary = false) {
  const el = node('button',text,secondary ? 'secondary':''); el.type='button'; el.disabled=busy;
  el.addEventListener('click', () => action(work)); return el;
}
async function loadDetail(id) {
  const sequence = ++detailSequence;
  selected = id; $('detail').replaceChildren(node('p', t('Đang tải yêu cầu…','Loading ticket…')));
  $('language').hash = id;
  document.querySelectorAll('.ticket-link').forEach(a => a.setAttribute('aria-current', String(Number(a.dataset.id) === id)));
  try {
    const { ticket, replies, history } = await api(`/api/tickets/${id}`);
    if (sequence !== detailSequence) return;
    const panel = $('detail'); panel.replaceChildren(node('p',ticket.code,'eyebrow'),node('h2',ticket.title));
    panel.append(node('span',label(ticket.status),'badge'),node('span',label(ticket.priority),'badge'),node('p',`${t('Tạo lúc','Created')} ${date(ticket.createdAt)} · GMT+7`,'meta'),node('p',ticket.content,'prose'));
    const ownAgent = user.role === 'Agent' && ticket.agentId === user.id;
    const refresh = async () => { await loadDetail(id); await loadList(); };
    const actions = node('div',undefined,'actions');
    if (user.role === 'Agent' && !ticket.agentId && ticket.status === 'Mới') actions.append(button(t('Nhận yêu cầu','Claim ticket'),async () => { await api(`/api/tickets/${id}/claim`,{}); notice(t('Đã nhận yêu cầu.','Ticket claimed.')); await refresh(); }));
    if (ownAgent && ['Đang xử lý','Đã giải quyết'].includes(ticket.status)) {
      const target = ticket.status === 'Đang xử lý' ? 'Đã giải quyết':'Đã đóng';
      actions.append(button(t(target === 'Đã đóng' ? 'Đóng yêu cầu':'Đánh dấu đã giải quyết',target === 'Đã đóng' ? 'Close ticket':'Mark resolved'),async () => { await api(`/api/tickets/${id}/status`,{status:target}); notice(t('Đã cập nhật trạng thái.','Status updated.')); await refresh(); }));
    }
    panel.append(actions);
    if (ownAgent && ticket.status === 'Đang xử lý') {
      const form = node('form'), priority = node('select'); priority.id='priority';
      const caption = node('label',t('Mức ưu tiên','Priority')); caption.htmlFor='priority';
      for (const value of ['Thấp','Trung bình','Cao','Khẩn cấp']) { const option=node('option',label(value)); option.value=value; priority.append(option); }
      priority.value=ticket.priority;
      form.append(caption,priority,button(t('Lưu ưu tiên','Save priority'),async () => { await api(`/api/tickets/${id}/priority`,{priority:priority.value}); notice(t('Đã lưu ưu tiên.','Priority saved.')); await refresh(); },true)); panel.append(form);
    }
    panel.append(node('h3',t('Trao đổi','Conversation')));
    if (!replies.length) panel.append(node('p',t('Chưa có phản hồi.','No replies yet.'),'meta'));
    for (const reply of replies) {
      const card=node('article',undefined,`reply ${reply.role === 'Customer' ? '':'staff'}`);
      card.append(node('strong',`${reply.author} · ${reply.role === 'Customer' ? t('Khách hàng','Customer'):t('Nhân viên','Agent')}`),node('p',date(reply.createdAt),'meta'),node('p',reply.content,'prose')); panel.append(card);
    }
    if ((user.role === 'Customer' || ownAgent) && ['Mới','Đang xử lý'].includes(ticket.status)) {
      const form=node('form'), caption=node('label',t('Thêm phản hồi','Add reply')), input=node('textarea');
      caption.htmlFor='reply'; input.id='reply'; input.maxLength=3000; input.required=true; input.rows=4;
      const send=node('button',t('Gửi phản hồi','Send reply')); send.type='submit'; send.disabled=busy;
      form.append(caption,input,send);
      form.addEventListener('submit',e => { e.preventDefault(); if(form.reportValidity()) action(async () => { await api(`/api/tickets/${id}/replies`,{content:input.value.trim()}); input.value=''; notice(t('Đã gửi phản hồi.','Reply sent.')); await refresh(); }); }); panel.append(form);
    } else if (['Đã giải quyết','Đã đóng'].includes(ticket.status)) panel.append(node('p',t('Yêu cầu đã hoàn tất, chỉ xem nội dung.','This ticket is complete and read-only.'),'meta'));
    panel.append(node('h3',t('Lịch sử trạng thái','Status history')));
    const list=node('ol',undefined,'history');
    for (const item of history) list.append(node('li',`${label(item.status)} · ${item.author} · ${date(item.createdAt)}`));
    panel.append(list);
  } catch (error) { if (sequence === detailSequence) { $('detail').replaceChildren(node('p',(errors[error.message] || [ 'Không tải được chi tiết. Nhấn Làm mới để thử lại.', 'Could not load details. Select Refresh to retry.' ])[english ? 1:0])); throw error; } }
}
function hashId() { return /^[1-9]\d{0,9}$/.test(location.hash.slice(1)) ? Number(location.hash.slice(1)) : null; }
$('createForm').addEventListener('submit', e => {
  e.preventDefault(); if (!$('createForm').reportValidity()) return;
  action(async () => {
    const result = await api('/api/tickets',{title:$('title').value.trim(),content:$('content').value.trim()});
    $('createForm').reset(); $('filter').value='';
    notice(t(`Đã lưu yêu cầu ${result.code}.`,`Ticket ${result.code} saved.`));
    history.replaceState(null,'',`#${result.id}`);
    await loadDetail(result.id); await loadList();
  });
});
$('refresh').addEventListener('click', () => action(async () => { await loadList(); if (selected) await loadDetail(selected); notice(t('Đã làm mới.','Refreshed.')); }));
$('filter').addEventListener('change', () => loadList().catch(fail));
$('more').addEventListener('click', () => { if (!busy) action(async () => { await loadList(true); notice(''); }); });
window.addEventListener('hashchange', () => { const id=hashId(); if (id && user) loadDetail(id).catch(fail); });
(async () => {
  try {
    user = await window.VietinWorkspace.ready;
    if (!['Customer','Agent','Supervisor'].includes(user.role)) { $('intro').textContent=t('Chức năng này dành cho khách hàng, nhân viên hỗ trợ và giám sát viên.','This workspace is for customers, support agents and supervisors.'); return; }
    $('intro').textContent=user.role === 'Customer' ? t('Theo dõi yêu cầu và trao đổi với nhân viên hỗ trợ.','Track your requests and talk to support.') : user.role === 'Agent' ? t('Nhận yêu cầu mới và xử lý các yêu cầu được giao cho bạn.','Claim new tickets and process your assigned requests.') : t('Xem tiến độ và lịch sử xử lý của các yêu cầu.','View ticket progress and activity.');
    $('createSection').hidden=user.role !== 'Customer'; $('workspace').hidden=false;
    const initialFilter = new URLSearchParams(location.search).get('status');
    if (['Mới','Đang xử lý','Đã giải quyết','Đã đóng'].includes(initialFilter)) $('filter').value = initialFilter;
    await loadList(); const id=hashId(); if (id) await loadDetail(id);
  } catch(e) { fail(e); }
})();
