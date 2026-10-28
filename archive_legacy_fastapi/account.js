const en = document.documentElement.lang === 'en';
const text = (vi, english) => en ? english : vi;
const byId = id => document.getElementById(id);
const statusLabels = {'Mới':'New','Đang xử lý':'In progress','Chờ khách hàng':'Waiting for customer','Đã đóng':'Closed'};
const statusLabel = value => en ? (statusLabels[value] || value) : value;
async function loadRecent() {
  byId('refreshOverview').disabled = true;
  byId('recentStatus').textContent = text('Đang tải yêu cầu…','Loading tickets…');
  try {
    const response = await fetch('/api/tickets',{credentials:'same-origin',cache:'no-store'});
    if (response.status === 401) { location.replace(`login-${en ? 'en' : 'vi'}.html`); return; }
    if (!response.ok) throw new Error();
    const {tickets} = await response.json();
    byId('recentList').replaceChildren();
    for (const ticket of tickets.slice(0,5)) {
      const li = document.createElement('li'), a = document.createElement('a'), info = document.createElement('div'), title = document.createElement('strong'), meta = document.createElement('small'), badge = document.createElement('span');
      a.href = `tickets-${en ? 'en':'vi'}.html#${ticket.id}`;
      title.textContent = ticket.title;
      meta.textContent = `${ticket.code} · ${new Intl.DateTimeFormat(en ? 'en-GB':'vi-VN',{timeZone:'Asia/Ho_Chi_Minh',dateStyle:'medium'}).format(new Date(ticket.createdAt))}`;
      badge.className = 'badge'; badge.dataset.status = ticket.status; badge.textContent = en ? statusLabels[ticket.status] : ticket.status;
      info.append(title,meta); a.append(info,badge); li.append(a); byId('recentList').append(li);
    }
    byId('recentStatus').textContent = tickets.length ? '' : text('Chưa có yêu cầu. Các yêu cầu mới sẽ xuất hiện tại đây.','No tickets yet. New requests will appear here.');
  } catch { byId('recentStatus').textContent = text('Chưa tải được yêu cầu. Nhấn Làm mới để thử lại.','Unable to load tickets. Select Refresh to retry.'); }
  finally { byId('refreshOverview').disabled = false; }
}

async function loadReport() {
  byId('refreshReport').disabled = true;
  byId('reportStatus').textContent = text('Đang tải báo cáo…','Loading report…');
  try {
    const params = new URLSearchParams();
    if (byId('reportStart').value) params.set('startDate',byId('reportStart').value);
    if (byId('reportEnd').value) params.set('endDate',byId('reportEnd').value);
    const response = await fetch(`/api/reports/summary?${params}`,{credentials:'same-origin',cache:'no-store'});
    if (response.status === 401) { location.replace(`login-${en ? 'en':'vi'}.html`); return; }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'REPORT_FAILED');
    const number = value => new Intl.NumberFormat(en ? 'en-US':'vi-VN').format(value || 0);
    byId('reportPeriod').textContent = `${data.period.startDate} – ${data.period.endDate}`;
    byId('reportTicketCount').textContent = number(data.ticketsByStatus.reduce((sum,row)=>sum+row.count,0));
    byId('reportResolution').textContent = data.resolution.averageMinutes == null ? text('Chưa có dữ liệu','No data') : `${number(Math.round(data.resolution.averageMinutes))} ${text('phút','minutes')}`;
    byId('reportOverdue').textContent = number(data.sla.overdueTickets);
    byId('reportSessions').textContent = number(data.chatSessions);
    byId('reportCsat').textContent = data.csat.averageStars == null ? text('Chưa có dữ liệu','No data') : `${Number(data.csat.averageStars).toFixed(1)} / 5 · ${data.csat.satisfactionPercent}%`;
    byId('reportStatusList').replaceChildren(...data.ticketsByStatus.map(row=>{const li=document.createElement('li');li.textContent=`${en ? (statusLabels[row.status] || row.status):row.status}: ${number(row.count)}`;return li;}));
    byId('reportCategoryList').replaceChildren(...data.ticketsByCategory.map(row=>{const li=document.createElement('li');li.textContent=`${row.category}: ${number(row.count)}`;return li;}));
    byId('reportStatus').textContent = '';
  } catch {
    byId('reportStatus').textContent = text('Không tải được báo cáo. Kiểm tra khoảng ngày rồi thử lại.','Unable to load the report. Check the date range and retry.');
  } finally { byId('refreshReport').disabled = false; }
}

