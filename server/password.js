import { scrypt as scryptCallback, randomBytes, timingSafeEqual, createHash } from 'node:crypto';
import { promisify } from 'node:util';
const scrypt = promisify(scryptCallback);
const options = { N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 };
export const digest = text => createHash('sha256').update(text).digest();
export async function hashPassword(password) {
  const salt = randomBytes(16).toString('hex');
  const key = await scrypt(password, salt, 32, options);
  return `scrypt$32768$8$1$${salt}$${key.toString('hex')}`;
}
export async function verifyPassword(password, stored) {
  const match = /^scrypt\$32768\$8\$1\$([a-f0-9]{32})\$([a-f0-9]{64})$/.exec(stored || '');
  // Unknown/legacy accounts still pay the same password verification cost.
  const key = await scrypt(password, match?.[1] || '00000000000000000000000000000000', 32, options);
  return Boolean(match) && timingSafeEqual(key, Buffer.from(match[2], 'hex'));
}
