import express from 'express';
import { randomBytes } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { query, transaction } from './db.js';
import { hashPassword, verifyPassword, digest } from './password.js';
import { HttpError } from './http-error.js';
import { installTicketRoutes } from './tickets.js';
import { installChatRoutes } from './chats.js';
import { createAI } from './ai.js';
import { installKnowledgeRoutes } from './knowledge.js';
import { installRagRoutes } from './rag.js';

const root = fileURLToPath(new URL('../', import.meta.url));
const roles = ['Customer', 'Agent', 'Supervisor', 'Admin'];
const emailValid = email => typeof email === 'string' && email.length <= 100 && /^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+$/i.test(email);
const passwordValid = value => typeof value === 'string' && value.length >= 8 && value.length <= 128;
const publicUser = row => ({ id: row.MaUser, name: row.HoTen, email: row.Email, role: row.TenRole, customerId: row.MaKH ?? null });
function cookieToken(req) {
  const tokens = (req.headers.cookie || '').split(';').map(s => s.trim()).filter(s => s.startsWith('vietincare_session='));
  if (tokens.length !== 1) return null;
  const token = tokens[0].slice('vietincare_session='.length);
  return /^[a-f0-9]{64}$/.test(token) ? token : null;
}
const cookieOptions = settings => ({ httpOnly: true, sameSite: 'strict', secure: settings.secure, path: '/' });
async function throttle(c, key, limit) {
  const hash = digest(key);
  await c.execute('INSERT IGNORE INTO AuthThrottle(ThrottleKey,Attempts,WindowEnd) VALUES(?,0,DATE_ADD(UTC_TIMESTAMP(3),INTERVAL 15 MINUTE))', [hash]);
  const [[row]] = await c.execute('SELECT Attempts,WindowEnd<=UTC_TIMESTAMP(3) expired FROM AuthThrottle WHERE ThrottleKey=? FOR UPDATE', [hash]);
  if (Number(row.expired) === 0 && row.Attempts >= limit) return false;
  await c.execute('UPDATE AuthThrottle SET Attempts=IF(WindowEnd<=UTC_TIMESTAMP(3),1,Attempts+1),WindowEnd=IF(WindowEnd<=UTC_TIMESTAMP(3),DATE_ADD(UTC_TIMESTAMP(3),INTERVAL 15 MINUTE),WindowEnd) WHERE ThrottleKey=?', [hash]);
  return true;
}
async function audit(c, user, action, ip) {
  await c.execute('INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong,DiaChiIP) VALUES(?,?,\'UserAccount\',?,?)', [user, action, user, ip]);
}
export function createApp(pool, settings, dependencies = {}) {
  const ai = dependencies.ai || createAI(settings);
  const app = express();
  app.disable('x-powered-by');
  // No trust proxy: client IP must not come from an arbitrary forwarded header.
  app.use((req, res, next) => {
    res.set({ 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'same-origin',
      'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" });
    if (req.path.startsWith('/api/')) res.set('Cache-Control', 'no-store');
    next();
  });
  app.use('/api', (req, res, next) => {
    if (!['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
      if (req.headers.origin !== settings.origin || req.headers['x-vietincare-request'] !== '1') return next(new HttpError(403, 'ORIGIN_REJECTED'));
      if (!req.is('application/json')) return next(new HttpError(415, 'JSON_REQUIRED'));
    }
    next();
  }, express.json({ limit: '64kb', strict: true }));
  app.get('/api/health', async (req, res) => { await query(pool, 'SELECT 1'); res.json({ status: 'ok' }); });
  app.post('/api/auth/register', async (req, res) => {
    const email = typeof req.body?.email === 'string' ? req.body.email.trim().toLowerCase() : '';
    const fullName = typeof req.body?.fullName === 'string' ? req.body.fullName.trim() : '';
    const phone = typeof req.body?.phone === 'string' ? req.body.phone.trim() : '';
    const password = req.body?.password;
    if (!emailValid(email) || !fullName || fullName.length > 100 || !/^\+?[0-9 ()-]{8,20}$/.test(phone) || !passwordValid(password) || req.body.acceptTerms !== true) throw new HttpError(400, 'INVALID_INPUT');
    const allowed = await transaction(pool, c => throttle(c, `register:${req.ip}`, 20));
    if (!allowed) throw new HttpError(429, 'RATE_LIMITED');
    const passwordHash = await hashPassword(password);
    try {
      await transaction(pool, async c => {
        const [[role]] = await c.execute("SELECT MaRole FROM Role WHERE TenRole='Customer'");
        if (!role) throw new Error('Migrations required');
        const [result] = await c.execute('INSERT INTO UserAccount(MaRole,HoTen,Username,PasswordHash,Email,SoDienThoai) VALUES(?,?,?,?,?,?)', [role.MaRole, fullName, `customer_${randomBytes(16).toString('hex')}`, passwordHash, email, phone]);
        await c.execute('INSERT INTO Customer(MaUser,HoTen,Email,SoDienThoai,LoaiKhachHang) VALUES(?,?,?,?,?)', [result.insertId, fullName, email, phone, 'Cá nhân']);
        await audit(c, result.insertId, 'REGISTER', req.ip);
      });
    } catch (e) { if (e.code === 'ER_DUP_ENTRY') throw new HttpError(409, 'EMAIL_EXISTS'); throw e; }
    res.status(201).json({ message: 'REGISTERED' });
  });
  app.post('/api/auth/login', async (req, res) => {
    const email = typeof req.body?.email === 'string' ? req.body.email.trim().toLowerCase() : '';
    const password = req.body?.password;
    if (!emailValid(email) || !passwordValid(password)) throw new HttpError(400, 'INVALID_INPUT');
    // Commit attempt reservations before password checking so concurrent failures cannot bypass limits.
    const allowed = await transaction(pool, async c => {
      const byIp = await throttle(c, `login-ip:${req.ip}`, 40);
      const byEmail = await throttle(c, `login-email:${email}`, 5);
      return byIp && byEmail;
    });
    if (!allowed) throw new HttpError(429, 'RATE_LIMITED');
    const rows = await query(pool, `SELECT u.*,r.TenRole,c.MaKH,c.TrangThai CustomerActive FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole LEFT JOIN Customer c ON c.MaUser=u.MaUser WHERE u.EmailNormalized=?`, [email]);
    const user = rows[0];
    const valid = await verifyPassword(password, user?.PasswordHash);
    if (!valid || !user?.TrangThai || !roles.includes(user.TenRole) || (user.TenRole === 'Customer' && (!user.MaKH || !user.CustomerActive))) throw new HttpError(401, 'INVALID_CREDENTIALS');
    const token = randomBytes(32).toString('hex');
    await transaction(pool, async c => {
      const oldToken = cookieToken(req);
      if (oldToken) await c.execute('DELETE FROM AuthSession WHERE TokenHash=?', [digest(oldToken)]);
      await c.execute('INSERT INTO AuthSession(TokenHash,MaUser,ExpiresAt) VALUES(?,?,TIMESTAMPADD(HOUR,?,UTC_TIMESTAMP(3)))', [digest(token), user.MaUser, settings.sessionHours]);
      await c.execute('DELETE FROM AuthThrottle WHERE ThrottleKey=?', [digest(`login-email:${email}`)]);
      await audit(c, user.MaUser, 'LOGIN', req.ip);
    });
    res.cookie('vietincare_session', token, { ...cookieOptions(settings), maxAge: settings.sessionHours * 3600000 });
    res.json({ user: publicUser(user) });
  });
  async function authenticated(req, res, next) {
    const token = cookieToken(req);
    if (!token) throw new HttpError(401, 'UNAUTHENTICATED');
    const rows = await query(pool, `SELECT u.MaUser,u.HoTen,u.Email,r.TenRole,c.MaKH FROM AuthSession s JOIN UserAccount u ON u.MaUser=s.MaUser JOIN Role r ON r.MaRole=u.MaRole LEFT JOIN Customer c ON c.MaUser=u.MaUser WHERE s.TokenHash=? AND s.ExpiresAt>UTC_TIMESTAMP(3) AND u.TrangThai=1 AND (r.TenRole<>'Customer' OR (c.MaKH IS NOT NULL AND c.TrangThai=1))`, [digest(token)]);
    if (!rows.length || !roles.includes(rows[0].TenRole)) throw new HttpError(401, 'UNAUTHENTICATED');
    req.user = rows[0]; req.token = token; next();
  }
  app.get('/api/auth/me', authenticated, (req, res) => res.json({ user: publicUser(req.user) }));
  app.post('/api/auth/logout', authenticated, async (req, res) => {
    await transaction(pool, async c => { await c.execute('DELETE FROM AuthSession WHERE TokenHash=?', [digest(req.token)]); await audit(c, req.user.MaUser, 'LOGOUT', req.ip); });
    res.clearCookie('vietincare_session', cookieOptions(settings)); res.status(204).end();
  });
  const requireRole = (...allowed) => (req, res, next) => {
    if (!allowed.includes(req.user.TenRole)) return next(new HttpError(403, 'FORBIDDEN')); next();
  };
  app.get('/api/customer/profile/:id', authenticated, requireRole('Customer'), async (req, res) => {
    if (!/^\d+$/.test(req.params.id) || Number(req.params.id) !== req.user.MaKH) throw new HttpError(403, 'FORBIDDEN');
    const [profile] = await query(pool, 'SELECT MaKH,HoTen,Email,SoDienThoai FROM Customer WHERE MaKH=? AND MaUser=?', [req.user.MaKH, req.user.MaUser]);
    res.json({ profile });
  });
  app.get('/api/workspace/:role', authenticated, (req, res, next) => {
    if (req.params.role !== req.user.TenRole) return next(new HttpError(403, 'FORBIDDEN'));
    res.json({ user: publicUser(req.user), implemented: ['authentication', 'tickets'], pending: ['rag', 'reports'] });
  });
  installTicketRoutes(app, pool, authenticated, requireRole);
  installChatRoutes(app, pool, authenticated, requireRole, ai);
  installKnowledgeRoutes(app, pool, authenticated, requireRole, ai);
  installRagRoutes(app, pool, authenticated, requireRole, ai, settings);
  app.use('/api', (req, res) => res.status(404).json({ error: 'NOT_FOUND' }));
  app.get('/', (req, res) => res.redirect('/VI/index-vi.html'));
  // Only public assets, never the project directory, SQL, secrets or document backups.
  const publicFiles = new Set(['script.js', 'auth.js', 'account.js', 'tickets.js', 'tickets.css', 'style.css', 'pages.css', 'landing-vi.css', 'account.css', 'workspace.css', 'workspace.js', 'chat.js', 'chat.css', 'knowledge.js', 'knowledge.css']);
  app.use((req, res, next) => {
    if (!['GET', 'HEAD'].includes(req.method)) return next();
    const name = req.path.slice(1);
    if (publicFiles.has(name) || /^(VI|EN)\/(index|login|register|account|tickets|chat|knowledge)-(vi|en)\.html$/.test(name)) return res.sendFile(join(root, name), err => { if (err) next(err); });
    next();
  });
  app.use((req, res) => res.status(404).send('Not found'));
  app.use((err, req, res, next) => {
    if (res.headersSent) return next(err);
    const status = err.status || 503;
    const code = err instanceof HttpError ? err.code : status === 400 ? 'INVALID_JSON' : status === 413 ? 'BODY_TOO_LARGE' : 'SERVICE_UNAVAILABLE';
    if (status >= 500) console.error('Request failed:', err.code || err.name); // no SQL, bodies or credentials
    res.status(status).json({ error: code });
  });
  return app;
}