const adminRoles = ['Customer','Agent','Supervisor','Admin'];
const adminRoleLabel = role => ({Customer:text('Khách hàng','Customer'),Agent:text('Nhân viên hỗ trợ','Support agent'),Supervisor:text('Giám sát viên','Supervisor'),Admin:text('Quản trị viên','Administrator')}[role] || role);
function adminNode(tag, content, className) {
  const element = document.createElement(tag);
  if (content !== undefined) element.textContent = content;
  if (className) element.className = className;
  return element;
}
async function adminRequest(path, method = 'GET', body) {
  const response = await fetch(path, {
    method, credentials:'same-origin', cache:'no-store',
    ...(body ? {headers:{'Content-Type':'application/json','X-Vietincare-Request':'1'},body:JSON.stringify(body)} : {})
  });
  if (response.status === 401) { location.replace(`login-${en ? 'en' : 'vi'}.html`); throw new Error('UNAUTHENTICATED'); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'SERVICE_UNAVAILABLE');
  return data;
}
function adminMessage(error) {
  return ({
    EMAIL_EXISTS:text('Email đã được sử dụng.','That email is already registered.'),
    INVALID_INPUT:text('Kiểm tra lại thông tin nhập.','Check the entered values.'),
    LAST_ACTIVE_ADMIN:text('Không thể khóa hoặc hạ quyền quản trị viên cuối cùng.','The last active administrator cannot be disabled or demoted.'),
    CANNOT_CHANGE_SELF_ROLE:text('Bạn không thể khóa hoặc đổi quyền tài khoản đang đăng nhập.','You cannot disable or change the role of your current account.'),
    USER_NOT_FOUND:text('Không tìm thấy tài khoản.','Account not found.'),
    FORBIDDEN:text('Bạn không có quyền quản lý tài khoản.','You are not allowed to manage accounts.')
  })[error.message] || text('Không kết nối được dịch vụ. Hãy thử lại.','Service unavailable. Please retry.');
}
function adminSelectRole(value = 'Customer') {
  const select = document.createElement('select');
  for (const role of adminRoles) {
    const option = adminNode('option',adminRoleLabel(role)); option.value = role; select.append(option);
  }
  select.value = value;
  return select;
}
let adminLoadSequence = 0, adminLoadMore;
async function loadAdminUsers(panel, body, search, roleFilter, status, before = null, append = false) {
  const sequence = ++adminLoadSequence;
  status.textContent = text('Đang tải tài khoản…','Loading accounts…');
  try {
    const params = new URLSearchParams();
    if (search.value.trim()) params.set('query',search.value.trim());
    if (roleFilter.value) params.set('role',roleFilter.value);
    if (before) params.set('before',String(before));
    const result = await adminRequest(`/api/admin/users?${params}`);
    if (sequence !== adminLoadSequence) return;
    if (!append) body.replaceChildren();
    for (const user of result.users) {
      const row = document.createElement('tr');
      const name = document.createElement('input'); name.value = user.name; name.maxLength = 100; name.required = true; name.setAttribute('aria-label',text('Họ tên','Full name'));
      const email = document.createElement('input'); email.type = 'email'; email.value = user.email; email.maxLength = 100; email.required = true; email.setAttribute('aria-label','Email');
      const phone = document.createElement('input'); phone.type = 'tel'; phone.value = user.phone || ''; phone.maxLength = 20; phone.setAttribute('aria-label',text('Số điện thoại','Phone number'));
      const password = document.createElement('input'); password.type = 'password'; password.minLength = 12; password.maxLength = 128; password.autocomplete = 'new-password'; password.placeholder = text('Để trống nếu giữ nguyên','Blank to keep'); password.setAttribute('aria-label',text('Mật khẩu mới (tùy chọn)','New password (optional)'));
      const role = adminSelectRole(user.role);
      const activeLabel = document.createElement('label'); activeLabel.className = 'admin-active';
      const active = document.createElement('input'); active.type = 'checkbox'; active.checked = Boolean(user.isActive);
      activeLabel.append(active,adminNode('span',text('Hoạt động','Active')));
      const save = adminNode('button',text('Lưu','Save'),'secondary'); save.type = 'button';
      save.addEventListener('click',async () => {
        save.disabled = true;
        const values = {fullName:name.value.trim(),email:email.value.trim(),phone:phone.value.trim(),role:role.value,isActive:active.checked};
        if (password.value) values.password = password.value;
        try {
          await adminRequest(`/api/admin/users/${user.id}`,'PATCH',values);
          password.value = '';
          status.textContent = text('Đã cập nhật tài khoản.','Account updated.');
          await loadAdminUsers(panel,body,search,roleFilter,status);
        } catch(error) { status.textContent = adminMessage(error); }
        finally { save.disabled = false; }
      });
      for (const cell of [name,email,phone,role,activeLabel,password,save]) { const td = document.createElement('td'); td.append(cell); row.append(td); }
      body.append(row);
    }
    status.textContent = body.children.length ? text(`Đang hiển thị ${body.children.length} tài khoản.`,`Showing ${body.children.length} accounts.`) : text('Không tìm thấy tài khoản.','No accounts found.');
    adminLoadMore.hidden = !result.next;
    adminLoadMore.dataset.cursor = result.next || '';
  } catch(error) { adminLoadMore.hidden = true; status.textContent = adminMessage(error); }
}
function setupAdminUsers(panel) {
  const section = adminNode('section',undefined,'admin-users');
  const heading = adminNode('h2',text('Quản lý tài khoản','Account management'));
  const createHeading = adminNode('h3',text('Tạo tài khoản','Create account'));
  const createForm = document.createElement('form'); createForm.className = 'admin-user-create';
  const fields = [
    ['fullName',text('Họ tên','Full name'),'text'],
    ['email','Email','email'],
    ['phone',text('Số điện thoại','Phone number'),'tel'],
    ['password',text('Mật khẩu ban đầu (ít nhất 12 ký tự)','Initial password (12 characters minimum)'),'password']
  ];
  const inputs = {};
  for (const [key,label,type] of fields) {
    const wrapper = document.createElement('label'); wrapper.textContent = label;
    const input = document.createElement('input'); input.type = type; input.name = key; input.required = key !== 'phone';
    if (key === 'fullName') input.maxLength = 100;
    if (key === 'email') input.maxLength = 100;
    if (key === 'phone') { input.maxLength = 20; input.autocomplete = 'tel'; }
    if (key === 'password') { input.minLength = 12; input.maxLength = 128; input.autocomplete = 'new-password'; }
    wrapper.append(input); inputs[key] = input; createForm.append(wrapper);
  }
  const roleWrapper = document.createElement('label'); roleWrapper.textContent = text('Vai trò','Role');
  const createRole = adminSelectRole(); roleWrapper.append(createRole); createForm.append(roleWrapper);
  const createButton = adminNode('button',text('Tạo tài khoản','Create account'),'button'); createButton.type = 'submit'; createForm.append(createButton);
  const status = adminNode('p','', 'admin-status'); status.setAttribute('role','status'); status.setAttribute('aria-live','polite');
  const tools = document.createElement('form'); tools.className = 'admin-user-tools';
  const searchLabel = document.createElement('label'); searchLabel.textContent = text('Tìm tên, email hoặc số điện thoại','Search name, email or phone');
  const search = document.createElement('input'); search.type = 'search'; search.maxLength = 100; searchLabel.append(search);
  const filterLabel = document.createElement('label'); filterLabel.textContent = text('Lọc vai trò','Filter role');
  const roleFilter = document.createElement('select');
  const allRoles = adminNode('option',text('Tất cả vai trò','All roles')); allRoles.value = ''; roleFilter.append(allRoles);
  for (const role of adminRoles) { const option=adminNode('option',adminRoleLabel(role));option.value=role;roleFilter.append(option); }
  filterLabel.append(roleFilter);
  const refresh = adminNode('button',text('Tìm kiếm','Search'),'secondary'); refresh.type = 'submit'; tools.append(searchLabel,filterLabel,refresh);
  const tableWrap = adminNode('div',undefined,'admin-table-wrap');
  const table = document.createElement('table'); table.className = 'admin-user-table';
  const headers = [text('Họ tên','Name'),'Email',text('Điện thoại','Phone'),text('Vai trò','Role'),text('Trạng thái','Status'),text('Đổi mật khẩu','Reset password'),''];
  const thead = document.createElement('thead'), headerRow = document.createElement('tr');
  for (const header of headers) { const th = adminNode('th',header); th.scope = 'col'; headerRow.append(th); }
  thead.append(headerRow); const body = document.createElement('tbody'); table.append(thead,body); tableWrap.append(table);
  adminLoadMore = adminNode('button',text('Tải thêm tài khoản','Load more accounts'),'secondary');
  adminLoadMore.type = 'button'; adminLoadMore.hidden = true;
  adminLoadMore.addEventListener('click',() => loadAdminUsers(panel,body,search,roleFilter,status,adminLoadMore.dataset.cursor,true));
  createForm.addEventListener('submit',async event => {
    event.preventDefault(); if (!createForm.reportValidity()) return;
    createButton.disabled = true;
    try {
      await adminRequest('/api/admin/users','POST',{
        fullName:inputs.fullName.value.trim(),email:inputs.email.value.trim(),phone:inputs.phone.value.trim(),
        password:inputs.password.value,role:createRole.value
      });
      createForm.reset(); status.textContent = text('Tạo tài khoản thành công.','Account created.');
      await loadAdminUsers(panel,body,search,roleFilter,status);
    } catch(error) { status.textContent = adminMessage(error); }
    finally { createButton.disabled = false; }
  });
  tools.addEventListener('submit',event => { event.preventDefault(); loadAdminUsers(panel,body,search,roleFilter,status); });
  roleFilter.addEventListener('change',() => loadAdminUsers(panel,body,search,roleFilter,status));
  section.append(heading,createHeading,createForm,tools,status,tableWrap,adminLoadMore); panel.append(section);
  loadAdminUsers(panel,body,search,roleFilter,status);
}

