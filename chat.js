(() => {
  const en = document.documentElement.lang === 'en', t = (vi,eng) => en ? eng : vi, $ = id => document.getElementById(id);
  let user, selected = null, nextChats = null, nextMessages = null, busy = false, detailSequence = 0, listSequence = 0, assistantReady = false;
  const retryKeys = new Map();
  const errors = {INVALID_INPUT:t('Nhập từ 1 đến 3.000 ký tự.','Enter between 1 and 3,000 characters.'),CHAT_NOT_FOUND:t('Không tìm thấy hội thoại hoặc bạn không có quyền xem.','Conversation not found or access unavailable.'),CHAT_READ_ONLY:t('Hội thoại chỉ được xem. Hãy làm mới hoặc tạo hội thoại mới.','This conversation is read-only. Refresh or start a new one.'),FORBIDDEN:t('Lịch sử trò chuyện hiện dành cho tài khoản khách hàng.','Conversation history is currently available to customers.'),REQUEST_KEY_CONFLICT:t('Nội dung thử lại không khớp. Hãy tải lại trang.','Retry content does not match. Please reload.')};
  function notice(message,error=false) { $('notice').textContent=message; $('notice').classList.toggle('error',error); }
  function fail(e) { notice(errors[e.message] || t('Chưa xác nhận được kết quả. Nội dung vẫn giữ trong ô nhập; bạn có thể thử lại mà không tạo trùng.','The result could not be confirmed. Your text remains in the input; retrying will not create a duplicate.'),true); }
  function node(tag,text,cls) { const el=document.createElement(tag); if(text!==undefined) el.textContent=text; if(cls) el.className=cls; return el; }
  function date(value) { return value ? new Intl.DateTimeFormat(en?'en-GB':'vi-VN',{timeZone:'Asia/Ho_Chi_Minh',dateStyle:'short',timeStyle:'short'}).format(new Date(value)) : ''; }
  async function api(path,body) {
    let storageKey,key;
    if(body!==undefined) {
      const bytes=new TextEncoder().encode(JSON.stringify([user.id,path,body]));
      storageKey='vietincare-chat-'+[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
      try { key=sessionStorage.getItem(storageKey); } catch { /* Optional storage. */ }
      key ||= retryKeys.get(storageKey) || crypto.randomUUID(); retryKeys.set(storageKey,key);
      try { sessionStorage.setItem(storageKey,key); } catch { /* Keep an in-memory retry key. */ }
    }
    const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),70000);
    try {
      const response=await fetch(path,{credentials:'same-origin',cache:'no-store',signal:controller.signal,...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Vietincare-Request':'1','Idempotency-Key':key},body:JSON.stringify(body)})});
      if(response.status===401) { location.replace(`login-${en?'en':'vi'}.html`); throw new Error('UNAUTHENTICATED'); }
      const data=await response.json();
      if(storageKey && (response.ok || response.status<500)) { retryKeys.delete(storageKey); try { sessionStorage.removeItem(storageKey); } catch { /* Optional storage. */ } }
      if(!response.ok) throw new Error(data.error); return data;
    } finally { clearTimeout(timer); }
  }
  function controls(disabled) { document.querySelectorAll('.page button,.page textarea').forEach(el=>el.disabled=disabled); }
  async function action(work) { if(busy) return; busy=true; controls(true); try { await work(); } catch(e) { fail(e); } finally { busy=false; controls(false); } }
  function markSelected() { document.querySelectorAll('.chat-link').forEach(a=>a.setAttribute('aria-current',String(Number(a.dataset.id)===selected))); }
  function assistantState(status, provider) {
    assistantReady=status==='ready';const box=document.querySelector('.availability'),link=box.querySelector('a');
    box.replaceChildren(node('span',assistantReady?t(`AI trả lời theo nguồn đã xuất bản. Câu hỏi và đoạn nguồn liên quan được gửi đến ${provider==='gemini'?'Google Gemini':'OpenAI'}. Hãy nêu đầy đủ câu hỏi; chưa có nhân viên trực trong hội thoại.`,`AI answers from published sources. Your question and relevant source excerpts are sent to ${provider==='gemini'?'Google Gemini':'OpenAI'}. Ask a complete question; live agent chat is not available.`):t('AI chưa được kết nối. Tin nhắn được lưu vào lịch sử, chưa có phản hồi tự động.','AI is not connected. Messages are saved to history without automated replies.')),link);
    $('sendMessage').textContent=assistantReady?t('Gửi và hỏi AI','Send and ask AI'):t('Lưu tin nhắn','Save message');
  }
  async function askAI(messageId) {
    notice(t('Tin nhắn đã lưu. Đang tìm nguồn và chờ AI trả lời…','Message saved. Finding sources and waiting for AI…'));
    try { await api(`/api/chats/${selected}/messages/${messageId}/answer`,{language:en?'en':'vi'});await loadDetail(selected);notice(t('Đã lưu phản hồi. Bạn có thể xem nguồn bên dưới câu trả lời.','Response saved. You can review its sources below.')); }
    catch(e) { try{await loadDetail(selected);}catch{}const messages={AI_BUSY:t('AI đang xử lý. Chờ một lát rồi thử lại.','AI is busy. Wait a moment and retry.'),AI_NOT_CONFIGURED:t('AI chưa được cấu hình trên backend.','AI is not configured on the backend.'),KNOWLEDGE_CHANGED:t('Nguồn vừa thay đổi. Hãy thử hỏi lại AI.','Sources changed. Retry the AI response.'),CHAT_READ_ONLY:t('Hội thoại đã kết thúc.','The conversation has ended.')};notice(t('Tin nhắn đã được lưu. ','Your message is saved. ')+(messages[e.message]||t('Chưa lấy được phản hồi AI. Nhấn “Thử hỏi AI” bên dưới tin nhắn để thử lại, không cần gửi lại nội dung.','AI could not respond. Select “Retry AI” below the message; you do not need to send your text again.')),true); }
  }
  async function loadList(append=false) {
    const sequence=++listSequence; $('listStatus').textContent=t('Đang tải…','Loading…');
    try {
      const data=await api('/api/chats'+(append&&nextChats?`?before=${nextChats}`:'')); if(sequence!==listSequence)return;
      assistantState(data.assistantStatus, data.aiProvider);
      if(!append) $('chatList').replaceChildren();
      for(const chat of data.chats) {
        const li=node('li'),a=node('a',undefined,'chat-link'); a.href=`#${chat.id}`; a.dataset.id=chat.id;
        a.append(node('strong',chat.title||t(`Hội thoại #${chat.id}`,`Conversation #${chat.id}`)),node('small',`${date(chat.createdAt)} · ${chat.closedAt?t('Đã kết thúc','Ended'):t('Đang mở','Open')}`)); li.append(a); $('chatList').append(li);
      }
      nextChats=data.next; $('moreChats').hidden=!nextChats; markSelected(); $('listStatus').textContent=data.chats.length||append?'':t('Chưa có hội thoại. Lưu tin nhắn đầu tiên để bắt đầu.','No conversations yet. Save your first message to start.');
    } catch(e) { if(sequence===listSequence)$('listStatus').textContent=t('Chưa tải được lịch sử. Nhấn Làm mới.','Unable to load history. Select Refresh.'); throw e; }
  }
  async function loadDetail(id,older=false) {
    const sequence=++detailSequence; selected=id; markSelected(); $('chatForm').hidden=true; $('closeChat').hidden=true; $('detailStatus').textContent=t('Đang tải hội thoại…','Loading conversation…');
    if(!older) { $('messages').replaceChildren(); $('olderMessages').hidden=true; }
    try {
      const data=await api(`/api/chats/${id}`+(older&&nextMessages?`?before=${nextMessages}`:'')); if(sequence!==detailSequence)return;
      assistantState(data.assistantStatus, data.aiProvider);
      const chat=data.chat, readOnly=!!chat.closedAt||chat.status!=='Đang hoạt động';
      $('chatTitle').textContent=chat.title||t('Hội thoại','Conversation'); $('chatCode').textContent=`CHAT-${id}`; $('chatState').textContent=readOnly?t('Chỉ xem','Read-only'):t('Đang mở','Open');
      const fragment=document.createDocumentFragment();
      for(const message of data.messages) {
        const own=message.userId===user.id, card=node('article',undefined,`message ${own?'mine':''}`);
        card.append(node('strong',own?t('Bạn','You'):message.sender==='AI'?'AI':t('Người gửi trong lịch sử','History sender')),node('p',message.content),node('small',date(message.createdAt)));
        if(message.sources?.length){const details=node('details');details.append(node('summary',t('Nguồn tham khảo','Sources')));for(const s of message.sources){details.append(node('strong',`${s.title} · KB-${s.documentId} / #${s.chunkId}`),node('p',s.content));}card.append(details);}
        if(own&&!readOnly&&assistantReady&&!data.messages.some(m=>m.replyTo===message.id)){const retry=node('button',t('Thử hỏi AI','Retry AI'),'secondary');retry.type='button';retry.disabled=busy;retry.addEventListener('click',()=>action(()=>askAI(message.id)));card.append(retry);}
        fragment.append(card);
      }
      if(older)$('messages').prepend(fragment); else $('messages').replaceChildren(fragment);
      nextMessages=data.next; $('olderMessages').hidden=!nextMessages; $('chatForm').hidden=readOnly; $('closeChat').hidden=readOnly; $('closedNote').hidden=!readOnly; $('detailStatus').textContent=''; $('language').hash=id;
    } catch(e) { if(sequence===detailSequence)$('detailStatus').textContent=t('Chưa tải được hội thoại. Nhấn Làm mới để thử lại.','Unable to load this conversation. Select Refresh to retry.'); throw e; }
  }
  function fresh() { ++detailSequence; selected=null; nextMessages=null; history.replaceState(null,'',location.pathname); $('language').hash=''; $('chatTitle').textContent=t('Hội thoại mới','New conversation'); $('chatCode').textContent=''; $('chatState').textContent=''; $('messages').replaceChildren(); $('detailStatus').textContent=t('Hội thoại sẽ được tạo khi bạn lưu tin nhắn đầu tiên.','A conversation is created when you save your first message.'); $('chatForm').hidden=false; $('closedNote').hidden=true; $('closeChat').hidden=true; $('olderMessages').hidden=true; $('messageInput').value=''; markSelected(); }
  function hashId() { const value=location.hash.slice(1); return /^[1-9]\d{0,9}$/.test(value)&&Number(value)<=2147483647?Number(value):null; }
  $('chatList').addEventListener('click',e=>{ const link=e.target.closest('a'); if(!link)return; e.preventDefault(); if(busy)return; $('messageInput').value=''; history.replaceState(null,'',link.hash); loadDetail(Number(link.dataset.id)).catch(fail); });
  $('newChat').addEventListener('click',()=>{ if(!busy){fresh();notice('');$('messageInput').focus();} });
  $('refreshChats').addEventListener('click',()=>action(async()=>{ await loadList(); if(selected) await loadDetail(selected); notice(''); }));
  $('moreChats').addEventListener('click',()=>action(()=>loadList(true)));
  $('olderMessages').addEventListener('click',()=>action(()=>loadDetail(selected,true)));
  $('chatForm').addEventListener('submit',e=>{ e.preventDefault(); if(!$('chatForm').reportValidity())return; action(async()=>{
    const content=$('messageInput').value.trim(); if(!content)throw new Error('INVALID_INPUT'); notice(t('Đang lưu tin nhắn…','Saving message…'));
    const result=await api(selected?`/api/chats/${selected}/messages`:'/api/chats',{content});
    selected=result.id; $('messageInput').value=''; history.replaceState(null,'',`#${selected}`); notice(t('Đã lưu tin nhắn.','Message saved.'));
    try { await loadDetail(selected); await loadList(); if(assistantReady)await askAI(result.messageId); } catch { notice(t('Tin nhắn đã lưu, nhưng chưa tải lại được lịch sử. Nhấn Làm mới.','Message saved, but history could not be refreshed. Select Refresh.'),true); }
  }); });
  $('closeChat').addEventListener('click',()=>action(async()=>{ notice(t('Đang kết thúc…','Ending conversation…')); await api(`/api/chats/${selected}/close`,{}); $('chatForm').hidden=true; $('closeChat').hidden=true; $('closedNote').hidden=false; notice(t('Đã kết thúc hội thoại.','Conversation ended.')); try { await loadDetail(selected); await loadList(); } catch { notice(t('Đã kết thúc hội thoại, nhưng chưa tải lại được lịch sử. Nhấn Làm mới.','Conversation ended, but history could not be refreshed. Select Refresh.'),true); } }));
  window.addEventListener('hashchange',()=>{ if(!user||busy)return; const id=hashId(); if(id)loadDetail(id).catch(fail); else fresh(); });
  const initialId=hashId();
  (async()=>{ try { user=await window.VietinWorkspace.ready; if(user.role!=='Customer')throw new Error('FORBIDDEN'); $('chatWorkspace').hidden=false; notice(''); await action(async()=>{ fresh(); if(initialId){history.replaceState(null,'',`#${initialId}`);await loadDetail(initialId);} await loadList(); }); } catch(e){fail(e);} })();
})();
