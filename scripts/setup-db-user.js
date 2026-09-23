import mysql from 'mysql2/promise';

// Local setup only. Passwords come from the PowerShell wrapper, never files/arguments.
const user = 'vietincare_app';
const host = '127.0.0.1';
const database = 'qlkhviettin';
let admin, app;
let created = false;
try {
  const adminPassword = process.env.VIETINCARE_SETUP_ROOT_PASSWORD;
  const appPassword = process.env.VIETINCARE_SETUP_APP_PASSWORD;
  if (!adminPassword || !appPassword || appPassword.length < 12) {
    console.error('SETUP_INPUT_REQUIRED: root password and app password (12+ characters).');
    process.exitCode = 1;
  } else {
    admin = await mysql.createConnection({ host, port: 3306, user: 'root', password: adminPassword, connectTimeout: 5000 });
    const [[version]] = await admin.query('SELECT VERSION() version');
    if (!version.version.startsWith('8.0.46')) throw new Error('MYSQL_VERSION_REQUIRED');
    const [existing] = await admin.execute('SELECT Host FROM mysql.user WHERE User=?', [user]);
    if (existing.length) throw new Error('APP_USER_ALREADY_EXISTS');
    // Verify the migrated project exists before creating any account.
    await admin.query('SELECT TokenHash FROM qlkhviettin.AuthSession LIMIT 0');
    // In this session, quotes are escaped by doubling; backslashes remain literal.
    await admin.query("SET SESSION sql_mode = 'NO_BACKSLASH_ESCAPES'");
    const literal = value => "'" + value.replaceAll("'", "''") + "'";
    await admin.query(`CREATE USER '${user}'@'${host}' IDENTIFIED BY ${literal(appPassword)}`);
    created = true;
    await admin.query(`GRANT SELECT, INSERT, UPDATE, DELETE ON ${database}.* TO '${user}'@'${host}'`);
    app = await mysql.createConnection({ host, port: 3306, user, password: appPassword, database, connectTimeout: 5000 });
    const [[identity]] = await app.query('SELECT CURRENT_USER() identity');
    if (identity.identity !== `${user}@${host}`) throw new Error('UNEXPECTED_APP_IDENTITY');
    await app.query('SELECT TokenHash FROM AuthSession LIMIT 0');
    console.log('APP_USER_READY: vietincare_app; project data privileges only.');
  }
} catch (error) {
  // Never print SQL/error objects: these may contain passwords.
  const known = ['MYSQL_VERSION_REQUIRED', 'APP_USER_ALREADY_EXISTS', 'UNEXPECTED_APP_IDENTITY'];
  console.error(error.code || (known.includes(error.message) ? error.message : 'SETUP_FAILED'));
  if (created) console.error('Account was created. Inspect its grants before retrying; no password reset or deletion was performed.');
  process.exitCode = 1;
} finally {
  if (app) await app.end();
  if (admin) await admin.end();
}