function setupCustomers(panel) {
  const section=adminNode('section',undefined,'card customer-management');section.id='customers';
  const form=document.createElement('form'), search=document.createElement('input'), submit=adminNode('button',text('Tìm khách hàng','Find customers'));
  search.type='search';search.maxLength=100;search.placeholder=text('Tên, email, số điện thoại','Name, email, phone');search.setAttribute('aria-label',search.placeholder);
  const status=adminNode('p',''),list=adminNode('div'),detail=adminNode('section'),more=adminNode('button',text('Xem thêm khách hàng','More customers'),'secondary');
  status.setAttribute('role','status');more.type='button';more.hidden=true;let cursor=null,sequence=0,detailSequence=0;
  const open=async(id,before=null,append=false)=>{
    const seq=++detailSequence;
    try{
      const data=await adminRequest(`/api/customers/${id}${before?`?before=${before}`:''}`);if(seq!==detailSequence)return;
      if(!append){
        detail.replaceChildren(adminNode('h3',data.customer.name));
        const edit=document.createElement('form'),inputs={};
        for(const [key,label,value,type] of [['fullName',text('Họ tên','Full name'),data.customer.name,'text'],['email','Email',data.customer.email,'email'],['phone',text('Điện thoại','Phone'),data.customer.phone,'tel']]){
          const caption=document.createElement('label'),input=document.createElement('input');caption.textContent=label;input.type=type;input.value=value||'';input.maxLength=key==='phone'?20:100;input.required=key!=='phone';caption.append(input);edit.append(caption);inputs[key]=input;
        }
        const save=adminNode('button',text('Lưu thông tin liên hệ','Save contact details'));save.type='submit';edit.append(save);
        edit.addEventListener('submit',async event=>{event.preventDefault();if(!edit.reportValidity())return;save.disabled=true;try{await adminRequest(`/api/customers/${id}`,'PATCH',Object.fromEntries(Object.entries(inputs).map(([key,input])=>[key,input.value])));status.textContent=text('Đã lưu thông tin khách hàng.','Customer details saved.');await load();}catch(error){status.textContent=adminMessage(error);}finally{save.disabled=false;}});
        detail.append(edit,adminNode('h4',text('Lịch sử yêu cầu hỗ trợ','Support ticket history')),adminNode('ul',undefined,'customer-tickets'));
      }
      detail.querySelector('.customer-more')?.remove();
      for(const ticket of data.tickets){const item=adminNode('li',`TK-${String(ticket.id).padStart(6,'0')} · ${ticket.title} · ${statusLabel(ticket.status)}`);if(window.__vietincareRole==='Supervisor'){const link=adminNode('a',text('Mở yêu cầu','Open ticket'));link.href=`tickets-${en?'en':'vi'}.html#${ticket.id}`;item.append(document.createTextNode(' '),link);}detail.querySelector('.customer-tickets').append(item);}
      if(!data.tickets.length&&!append)detail.append(adminNode('p',text('Khách hàng chưa có yêu cầu.','This customer has no tickets.')));
      if(data.next){const next=adminNode('button',text('Xem thêm lịch sử','More history'),'secondary customer-more');next.type='button';next.addEventListener('click',()=>open(id,data.next,true));detail.append(next);}
    }catch(error){status.textContent=adminMessage(error);}
  };
  const load=async(append=false)=>{const seq=++sequence;try{const params=new URLSearchParams({query:search.value.trim()});if(append&&cursor)params.set('before',cursor);const data=await adminRequest(`/api/customers?${params}`);if(seq!==sequence)return;if(!append)list.replaceChildren();for(const customer of data.customers){const row=adminNode('p'),button=adminNode('button',`${customer.name} · ${customer.email||'—'} · ${customer.phone||'—'}`,'secondary');button.type='button';button.addEventListener('click',()=>open(customer.id));row.append(button);list.append(row);}cursor=data.next;more.hidden=!cursor;if(!list.children.length)status.textContent=text('Không có khách hàng phù hợp.','No matching customers.');}catch(error){status.textContent=adminMessage(error);}};
  form.append(search,submit);form.addEventListener('submit',event=>{event.preventDefault();load();});more.addEventListener('click',()=>load(true));
  section.append(adminNode('h2',text('Quản lý khách hàng','Customer management')),form,status,list,more,detail);panel.append(section);load();
}

