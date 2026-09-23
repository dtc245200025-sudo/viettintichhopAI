import test from 'node:test';
import assert from 'node:assert/strict';
import { hashPassword, verifyPassword } from '../server/password.js';
test('salted scrypt verifies Unicode passwords and rejects wrong/legacy hashes', async () => {
  const password = 'Mật-khẩu-thử-nghiệm-🙂';
  const a = await hashPassword(password), b = await hashPassword(password);
  assert.notEqual(a, b); assert.ok(!a.includes(password));
  assert.equal(await verifyPassword(password, a), true);
  assert.equal(await verifyPassword('wrong-password', a), false);
  assert.equal(await verifyPassword(password, 'legacy-plaintext'), false);
});
