(() => {
  const en = document.documentElement.lang === 'en';
  const tr = (vi, english) => en ? english : vi;
  const lang = en ? 'en' : 'vi';
  const knowledgePage = location.pathname.includes('knowledge-');
  const chatPage = location.pathname.includes('chat-');
  const ticketPage = location.pathname.includes('tickets-');
  const main = document.querySelector('main');
  main.classList.add('page');
  const oldNav = main.querySelector('nav');
  const language = oldNav.lastElementChild;
  language.className = 'language';
  oldNav.remove();
  const shell = document.createElement('div');
  shell.className = 'app-area';
  const sidebar = document.createElement('aside');
  sidebar.className = 'sidebar'; sidebar.id = 'navigation';
  sidebar.innerHTML = `<a class="brand" href="account-${lang}.html"><span class="brand-mark">V</span><span>VietinCare <b>AI</b><small>${tr('Đồng hành cùng bạn','Here to support you')}</small></span></a><p class="nav-caption">${tr('KHÔNG GIAN LÀM VIỆC','YOUR WORKSPACE')}</p><nav aria-label="${tr('Điều hướng chính','Main navigation')}"><a class="side-link ${(ticketPage || chatPage || knowledgePage) ? '' : 'active'}" href="account-${lang}.html" ${(ticketPage || chatPage || knowledgePage) ? '' : 'aria-current="page"'}><span aria-hidden="true">▦</span>${tr('Tổng quan','Overview')}</a><a data-ticket-nav class="side-link ${ticketPage ? 'active' : ''}" href="tickets-${lang}.html" ${ticketPage ? 'aria-current="page"' : ''}><span aria-hidden="true">▤</span>${tr('Yêu cầu hỗ trợ','Support tickets')}</a><a data-chat-nav hidden class="side-link ${chatPage ? 'active' : ''}" href="chat-${lang}.html" ${chatPage ? 'aria-current="page"' : ''}><span aria-hidden="true">☷</span>${tr('Lịch sử trò chuyện','Conversations')}</a><a data-knowledge-nav hidden class="side-link ${knowledgePage ? 'active' : ''}" href="knowledge-${lang}.html" ${knowledgePage ? 'aria-current="page"' : ''}><span aria-hidden="true">▣</span>${tr('Kho tri thức','Knowledge base')}</a><a class="side-link" href="index-${lang}.html"><span aria-hidden="true">⌂</span>${tr('Trang chủ','Home')}</a></nav><div class="sidebar-note"><strong>VietinCare AI</strong><p>${tr('Kết nối khách hàng với đội ngũ hỗ trợ.','Connecting customers with our support team.')}</p><small>${tr('Báo cáo và chuyển giao chat đang được xây dựng.','Reports and live chat handover are under development.')}</small></div>`;
  const topbar = document.createElement('div'); topbar.className = 'topbar';
  topbar.innerHTML = `<button class="menu-toggle secondary" type="button" aria-controls="navigation" aria-expanded="false" aria-label="${tr('Mở điều hướng','Open navigation')}">☰</button><span class="breadcrumb">${tr('Không gian làm việc','Workspace')} <b>/ ${knowledgePage ? tr('Kho tri thức','Knowledge base') : chatPage ? tr('Hội thoại','Conversations') : ticketPage ? tr('Yêu cầu hỗ trợ','Support tickets') : tr('Tổng quan','Overview')}</b></span><div class="top-actions"><span class="avatar" aria-hidden="true">V</span><span class="identity"></span></div>`;
  const actions = topbar.querySelector('.top-actions'); actions.prepend(language);
  let logout = document.getElementById('logout');
  if (!logout) { logout = document.createElement('button'); logout.id = 'logout'; logout.type = 'button'; logout.textContent = tr('Đăng xuất','Sign out'); }
  logout.className = 'secondary'; actions.append(logout);
  const backdrop = document.createElement('button'); backdrop.className = 'nav-backdrop'; backdrop.hidden = true; backdrop.setAttribute('aria-label',tr('Đóng điều hướng','Close navigation'));
  document.body.prepend(sidebar, backdrop, shell); shell.append(topbar, main);
  const toggle = topbar.querySelector('.menu-toggle');
  const media = matchMedia('(max-width: 800px)');
  function menu(open) { document.body.classList.toggle('nav-open',open); toggle.setAttribute('aria-expanded',String(open)); sidebar.inert = media.matches && !open; backdrop.hidden = !open; shell.inert = open; if(open) sidebar.querySelector('a').focus(); }
  toggle.addEventListener('click',() => menu(toggle.getAttribute('aria-expanded') !== 'true'));
  backdrop.addEventListener('click',() => { menu(false); toggle.focus(); });
  document.addEventListener('keydown',e => { if(e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') { menu(false); toggle.focus(); } });
  media.addEventListener('change',() => menu(false)); menu(false);
  logout.addEventListener('click',async () => {
    logout.disabled = true;
    try {
      const response = await fetch('/api/auth/logout',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Vietincare-Request':'1'},body:'{}'});
      if (!response.ok && response.status !== 401) throw new Error();
      location.replace(`login-${lang}.html`);
    } catch { (document.getElementById('accountStatus') || document.getElementById('notice')).textContent = tr('Chưa đăng xuất được. Vui lòng thử lại.','Unable to sign out. Please retry.'); logout.disabled = false; }
  });
  const roles = {Customer:tr('Khách hàng','Customer'),Agent:tr('Nhân viên hỗ trợ','Support agent'),Supervisor:tr('Quản lý hỗ trợ','Supervisor'),Admin:tr('Quản trị','Administrator')};
  const ready = fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'}).then(async response => {
    if (response.status === 401) { location.replace(`login-${lang}.html`); throw new Error('UNAUTHENTICATED'); }
    if (!response.ok) throw new Error('SERVICE_UNAVAILABLE');
    const {user} = await response.json();
    topbar.querySelector('.identity').textContent = roles[user.role];
    topbar.querySelector('.avatar').textContent = user.name.trim().split(/\s+/).slice(-2).map(s => Array.from(s)[0]).join('').toUpperCase();
    sidebar.querySelector('[data-knowledge-nav]').hidden = user.role !== 'Admin';
    sidebar.querySelector('[data-chat-nav]').hidden = user.role !== 'Customer';
    sidebar.querySelector('[data-ticket-nav]').hidden = user.role === 'Admin';
    return user;
  });
  ready.catch(() => {});
  window.VietinWorkspace = {ready,roles};
})();
