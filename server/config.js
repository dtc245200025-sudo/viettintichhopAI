export function config(env = process.env) {
  const provider = env.AI_PROVIDER || (env.GEMINI_API_KEY ? 'gemini' : 'openai');
  if (!['gemini', 'openai'].includes(provider)) throw new Error('Invalid AI_PROVIDER');
  const integer = (key, fallback, min, max) => {
    const value = Number(env[key] ?? fallback);
    if (!Number.isInteger(value) || value < min || value > max) throw new Error(`Invalid ${key}`);
    return value;
  };
  const origin = new URL(env.APP_ORIGIN || 'http://localhost:3000');
  if (!['http:', 'https:'].includes(origin.protocol) || origin.pathname !== '/') throw new Error('Invalid APP_ORIGIN');
  const secure = env.COOKIE_SECURE === 'true';
  if (env.NODE_ENV === 'production' && (!secure || origin.protocol !== 'https:')) throw new Error('Production requires HTTPS and secure cookies');
  const database = env.DB_NAME || 'QLKHViettin';
  if (!/^[a-zA-Z][a-zA-Z0-9_]{0,63}$/.test(database)) throw new Error('Invalid DB_NAME');
  return {
    ai: { provider, key: (provider === 'gemini' ? env.GEMINI_API_KEY : env.OPENAI_API_KEY) || '', model: provider === 'gemini' ? (env.GEMINI_CHAT_MODEL || 'gemini-2.5-flash') : (env.OPENAI_CHAT_MODEL || 'gpt-4.1-mini'), threshold: 0.35 },
    host: env.HOST || '127.0.0.1', port: integer('PORT', 3000, 1, 65535), origin: origin.origin,
    secure, sessionHours: integer('SESSION_HOURS', 8, 1, 24),
    db: { host: env.DB_HOST || '127.0.0.1', port: integer('DB_PORT', 3306, 1, 65535),
      user: env.DB_USER || 'vietincare_app', password: env.DB_PASSWORD || '', database,
      charset: 'utf8mb4', timezone: 'Z', supportBigNumbers: true, bigNumberStrings: true,
      connectionLimit: 10, multipleStatements: false, connectTimeout: 5000 }
  };
}
