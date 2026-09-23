import { config } from './config.js';
import { createPool, query } from './db.js';
import { createApp } from './app.js';
const settings = config();
const pool = createPool(settings);
try {
  await query(pool, 'SELECT TokenHash FROM AuthSession LIMIT 0');
  await query(pool, 'SELECT RequestKey FROM TicketRequest LIMIT 0');
  await query(pool, 'SELECT RequestKey FROM ChatRequest LIMIT 0');
  await query(pool, 'SELECT ReplyTo FROM Message LIMIT 0');
  const app = createApp(pool, settings);
  const server = app.listen(settings.port, settings.host, () => console.log(`VietinCare: ${settings.origin}`));
  // Expired sessions/attempt windows contain no useful live state.
  const timer = setInterval(async () => {
    try { await query(pool, 'DELETE FROM AuthSession WHERE ExpiresAt<=UTC_TIMESTAMP(3)'); await query(pool, 'DELETE FROM AuthThrottle WHERE WindowEnd<=UTC_TIMESTAMP(3)'); }
    catch(e) { console.error('Session cleanup:', e.code || e.name); }
  }, 15 * 60 * 1000).unref();
  const close = () => { clearInterval(timer); server.close(() => pool.end()); };
  process.on('SIGINT', close); process.on('SIGTERM', close);
} catch (e) { console.error('Startup failed:', e.code || e.name, 'Check MySQL credentials and run db:migrate.'); await pool.end(); process.exitCode = 1; }
