import {createHash} from 'node:crypto';
import {query,transaction} from './db.js';
import {HttpError} from './http-error.js';
import {splitKnowledge,validVector,cosine} from './openai.js';
export const kbFields='MaKB id,TieuDe title,NoiDung content,TrangThai status,ContentVersion version,ReplacesId replacesId,NgayTao createdAt';
export function numericId(value){if(!/^[1-9]\d{0,9}$/.test(String(value))||Number(value)>2147483647)throw new HttpError(400,'INVALID_INPUT');return Number(value);}
function text(value,max){if(typeof value!=='string'||!value.trim()||value.trim().length>max)throw new HttpError(400,'INVALID_INPUT');return value.trim();}
export function parseVector(value){try{return typeof value==='string'?JSON.parse(value):value;}catch{return null;}}
async function audit(c,req,id,action){await c.execute("INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,'KnowledgeBase',?,?)",[req.user.MaUser,action,id,req.ip]);}
async function mutate(pool,req,payload,work){
 const key=req.get('Idempotency-Key');if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(key||''))throw new HttpError(400,'REQUEST_KEY_REQUIRED');
 const hash=createHash('sha256').update(JSON.stringify([req.path,payload])).digest('hex');
 return transaction(pool,async c=>{
  const [[actor]]=await c.execute('SELECT u.TrangThai,r.TenRole FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole WHERE u.MaUser=? FOR UPDATE',[req.user.MaUser]);if(!actor?.TrangThai||actor.TenRole!=='Admin')throw new HttpError(403,'FORBIDDEN');
  const [[old]]=await c.execute('SELECT RequestHash,Result FROM KnowledgeRequest WHERE MaUser=? AND RequestKey=?',[req.user.MaUser,key]);
  if(old){if(old.RequestHash!==hash)throw new HttpError(409,'REQUEST_KEY_CONFLICT');return {...(typeof old.Result==='string'?JSON.parse(old.Result):old.Result),replayed:true};}
  const result=await work(c);await c.execute('INSERT INTO KnowledgeRequest(MaUser,RequestKey,RequestHash,Result) VALUES(?,?,?,?)',[req.user.MaUser,key,hash,JSON.stringify(result)]);return result;
 });
}
async function document(c,id,version){const [[row]]=await c.execute(`SELECT ${kbFields} FROM KnowledgeBase WHERE MaKB=? FOR UPDATE`,[id]);if(!row)throw new HttpError(404,'KNOWLEDGE_NOT_FOUND');if(row.version!==version)throw new HttpError(409,'KNOWLEDGE_CHANGED');return row;}
async function chunks(c,id){return (await c.execute('SELECT MaChunk id,ThuTu position,NoiDung content,Embedding embedding,TenMoHinh model,SoChieu dimensions FROM KnowledgeChunk WHERE MaKB=? ORDER BY ThuTu',[id]))[0];}
function indexed(rows,content,ai){const texts=splitKnowledge(content||'');return rows.length>0&&rows.length===texts.length&&rows.every((r,i)=>r.content===texts[i]&&r.model===ai.model&&r.dimensions===ai.dimensions&&validVector(parseVector(r.embedding),ai.dimensions));}
export function installKnowledgeRoutes(app,pool,auth,role,ai){
 app.use('/api/knowledge',auth,role('Admin'));
 app.get('/api/knowledge',async(req,res)=>{const before=req.query.before?numericId(req.query.before):null;const rows=await query(pool,`SELECT MaKB id,TieuDe title,TrangThai status,ContentVersion version,ReplacesId replacesId FROM KnowledgeBase ${before?'WHERE MaKB<?':''} ORDER BY MaKB DESC LIMIT 31`,before?[before]:[]);res.json({documents:rows.slice(0,30),next:rows.length>30?rows[29].id:null,aiConfigured:ai.enabled,aiProvider:ai.provider});});
 app.get('/api/knowledge/:id',async(req,res)=>{const id=numericId(req.params.id),[row]=await query(pool,`SELECT ${kbFields} FROM KnowledgeBase WHERE MaKB=?`,[id]);if(!row)throw new HttpError(404,'KNOWLEDGE_NOT_FOUND');const rows=await query(pool,'SELECT MaChunk id,ThuTu position,NoiDung content,Embedding embedding,TenMoHinh model,SoChieu dimensions FROM KnowledgeChunk WHERE MaKB=? ORDER BY ThuTu',[id]);res.json({document:row,chunks:rows.map(({embedding,...r})=>r),indexed:indexed(rows,row.content,ai),aiConfigured:ai.enabled,aiProvider:ai.provider});});
 app.post('/api/knowledge',async(req,res)=>{
  const payload={title:text(req.body?.title,200),content:text(req.body?.content,16000),replacesId:req.body?.replacesId?numericId(req.body.replacesId):null};
  const result=await mutate(pool,req,payload,async c=>{
   if(payload.replacesId){const [[previous]]=await c.execute('SELECT TrangThai FROM KnowledgeBase WHERE MaKB=? FOR UPDATE',[payload.replacesId]);if(previous?.TrangThai!=='Đã xuất bản')throw new HttpError(409,'KNOWLEDGE_CHANGED');}
   const [row]=await c.execute("INSERT INTO KnowledgeBase(MaUser,TieuDe,NoiDung,LoaiTaiLieu,ReplacesId) VALUES(?,?,?,'Text',?)",[req.user.MaUser,payload.title,payload.content,payload.replacesId]);await audit(c,req,row.insertId,'KNOWLEDGE_CREATE');return{id:row.insertId};
  });res.status(result.replayed?200:201).json(result);
 });
 app.post('/api/knowledge/:id/save',async(req,res)=>{
  const id=numericId(req.params.id),payload={version:numericId(req.body?.version),title:text(req.body?.title,200),content:text(req.body?.content,16000)};
  res.json(await mutate(pool,req,payload,async c=>{const row=await document(c,id,payload.version);if(row.status!=='Nháp')throw new HttpError(409,'KNOWLEDGE_READ_ONLY');await c.execute('DELETE FROM KnowledgeChunk WHERE MaKB=?',[id]);await c.execute('UPDATE KnowledgeBase SET TieuDe=?,NoiDung=?,ContentVersion=ContentVersion+1,NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaKB=?',[payload.title,payload.content,id]);await audit(c,req,id,'KNOWLEDGE_EDIT');return{id};}));
 });
 app.post('/api/knowledge/:id/index',async(req,res)=>{
  const id=numericId(req.params.id),version=numericId(req.body?.version);
  const key=req.get('Idempotency-Key');if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(key||''))throw new HttpError(400,'REQUEST_KEY_REQUIRED');
  const [old]=await query(pool,'SELECT RequestHash,Result FROM KnowledgeRequest WHERE MaUser=? AND RequestKey=?',[req.user.MaUser,key]);
  if(old){if(old.RequestHash!==createHash('sha256').update(JSON.stringify([req.path,{version}])).digest('hex'))throw new HttpError(409,'REQUEST_KEY_CONFLICT');return res.json({...typeof old.Result==='string'?JSON.parse(old.Result):old.Result,replayed:true});}
  const [row]=await query(pool,`SELECT ${kbFields} FROM KnowledgeBase WHERE MaKB=?`,[id]);if(!row)throw new HttpError(404,'KNOWLEDGE_NOT_FOUND');if(row.version!==version)throw new HttpError(409,'KNOWLEDGE_CHANGED');if(row.status!=='Nháp')throw new HttpError(409,'KNOWLEDGE_READ_ONLY');
  const texts=splitKnowledge(row.content||'');if(!texts.length)throw new HttpError(400,'INVALID_INPUT');
  // Remote calls run outside a SQL transaction. The version is checked again before saving.
  const vectors=await ai.embed(texts);if(vectors.length!==texts.length||vectors.some(v=>!validVector(v,ai.dimensions)))throw new HttpError(503,'AI_INVALID_OUTPUT');
  res.json(await mutate(pool,req,{version},async c=>{const current=await document(c,id,version);if(current.status!=='Nháp')throw new HttpError(409,'KNOWLEDGE_READ_ONLY');await c.execute('DELETE FROM KnowledgeChunk WHERE MaKB=?',[id]);for(let i=0;i<texts.length;i++)await c.execute('INSERT INTO KnowledgeChunk(MaKB,ThuTu,NoiDung,Embedding,TenMoHinh,SoChieu) VALUES(?,?,?,?,?,?)',[id,i,texts[i],JSON.stringify(vectors[i]),ai.model,ai.dimensions]);await audit(c,req,id,'KNOWLEDGE_INDEX');return{id};}));
 });
 app.post('/api/knowledge/:id/preview',async(req,res)=>{
  const id=numericId(req.params.id),question=text(req.body?.question,3000),version=numericId(req.body?.version);
  const [row]=await query(pool,`SELECT ${kbFields} FROM KnowledgeBase WHERE MaKB=?`,[id]);if(!row)throw new HttpError(404,'KNOWLEDGE_NOT_FOUND');if(row.version!==version)throw new HttpError(409,'KNOWLEDGE_CHANGED');
  const rows=await query(pool,'SELECT MaChunk id,NoiDung content,Embedding embedding,TenMoHinh model,SoChieu dimensions FROM KnowledgeChunk WHERE MaKB=? ORDER BY ThuTu',[id]);if(!indexed(rows,row.content,ai))throw new HttpError(409,'KNOWLEDGE_NOT_INDEXED');
  const [vector]=await ai.embed([question], 'query');const ranked=rows.map(r=>({...r,title:row.title,score:cosine(vector,parseVector(r.embedding)||[])})).filter(r=>r.score>=0.35).sort((a,b)=>b.score-a.score).slice(0,3);
  const result=ranked.length?await ai.answer(question,ranked,req.body?.language==='en'?'en':'vi'):{text:'',sourceIds:[]};
  res.json({answer:result.text,sources:ranked.filter(r=>result.sourceIds.includes(r.id)).map(({embedding,...r})=>r),preview:true});
 });
 for(const operation of ['publish','archive'])app.post(`/api/knowledge/:id/${operation}`,async(req,res)=>{
  const id=numericId(req.params.id),version=numericId(req.body?.version);
  res.json(await mutate(pool,req,{version},async c=>{
   const row=await document(c,id,version);
   if(operation==='publish'){
    if(row.status!=='Nháp')throw new HttpError(409,'KNOWLEDGE_READ_ONLY');if(!indexed(await chunks(c,id),row.content,ai))throw new HttpError(409,'KNOWLEDGE_NOT_INDEXED');
    if(row.replacesId){const [[old]]=await c.execute('SELECT TrangThai FROM KnowledgeBase WHERE MaKB=? FOR UPDATE',[row.replacesId]);if(old?.TrangThai!=='Đã xuất bản')throw new HttpError(409,'KNOWLEDGE_CHANGED');await c.execute("UPDATE KnowledgeBase SET TrangThai='Lưu trữ',NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaKB=?",[row.replacesId]);await audit(c,req,row.replacesId,'KNOWLEDGE_SUPERSEDED');}
   }else if(row.status!=='Đã xuất bản')throw new HttpError(409,'KNOWLEDGE_READ_ONLY');
   await c.execute('UPDATE KnowledgeBase SET TrangThai=?,NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaKB=?',[operation==='publish'?'Đã xuất bản':'Lưu trữ',id]);await audit(c,req,id,operation==='publish'?'KNOWLEDGE_PUBLISH':'KNOWLEDGE_ARCHIVE');return{id};
  }));
 });
}
