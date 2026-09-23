import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { randomBytes } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import mysql from 'mysql2/promise';
import { config } from '../server/config.js';
import { createPool, query } from '../server/db.js';
import { createApp } from '../server/app.js';
import { migrate, statements } from '../server/migrate.js';
import { hashPassword, digest } from '../server/password.js';

const enabled = process.env.RUN_MYSQL_TESTS === '1';
const integration = enabled ? test : test.skip;
let settings, pool, server, base, customer, cookie, adminConnection;
const password = 'Test-only-password-2026!';
const dbName = `vietincare_test_${randomBytes(6).toString('hex')}`;
async function api(path, { body, token = cookie, origin, headers = {} } = {}) {
  return fetch(base + path, { method: body === undefined ? 'GET' : 'POST', headers: {
    ...(token ? { Cookie: token } : {}),
    ...(body === undefined ? {} : { Origin: origin || settings.origin, 'Content-Type': 'application/json', 'X-Vietincare-Request': '1' }), ...headers
  }, body: body === undefined ? undefined : JSON.stringify(body) });
}
before(async () => {
  if (!enabled) return;
  settings = config({ ...process.env, DB_NAME: dbName });
  adminConnection = await mysql.createConnection({ ...settings.db, database: undefined, connectionLimit: undefined });
  await adminConnection.query(`CREATE DATABASE \`${dbName}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci`);
  await adminConnection.query(`USE \`${dbName}\``);
  const init = statements(await readFile(new URL('../SQLQuery1.sql', import.meta.url), 'utf8'));
  for (const sql of init.filter(s => /^CREATE TABLE/i.test(s))) await adminConnection.query(sql);
  // A real legacy record exists before migration; verify it is not deleted or guessed into an account.
  await adminConnection.execute("INSERT INTO Customer(HoTen,Email) VALUES('Khách cũ 🙂','legacy@example.test')");
  await migrate(settings);
  pool = createPool(settings);
  server = createApp(pool, settings).listen(0, '127.0.0.1');
  await once(server, 'listening'); base = `http://127.0.0.1:${server.address().port}`;
});
after(async () => {
  if (server) await new Promise(resolve => server.close(resolve));
  if (pool) await pool.end();
  if (adminConnection) {
    // Only the uniquely named database created by this test is removed.
    if (!/^vietincare_test_[a-f0-9]{12}$/.test(dbName)) throw new Error('Unsafe cleanup target');
    await adminConnection.query(`DROP DATABASE \`${dbName}\``); await adminConnection.end();
  }
});
integration('migration preserves legacy rows, is repeatable, and refuses init over existing data', async () => {
  const [old] = await query(pool, 'SELECT HoTen,MaUser FROM Customer WHERE Email=?', ['legacy@example.test']);
  assert.equal(old.HoTen, 'Khách cũ 🙂'); assert.equal(old.MaUser, null);
  assert.equal((await migrate(settings)).status, 'current');
  await assert.rejects(migrate(settings, { init: true }), /empty database/);
  await query(pool, "UPDATE SchemaMigration SET State='running' WHERE Step=1");
  await assert.rejects(migrate(settings), /interrupted/);
  await query(pool, "UPDATE SchemaMigration SET State='done' WHERE Step=1");
});
integration('register creates one linked Customer and ignores submitted elevated role', async () => {
  const res = await api('/api/auth/register', { body: { email: ' Customer@Example.test ', password, fullName: 'Nguyễn 🙂', phone: '0901234567', acceptTerms: true, role: 'Admin' }, token: null });
  assert.equal(res.status, 201);
  const [row] = await query(pool, "SELECT u.MaUser,u.PasswordHash,r.TenRole,c.MaKH FROM UserAccount u JOIN Role r ON u.MaRole=r.MaRole JOIN Customer c ON c.MaUser=u.MaUser WHERE u.EmailNormalized='customer@example.test'");
  assert.equal(row.TenRole, 'Customer'); assert.match(row.PasswordHash, /^scrypt\$/); customer = row;
  const duplicate = await api('/api/auth/register', { body: { email: 'CUSTOMER@example.test', password, fullName: 'Duplicate', phone: '0901234567', acceptTerms: true }, token: null });
  assert.equal(duplicate.status, 409);
  const [[count]] = await adminConnection.query("SELECT COUNT(*) n FROM Customer WHERE Email='customer@example.test'"); assert.equal(Number(count.n), 1);
});
integration('invalid inputs and cross-origin mutations are rejected', async () => {
  assert.equal((await api('/api/auth/register', { body: { email: 'bad', password: 'short' } })).status, 400);
  assert.equal((await api('/api/auth/login', { body: { email: 'customer@example.test', password }, origin: 'https://evil.example' })).status, 403);
  assert.equal((await api('/api/auth/login', { body: { email: 'customer@example.test', password }, headers: { 'X-Vietincare-Request': '' } })).status, 403);
  assert.equal((await api('/api/auth/login', { body: { email: "' OR 1=1 --", password } })).status, 400);
});
integration('login rejects wrong passwords and issues a server-side HttpOnly session', async () => {
  assert.equal((await api('/api/auth/login', { body: { email: 'customer@example.test', password: 'WrongPassword!' }, token: null })).status, 401);
  const res = await api('/api/auth/login', { body: { email: 'CUSTOMER@example.test', password }, token: null });
  assert.equal(res.status, 200); const setCookie = res.headers.get('set-cookie');
  assert.match(setCookie, /HttpOnly/i); assert.match(setCookie, /SameSite=Strict/i);
  cookie = setCookie.split(';')[0]; const payload = await res.json(); assert.equal(payload.user.customerId, customer.MaKH);
  const rows = await query(pool, 'SELECT TokenHash FROM AuthSession WHERE MaUser=?', [customer.MaUser]);
  assert.equal(rows.length, 1); assert.notEqual(rows[0].TokenHash.toString('hex'), cookie.split('=')[1]);
  assert.equal((await api('/api/auth/me')).status, 200);
});
integration('authorization denies other customers and roles; sensitive project files are not public', async () => {
  assert.equal((await api(`/api/customer/profile/${customer.MaKH}`)).status, 200);
  assert.equal((await api('/api/customer/profile/1')).status, 403);
  assert.equal((await api('/api/workspace/Admin')).status, 403);
  for (const path of ['/.env', '/SQLQuery1.sql', '/server/app.js', '/.mysql-sync/scope-before-2026-09-21.zip']) assert.equal((await api(path)).status, 404);
  assert.equal((await api('/api/auth/me', { token: 'vietincare_session=invalid' })).status, 401);
});
integration('all staff roles authenticate and cannot open another role workspace', async () => {
  for (const role of ['Agent', 'Supervisor', 'Admin']) {
    const hash = await hashPassword(password);
    await query(pool, 'INSERT INTO UserAccount(MaRole,HoTen,Username,Email,PasswordHash) SELECT MaRole,?,?,?,? FROM Role WHERE TenRole=?', [role, role, `${role.toLowerCase()}@example.test`, hash, role]);
    const res = await api('/api/auth/login', { body: { email: `${role.toLowerCase()}@example.test`, password }, token: null });
    assert.equal(res.status, 200); const token = res.headers.get('set-cookie').split(';')[0];
    assert.equal((await api(`/api/workspace/${role}`, { token })).status, 200);
    assert.equal((await api('/api/workspace/Customer', { token })).status, 403);
  }
});
integration('five failed attempts lock the email; expired throttle permits retry', async () => {
  for (let i = 0; i < 5; i++) assert.equal((await api('/api/auth/login', { body: { email: 'missing@example.test', password }, token: null })).status, 401);
  assert.equal((await api('/api/auth/login', { body: { email: 'missing@example.test', password }, token: null })).status, 429);
  await query(pool, "UPDATE AuthThrottle SET WindowEnd=DATE_SUB(UTC_TIMESTAMP(3),INTERVAL 1 SECOND) WHERE ThrottleKey=?", [digest('login-email:missing@example.test')]);
  assert.equal((await api('/api/auth/login', { body: { email: 'missing@example.test', password }, token: null })).status, 401);
});
integration('disabled accounts, expired sessions and logout invalidate access', async () => {
  await query(pool, 'UPDATE UserAccount SET TrangThai=0 WHERE MaUser=?', [customer.MaUser]);
  assert.equal((await api('/api/auth/me')).status, 401);
  await query(pool, 'UPDATE UserAccount SET TrangThai=1 WHERE MaUser=?', [customer.MaUser]);
  await query(pool, 'UPDATE AuthSession SET ExpiresAt=DATE_SUB(UTC_TIMESTAMP(3),INTERVAL 1 SECOND) WHERE MaUser=?', [customer.MaUser]);
  assert.equal((await api('/api/auth/me')).status, 401);
  const res = await api('/api/auth/login', { body: { email: 'customer@example.test', password } });
  cookie = res.headers.get('set-cookie').split(';')[0];
  assert.equal((await api('/api/auth/logout', { body: {} })).status, 204);
  assert.equal((await api('/api/auth/me')).status, 401);
});
integration('ownership and evaluation constraints reject mismatched or duplicate data', async () => {
  const [session] = await adminConnection.execute('INSERT INTO ChatSession(MaKH) VALUES(?)', [customer.MaKH]);
  await assert.rejects(query(pool, "INSERT INTO Ticket(MaKH,MaSession,TieuDe,NoiDung) VALUES(1,?,'a','b')", [session.insertId]), e => e.code === 'ER_NO_REFERENCED_ROW_2');
  await assert.rejects(query(pool, 'INSERT INTO Evaluation(MaKH,SoSao) VALUES(?,5)', [customer.MaKH]), e => e.code === 'ER_CHECK_CONSTRAINT_VIOLATED');
  await query(pool, 'INSERT INTO Evaluation(MaKH,MaSession,SoSao) VALUES(?,?,5)', [customer.MaKH, session.insertId]);
  await assert.rejects(query(pool, 'INSERT INTO Evaluation(MaKH,MaSession,SoSao) VALUES(?,?,4)', [customer.MaKH, session.insertId]), e => e.code === 'ER_DUP_ENTRY');
  await assert.rejects(query(pool, "INSERT INTO Ticket(MaKH,TieuDe,NoiDung,TrangThai) VALUES(?,'a','b','Invalid')", [customer.MaKH]), e => e.code === 'ER_CHECK_CONSTRAINT_VIOLATED');
});
