import { randomBytes } from 'node:crypto';
import { config } from './config.js';
import { createPool, transaction } from './db.js';
import { hashPassword } from './password.js';

// Administrative CLI only; never exposed as a public registration endpoint.
const pool = createPool(config());
try {
  const email = (process.env.VC_AGENT_EMAIL || '').trim().toLowerCase();
  const name = (process.env.VC_AGENT_NAME || '').trim();
  const password = process.env.VC_AGENT_PASSWORD || '';
  if (!name || name.length > 100 || email.length > 100 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || password.length < 12 || password.length > 128) throw new Error('INVALID_AGENT_INPUT');
  const hash = await hashPassword(password);
  await transaction(pool, async c => {
    const [[role]] = await c.execute("SELECT MaRole FROM Role WHERE TenRole='Agent'");
    if (!role) throw new Error('MIGRATION_REQUIRED');
    const [result] = await c.execute('INSERT INTO UserAccount(MaRole,HoTen,Username,Email,PasswordHash) VALUES(?,?,?,?,?)', [role.MaRole, name, `agent_${randomBytes(12).toString('hex')}`, email, hash]);
    await c.execute("INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,MaDoiTuong) VALUES(?,'AGENT_CREATE_LOCAL','UserAccount',?)", [result.insertId, result.insertId]);
  });
  console.log('AGENT_CREATED: Dang nhap bang email va mat khau vua nhap / Sign in with the supplied email and password.');
} catch (e) {
  console.error(e.code || (['INVALID_AGENT_INPUT','MIGRATION_REQUIRED'].includes(e.message) ? e.message : 'AGENT_CREATE_FAILED'));
  process.exitCode=1;
} finally { await pool.end(); }
