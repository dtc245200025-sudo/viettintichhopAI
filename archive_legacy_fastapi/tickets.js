const english = document.documentElement.lang === 'en';
const t = (vi, en) => english ? en : vi;
const $ = id => document.getElementById(id);
const labels = { 'Mới':'New', 'Đang xử lý':'In progress', 'Chờ khách hàng':'Waiting for customer', 'Đã đóng':'Closed', 'Thấp':'Low', 'Trung bình':'Normal', 'Cao':'High', 'Khẩn cấp':'Urgent' };
const label = value => english ? (labels[value] || value) : value;
const errors = {
  INVALID_INPUT: ['Nhập đủ nội dung, tiêu đề tối đa 200 ký tự, nội dung tối đa 3.000 ký tự.', 'Complete the fields: subject up to 200 characters, message up to 3,000 characters.'],
  TICKET_NOT_FOUND: ['Không tìm thấy yêu cầu hoặc bạn không có quyền xem.', 'Ticket not found or access unavailable.'],
  TICKET_ALREADY_CLAIMED: ['Yêu cầu đã được nhận. Hãy làm mới danh sách.', 'This ticket has already been claimed. Refresh the list.'],
  AGENT_NOT_AVAILABLE: ['Nhân viên được chọn không tồn tại hoặc đã bị khóa. Hãy làm mới danh sách.', 'The selected agent is missing or inactive. Refresh the agent list.'],
  CLAIM_REQUIRED: ['Hãy nhận yêu cầu trước khi xử lý.', 'Claim the ticket before processing it.'],
  REPLY_REQUIRED: ['Cần gửi phản hồi trước khi đóng yêu cầu.', 'Send a reply before closing the ticket.'],
  INVALID_TRANSITION: ['Trạng thái đã thay đổi hoặc bước chuyển không hợp lệ. Hãy làm mới.', 'The status changed or this transition is invalid. Refresh the ticket.'],
  TICKET_READ_ONLY: ['Yêu cầu đã đóng, không nhận thêm phản hồi.', 'Closed tickets cannot receive more replies.'],
  FORBIDDEN: ['Vai trò của bạn không được thực hiện thao tác này.', 'Your role cannot perform this action.'],
  ORIGIN_REJECTED: ['Hãy mở trang tại http://localhost:3000.', 'Open this page at http://localhost:3000.'],
  REQUEST_KEY_CONFLICT: ['Yêu cầu thử lại không khớp. Hãy làm mới trang.', 'The retry does not match. Refresh the page.'],
  AI_NOT_CONFIGURED: ['Chức năng AI chưa được cấu hình.', 'AI assistance is not configured.'],
  AI_SUGGESTION_REVIEWED: ['Gợi ý này đã được duyệt trước đó.', 'This suggestion has already been reviewed.'],
  TICKET_NOT_CLOSED: ['Chỉ đánh giá yêu cầu đã đóng.', 'Only closed tickets can be rated.'],
  EVALUATION_EXISTS: ['Yêu cầu này đã được đánh giá.', 'This ticket has already been rated.']
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
  if ($('customerFilter').value.trim()) params.set('customer',$('customerFilter').value.trim());
  if ($('priorityFilter').value) params.set('priority',$('priorityFilter').value);
  if ($('startDate').value) params.set('startDate',$('startDate').value);
  if ($('endDate').value) params.set('endDate',$('endDate').value);
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
    const { ticket, replies, history, assignments = [], evaluation, analyses = [] } = await api(`/api/tickets/${id}`);
    ticket.evaluation = evaluation;
    if (sequence !== detailSequence) return;
    const panel = $('detail'); panel.replaceChildren(node('p',ticket.code,'eyebrow'),node('h2',ticket.title));
    panel.append(node('span',label(ticket.status),'badge'),node('span',label(ticket.priority),'badge'),node('p',`${t('Tạo lúc','Created')} ${date(ticket.createdAt)} · GMT+7`,'meta'),node('p',ticket.content,'prose'));
    const ownAgent = user.role === 'Agent' && ticket.agentId === user.id;
    const refresh = async () => { await loadDetail(id); await loadList(); };
    if ((ownAgent && ['Đang xử lý','Chờ khách hàng'].includes(ticket.status)) || (user.role === 'Supervisor' && ticket.status !== 'Đã đóng')) {
      const editor=node('details'), title=node('input'), content=node('textarea'), category=node('select'), form=node('form');
      editor.append(node('summary',t('Chỉnh sửa yêu cầu và nhóm vấn đề','Edit ticket and category')));
      title.value=ticket.title;title.required=true;title.maxLength=200;
      content.value=ticket.content;content.required=true;content.maxLength=3000;content.rows=5;
      const empty=node('option',t('Chưa phân loại','Uncategorized'));empty.value='';category.append(empty);
      const result=await api('/api/tickets/categories');
      if(sequence!==detailSequence)return;
      for(const item of result.categories){const option=node('option',item.name);option.value=String(item.id);category.append(option);}
      category.value=ticket.categoryId?String(ticket.categoryId):'';
      for(const [name,input] of [[t('Tiêu đề','Subject'),title],[t('Mô tả','Description'),content],[t('Nhóm vấn đề','Category'),category]]){const caption=node('label',name);caption.append(input);form.append(caption);}
      const save=node('button',t('Lưu thay đổi','Save changes'));save.type='submit';form.append(save);
      form.addEventListener('submit',event=>{event.preventDefault();if(form.reportValidity())action(async()=>{await api(`/api/tickets/${id}/details`,{title:title.value,content:content.value,categoryId:category.value?Number(category.value):null});notice(t('Đã cập nhật yêu cầu.','Ticket updated.'));await refresh();});});
      editor.append(form);panel.append(editor);
    }
    if(analyses.length){
      const saved=node('details');saved.append(node('summary',t('Lịch sử phân tích và tóm tắt AI','Saved AI analyses and summaries')));
      saved.append(node('p',t('Gợi ý có thể đã cũ. Kiểm tra lịch sử mới nhất trước khi sử dụng.','Suggestions may be outdated. Review the latest history before use.'),'meta'));
      for(const item of analyses){const block=node('section',undefined,'ai-suggestion');block.append(node('h3',`${t('Phân tích','Analysis')} #${item.id}`),node('p',`${item.category} · ${label(item.priority)} · ${item.status}`),node('p',item.summary),node('p',item.draftReply));
        if(ownAgent && ticket.status==='Đang xử lý' && item.status==='Pending')block.append(button(t('Duyệt và dùng bản nháp','Review and use draft'),async()=>{await api(`/api/tickets/${id}/ai-assist/${item.id}/review`,{decision:'selected'});const reply=panel.querySelector('#reply');if(reply){reply.value=item.draftReply;reply.focus();}notice(t('Đã chọn bản nháp; hãy kiểm tra rồi nhấn Gửi phản hồi.','Draft selected; review it and select Send reply.'));},true));
        saved.append(block);
      }panel.append(saved);
    }
    const actions = node('div',undefined,'actions');
    if (user.role === 'Agent' && ticket.status === 'Mới' && (!ticket.agentId || ticket.agentId === user.id)) actions.append(button(ticket.agentId ? t('Nhận ca được giao','Accept assigned ticket') : t('Nhận yêu cầu','Claim ticket'),async () => { await api(`/api/tickets/${id}/claim`,{}); notice(t('Đã nhận yêu cầu.','Ticket claimed.')); await refresh(); }));
    if (user.role === 'Supervisor' && ['Mới','Đang xử lý','Chờ khách hàng'].includes(ticket.status)) {
      try {
        const {agents} = await api('/api/tickets/agents');
        const assignment = node('div',undefined,'actions'), caption = node('label',t('Giao cho nhân viên hỗ trợ','Assign to support agent'));
        const agentSelect = node('select'); agentSelect.setAttribute('aria-label',caption.textContent);
        for (const agent of agents) { const option=node('option',`${agent.name} · ${agent.email}`);option.value=String(agent.id);agentSelect.append(option); }
        if (ticket.agentId && agents.some(agent=>agent.id===ticket.agentId)) agentSelect.value=String(ticket.agentId);
        const assignButton = button(ticket.agentId ? t('Đổi người xử lý','Reassign ticket') : t('Giao yêu cầu','Assign ticket'),async()=>{
          if (!agentSelect.value) return;
          await api(`/api/tickets/${id}/assign`,{agentId:Number(agentSelect.value)});
          notice(t('Đã lưu phân công. Nhân viên sẽ nhận ca trước khi xử lý.','Assignment saved. The agent must accept before working on it.'));
          await refresh();
        });
        assignButton.disabled = busy || agents.length === 0;
        caption.htmlFor = `assignAgent-${id}`;agentSelect.id=caption.htmlFor;
        if (!agents.length) assignment.append(node('p',t('Chưa có nhân viên đang hoạt động.','No active support agents are available.')));
        assignment.append(caption,agentSelect,assignButton);actions.append(assignment);
      } catch { actions.append(node('p',t('Không tải được danh sách nhân viên. Hãy làm mới.','Could not load the agent list. Refresh to retry.'))); }
    }
    if (ownAgent && ticket.status === 'Đang xử lý') actions.append(button(t('Phân tích và gợi ý bằng AI','Analyze with AI'),async () => {
      const suggestion=await api(`/api/tickets/${id}/ai-assist`,{language:english?'en':'vi'});
      panel.querySelector('.ai-suggestion')?.remove();
      const block=node('section',undefined,'ai-suggestion'),heading=node('h3',t('Gợi ý AI · cần nhân viên duyệt','AI suggestions · agent review required'));
      block.append(heading,node('p',`${t('Nhóm vấn đề','Category')}: ${suggestion.category}`),node('p',`${t('Ưu tiên gợi ý','Suggested priority')}: ${label(suggestion.priority)}`),node('p',`${t('Cảm xúc','Sentiment')}: ${label(suggestion.sentiment)}`),node('p',`${t('Tóm tắt','Summary')}: ${suggestion.summary}`));
      const caption=node('label',t('Bản nháp có thể chỉnh sửa','Editable reply draft')),draft=node('textarea');
      draft.value=suggestion.draftReply;draft.maxLength=2000;draft.rows=4;draft.className='ai-draft';caption.htmlFor='aiDraft';draft.id='aiDraft';block.append(caption,draft);
      const review=node('div',undefined,'actions');
      const reviewOnce=async decision=>{await api(`/api/tickets/${id}/ai-assist/${suggestion.id}/review`,{decision});review.replaceChildren(node('p',decision==='selected'?t('Đã chọn gợi ý. Bản nháp chưa được gửi.','Suggestion selected. The draft has not been sent.') : t('Đã bỏ gợi ý.','Suggestion dismissed.'),'meta'));};
      review.append(button(t('Dùng bản nháp','Use draft'),async()=>{const reply=panel.querySelector('#reply');if(reply){reply.value=draft.value;reply.focus();}await reviewOnce('selected');},true));
      review.append(button(`${t('Áp dụng ưu tiên','Apply priority')}: ${label(suggestion.priority)}`,async()=>{await api(`/api/tickets/${id}/priority`,{priority:suggestion.priority});await reviewOnce('selected');await refresh();},true));
      review.append(button(t('Bỏ gợi ý','Dismiss'),async()=>reviewOnce('dismissed'),true));
      block.append(review);panel.insertBefore(block,panel.querySelector('h3'));
      notice(t('Gợi ý được lưu, chưa gửi cho khách hàng.','Suggestions saved; nothing was sent to the customer.'));
    },true));
    if (ownAgent && ticket.status === 'Đang xử lý') {
      actions.append(button(t('Chờ khách hàng','Wait for customer'),async () => { await api(`/api/tickets/${id}/status`,{status:'Chờ khách hàng'}); notice(t('Đã chuyển sang chờ khách hàng.','Ticket is waiting for the customer.')); await refresh(); },true));
      actions.append(button(t('Đóng yêu cầu','Close ticket'),async () => { await api(`/api/tickets/${id}/status`,{status:'Đã đóng'}); notice(t('Đã đóng yêu cầu.','Ticket closed.')); await refresh(); }));
    } else if (ownAgent && ticket.status === 'Chờ khách hàng') {
      actions.append(button(t('Tiếp tục xử lý','Resume processing'),async () => { await api(`/api/tickets/${id}/status`,{status:'Đang xử lý'}); notice(t('Đã tiếp tục xử lý.','Processing resumed.')); await refresh(); },true));
      actions.append(button(t('Đóng yêu cầu','Close ticket'),async () => { await api(`/api/tickets/${id}/status`,{status:'Đã đóng'}); notice(t('Đã đóng yêu cầu.','Ticket closed.')); await refresh(); }));
    }
    panel.append(actions);
    if (ownAgent && ['Đang xử lý','Chờ khách hàng'].includes(ticket.status)) {
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
    if ((user.role === 'Customer' && ['Mới','Đang xử lý','Chờ khách hàng'].includes(ticket.status)) || (ownAgent && ['Đang xử lý','Chờ khách hàng'].includes(ticket.status))) {
      const form=node('form'), caption=node('label',t('Thêm phản hồi','Add reply')), input=node('textarea');
      caption.htmlFor='reply'; input.id='reply'; input.maxLength=2000; input.required=true; input.rows=4;
      const send=node('button',t('Gửi phản hồi','Send reply')); send.type='submit'; send.disabled=busy;
      form.append(caption,input,send);
      form.addEventListener('submit',e => { e.preventDefault(); if(form.reportValidity()) action(async () => { await api(`/api/tickets/${id}/replies`,{content:input.value.trim()}); input.value=''; notice(t('Đã gửi phản hồi.','Reply sent.')); await refresh(); }); }); panel.append(form);
    } else if (ticket.status === 'Đã đóng') panel.append(node('p',t('Yêu cầu đã đóng, chỉ xem nội dung.','This ticket is closed and read-only.'),'meta'));
    if (user.role === 'Customer' && ticket.status === 'Đã đóng') {
      if (ticket.evaluation) panel.append(node('p',t(`Bạn đã đánh giá ${ticket.evaluation.stars}/5. Cảm ơn phản hồi của bạn.`,`You rated this ticket ${ticket.evaluation.stars}/5. Thank you for your feedback.`),'evaluation-note'));
      else {
        const section=node('section',undefined,'evaluation'),heading=node('h3',t('Đánh giá hỗ trợ','Rate your support'));
        const form=node('form'),stars=node('select'),starsLabel=node('label',t('Mức hài lòng','Rating')),comment=node('textarea'),commentLabel=node('label',t('Nhận xét (không bắt buộc)','Comment (optional)'));
        stars.id='evaluationStars';starsLabel.htmlFor=stars.id;
        for(let value=1;value<=5;value++){const option=node('option',`${value} / 5`);option.value=String(value);stars.append(option);}
        comment.id='evaluationComment';comment.maxLength=1000;comment.rows=3;commentLabel.htmlFor=comment.id;
        const submit=node('button',t('Gửi đánh giá','Submit rating'));submit.type='submit';
        form.append(starsLabel,stars,commentLabel,comment,submit);
        form.addEventListener('submit',event=>{event.preventDefault();action(async()=>{await api(`/api/tickets/${id}/evaluation`,{stars:Number(stars.value),comment:comment.value});notice(t('Đã lưu đánh giá.','Rating saved.'));await refresh();});});
        section.append(heading,form);panel.append(section);
      }
    }
    panel.append(node('h3',t('Lịch sử trạng thái','Status history')));
    const list=node('ol',undefined,'history');
    for (const item of history) list.append(node('li',`${label(item.status)} · ${item.author} · ${date(item.createdAt)}`));
    panel.append(list);
    if (assignments.length) {
      panel.append(node('h3',t('Lịch sử phân công','Assignment history')));
      const assignmentList=node('ol',undefined,'history');
      for (const item of assignments) assignmentList.append(node('li',`${item.previousAgent ? `${item.previousAgent} → ` : ''}${item.agent} · ${t('thực hiện bởi','by')} ${item.performedBy} · ${date(item.createdAt)}`));
      panel.append(assignmentList);
    }
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
$('filters').addEventListener('submit', event => { event.preventDefault(); loadList().catch(fail); });
$('filter').addEventListener('change', () => loadList().catch(fail));
$('priorityFilter').addEventListener('change', () => loadList().catch(fail));
$('more').addEventListener('click', () => { if (!busy) action(async () => { await loadList(true); notice(''); }); });
window.addEventListener('hashchange', () => { const id=hashId(); if (id && user) loadDetail(id).catch(fail); });
(async () => {
  try {
    user = await window.VietinWorkspace.ready;
    if (!['Customer','Agent','Supervisor'].includes(user.role)) { $('intro').textContent=t('Chức năng này dành cho khách hàng, nhân viên hỗ trợ và giám sát viên.','This workspace is for customers, support agents and supervisors.'); return; }
    $('intro').textContent=user.role === 'Customer' ? t('Theo dõi yêu cầu và trao đổi với nhân viên hỗ trợ.','Track your requests and talk to support.') : user.role === 'Agent' ? t('Nhận yêu cầu mới và xử lý các yêu cầu được giao cho bạn.','Claim new tickets and process your assigned requests.') : t('Xem tiến độ và lịch sử xử lý của các yêu cầu.','View ticket progress and activity.');
    $('createSection').hidden=user.role !== 'Customer'; $('workspace').hidden=false;
    const initialFilter = new URLSearchParams(location.search).get('status');
    if (['Mới','Đang xử lý','Chờ khách hàng','Đã đóng'].includes(initialFilter)) $('filter').value = initialFilter;
    await loadList(); const id=hashId(); if (id) await loadDetail(id);
  } catch(e) { fail(e); }
})();
