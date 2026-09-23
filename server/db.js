import mysql from 'mysql2/promise';

export function createPool(settings) { return mysql.createPool(settings.db); }
export async function connection(pool) {
  const c = await pool.getConnection();
  try {
    await c.query("SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci");
    await c.query("SET SESSION time_zone = '+00:00'");
    return c;
  } catch (e) { c.release(); throw e; }
}
export async function transaction(pool, work) {
  const c = await connection(pool);
  try { await c.beginTransaction(); const result = await work(c); await c.commit(); return result; }
  catch (e) { await c.rollback(); throw e; }
  finally { c.release(); }
}
export async function query(pool, sql, params = []) {
  const c = await connection(pool);
  try { return (await c.execute(sql, params))[0]; } finally { c.release(); }
}