function setupSupportQueue(panel) {
  const section=adminNode('section',undefined,'support-queue'), heading=adminNode('h2',text('Chuyển giao hội thoại','Conversation handovers'));
  const status=adminNode('p',text('Đang tải hàng chờ…','Loading queue…'),'admin-status'), list=adminNode('div',undefined,'support-list');
  const load=async()=>{try{const result=await adminRequest('/api/handovers');list.replaceChildren();for(const item of result.handovers){
    const card=adminNode('article',undefined,'support-card');card.append(adminNode('h3',item.title||`CHAT-${item.chatId}`),adminNode('p',`${item.customerName} · ${item.status}`,'meta'),adminNode('p',item.reason));
    if(item.summary)card.append(adminNode('p',item.summary,'support-summary'));
    const actions=adminNode('div',undefined,'support-actions');
    if(item.status==='Chờ tiếp nhận'){const accept=adminNode('button',text('Tiếp nhận','Accept'));accept.type='button';accept.addEventListener('click',async()=>{accept.disabled=true;try{await adminRequest(`/api/handovers/${item.id}/accept`,'POST',{});await load();}catch(error){status.textContent=adminMessage(error);}finally{accept.disabled=false;}});actions.append(accept);}
    if(item.status==='Đã tiếp nhận'&&(item.agentId===window.__vietincareUserId||window.__vietincareRole==='Supervisor')){const summary=adminNode('button',text('Tạo tóm tắt','Create summary'),'secondary');summary.type='button';summary.addEventListener('click',async()=>{summary.disabled=true;try{await adminRequest(`/api/handovers/${item.id}/summary`,'POST',{language:en?'en':'vi'});await load();}catch(error){status.textContent=adminMessage(error);}finally{summary.disabled=false;}});const finish=adminNode('button',text('Kết thúc hỗ trợ','Finish handover'),'secondary');finish.type='button';finish.addEventListener('click',async()=>{finish.disabled=true;try{await adminRequest(`/api/handovers/${item.id}/finish`,'POST',{});await load();}catch(error){status.textContent=adminMessage(error);}finally{finish.disabled=false;}});actions.append(summary,finish);
    if(item.status==='Đã tiếp nhận'&&item.agentId===window.__vietincareUserId){
      const form=document.createElement('form'),input=document.createElement('textarea'),send=adminNode('button',text('Gửi phản hồi','Send reply'));input.required=true;input.maxLength=3000;input.rows=2;input.placeholder=text('Phản hồi cho khách hàng…','Reply to the customer…');form.append(input,send);form.addEventListener('submit',async event=>{event.preventDefault();send.disabled=true;try{await adminRequest(`/api/handovers/${item.id}/messages`,'POST',{content:input.value.trim()});input.value='';status.textContent=text('Đã gửi phản hồi.','Reply sent.');}catch(error){status.textContent=adminMessage(error);}finally{send.disabled=false;}});card.append(form);}}
    card.append(actions);list.append(card);
  }status.textContent=result.handovers.length?'':text('Hàng chờ đang trống.','The queue is empty.');}catch(error){status.textContent=adminMessage(error);}};
  const refresh=adminNode('button',text('Làm mới hàng chờ','Refresh queue'),'secondary');refresh.type='button';refresh.addEventListener('click',load);section.append(heading,refresh,status,list);panel.append(section);load();
}

