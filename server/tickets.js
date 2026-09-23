import { createHash } from 'node:crypto';
import { query, transaction } from './db.js';
import { HttpError } from './http-error.js';

const stages = ['Mới', 'Đang xử lý', 'Đã giải quyết', 'Đã đóng'];
const priorities = ['Thấp', 'Trung bình', 'Cao', 'Khẩn cấp'];
const ticketCode = id => `TK-${String(id).padStart(6, '0')}`;
const fields = 't.MaTicket id,t.MaKH customerId,t.MaAgent agentId,t.TieuDe title,t.TrangThai status,t.MucDoUuTien priority,t.NgayTao createdAt,t.NgayCapNhat updatedAt,t.NgayDong closedAt';
function idOf(value) {
  if (!/^[1-9]\d{0,9}$/.test(String(value)) || Number(value) > 2147483647) throw new HttpError(400, 'INVALID_INPUT');
  return Number(value);
}
function text(value, max) {
  if (typeof value !== 'string' || !value.trim() || value.trim().length > max) throw new HttpError(400, 'INVALID_INPUT');
  return value.trim();
}
function visibility(user) {
  if (user.TenRole === 'Customer') return ['t.MaKH=?', [user.MaKH]];
  if (user.TenRole === 'Agent') return ["(t.MaAgent=? OR (t.MaAgent IS NULL AND t.TrangThai='Mới'))", [user.MaUser]];
  return ['1=1', []]; // Only Supervisor reaches here: routes explicitly reject Admin.
}
async function accessible(c, user, id, lock = false) {
  const [where, args] = visibility(user);
  const [[row]] = await c.execute(`SELECT ${fields},t.NoiDung content FROM Ticket t WHERE t.MaTicket=? AND ${where}${lock ? ' FOR UPDATE' : ''}`, [id, ...args]);
  if (!row) throw new HttpError(404, 'TICKET_NOT_FOUND');
  return { ...row, code: ticketCode(row.id) };
}
async function event(c, req, id, action, previous, next) {
  if (next) await c.execute('INSERT INTO TicketStatusHistory(MaTicket,TrangThaiCu,TrangThaiMoi,MaUser) VALUES(?,?,?,?)', [id, previous, next, req.user.MaUser]);
  await c.execute("INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,'Ticket',?,?)", [req.user.MaUser, action, id, req.ip]);
}
// Lock the actor first, then the ticket. Retries of one user cannot race, including
// the first request where no retry record exists yet. No application memory cache.
async function mutate(pool, req, payload, work) {
  const key = req.get('Idempotency-Key');
  if (typeof key !== 'string' || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(key)) throw new HttpError(400, 'REQUEST_KEY_REQUIRED');
  const hash = createHash('sha256').update(JSON.stringify([req.path, payload])).digest('hex');
  return transaction(pool, async c => {
    const [[actor]] = await c.execute('SELECT TrangThai,MaRole FROM UserAccount WHERE MaUser=? FOR UPDATE', [req.user.MaUser]);
    if (!actor?.TrangThai) throw new HttpError(401, 'UNAUTHENTICATED');
    const [[old]] = await c.execute('SELECT RequestHash,Result FROM TicketRequest WHERE MaUser=? AND RequestKey=?', [req.user.MaUser, key]);
    if (old) {
      if (old.RequestHash !== hash) throw new HttpError(409, 'REQUEST_KEY_CONFLICT');
      return { ...(typeof old.Result === 'string' ? JSON.parse(old.Result) : old.Result), replayed: true };
    }
    const result = await work(c);
    await c.execute('INSERT INTO TicketRequest(MaUser,RequestKey,RequestHash,Result) VALUES(?,?,?,?)', [req.user.MaUser, key, hash, JSON.stringify(result)]);
    return result;
  });
}

