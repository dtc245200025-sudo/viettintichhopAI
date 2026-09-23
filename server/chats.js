import { createHash } from 'node:crypto';
import { query, transaction } from './db.js';
import { HttpError } from './http-error.js';

const fields = 'MaSession id,TieuDe title,TrangThai status,ThoiGianBatDau createdAt,ThoiGianKetThuc closedAt';
function idOf(value) {
  if (!/^[1-9]\d{0,9}$/.test(String(value)) || Number(value) > 2147483647) throw new HttpError(400,'INVALID_INPUT');
  return Number(value);
}
function contentOf(value) {
  if (typeof value !== 'string' || !value.trim() || value.trim().length > 3000) throw new HttpError(400,'INVALID_INPUT');
  return value.trim();
}
async function mutate(pool, req, payload, work) {
  const key = req.get('Idempotency-Key');
  if (typeof key !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(key)) throw new HttpError(400,'REQUEST_KEY_REQUIRED');
  const hash = createHash('sha256').update(JSON.stringify([req.path,payload])).digest('hex');
  return transaction(pool,async c => {
    const [[actor]] = await c.execute("SELECT u.TrangThai,r.TenRole FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole WHERE u.MaUser=? FOR UPDATE",[req.user.MaUser]);
    if (!actor?.TrangThai) throw new HttpError(401,'UNAUTHENTICATED');
    if (actor.TenRole !== 'Customer') throw new HttpError(403,'FORBIDDEN');
    const [[owner]] = await c.execute('SELECT MaKH FROM Customer WHERE MaKH=? AND MaUser=? AND TrangThai=1 FOR UPDATE',[req.user.MaKH,req.user.MaUser]);
    if (!owner) throw new HttpError(403,'FORBIDDEN');
    const [[old]] = await c.execute('SELECT RequestHash,Result FROM ChatRequest WHERE MaUser=? AND RequestKey=?',[req.user.MaUser,key]);
    if (old) {
      if (old.RequestHash !== hash) throw new HttpError(409,'REQUEST_KEY_CONFLICT');
      return {...(typeof old.Result === 'string' ? JSON.parse(old.Result) : old.Result),replayed:true};
    }
    const result = await work(c);
    await c.execute('INSERT INTO ChatRequest(MaUser,RequestKey,RequestHash,Result) VALUES(?,?,?,?)',[req.user.MaUser,key,hash,JSON.stringify(result)]);
    return result;
  });
}
async function owned(c, req, id) {
  const [[chat]] = await c.execute(`SELECT ${fields} FROM ChatSession WHERE MaSession=? AND MaKH=? FOR UPDATE`,[id,req.user.MaKH]);
  if (!chat) throw new HttpError(404,'CHAT_NOT_FOUND');
  return chat;
}
async function record(c,req,id,action) {
  await c.execute("INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,'ChatSession',?,?)",[req.user.MaUser,action,id,req.ip]);
}
export function installChatRoutes(app,pool,authenticated,requireRole,ai) {
  app.use('/api/chats',authenticated,requireRole('Customer'));
  app.get('/api/chats',async(req,res) => {
    const before = req.query.before === undefined ? null : idOf(req.query.before);
    const rows = await query(pool,`SELECT ${fields} FROM ChatSession WHERE MaKH=? ${before ? 'AND MaSession<?' : ''} ORDER BY MaSession DESC LIMIT 31`,[req.user.MaKH,...(before ? [before] : [])]);
    const chats = rows.slice(0,30);
    res.json({chats,next:rows.length > 30 ? chats.at(-1).id : null,aiProvider:ai.provider,assistantStatus:ai.enabled?'ready':'not_configured'});
  });
  app.get('/api/chats/:id',async(req,res) => {
    const id = idOf(req.params.id), before = req.query.before === undefined ? null : idOf(req.query.before);
    const [chat] = await query(pool,`SELECT ${fields} FROM ChatSession WHERE MaSession=? AND MaKH=?`,[id,req.user.MaKH]);
    if (!chat) throw new HttpError(404,'CHAT_NOT_FOUND');
    const rows = await query(pool,`SELECT MaMessage id,NguoiGui sender,MaUser userId,NoiDung content,ThoiGian createdAt,ReplyTo replyTo,AnswerStatus answerStatus FROM Message WHERE MaSession=? ${before ? 'AND MaMessage<?' : ''} ORDER BY MaMessage DESC LIMIT 51`,[id,...(before ? [before] : [])]);
    const messages = rows.slice(0,50), next = rows.length > 50 ? messages.at(-1).id : null;
    if(messages.length){
      const sources=await query(pool,`SELECT s.MaMessage messageId,s.MaChunk chunkId,k.MaKB documentId,s.TieuDeNguon title,s.NoiDungNguon content FROM MessageSource s JOIN KnowledgeChunk k ON k.MaChunk=s.MaChunk WHERE s.MaMessage IN (${messages.map(()=>'?').join(',')}) ORDER BY s.MaSource`,messages.map(m=>m.id));
      for(const m of messages)m.sources=sources.filter(s=>s.messageId===m.id);
    }
    res.json({chat,messages:messages.reverse(),next,aiProvider:ai.provider,assistantStatus:ai.enabled?'ready':'not_configured'});
  });
  app.post('/api/chats',async(req,res) => {
    const content = contentOf(req.body?.content);
    const result = await mutate(pool,req,{content},async c => {
      const [row] = await c.execute("INSERT INTO ChatSession(MaKH,TieuDe,KenhChat) VALUES(?,?,'Web')",[req.user.MaKH,Array.from(content).slice(0,100).join('')]);
      const [message] = await c.execute("INSERT INTO Message(MaSession,NguoiGui,MaUser,NoiDung) VALUES(?,'Customer',?,?)",[row.insertId,req.user.MaUser,content]);
      await record(c,req,row.insertId,'CHAT_CREATE');
      return {id:row.insertId,messageId:message.insertId,assistantStatus:'not_configured'};
    });
    res.status(result.replayed ? 200 : 201).json(result);
  });
  app.post('/api/chats/:id/messages',async(req,res) => {
    const id = idOf(req.params.id), content = contentOf(req.body?.content);
    res.json(await mutate(pool,req,{content},async c => {
      const chat = await owned(c,req,id);
      if (chat.closedAt || chat.status !== 'Đang hoạt động') throw new HttpError(409,'CHAT_READ_ONLY');
      const [row] = await c.execute("INSERT INTO Message(MaSession,NguoiGui,MaUser,NoiDung) VALUES(?,'Customer',?,?)",[id,req.user.MaUser,content]);
      await record(c,req,id,'CHAT_MESSAGE');
      return {id,messageId:row.insertId,assistantStatus:'not_configured'};
    }));
  });
  app.post('/api/chats/:id/close',async(req,res) => {
    const id = idOf(req.params.id);
    res.json(await mutate(pool,req,{},async c => {
      const chat = await owned(c,req,id);
      if (!chat.closedAt) {
        if (chat.status !== 'Đang hoạt động') throw new HttpError(409,'CHAT_READ_ONLY');
        await c.execute("UPDATE ChatSession SET TrangThai='Đã kết thúc',ThoiGianKetThuc=UTC_TIMESTAMP(3) WHERE MaSession=?",[id]);
        await record(c,req,id,'CHAT_CLOSE');
      }
      return {id};
    }));
  });
}