function setupSystemAdmin(panel) {
  const settingsSection=adminNode('section',undefined,'system-admin'), heading=adminNode('h2',text('Cấu hình hệ thống','System settings')),status=adminNode('p','', 'admin-status'),form=document.createElement('form');form.className='system-settings-form';
  const fields=[['rag.threshold',text('Ngưỡng truy xuất RAG (0–1)','RAG retrieval threshold (0–1)'),'number','0.01'],['ai.timeout_seconds',text('Thời gian chờ AI (5–120 giây)','AI timeout (5–120 seconds)'),'number','1']],inputs={};
  for(const [key,label,type,step] of fields){const wrapper=document.createElement('label');wrapper.textContent=label;const input=document.createElement('input');input.type=type;input.step=step;input.dataset.key=key;wrapper.append(input);form.append(wrapper);inputs[key]=input;}
  const save=adminNode('button',text('Lưu cấu hình','Save settings'));save.type='submit';form.append(save);
  const loadSettings=async()=>{try{const result=await adminRequest('/api/admin/settings');for(const item of result.settings)if(inputs[item.key])inputs[item.key].value=item.value;status.textContent='';}catch(error){status.textContent=adminMessage(error);}};
  form.addEventListener('submit',async event=>{event.preventDefault();save.disabled=true;try{for(const [key,input] of Object.entries(inputs))await adminRequest(`/api/admin/settings/${key}`,'PATCH',{value:Number(input.value)});status.textContent=text('Đã áp dụng cấu hình và ghi nhật ký.','Settings applied and audited.');}catch(error){status.textContent=adminMessage(error);}finally{save.disabled=false;}});
  settingsSection.append(heading,form,status);panel.append(settingsSection);loadSettings();
  const audit=adminNode('section',undefined,'audit-admin'),auditHeading=adminNode('h2',text('Nhật ký hệ thống','Audit logs')),auditStatus=adminNode('p','', 'admin-status'),filters=document.createElement('form'),action=document.createElement('input'),target=document.createElement('input'),search=adminNode('button',text('Tra cứu','Search'));
  filters.className='audit-filters';action.placeholder=text('Hành động, ví dụ SETTING_UPDATE','Action, e.g. SETTING_UPDATE');target.placeholder=text('Đối tượng, ví dụ Handover','Target, e.g. Handover');filters.append(action,target,search);const tableWrap=adminNode('div',undefined,'admin-table-wrap'),table=document.createElement('table');table.className='audit-table';const body=document.createElement('tbody');table.innerHTML=`<thead><tr><th>${text('Thời gian','Time')}</th><th>${text('Người thực hiện','Actor')}</th><th>${text('Hành động','Action')}</th><th>${text('Đối tượng','Target')}</th><th>${text('Chi tiết','Details')}</th></tr></thead>`;table.append(body);tableWrap.append(table);
  const loadLogs=async()=>{try{const params=new URLSearchParams();if(action.value.trim())params.set('action',action.value.trim());if(target.value.trim())params.set('target',target.value.trim());const result=await adminRequest(`/api/admin/audit-logs?${params}`);body.replaceChildren();for(const row of result.logs){const tr=document.createElement('tr');for(const value of [row.createdAt?new Date(row.createdAt).toLocaleString(en?'en-GB':'vi-VN'):'' ,row.actorName||row.actorEmail||'—',row.action,`${row.target||'—'}${row.targetId?` #${row.targetId}`:''}`,row.details||'—'])tr.append(Object.assign(document.createElement('td'),{textContent:value}));body.append(tr);}auditStatus.textContent=result.logs.length?'':text('Không có nhật ký phù hợp.','No matching logs.');}catch(error){auditStatus.textContent=adminMessage(error);}};
  filters.addEventListener('submit',event=>{event.preventDefault();loadLogs();});audit.append(auditHeading,filters,auditStatus,tableWrap);panel.append(audit);loadLogs();
}

const profileSection = document.querySelector('.card.profile');
const showProfile = location.hash === '#profile';
if (profileSection) profileSection.hidden = !showProfile;

byId('refreshOverview').addEventListener('click',loadRecent);
byId('refreshReport').addEventListener('click',loadReport);
(async () => {
  try {
    const user = await window.VietinWorkspace.ready;
    if (showProfile) profileSection?.scrollIntoView({behavior:'smooth',block:'start'});
    byId('name').textContent = user.name; byId('email').textContent = user.email;
    byId('role').textContent = window.VietinWorkspace.roles[user.role];
    byId('welcomeName').textContent = text(`Xin chào, ${user.name}`,`Welcome, ${user.name}`);
    const agent = user.role === 'Agent', supervisor = user.role === 'Supervisor', admin = user.role === 'Admin';
    window.__vietincareUserId=user.id;window.__vietincareRole=user.role;
    byId('reportSection').hidden = !supervisor;
    if (user.role === 'Customer') {
      const link = document.createElement('a'); link.className = 'quick-card'; link.href = `chat-${en ? 'en':'vi'}.html`;
      const icon = document.createElement('span'); icon.className = 'quick-icon cyan'; icon.textContent = '☷'; icon.setAttribute('aria-hidden','true');
      const title = document.createElement('strong'); title.textContent = text('Lịch sử trò chuyện','Conversation history');
      const description = document.createElement('p'); description.textContent = text('Xem lịch sử và hỏi AI khi dịch vụ được kết nối.','Review history and ask AI when the service is connected.');
      link.append(icon,title,description); byId('quickActions').append(link);
    }
    byId('welcomeDescription').textContent = admin ? text('Quản lý tài khoản và theo dõi hệ thống.','Manage your account and monitor the system.') : agent ? text('Tiếp nhận yêu cầu và đồng hành cùng khách hàng trong từng bước xử lý.','Pick up requests and help customers through every step.') : supervisor ? text('Theo dõi tiến độ hỗ trợ và lịch sử xử lý yêu cầu.','Review support progress and ticket activity.') : text('Gửi yêu cầu, theo dõi tiến độ và kết nối với đội ngũ hỗ trợ.','Send a request, follow its progress and connect with support.');
    byId('quickTitle').textContent = agent ? text('Tiếp nhận yêu cầu','Pick up a request') : supervisor ? text('Giám sát yêu cầu','Review requests') : text('Tạo yêu cầu mới','Create a request');
    byId('quickDescription').textContent = agent ? text('Mở hàng chờ và nhận yêu cầu mới.','Open the queue and claim a new ticket.') : supervisor ? text('Xem nội dung, tiến độ và lịch sử xử lý.','Read ticket details, progress and activity.') : text('Mô tả vấn đề để đội ngũ hỗ trợ giúp bạn.','Tell the support team what you need help with.');
    if (agent) byId('quickNew').search = new URLSearchParams({status:'Mới'}).toString();
    byId('ticketsLink').hidden = admin; byId('quickActions').hidden = admin; byId('recentSection').hidden = admin; byId('adminInfo').hidden = !admin;
    if(admin){
      byId('welcomeDescription').textContent=text('Quản lý tài khoản và nội dung hỗ trợ.','Manage accounts and support content.');
      const info = byId('adminInfo'); info.replaceChildren();
      const knowledge = adminNode('section',undefined,'admin-knowledge');
      const heading = adminNode('h2',text('Kho tri thức','Knowledge base'));
      const note = adminNode('p',text('Soạn tài liệu, kiểm tra câu trả lời và xuất bản nguồn cho AI.','Draft documents, test answers and publish sources for AI.'));
      const link = adminNode('a',text('Mở kho tri thức →','Open knowledge base →'),'button');
      link.href = `knowledge-${en?'en':'vi'}.html`; knowledge.append(heading,note,link);
      info.append(knowledge); setupAdminUsers(info);
      setupSystemAdmin(info);
      if (!document.querySelector('link[data-admin-styles]')) {
        const style = document.createElement('link'); style.rel = 'stylesheet'; style.href = '../admin.css'; style.dataset.adminStyles = 'true'; document.head.append(style);
      }
    }
    if(admin||supervisor)setupCustomers(byId('account'));
    if(agent||supervisor)setupSupportQueue(byId('account'));
    byId('account').hidden = false; byId('accountStatus').textContent = '';
    if (!admin) await loadRecent();
    if (supervisor) await loadReport();
  } catch { byId('accountStatus').textContent = text('Không tải được tài khoản. Vui lòng tải lại trang.','Unable to load your account. Please reload.'); }
})();