export function installTicketRoutes(app, pool, authenticated, requireRole) {
  const readers = [authenticated, requireRole('Customer', 'Agent', 'Supervisor')];
  app.get('/api/tickets', ...readers, async (req, res) => {
    const before = req.query.before === undefined ? 2147483647 : idOf(req.query.before);
    const status = req.query.status;
    if (status !== undefined && !stages.includes(status)) throw new HttpError(400, 'INVALID_INPUT');
    const [where, args] = visibility(req.user);
    const rows = await query(pool, `SELECT ${fields} FROM Ticket t WHERE ${where} AND t.MaTicket<? ${status ? 'AND t.TrangThai=?' : ''} ORDER BY t.MaTicket DESC LIMIT 31`, [...args, before, ...(status ? [status] : [])]);
    const more = rows.length > 30;
    const tickets = rows.slice(0, 30).map(row => ({ ...row, code: ticketCode(row.id) }));
    res.json({ tickets, next: more ? tickets.at(-1).id : null });
  });
  app.get('/api/tickets/:id', ...readers, async (req, res) => {
    const id = idOf(req.params.id);
    const result = await transaction(pool, async c => {
      const ticket = await accessible(c, req.user, id);
      const [replies] = await c.execute('SELECT r.MaReply id,r.MaUser userId,u.HoTen author,role.TenRole role,r.NoiDung content,r.ThoiGian createdAt FROM TicketReply r JOIN UserAccount u ON u.MaUser=r.MaUser JOIN Role role ON role.MaRole=u.MaRole WHERE r.MaTicket=? ORDER BY r.MaReply', [id]);
      const [history] = await c.execute('SELECT h.MaHistory id,h.TrangThaiCu previous,h.TrangThaiMoi status,u.HoTen author,h.ThoiGian createdAt FROM TicketStatusHistory h JOIN UserAccount u ON u.MaUser=h.MaUser WHERE h.MaTicket=? ORDER BY h.MaHistory', [id]);
      return { ticket, replies, history };
    });
    res.json(result);
  });
  app.post('/api/tickets', authenticated, requireRole('Customer'), async (req, res) => {
    const payload = { title: text(req.body?.title, 200), content: text(req.body?.content, 3000) };
    const result = await mutate(pool, req, payload, async c => {
      const [row] = await c.execute('INSERT INTO Ticket(MaKH,TieuDe,NoiDung) VALUES(?,?,?)', [req.user.MaKH, payload.title, payload.content]);
      await event(c, req, row.insertId, 'TICKET_CREATE', null, stages[0]);
      return { id: row.insertId, code: ticketCode(row.insertId) };
    });
    res.status(result.replayed ? 200 : 201).json(result);
  });
  app.post('/api/tickets/:id/claim', authenticated, requireRole('Agent'), async (req, res) => {
    const id = idOf(req.params.id);
    res.json(await mutate(pool, req, {}, async c => {
      // All claimants lock the same row; one can win. Do not expose the new owner.
      const [[ticket]] = await c.execute('SELECT MaAgent,TrangThai FROM Ticket WHERE MaTicket=? FOR UPDATE', [id]);
      if (!ticket) throw new HttpError(404, 'TICKET_NOT_FOUND');
      if (ticket.MaAgent !== null || ticket.TrangThai !== stages[0]) throw new HttpError(409, 'TICKET_ALREADY_CLAIMED');
      await c.execute("UPDATE Ticket SET MaAgent=?,TrangThai='Đang xử lý',NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaTicket=?", [req.user.MaUser, id]);
      await event(c, req, id, 'TICKET_CLAIM', stages[0], stages[1]);
      return { id };
    }));
  });
  app.post('/api/tickets/:id/replies', authenticated, requireRole('Customer', 'Agent'), async (req, res) => {
    const id = idOf(req.params.id);
    const payload = { content: text(req.body?.content, 3000) };
    res.json(await mutate(pool, req, payload, async c => {
      const ticket = await accessible(c, req.user, id, true);
      if (req.user.TenRole === 'Agent' && ticket.agentId !== req.user.MaUser) throw new HttpError(403, 'CLAIM_REQUIRED');
      if (!stages.slice(0, 2).includes(ticket.status)) throw new HttpError(409, 'TICKET_READ_ONLY');
      const [row] = await c.execute('INSERT INTO TicketReply(MaTicket,MaUser,NoiDung) VALUES(?,?,?)', [id, req.user.MaUser, payload.content]);
      await c.execute('UPDATE Ticket SET NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaTicket=?', [id]);
      await event(c, req, id, 'TICKET_REPLY');
      return { id, replyId: row.insertId };
    }));
  });
  app.post('/api/tickets/:id/status', authenticated, requireRole('Agent'), async (req, res) => {
    const id = idOf(req.params.id);
    const status = req.body?.status;
    if (!stages.slice(2).includes(status)) throw new HttpError(400, 'INVALID_INPUT');
    res.json(await mutate(pool, req, { status }, async c => {
      const ticket = await accessible(c, req.user, id, true);
      if (ticket.agentId !== req.user.MaUser) throw new HttpError(403, 'CLAIM_REQUIRED');
      if (stages.indexOf(status) !== stages.indexOf(ticket.status) + 1) throw new HttpError(409, 'INVALID_TRANSITION');
      if (status === stages[2]) {
        const [[reply]] = await c.execute('SELECT MaReply FROM TicketReply WHERE MaTicket=? AND MaUser=? LIMIT 1', [id, req.user.MaUser]);
        if (!reply) throw new HttpError(409, 'REPLY_REQUIRED');
      }
      await c.execute("UPDATE Ticket SET TrangThai=?,NgayCapNhat=UTC_TIMESTAMP(3),NgayDong=IF(?='Đã đóng',UTC_TIMESTAMP(3),NULL) WHERE MaTicket=?", [status, status, id]);
      await event(c, req, id, 'TICKET_STATUS', ticket.status, status);
      return { id };
    }));
  });
  app.post('/api/tickets/:id/priority', authenticated, requireRole('Agent'), async (req, res) => {
    const id = idOf(req.params.id), priority = req.body?.priority;
    if (!priorities.includes(priority)) throw new HttpError(400, 'INVALID_INPUT');
    res.json(await mutate(pool, req, { priority }, async c => {
      const ticket = await accessible(c, req.user, id, true);
      if (ticket.agentId !== req.user.MaUser) throw new HttpError(403, 'CLAIM_REQUIRED');
      if (ticket.status !== stages[1]) throw new HttpError(409, 'TICKET_READ_ONLY');
      await c.execute('UPDATE Ticket SET MucDoUuTien=?,NgayCapNhat=UTC_TIMESTAMP(3) WHERE MaTicket=?', [priority, id]);
      await event(c, req, id, 'TICKET_PRIORITY');
      return { id };
    }));
  });
}
