import {createHash} from 'node:crypto';
import {connection,query,transaction} from './db.js';
import {HttpError} from './http-error.js';
import {cosine,validVector} from './openai.js';
import {numericId,parseVector} from './knowledge.js';
const hash=value=>createHash('sha256').update(value).digest('hex');
const missing=language=>language==='en'?'I could not find enough published information to answer this question. Please create a support ticket for help.':'Chưa tìm thấy đủ thông tin đã xuất bản để trả lời câu hỏi này. Bạn có thể tạo yêu cầu để được nhân viên hỗ trợ.';
export function installRagRoutes(app,pool,auth,role,ai,settings){
 let active=0;
 app.post('/api/chats/:id/messages/:messageId/answer',auth,role('Customer'),async(req,res)=>{
  const id=numericId(req.params.id),messageId=numericId(req.params.messageId),language=req.body?.language==='en'?'en':'vi';
  // Verify ownership before consuming API capacity or taking a generation lock.
  const [source]=await query(pool,"SELECT m.NoiDung content FROM Message m JOIN ChatSession s ON s.MaSession=m.MaSession WHERE m.MaMessage=? AND m.MaSession=? AND m.MaUser=? AND m.NguoiGui='Customer' AND s.MaKH=?",[messageId,id,req.user.MaUser,req.user.MaKH]);if(!source)throw new HttpError(404,'CHAT_NOT_FOUND');
  if(active>=4)throw new HttpError(429,'AI_BUSY');active++;
  let c,locked=false;const lock=`vc:rag:${hash(settings.db.database).slice(0,16)}:${messageId}`;
  try{
   c=await connection(pool);const [[got]]=await c.execute('SELECT GET_LOCK(?,0) ok',[lock]);locked=Number(got.ok)===1;if(!locked)throw new HttpError(409,'AI_BUSY');
   const [[previous]]=await c.execute('SELECT MaMessage id,AnswerStatus status FROM Message WHERE ReplyTo=?',[messageId]);if(previous)return res.json({messageId:previous.id,status:previous.status,replayed:true});
   const [[chat]]=await c.execute('SELECT TrangThai,ThoiGianKetThuc FROM ChatSession WHERE MaSession=?',[id]);if(chat?.TrangThai!=='Đang hoạt động'||chat.ThoiGianKetThuc)throw new HttpError(409,'CHAT_READ_ONLY');
   if(!ai.enabled)throw new HttpError(503,'AI_NOT_CONFIGURED');
   const rows=await query(pool,"SELECT k.MaChunk id,k.NoiDung content,k.Embedding embedding,k.TenMoHinh model,k.SoChieu dimensions,b.MaKB documentId,b.TieuDe title,b.ContentVersion version FROM KnowledgeChunk k JOIN KnowledgeBase b ON b.MaKB=k.MaKB WHERE b.TrangThai='Đã xuất bản' AND k.TenMoHinh=? AND k.SoChieu=? ORDER BY k.MaChunk LIMIT 1001",[ai.model,ai.dimensions]);
   if(rows.length>1000)throw new HttpError(503,'KNOWLEDGE_LIMIT');
   let sources=[],answer={text:'',sourceIds:[]};
   if(rows.length){const [vector]=await ai.embed([source.content], 'query');if(!validVector(vector,ai.dimensions))throw new HttpError(503,'AI_INVALID_OUTPUT');sources=rows.map(r=>({...r,score:cosine(vector,parseVector(r.embedding)||[])})).filter(r=>r.score>=settings.ai.threshold).sort((a,b)=>b.score-a.score||a.id-b.id).slice(0,3);if(sources.length)answer=await ai.answer(source.content,sources,language);}
   if(typeof answer.text!=='string'||!Array.isArray(answer.sourceIds)||answer.sourceIds.some(s=>!sources.some(x=>x.id===s)))throw new HttpError(503,'AI_INVALID_OUTPUT');
   const used=answer.text&&answer.sourceIds.length?sources.filter(s=>answer.sourceIds.includes(s.id)):[];
   const text=used.length?answer.text:missing(language),status=used.length?'answered':'no_sources';
   const result=await transaction(pool,async tx=>{
    const [[owner]]=await tx.execute("SELECT u.TrangThai,r.TenRole,c.MaKH FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole JOIN Customer c ON c.MaUser=u.MaUser AND c.TrangThai=1 WHERE u.MaUser=? FOR UPDATE",[req.user.MaUser]);if(!owner?.TrangThai||owner.TenRole!=='Customer'||owner.MaKH!==req.user.MaKH)throw new HttpError(403,'FORBIDDEN');
    const [[current]]=await tx.execute('SELECT TrangThai,ThoiGianKetThuc FROM ChatSession WHERE MaSession=? AND MaKH=? FOR UPDATE',[id,owner.MaKH]);if(current?.TrangThai!=='Đang hoạt động'||current.ThoiGianKetThuc)throw new HttpError(409,'CHAT_READ_ONLY');
    for(const s of [...sources].sort((a,b)=>a.documentId-b.documentId)){const [[doc]]=await tx.execute('SELECT TrangThai,ContentVersion FROM KnowledgeBase WHERE MaKB=? FOR SHARE',[s.documentId]);if(doc?.TrangThai!=='Đã xuất bản'||doc.ContentVersion!==s.version)throw new HttpError(409,'KNOWLEDGE_CHANGED');}
    const [result]=await tx.execute("INSERT INTO Message(MaSession,NguoiGui,NoiDung,ReplyTo,AnswerStatus) VALUES(?,'AI',?,?,?)",[id,text,messageId,status]);
    for(const s of used)await tx.execute('INSERT INTO MessageSource(MaMessage,MaChunk,TieuDeNguon,NoiDungNguon,SourceHash) VALUES(?,?,?,?,?)',[result.insertId,s.id,s.title,s.content,hash(s.content)]);
    await tx.execute("INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong) VALUES(?,'RAG_ANSWER','Message',?)",[req.user.MaUser,result.insertId]);return{messageId:result.insertId,status};
   });res.json(result);
  }finally{if(locked)await c.execute('SELECT RELEASE_LOCK(?)',[lock]).catch(()=>{});if(c)c.release();active--;}
 });
}
