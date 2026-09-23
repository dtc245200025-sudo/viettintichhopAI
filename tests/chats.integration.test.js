import { test } from 'node:test';
import assert from 'node:assert/strict';
import { randomBytes,randomUUID,createHash } from 'node:crypto';
import { once } from 'node:events';
import { readFile } from 'node:fs/promises';
import mysql from 'mysql2/promise';
import { config } from '../server/config.js';
import { migrate,statements } from '../server/migrate.js';
import { createPool } from '../server/db.js';
import { createApp } from '../server/app.js';
import { hashPassword } from '../server/password.js';

test('persistent customer conversations on MySQL', {skip:process.env.RUN_MYSQL_TESTS!=='1'},async t=>{
  const suffix=randomBytes(6).toString('hex'),database=`vietincare_chat_test_${suffix}`,runtime=`chat_test_${suffix}`;
  const settings=config({...process.env,DB_NAME:database}), password='Chat-test-only-2026!';
  const admin=await mysql.createConnection({...settings.db,database:undefined,connectionLimit:undefined});
  let pool,server,base,created=false,granted=false;
  async function api(path,cookie,body,key=randomUUID(),origin=settings.origin) {
    const res=await fetch(base+path,{method:body===undefined?'GET':'POST',headers:{...(cookie?{Cookie:cookie}:{}),...(body===undefined?{}:{Origin:origin,'Content-Type':'application/json','X-Vietincare-Request':'1','Idempotency-Key':key})},body:body===undefined?undefined:JSON.stringify(body)});
    return {status:res.status,body:await res.json(),cookie:res.headers.get('set-cookie')?.split(';')[0]};
  }
  try {
    await admin.query(`CREATE DATABASE \`${database}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci`);created=true;
    await admin.query(`USE \`${database}\``);
    for(const sql of statements(await readFile(new URL('../SQLQuery1.sql',import.meta.url),'utf8')).filter(s=>/^CREATE TABLE/i.test(s))) await admin.query(sql);
    await admin.query('CREATE TABLE SchemaMigration (Version INT NOT NULL,Step INT NOT NULL,Checksum CHAR(64) NOT NULL,State VARCHAR(10) NOT NULL,AppliedAt DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),PRIMARY KEY(Version,Step)) ENGINE=InnoDB');
    for(const [index,file] of ['001_auth_and_support.sql','002_ticket_requests.sql'].entries()) {
      const source=await readFile(new URL('../migrations/'+file,import.meta.url),'utf8'), hash=createHash('sha256').update(source).digest('hex');
      for(const [step,sql] of statements(source).entries()) { await admin.query(sql); await admin.execute("INSERT INTO SchemaMigration(Version,Step,Checksum,State) VALUES(?,?,?,'done')",[index+1,step+1,hash]); }
    }
    await admin.query("INSERT INTO Customer(HoTen) VALUES('Legacy chat owner')");
    await admin.query('INSERT INTO ChatSession(MaKH) VALUES(1)');
    await admin.query("INSERT INTO Message(MaSession,NguoiGui,NoiDung) VALUES(1,'Customer','Lịch sử cũ 🙂')");
    await t.test('v2 migration preserves legacy history and is repeatable',async()=>{
      assert.deepEqual(await migrate(settings,{check:true}),{status:'ready',remaining:6});
      assert.deepEqual(await migrate(settings),{status:'applied',steps:22});
      assert.deepEqual(await migrate(settings),{status:'current',steps:22});
      const [[old]]=await admin.query('SELECT NoiDung FROM Message WHERE MaSession=1');assert.equal(old.NoiDung,'Lịch sử cũ 🙂');
    });
    await admin.query(`CREATE USER '${runtime}'@'127.0.0.1' IDENTIFIED BY '${password}'`);granted=true;
    const [tables]=await admin.query('SHOW TABLES');
    for(const row of tables) await admin.query(`GRANT SELECT,INSERT,UPDATE,DELETE ON \`${database}\`.\`${Object.values(row)[0]}\` TO '${runtime}'@'127.0.0.1'`);
    pool=createPool({...settings,db:{...settings.db,host:'127.0.0.1',user:runtime,password}});
    server=createApp(pool,settings).listen(0,'127.0.0.1');await once(server,'listening');base=`http://127.0.0.1:${server.address().port}`;
    const hash=await hashPassword(password),people=[];
    for(const [i,role] of ['Customer','Customer','Agent','Supervisor','Admin'].entries()) {
      const email=`chat${i}@example.test`;
      const [r]=await admin.execute('INSERT INTO UserAccount(MaRole,HoTen,Username,Email,PasswordHash) SELECT MaRole,?,?,?,? FROM Role WHERE TenRole=?',[`Chat ${i}`,`chat${i}`,email,hash,role]);
      let customerId;
      if(role==='Customer') { const [c]=await admin.execute('INSERT INTO Customer(MaUser,HoTen,Email) VALUES(?,?,?)',[r.insertId,`Chat ${i}`,email]); customerId=c.insertId; }
      const login=await api('/api/auth/login',null,{email,password});assert.equal(login.status,200);people.push({id:r.insertId,customerId,cookie:login.cookie});
    }
    const owner=people[0],other=people[1];let id,firstKey;
    await t.test('first message and concurrent retry create exactly one conversation',async()=>{
      firstKey=randomUUID(); const body={content:'Xin chào 🙂 <img src=x onerror=alert(1)>'};
      const results=await Promise.all([api('/api/chats',owner.cookie,body,firstKey),api('/api/chats',owner.cookie,body,firstKey)]);
      assert.deepEqual(results.map(r=>r.status).sort(),[200,201]);id=results[0].body.id;assert.equal(id,results[1].body.id);
      const detail=await api(`/api/chats/${id}`,owner.cookie);assert.equal(detail.body.messages.length,1);assert.equal(detail.body.messages[0].content,body.content);assert.equal(detail.body.messages[0].userId,owner.id);assert.equal(detail.body.assistantStatus,'not_configured');
      assert.equal((await api('/api/chats',owner.cookie,{content:'Different'},firstKey)).status,409);
    });
    await t.test('anonymous, wrong owner, staff roles and malformed inputs are rejected',async()=>{
      assert.equal((await api('/api/chats',null)).status,401);
      for(const person of people.slice(2)) assert.equal((await api('/api/chats',person.cookie)).status,403);
      assert.equal((await api(`/api/chats/${id}`,other.cookie)).status,404);
      assert.equal((await api(`/api/chats/${id}/messages`,other.cookie,{content:'No access'})).status,404);
      assert.equal((await api(`/api/chats/${id}/close`,other.cookie,{})).status,404);
      for(const content of ['', '   ', 'x'.repeat(3001), 12])assert.equal((await api('/api/chats',owner.cookie,{content})).status,400);
      assert.equal((await api('/api/chats',owner.cookie,{content:'Hello'},'bad-key')).status,400);
      assert.equal((await api('/api/chats',owner.cookie,{content:'Hello'},randomUUID(),'http://untrusted.test')).status,403);
      assert.equal((await api('/api/chats?before=abc',owner.cookie)).status,400);
      assert.equal((await api(`/api/chats/${id}?before=-1`,owner.cookie)).status,400);
      assert.equal((await api('/api/chats/2147483648',owner.cookie)).status,400);
    });
    await t.test('message replay survives a new application instance and does not duplicate',async()=>{
      const key=randomUUID(),body={content:'Tin nhắn thứ hai'};
      const results=await Promise.all([api(`/api/chats/${id}/messages`,owner.cookie,body,key),api(`/api/chats/${id}/messages`,owner.cookie,body,key)]);
      assert.equal(results[0].body.messageId,results[1].body.messageId);
      await new Promise(resolve=>server.close(resolve));server=createApp(pool,settings).listen(0,'127.0.0.1');await once(server,'listening');base=`http://127.0.0.1:${server.address().port}`;
      assert.equal((await api(`/api/chats/${id}/messages`,owner.cookie,body,key)).body.replayed,true);
      assert.equal((await api(`/api/chats/${id}`,owner.cookie)).body.messages.length,2);
    });
    await t.test('message and conversation pagination are ordered and scoped',async()=>{
      for(let i=0;i<53;i++) await admin.execute("INSERT INTO Message(MaSession,NguoiGui,MaUser,NoiDung) VALUES(?,'Customer',?,?)",[id,owner.id,`Older message ${i}`]);
      const first=await api(`/api/chats/${id}`,owner.cookie);assert.equal(first.body.messages.length,50);assert.ok(first.body.next);
      const older=await api(`/api/chats/${id}?before=${first.body.next}`,owner.cookie);assert.equal(older.body.messages.length,5);assert.equal(older.body.next,null);assert.ok(older.body.messages.at(-1).id<first.body.messages[0].id);
      for(let i=0;i<31;i++)await admin.execute('INSERT INTO ChatSession(MaKH,TieuDe) VALUES(?,?)',[owner.customerId,`Chat ${i}`]);
      await api('/api/chats',other.cookie,{content:'Private other chat'});
      const page=await api('/api/chats',owner.cookie);assert.equal(page.body.chats.length,30);assert.ok(page.body.next);
      const tail=await api(`/api/chats?before=${page.body.next}`,owner.cookie);assert.equal(tail.body.chats.length,2);assert.equal(tail.body.next,null);
      assert.equal((await api('/api/chats',other.cookie)).body.chats.length,1);
    });
    await t.test('close and send serialize; ended history stays read-only',async()=>{
      const results=await Promise.all([api(`/api/chats/${id}/close`,owner.cookie,{}),api(`/api/chats/${id}/messages`,owner.cookie,{content:'Concurrent final message'})]);
      assert.equal(results[0].status,200);assert.ok([200,409].includes(results[1].status));
      assert.equal((await api(`/api/chats/${id}/messages`,owner.cookie,{content:'After close'})).status,409);
      assert.equal((await api(`/api/chats/${id}/close`,owner.cookie,{})).status,200);
      const detail=await api(`/api/chats/${id}`,owner.cookie);assert.ok(detail.body.chat.closedAt);assert.equal(detail.body.chat.status,'Đã kết thúc');
      const [[audit]]=await admin.execute("SELECT COUNT(*) n FROM AuditLog WHERE DoiTuong='ChatSession' AND MaDoiTuong=? AND HanhDong='CHAT_CLOSE'",[id]);assert.equal(Number(audit.n),1);
    });
  } finally {
    if(server)await new Promise(resolve=>server.close(resolve));if(pool)await pool.end();
    if(!/^vietincare_chat_test_[a-f0-9]{12}$/.test(database))throw Error('Unsafe cleanup target');
    if(created)await admin.query(`DROP DATABASE \`${database}\``);
    if(granted)await admin.query(`DROP USER '${runtime}'@'127.0.0.1'`);
    await admin.end();
  }
});

