import { test } from 'node:test';
import assert from 'node:assert/strict';
import { randomBytes, randomUUID, createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { once } from 'node:events';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import mysql from 'mysql2/promise';
import { config } from '../server/config.js';
import { migrate, statements } from '../server/migrate.js';
import { createPool, query } from '../server/db.js';
import { createApp } from '../server/app.js';
import { hashPassword } from '../server/password.js';

test('ticket workflow on real MySQL with restricted runtime grants', { skip: process.env.RUN_MYSQL_TESTS !== '1' }, async t => {
  const suffix=randomBytes(6).toString('hex'), db=`vietincare_test_${suffix}`, runtime=`vc_test_${suffix}`;
  const settings=config({...process.env,DB_NAME:db});
  const admin=await mysql.createConnection({...settings.db,database:undefined,connectionLimit:undefined});
  let pool, server, base, created=false, accountCreated=false;
  const password='Test-only-Password-2026!';
  async function api(path, token, body, key=randomUUID()) {
    const response=await fetch(base+path,{method:body === undefined?'GET':'POST',headers:{...(token?{Cookie:token}:{}),...(body === undefined?{}:{Origin:settings.origin,'Content-Type':'application/json','X-Vietincare-Request':'1','Idempotency-Key':key})},body:body === undefined?undefined:JSON.stringify(body)});
    return {status:response.status,body:await response.json(),cookie:response.headers.get('set-cookie')?.split(';')[0]};
  }
  try {
    await admin.query(`CREATE DATABASE \`${db}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci`); created=true;
    await admin.query(`USE \`${db}\``);
    const initial=statements(await readFile(new URL('../SQLQuery1.sql',import.meta.url),'utf8'));
    for(const sql of initial.filter(s=>/^CREATE TABLE/i.test(s))) await admin.query(sql);
    // Reproduce the deployed v1 journal and a pre-existing ticket before adding v2.
    const v1=await readFile(new URL('../migrations/001_auth_and_support.sql',import.meta.url),'utf8');
    await admin.query('CREATE TABLE SchemaMigration (Version INT NOT NULL,Step INT NOT NULL,Checksum CHAR(64) NOT NULL,State VARCHAR(10) NOT NULL,AppliedAt DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),PRIMARY KEY(Version,Step)) ENGINE=InnoDB');
    const v1steps=statements(v1), checksum=createHash('sha256').update(v1).digest('hex');
    for(let i=0;i<v1steps.length;i++) { await admin.query(v1steps[i]); await admin.execute("INSERT INTO SchemaMigration(Version,Step,Checksum,State) VALUES(1,?,?,'done')",[i+1,checksum]); }
    await admin.query("INSERT INTO Customer(HoTen) VALUES('Legacy customer')");
    await admin.query("INSERT INTO Ticket(MaKH,TieuDe,NoiDung) VALUES(1,'Legacy ticket','Keep this record')");
    await t.test('v1 upgrades without losing data and v2 is repeatable',async()=>{
      assert.deepEqual(await migrate(settings,{check:true}),{status:'ready',remaining:7});
      assert.equal((await migrate(settings)).status,'applied');
      assert.equal((await migrate(settings)).status,'current');
      const [[row]]=await admin.query('SELECT NoiDung FROM Ticket WHERE MaTicket=1'); assert.equal(row.NoiDung,'Keep this record');
    });
    await admin.query(`CREATE USER '${runtime}'@'127.0.0.1' IDENTIFIED BY '${password}'`); accountCreated=true;
    // Table-scoped test grants avoid underscores acting as database wildcards.
    const [tables]=await admin.query('SHOW TABLES');
    for(const row of tables) await admin.query(`GRANT SELECT,INSERT,UPDATE,DELETE ON \`${db}\`.\`${Object.values(row)[0]}\` TO '${runtime}'@'127.0.0.1'`);
    pool=createPool({...settings,db:{...settings.db,host:'127.0.0.1',user:runtime,password}});
    server=createApp(pool,settings).listen(0,'127.0.0.1'); await once(server,'listening'); base=`http://127.0.0.1:${server.address().port}`;
    const roles=['Customer','Customer','Agent','Agent','Supervisor','Admin'];
    const people=[];
    const hash=await hashPassword(password);
    for(let i=0;i<roles.length;i++) {
      const email=`person${i}@example.test`, role=roles[i];
      const [r]=await admin.execute('INSERT INTO UserAccount(MaRole,HoTen,Username,Email,PasswordHash) SELECT MaRole,?,?,?,? FROM Role WHERE TenRole=?',[`Person ${i}`,`person${i}`,email,hash,role]);
      if(role==='Customer') await admin.execute('INSERT INTO Customer(MaUser,HoTen,Email) VALUES(?,?,?)',[r.insertId,`Person ${i}`,email]);
      const login=await api('/api/auth/login',null,{email,password}); assert.equal(login.status,200);
      people.push({token:login.cookie,id:r.insertId});
    }
    const [customer,other,a,b,supervisor,adminUser]=people;
    let id,winner,loser;
    await t.test('administrative agent provisioning creates one Agent and refuses duplicate email',async()=>{
      const env={...process.env,DB_NAME:db,VC_AGENT_NAME:'CLI Agent',VC_AGENT_EMAIL:'cli-agent@example.test',VC_AGENT_PASSWORD:password};
      const run=promisify(execFile);
      const result=await run(process.execPath,['server/provision-agent.js'],{env});
      assert.match(result.stdout,/AGENT_CREATED/); assert.ok(!result.stdout.includes(password));
      await assert.rejects(run(process.execPath,['server/provision-agent.js'],{env}),e=>e.stderr.includes('ER_DUP_ENTRY') && !e.stderr.includes(password));
      const [[record]]=await admin.execute("SELECT r.TenRole FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole WHERE u.EmailNormalized='cli-agent@example.test'"); assert.equal(record.TenRole,'Agent');
      await assert.rejects(query(pool,'CREATE TABLE ShouldNotExist(Id INT)'),e=>e.code==='ER_TABLEACCESS_DENIED_ERROR');
    });
    await t.test('create persists, concurrent retries reuse one ticket and changed payload conflicts',async()=>{
      const key=randomUUID(),body={title:'Thẻ bị lỗi 🙂',content:'<img src=x onerror=alert(1)> Nội dung hỗ trợ'};
      const responses=await Promise.all([api('/api/tickets',customer.token,body,key),api('/api/tickets',customer.token,body,key)]);
      assert.deepEqual(responses.map(r=>r.status).sort(),[200,201]);
      id=responses[0].body.id; assert.equal(responses[1].body.id,id);
      assert.match(responses[0].body.code,/^TK-\d{6,}$/);
      assert.equal((await api('/api/tickets',customer.token,{...body,title:'Changed'},key)).status,409);
      const detail=await api(`/api/tickets/${id}`,customer.token); assert.equal(detail.status,200); assert.equal(detail.body.ticket.content,body.content); assert.equal(detail.body.history.length,1);
    });
    await t.test('ownership, roles, anonymous users and invalid input are rejected',async()=>{
      assert.equal((await api(`/api/tickets/${id}`,other.token)).status,404);
      assert.equal((await api(`/api/tickets/${id}/replies`,other.token,{content:'Intrusion'})).status,404);
      assert.equal((await api('/api/tickets',other.token)).body.tickets.length,0);
      assert.equal((await api('/api/tickets',null)).status,401);
      assert.equal((await api('/api/tickets',adminUser.token)).status,403);
      assert.equal((await api('/api/tickets',a.token,{title:'No',content:'No'})).status,403);
      assert.equal((await api('/api/tickets',customer.token,{title:' ',content:'x'})).status,400);
      assert.equal((await api('/api/tickets',customer.token,{title:'x',content:'x'.repeat(3001)})).status,400);
      assert.equal((await api('/api/tickets',customer.token,{title:'x',content:'y'},'bad')).status,400);
      assert.equal((await api('/api/tickets?before=oops',customer.token)).status,400);
      assert.equal((await api(`/api/tickets/${id}/replies`,a.token,{content:'Must claim first'})).status,403);
      assert.equal((await api(`/api/tickets/${id}`,supervisor.token)).status,200);
      assert.equal((await api(`/api/tickets/${id}/claim`,supervisor.token,{})).status,403);
    });
    await t.test('two agents race to claim; exactly one wins',async()=>{
      const responses=await Promise.all([api(`/api/tickets/${id}/claim`,a.token,{}),api(`/api/tickets/${id}/claim`,b.token,{})]);
      assert.deepEqual(responses.map(r=>r.status).sort(),[200,409]);
      winner=responses[0].status===200?a:b; loser=winner===a?b:a;
      assert.equal((await api(`/api/tickets/${id}`,loser.token)).status,404);
      assert.equal((await api(`/api/tickets/${id}/replies`,loser.token,{content:'Not assigned'})).status,404);
      assert.equal((await api(`/api/tickets/${id}/status`,customer.token,{status:'Đã đóng'})).status,403);
    });
    await t.test('agent reply is persisted once, visible to customer, and priority is validated',async()=>{
      assert.equal((await api(`/api/tickets/${id}/status`,winner.token,{status:'Đã giải quyết'})).body.error,'REPLY_REQUIRED');
      assert.equal((await api(`/api/tickets/${id}/status`,winner.token,{status:'Đã đóng'})).body.error,'INVALID_TRANSITION');
      const key=randomUUID(); const body={content:'Đã kiểm tra yêu cầu 🙂'};
      const replies=await Promise.all([api(`/api/tickets/${id}/replies`,winner.token,body,key),api(`/api/tickets/${id}/replies`,winner.token,body,key)]);
      assert.equal(replies[0].status,200); assert.equal(replies[0].body.replyId,replies[1].body.replyId);
      assert.equal((await api(`/api/tickets/${id}/priority`,winner.token,{priority:'Extreme'})).status,400);
      assert.equal((await api(`/api/tickets/${id}/priority`,winner.token,{priority:'Cao'})).status,200);
      const detail=await api(`/api/tickets/${id}`,customer.token); assert.equal(detail.body.replies.length,1); assert.equal(detail.body.replies[0].content,body.content); assert.equal(detail.body.ticket.priority,'Cao');
    });
    await t.test('resolve and close enforce the lifecycle, history, and read-only closed tickets',async()=>{
      assert.equal((await api(`/api/tickets/${id}/status`,winner.token,{status:'Đã giải quyết'})).status,200);
      assert.equal((await api(`/api/tickets/${id}/replies`,customer.token,{content:'Late reply'})).status,409);
      assert.equal((await api(`/api/tickets/${id}/status`,winner.token,{status:'Đã đóng'})).status,200);
      assert.equal((await api(`/api/tickets/${id}/status`,winner.token,{status:'Đang xử lý'})).status,400);
      const detail=await api(`/api/tickets/${id}`,customer.token);
      assert.equal(detail.body.ticket.status,'Đã đóng'); assert.ok(detail.body.ticket.closedAt);
      assert.deepEqual(detail.body.history.map(h=>h.status),['Mới','Đang xử lý','Đã giải quyết','Đã đóng']);
      assert.equal((await api(`/api/tickets/${id}/priority`,winner.token,{priority:'Thấp'})).status,409);
      const [[count]]=await admin.execute("SELECT COUNT(*) n FROM AuditLog WHERE DoiTuong='Ticket' AND MaDoiTuong=?",[id]); assert.equal(Number(count.n),6);
    });
    await t.test('list pagination is scoped, ordered, and preserves filters',async()=>{
      const [[c]]=await admin.execute('SELECT MaKH FROM Customer WHERE MaUser=?',[customer.id]);
      for(let i=0;i<31;i++) await admin.execute('INSERT INTO Ticket(MaKH,TieuDe,NoiDung) VALUES(?,?,?)',[c.MaKH,`Page ${i}`,'Test']);
      const first=await api('/api/tickets?status='+encodeURIComponent('Mới'),customer.token); assert.equal(first.body.tickets.length,30); assert.ok(first.body.next);
      const second=await api('/api/tickets?status='+encodeURIComponent('Mới')+'&before='+first.body.next,customer.token); assert.equal(second.body.tickets.length,1); assert.equal(second.body.next,null);
      assert.ok(second.body.tickets[0].id<first.body.next);
    });
  } finally {
    if(server) await new Promise(resolve=>server.close(resolve));
    if(pool) await pool.end();
    if(accountCreated && /^vc_test_[a-f0-9]{12}$/.test(runtime)) await admin.query(`DROP USER '${runtime}'@'127.0.0.1'`);
    if(created && /^vietincare_test_[a-f0-9]{12}$/.test(db)) await admin.query(`DROP DATABASE \`${db}\``);
    await admin.end();
  }
});
