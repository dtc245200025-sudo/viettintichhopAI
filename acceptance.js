/* Shared VI/EN acceptance workflows: presence, supervisor alerts and chat CSAT. */
(() => {
  const en = document.documentElement.lang === 'en';
  const tr = (vi, english) => en ? english : vi;
  const el = (tag, text) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; return n; };
  async function api(path, body) {
    const r = await fetch(path, {method: body === undefined ? 'GET' : 'POST', credentials:'same-origin', cache:'no-store',
      headers: body === undefined ? {} : {'Content-Type':'application/json','X-Vietincare-Request':'1','Idempotency-Key':crypto.randomUUID()},
      body: body === undefined ? undefined : JSON.stringify(body)});
    const data = await r.json(); if (!r.ok) throw new Error(data.error || 'SERVICE_UNAVAILABLE'); return data;
  }
  window.VietinWorkspace.ready.then(user => {
    if (user.role === 'Agent') {
      const status = el('small'); status.id = 'presenceStatus'; document.querySelector('.top-actions').append(status);
      const pulse = () => api('/api/presence', {}).then(() => {status.textContent=tr('Sẵn sàng nhận hỗ trợ','Available for support');})
        .catch(() => {status.textContent=tr('Chưa xác nhận trạng thái trực tuyến','Online status unavailable');});
      pulse(); const timer=setInterval(pulse,45000); window.addEventListener('pagehide',()=>clearInterval(timer),{once:true});
    }
    if (user.role === 'Supervisor') {
      const panel=el('section'); panel.className='card'; panel.id='supervisorAutomation';
      panel.append(el('h2',tr('Cảnh báo và hàng chờ tự động','Alerts and automation queue')));
      const status=el('p'), list=el('ul'), queue=el('ul'), refresh=el('button',tr('Làm mới cảnh báo','Refresh alerts'));
      panel.append(status,list,el('h3',tr('Ticket cần kiểm tra','Tickets requiring review')),queue,refresh);
      document.querySelector('main').append(panel);
      const load=async()=>{try{
        const [a,q]=await Promise.all([api('/api/supervisor/alerts'),api('/api/supervisor/automation')]);
        list.replaceChildren(); queue.replaceChildren(); status.textContent=a.alerts.length?tr('Cần ưu tiên hỗ trợ khách hàng.','Customer attention required.'):tr('Không có cảnh báo mới.','No new alerts.');
        for(const row of a.alerts){const li=el('li',`${row.source} #${row.sourceId}: ${tr('Bức xúc cao','High distress')} `);
          const button=el('button',tr('Đã tiếp nhận','Acknowledge'));button.type='button';button.onclick=async()=>{button.disabled=true;try{await api(`/api/supervisor/alerts/${row.id}/acknowledge`,{});await load();}catch{button.disabled=false;status.textContent=tr('Chưa lưu được. Hãy thử lại.','Could not save. Please retry.');}};li.append(button);list.append(li);}
        for(const row of q.tickets){const li=el('li',`#${row.id} · ${row.title} · ${row.state} `),button=el('button',tr('Thử phân loại lại','Retry classification'));button.type='button';
          button.onclick=async()=>{button.disabled=true;try{await api(`/api/tickets/${row.id}/automation/retry`,{});await load();}catch{button.disabled=false;status.textContent=tr('Chưa thực hiện được.','Unable to retry.');}};li.append(button);queue.append(li);}
      }catch{status.textContent=tr('Chưa tải được cảnh báo. Nhấn Làm mới.','Unable to load alerts. Select Refresh.');}};
      refresh.type='button';refresh.onclick=load;load();const timer=setInterval(load,30000);window.addEventListener('pagehide',()=>clearInterval(timer),{once:true});
    }
    if(user.role==='Customer' && /\/chat-/.test(location.pathname)) {
      const panel=el('section');panel.className='card';panel.id='chatEvaluation';panel.hidden=true;
      const heading=el('h2',tr('Đánh giá hỗ trợ','Rate this support')),form=el('form'),rating=el('select'),comment=el('textarea'),save=el('button',tr('Gửi đánh giá','Submit rating')),status=el('p');
      rating.required=true;rating.setAttribute('aria-label',tr('Số sao','Stars')); for(let i=5;i>=1;i--){const o=el('option',`${i} ★`);o.value=i;rating.append(o);}
      comment.maxLength=1000;comment.setAttribute('aria-label',tr('Nhận xét','Comment'));save.type='submit';form.append(rating,comment,save);panel.append(heading,form,status);document.querySelector('main').append(panel);
      let shown=null,timer=null,sequence=0;
      async function refresh(){const n=++sequence,id=location.hash.slice(1);panel.hidden=true;if(!/^[1-9]\d*$/.test(id))return;
        try{const data=await api(`/api/chats/${id}`);if(n!==sequence||!data.chat.closedAt)return;panel.hidden=false;form.hidden=!!data.evaluation;status.textContent=data.evaluation?tr('Đã ghi nhận đánh giá của bạn.','Your rating is saved.'):'';
          if(shown!==id){shown=id;clearTimeout(timer);timer=setTimeout(()=>{panel.hidden=true;},60000);}
        }catch{panel.hidden=true;}}
      form.onsubmit=async e=>{e.preventDefault();clearTimeout(timer);save.disabled=true;try{await api(`/api/chats/${location.hash.slice(1)}/evaluation`,{stars:Number(rating.value),comment:comment.value});form.hidden=true;status.textContent=tr('Cảm ơn bạn đã đánh giá.','Thank you for your feedback.');}catch{status.textContent=tr('Chưa lưu được đánh giá. Vui lòng thử lại.','Could not save the rating. Please retry.');}finally{save.disabled=false;}};
      const state=document.getElementById('chatState');if(state)new MutationObserver(refresh).observe(state,{childList:true,characterData:true,subtree:true});window.addEventListener('hashchange',refresh);refresh();
      const ticketLink=el('a',tr('Tạo Ticket từ hội thoại này','Create a ticket from this conversation'));ticketLink.id='chatTicketLink';
      const updateLink=()=>{const id=location.hash.slice(1);ticketLink.hidden=!/^[1-9]\d*$/.test(id);ticketLink.href=`tickets-${en?'en':'vi'}.html?chat=${encodeURIComponent(id)}`;};
      document.querySelector('main').append(ticketLink);window.addEventListener('hashchange',updateLink);if(state)new MutationObserver(updateLink).observe(state,{childList:true,characterData:true,subtree:true});updateLink();
    }
  }).catch(()=>{});
})();
