import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import mysql from 'mysql2/promise';
import { config } from './config.js';

const root = new URL('../', import.meta.url);
export function statements(text) { return text.replace(/^\s*--.*$/gm, '').split(';').map(s => s.trim()).filter(Boolean); }
export async function preflight(c) {
  const checks = [
    ['duplicate-email', 'SELECT COUNT(*) n FROM (SELECT LOWER(TRIM(Email)) FROM UserAccount WHERE Email IS NOT NULL GROUP BY LOWER(TRIM(Email)) HAVING COUNT(*)>1) d'],
    ['invalid-email', "SELECT COUNT(*) n FROM UserAccount WHERE Email IS NOT NULL AND (TRIM(Email)='' OR TRIM(Email) NOT LIKE '%_@_%._%')"],
    ['ticket-owner', 'SELECT COUNT(*) n FROM Ticket t JOIN ChatSession s ON t.MaSession=s.MaSession WHERE t.MaKH<>s.MaKH'],
    ['ticket-status', "SELECT COUNT(*) n FROM Ticket WHERE TrangThai IS NULL OR TrangThai NOT IN ('Mới','Đang xử lý','Đã giải quyết','Đã đóng') OR MucDoUuTien IS NULL OR MucDoUuTien NOT IN ('Thấp','Trung bình','Cao','Khẩn cấp')"],
    ['evaluation-target', 'SELECT COUNT(*) n FROM Evaluation WHERE (MaSession IS NOT NULL)+(MaTicket IS NOT NULL)<>1 OR SoSao IS NULL OR SoSao NOT BETWEEN 1 AND 5 OR DiemNPS NOT BETWEEN 0 AND 10'],
    ['evaluation-owner', 'SELECT COUNT(*) n FROM Evaluation e LEFT JOIN Ticket t ON e.MaTicket=t.MaTicket LEFT JOIN ChatSession s ON e.MaSession=s.MaSession WHERE (t.MaKH IS NOT NULL AND t.MaKH<>e.MaKH) OR (s.MaKH IS NOT NULL AND s.MaKH<>e.MaKH)'],
    ['duplicate-rating-session', 'SELECT COUNT(*) n FROM (SELECT MaSession FROM Evaluation WHERE MaSession IS NOT NULL GROUP BY MaSession HAVING COUNT(*)>1) d'],
    ['duplicate-rating-ticket', 'SELECT COUNT(*) n FROM (SELECT MaTicket FROM Evaluation WHERE MaTicket IS NOT NULL GROUP BY MaTicket HAVING COUNT(*)>1) d'],
    ['sentiment-label', "SELECT COUNT(*) n FROM SentimentAnalysis WHERE CamXuc NOT IN ('Tích cực','Trung tính','Tiêu cực')"],
    ['handover-status', "SELECT COUNT(*) n FROM Handover WHERE TrangThai IS NULL OR TrangThai NOT IN ('Chờ tiếp nhận','Đã tiếp nhận','Đã kết thúc','Đã hủy')"],
    ['handover-duplicate', "SELECT COUNT(*) n FROM (SELECT MaSession FROM Handover WHERE TrangThai IN ('Chờ tiếp nhận','Đã tiếp nhận') GROUP BY MaSession HAVING COUNT(*)>1) d"],
    ['ticket-time', "SELECT COUNT(*) n FROM Ticket WHERE NgayTao IS NULL OR NgayCapNhat<NgayTao OR (NgayDong IS NOT NULL AND (NgayDong<NgayTao OR TrangThai<>'Đã đóng'))"],
    ['chat-time', 'SELECT COUNT(*) n FROM ChatSession WHERE ThoiGianKetThuc IS NOT NULL AND (ThoiGianBatDau IS NULL OR ThoiGianKetThuc<ThoiGianBatDau)'],
    ['confidence-range', 'SELECT COUNT(*) n FROM Message WHERE DoTinCayAI NOT BETWEEN 0 AND 100']
  ];
  const issues = [];
  for (const [name, sql] of checks) { const [[row]] = await c.query(sql); if (Number(row.n)) issues.push(`${name}: ${row.n}`); }
  if (issues.length) throw new Error(`Preflight failed; no application schema changed. Resolve records explicitly: ${issues.join(', ')}`);
}
export async function migrate(settings, { init = false, check = false } = {}) {
  const c = await mysql.createConnection({ ...settings.db, database: undefined, connectionLimit: undefined });
  const db = settings.db.database;
  let locked = false;
  try {
    await c.query("SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci");
    await c.query("SET SESSION time_zone='+00:00'");
    const [[version]] = await c.query('SELECT VERSION() version');
    if (!version.version.startsWith('8.0.46')) throw new Error('This project requires MySQL Community Server 8.0.46');
    const [[lock]] = await c.execute('SELECT GET_LOCK(?, 10) acquired', [`vietincare:${db}`]);
    if (Number(lock.acquired) !== 1) throw new Error('Migration lock unavailable');
    locked = true;
    if (init) await c.query(`CREATE DATABASE IF NOT EXISTS \`${db}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci`);
    await c.query(`USE \`${db}\``);
    const [tables] = await c.execute('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=?', [db]);
    if (init) {
      if (tables.length) throw new Error('--init requires an empty database; use db:migrate for an existing schema');
      const initial = statements(await readFile(new URL('SQLQuery1.sql', root), 'utf8'));
      for (const sql of initial.filter(s => /^CREATE TABLE/i.test(s))) await c.query(sql);
    }
    const files = ['001_auth_and_support.sql', '002_ticket_requests.sql', '003_chat_history.sql', '004_knowledge_rag.sql'];
    const [journal] = await c.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=? AND TABLE_NAME='SchemaMigration'", [db]);
    let recorded = [];
    if (journal.length) [recorded] = await c.query('SELECT Version,Step,Checksum,State FROM SchemaMigration ORDER BY Version,Step');
    if (recorded.some(r => r.Version < 1 || r.Version > files.length)) throw new Error('Unknown migration version; no automatic changes.');
    const plans = [];
    for (let index = 0; index < files.length; index++) {
      const sqlText = await readFile(new URL(`migrations/${files[index]}`, root), 'utf8');
      const hash = createHash('sha256').update(sqlText).digest('hex');
      const steps = statements(sqlText), version = index + 1;
      const previous = recorded.filter(r => r.Version === version);
      if (previous.length > steps.length || previous.some((r, i) => r.Step !== i + 1 || r.Checksum !== hash || r.State !== 'done')) throw new Error('Migration has changed or a step was interrupted. Inspect SchemaMigration and actual DDL; see migrations/README.md. No automatic retry.');
      if (previous.length && plans.some(p => p.remaining > 0)) throw new Error('Migration versions are out of order; inspect SchemaMigration.');
      plans.push({ version, hash, steps, remaining: steps.length - previous.length });
    }
    const remaining = plans.reduce((n, p) => n + p.remaining, 0);
    const total = plans.reduce((n, p) => n + p.steps.length, 0);
    if (!remaining) return { status: 'current', steps: total };
    if (plans[0].remaining) await preflight(c);
    if (check) return { status: 'ready', remaining };
    await c.query("CREATE TABLE IF NOT EXISTS SchemaMigration (Version INT NOT NULL, Step INT NOT NULL, Checksum CHAR(64) NOT NULL, State VARCHAR(10) NOT NULL, AppliedAt DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3), PRIMARY KEY(Version,Step)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");
    for (const plan of plans) {
      for (let i = plan.steps.length - plan.remaining; i < plan.steps.length; i++) {
        await c.execute("INSERT INTO SchemaMigration(Version,Step,Checksum,State) VALUES(?,?,?,'running')", [plan.version, i + 1, plan.hash]);
        await c.query(plan.steps[i]);
        await c.execute("UPDATE SchemaMigration SET State='done',AppliedAt=UTC_TIMESTAMP(3) WHERE Version=? AND Step=?", [plan.version, i + 1]);
      }
    }
    return { status: 'applied', steps: total };
  } finally {
    if (locked) await c.execute('SELECT RELEASE_LOCK(?)', [`vietincare:${db}`]).catch(() => {});
    await c.end();
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try { console.log(await migrate(config(), { init: process.argv.includes('--init'), check: process.argv.includes('--check') })); }
  catch (e) { console.error(e.code || e.message); process.exitCode = 1; }
}
