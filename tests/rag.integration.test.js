import {test} from 'node:test';
import assert from 'node:assert/strict';
import {randomBytes,randomUUID} from 'node:crypto';
import {once} from 'node:events';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import mysql from 'mysql2/promise';
import {config} from '../server/config.js';
import {migrate} from '../server/migrate.js';
import {createPool} from '../server/db.js';
import {createApp} from '../server/app.js';
import {hashPassword} from '../server/password.js';
import {createGemini} from '../server/gemini.js';
test('knowledge publication and grounded chat integration with a fake provider',{skip:process.env.RUN_MYSQL_TESTS!=='1'},async t=>{
 const suffix=randomBytes(6).toString('hex'),database=`vietincare_rag_test_${suffix}`,runtime=`rag_test_${suffix}`,password='Rag-test-only-2026!';
 const settings=config({...process.env,DB_NAME:database,OPENAI_API_KEY:''});let pool,server,created=false,granted=false,base;
 const admin=await mysql.createConnection({...settings.db,database:undefined,connectionLimit:undefined});
 let failEmbed=false,failAnswer=false,pause=null,embeddingCalls=0,answerCalls=0;
 const ai={enabled:true,model:'test-embedding',dimensions:2,async embed(texts){embeddingCalls++;if(failEmbed)throw Error('fake provider failure');return texts.map(s=>s.includes('unrelated')?[0,1]:[1,0]);},async answer(question,sources){answerCalls++;if(pause)await pause();if(failAnswer)throw Error('fake provider failure');return {text:'Câu trả lời kiểm thử từ nguồn đã xuất bản.',sourceIds:[sources[0].id]};}};
 async function api(path,cookie,body,key=randomUUID()){const r=await fetch(base+path,{method:body===undefined?'GET':'POST',headers:{...(cookie?{Cookie:cookie}:{}),...(body===undefined?{}:{Origin:settings.origin,'Content-Type':'application/json','X-Vietincare-Request':'1','Idempotency-Key':key})},body:body===undefined?undefined:JSON.stringify(body)});return{status:r.status,body:await r.json(),cookie:r.headers.get('set-cookie')?.split(';')[0]};}
 try{
  await migrate(settings,{init:true});created=true;await admin.query(`USE \`${database}\``);
  await admin.query(`CREATE USER '${runtime}'@'127.0.0.1' IDENTIFIED BY '${password}'`);granted=true;const[tables]=await admin.query('SHOW TABLES');for(const row of tables)await admin.query(`GRANT SELECT,INSERT,UPDATE,DELETE ON \`${database}\`.\`${Object.values(row)[0]}\` TO '${runtime}'@'127.0.0.1'`);
  pool=createPool({...settings,db:{...settings.db,host:'127.0.0.1',user:runtime,password}});server=createApp(pool,settings,{ai}).listen(0,'127.0.0.1');await once(server,'listening');base=`http://127.0.0.1:${server.address().port}`;
  const hash=await hashPassword(password),people=[];
  for(const[i,role]of ['Admin','Customer','Customer','Agent','Supervisor'].entries()){const email=`rag${i}@example.test`;const[r]=await admin.execute('INSERT INTO UserAccount(MaRole,HoTen,Username,Email,PasswordHash) SELECT MaRole,?,?,?,? FROM Role WHERE TenRole=?',[`Rag ${i}`,`rag${i}`,email,hash,role]);if(role==='Customer')await admin.execute('INSERT INTO Customer(MaUser,HoTen,Email) VALUES(?,?,?)',[r.insertId,`Rag ${i}`,email]);people.push((await api('/api/auth/login',null,{email,password})).cookie);}
  const[administrator,customer,other,agent,supervisor]=people;let documentId,chatId,messageId;
  async function question(content='How can I request support?'){const r=await api('/api/chats',customer,{content});assert.equal(r.status,201);return r.body;}
  const answer=(q)=>api(`/api/chats/${q.id}/messages/${q.messageId}/answer`,customer,{language:'vi'});
  await t.test('only admins manage sources and local admin provisioning remains private',async()=>{
   for(const cookie of [customer,agent,supervisor])assert.equal((await api('/api/knowledge',cookie)).status,403);assert.equal((await api('/api/knowledge',null)).status,401);
   await promisify(execFile)(process.execPath,['server/provision-admin.js'],{env:{...process.env,DB_NAME:database,VC_ADMIN_EMAIL:'provisioned@example.test',VC_ADMIN_NAME:'Provisioned Admin',VC_ADMIN_PASSWORD:password}});
   const [[row]]=await admin.query("SELECT r.TenRole FROM UserAccount u JOIN Role r ON r.MaRole=u.MaRole WHERE u.Email='provisioned@example.test'");assert.equal(row.TenRole,'Admin');
  });
  await t.test('draft creation retries are idempotent, edits use version checks, and drafts are excluded',async()=>{
   const key=randomUUID(),body={title:'Support instructions',content:'To request help, open Support tickets and describe your issue.'};const first=await api('/api/knowledge',administrator,body,key);documentId=first.body.id;assert.equal(first.status,201);assert.equal((await api('/api/knowledge',administrator,body,key)).body.id,documentId);
   assert.equal((await api(`/api/knowledge/${documentId}/save`,administrator,{version:9,...body})).status,409);
   assert.equal((await api(`/api/knowledge/${documentId}/publish`,administrator,{version:1})).status,409);
   const q=await question();assert.equal((await answer(q)).body.status,'no_sources');assert.equal(answerCalls,0);
  });
  await t.test('index errors leave draft safe; preview and publish require validated vectors',async()=>{
   failEmbed=true;assert.equal((await api(`/api/knowledge/${documentId}/index`,administrator,{version:1})).status,503);failEmbed=false;
   assert.equal((await api(`/api/knowledge/${documentId}`,administrator)).body.chunks.length,0);
   const key=randomUUID();assert.equal((await api(`/api/knowledge/${documentId}/index`,administrator,{version:1},key)).status,200);const calls=embeddingCalls;assert.equal((await api(`/api/knowledge/${documentId}/index`,administrator,{version:1},key)).status,200);assert.equal(embeddingCalls,calls);
   assert.equal((await api(`/api/knowledge/${documentId}/preview`,administrator,{version:1,question:'Support?'})).body.sources.length,1);
   assert.equal((await api(`/api/knowledge/${documentId}/publish`,administrator,{version:1})).status,200);
   assert.equal((await api(`/api/knowledge/${documentId}/save`,administrator,{version:1,title:'Edit published',content:'No'})).status,409);
  });
  await t.test('answers cite persisted snapshots, repeat without duplicate, and deny other owners',async()=>{
   const q=await question();chatId=q.id;messageId=q.messageId;const first=await answer(q);assert.equal(first.status,200);assert.equal(first.body.status,'answered');const calls=answerCalls;assert.equal((await answer(q)).body.messageId,first.body.messageId);assert.equal(answerCalls,calls);
   const detail=await api(`/api/chats/${q.id}`,customer);const reply=detail.body.messages.find(m=>m.replyTo===q.messageId);assert.equal(reply.sources.length,1);assert.equal(reply.sources[0].documentId,documentId);assert.equal(reply.sources[0].title,'Support instructions');
   assert.equal((await api(`/api/chats/${q.id}/messages/${q.messageId}/answer`,other,{language:'en'})).status,404);
   assert.equal((await api(`/api/chats/${q.id}/messages/${q.messageId}/answer`,agent,{})).status,403);
   const unrelated=await question('unrelated question');assert.equal((await answer(unrelated)).body.status,'no_sources');
  });
  await t.test('provider failure preserves the question and retry generates one answer',async()=>{
   const q=await question();failAnswer=true;assert.equal((await answer(q)).status,503);failAnswer=false;assert.equal((await api(`/api/chats/${q.id}`,customer)).body.messages.length,1);assert.equal((await answer(q)).status,200);assert.equal((await api(`/api/chats/${q.id}`,customer)).body.messages.length,2);
  });
  await t.test('concurrent generation locks; withdrawing sources cancels an in-flight answer',async()=>{
   let enter,release;const entered=new Promise(r=>enter=r),held=new Promise(r=>release=r);pause=async()=>{enter();await held;};const q=await question(),pending=answer(q);await entered;
   assert.equal((await answer(q)).status,409);assert.equal((await api(`/api/knowledge/${documentId}/archive`,administrator,{version:1})).status,200);release();assert.equal((await pending).status,409);pause=null;
   assert.equal((await api(`/api/chats/${q.id}`,customer)).body.messages.length,1);assert.equal((await answer(q)).body.status,'no_sources');
   const historical=await api(`/api/chats/${chatId}`,customer);assert.equal(historical.body.messages.find(m=>m.replyTo===messageId).sources[0].title,'Support instructions');
  });
  await t.test('published revision atomically replaces previous version and closed chats reject generation',async()=>{
   const original=(await api('/api/knowledge',administrator,{title:'Version one',content:'Support source v1'})).body.id;
   await api(`/api/knowledge/${original}/index`,administrator,{version:1});await api(`/api/knowledge/${original}/publish`,administrator,{version:1});
   const revised=(await api('/api/knowledge',administrator,{title:'Version two',content:'Support source v2',replacesId:original})).body.id;
   await api(`/api/knowledge/${revised}/index`,administrator,{version:1});assert.equal((await api(`/api/knowledge/${revised}/publish`,administrator,{version:1})).status,200);
   assert.equal((await api(`/api/knowledge/${original}`,administrator)).body.document.status,'Lưu trữ');
   const q=await question();await api(`/api/chats/${q.id}/close`,customer,{});assert.equal((await answer(q)).status,409);
  });
  await t.test('Gemini adapter indexes, previews and answers through MySQL without mixing old vectors',async()=>{
   const purposes=[];
   Object.assign(ai,createGemini({ai:{key:'fake-only',model:'gemini-2.5-flash'}},async(url,options)=>{
    const body=JSON.parse(options.body);
    if(url.endsWith(':batchEmbedContents')){
     purposes.push(...body.requests.map(r=>r.taskType));
     return {ok:true,json:async()=>({embeddings:body.requests.map(()=>({values:Array.from({length:768},(_,i)=>i===0?1:0)}))})};
    }
    const input=JSON.parse(body.contents[0].parts[0].text);
    return {ok:true,json:async()=>({candidates:[{finishReason:'STOP',content:{parts:[{text:JSON.stringify({answer:'Gemini transport fixture answer',source_ids:[input.sources[0].id]})}]}}]})};
   }));
   assert.equal((await api('/api/knowledge',administrator)).body.aiProvider,'gemini');
   const before=await question();assert.equal((await answer(before)).body.status,'no_sources');assert.equal(purposes.length,0);
   const draft=await api('/api/knowledge',administrator,{title:'Gemini source',content:'Open a support ticket to request help.'});const id=draft.body.id;
   assert.equal((await api(`/api/knowledge/${id}/index`,administrator,{version:1})).status,200);
   const detail=(await api(`/api/knowledge/${id}`,administrator)).body;
   assert.equal(detail.indexed,true);assert.equal(detail.chunks[0].model,'gemini-embedding-001');assert.equal(detail.chunks[0].dimensions,768);
   assert.equal((await api(`/api/knowledge/${id}/preview`,administrator,{version:1,question:'How to request help?'})).body.sources.length,1);
   assert.equal((await api(`/api/knowledge/${id}/publish`,administrator,{version:1})).status,200);
   const q=await question();assert.equal((await answer(q)).body.status,'answered');
   const history=(await api(`/api/chats/${q.id}`,customer)).body;
   assert.equal(history.aiProvider,'gemini');assert.equal(history.messages.find(m=>m.replyTo===q.messageId).sources[0].documentId,id);
   assert.deepEqual(purposes,['RETRIEVAL_DOCUMENT','RETRIEVAL_QUERY','RETRIEVAL_QUERY']);
  });
 }finally{if(server)await new Promise(r=>server.close(r));if(pool)await pool.end();if(!/^vietincare_rag_test_[a-f0-9]{12}$/.test(database))throw Error('Unsafe cleanup');if(created)await admin.query(`DROP DATABASE \`${database}\``);if(granted)await admin.query(`DROP USER '${runtime}'@'127.0.0.1'`);await admin.end();}
});
