import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createOpenAI,validVector,cosine,splitKnowledge} from '../server/openai.js';
const vector=()=>Array.from({length:512},(_,i)=>i===0?1:0);
test('embedding validation, cosine and Unicode chunk boundaries',()=>{
 assert.equal(validVector(Array(512).fill(0)),false);assert.equal(validVector([NaN]),false);assert.equal(validVector(vector()),true);
 assert.equal(cosine([1,0],[1,0]),1);assert.equal(cosine([1,0],[0,1]),0);assert.equal(cosine([1,0],[1]),-1);
 const chunks=splitKnowledge('🙂'.repeat(1700));assert.equal(chunks.length,3);assert.equal(Array.from(chunks[0]).length,800);assert.ok(chunks.every(s=>!s.includes('\ufffd')));
});
test('OpenAI requests use fixed HTTPS endpoints, bounded schema and no response storage',async()=>{
 const calls=[];const ai=createOpenAI({ai:{key:'test-only-key',model:'gpt-4.1-mini'}},async(url,options)=>{const body=JSON.parse(options.body);calls.push({url,body});return {ok:true,json:async()=>url.endsWith('embeddings')?{data:[{index:0,embedding:vector()}]}:{status:'completed',output:[{type:'message',content:[{type:'output_text',text:JSON.stringify({answer:'A supported answer.',source_ids:[7]})}]}]}};});
 assert.deepEqual(await ai.embed(['test']),[vector()]);assert.deepEqual(await ai.answer('question',[{id:7,title:'Source',content:'fact'}],'en'),{text:'A supported answer.',sourceIds:[7]});
 assert.equal(calls[0].url,'https://api.openai.com/v1/embeddings');assert.equal(calls[0].body.dimensions,512);assert.equal(calls[1].url,'https://api.openai.com/v1/responses');assert.equal(calls[1].body.store,false);assert.equal(calls[1].body.text.format.strict,true);assert.equal(calls[1].body.tools,undefined);
});
test('missing keys, malformed embeddings, unsupported citations and service errors fail closed',async()=>{
 const disabled=createOpenAI({ai:{key:''}},()=>{throw Error('must not call');});await assert.rejects(()=>disabled.embed(['x']),/AI_NOT_CONFIGURED/);
 const invalid=createOpenAI({ai:{key:'test'}},async()=>({ok:true,json:async()=>({data:[{index:0,embedding:Array(512).fill(0)}]})}));await assert.rejects(()=>invalid.embed(['x']),/AI_INVALID_OUTPUT/);
 const fabricated=createOpenAI({ai:{key:'test',model:'test'}},async()=>({ok:true,json:async()=>({status:'completed',output:[{type:'message',content:[{type:'output_text',text:'{"answer":"unsupported","source_ids":[999]}'}]}]})}));await assert.rejects(()=>fabricated.answer('x',[{id:1,title:'a',content:'a'}],'vi'),/AI_INVALID_OUTPUT/);
 const limited=createOpenAI({ai:{key:'test'}},async()=>({ok:false,status:429}));await assert.rejects(()=>limited.embed(['x']),/AI_RATE_LIMITED/);
 const timedout=createOpenAI({ai:{key:'test'}},async()=>{throw Error('network details that should not leak');});await assert.rejects(()=>timedout.embed(['x']),/AI_UNAVAILABLE/);
});
