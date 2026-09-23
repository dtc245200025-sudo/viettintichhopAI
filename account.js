const en = document.documentElement.lang === 'en';
const text = (vi, english) => en ? english : vi;
const byId = id => document.getElementById(id);
const statusLabels = {'Mới':'New','Đang xử lý':'In progress','Đã giải quyết':'Resolved','Đã đóng':'Closed'};
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
byId('refreshOverview').addEventListener('click',loadRecent);
(async () => {
  try {
    const user = await window.VietinWorkspace.ready;
    byId('name').textContent = user.name; byId('email').textContent = user.email;
    byId('role').textContent = window.VietinWorkspace.roles[user.role];
    byId('welcomeName').textContent = text(`Xin chào, ${user.name}`,`Welcome, ${user.name}`);
    const agent = user.role === 'Agent', supervisor = user.role === 'Supervisor', admin = user.role === 'Admin';
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
    if(admin){byId('welcomeDescription').textContent=text('Chuẩn bị và xuất bản nguồn trả lời cho trợ lý AI.','Prepare and publish answer sources for the AI assistant.');const info=byId('adminInfo');info.replaceChildren();const heading=document.createElement('h2');heading.textContent=text('Kho tri thức','Knowledge base');const note=document.createElement('p');note.textContent=text('Soạn tài liệu, kiểm tra câu trả lời và xuất bản nguồn cho AI. Quản lý người dùng và báo cáo đang được xây dựng.','Draft documents, test answers and publish sources for AI. User management and reports are under development.');const link=document.createElement('a');link.className='button';link.href=`knowledge-${en?'en':'vi'}.html`;link.textContent=text('Mở kho tri thức →','Open knowledge base →');info.append(heading,note,link);}
    byId('account').hidden = false; byId('accountStatus').textContent = '';
    if (!admin) await loadRecent();
  } catch { byId('accountStatus').textContent = text('Không tải được tài khoản. Vui lòng tải lại trang.','Unable to load your account. Please reload.'); }
})();
