import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createGemini} from '../server/gemini.js';
import {createAI} from '../server/ai.js';
import {config} from '../server/config.js';
const vector = () => Array.from({length:768}, (_,i) => i === 0 ? 2 : 0);
const settings = {ai:{provider:'gemini',key:'fake-test-key',model:'gemini-2.5-flash'}};
const response = value => ({ok:true,json:async()=>value});
const generated = (text, finishReason='STOP') => ({candidates:[{finishReason,content:{parts:[{text}]}}]});

test('Gemini selection isolates provider keys and rejects unknown providers', () => {
  const env={AI_PROVIDER:'gemini',GEMINI_API_KEY:'fake-google',OPENAI_API_KEY:'fake-openai'};
  assert.equal(config(env).ai.key,'fake-google');
  assert.equal(config({...env,AI_PROVIDER:'openai'}).ai.key,'fake-openai');
  assert.equal(config({GEMINI_API_KEY:'fake-google'}).ai.provider,'gemini');
  assert.equal(createAI(config(env)).model,'gemini-embedding-001');
  assert.equal(createAI(config({...env,AI_PROVIDER:'openai'})).model,'text-embedding-3-small');
  assert.throws(()=>config({AI_PROVIDER:'other'}),/Invalid AI_PROVIDER/);
  assert.throws(()=>createGemini({ai:{model:'../bad?key=secret'}}),/Invalid GEMINI_CHAT_MODEL/);
});
test('Gemini embeds documents and queries separately, normalizes and preserves batch order', async () => {
  const calls=[];
  const ai=createAI(settings,async(url,options)=>{calls.push({url,options,body:JSON.parse(options.body)});return response({embeddings:[{values:vector()},{values:vector().map(v=>-v)}]});});
  const result=await ai.embed(['first','second']);
  assert.equal(result[0][0],1);assert.equal(result[1][0],-1);
  await ai.embed(['q1','q2'],'query');
  assert.equal(calls[0].url,'https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:batchEmbedContents');
  assert.equal(calls[0].url.includes(settings.ai.key),false);
  assert.equal(calls[0].options.headers['x-goog-api-key'],settings.ai.key);
  assert.equal(calls[0].options.redirect,'error');
  assert.equal(calls[0].body.requests[0].taskType,'RETRIEVAL_DOCUMENT');
  assert.equal(calls[1].body.requests[0].taskType,'RETRIEVAL_QUERY');
  assert.equal(calls[0].body.requests[0].outputDimensionality,768);
});
test('Gemini uses structured grounded answers and only returns supplied citation IDs', async () => {
  let request;
  const ai=createGemini(settings,async(url,options)=>{request={url,body:JSON.parse(options.body)};return response(generated('{"answer":" Có nguồn. ","source_ids":[7,7]}'));});
  assert.deepEqual(await ai.answer('question',[{id:7,title:'Guide',content:'fact'}],'vi'),{text:'Có nguồn.',sourceIds:[7]});
  assert.match(request.url,/gemini-2\.5-flash:generateContent$/);
  assert.equal(request.body.generationConfig.responseMimeType,'application/json');
  assert.equal(request.body.generationConfig.responseJsonSchema.additionalProperties,false);
  assert.equal(request.body.tools,undefined);
  assert.match(request.body.systemInstruction.parts[0].text,/Vietnamese/);
});
test('Gemini rejects blocked, truncated, malformed and fabricated responses', async () => {
  for(const value of [null,{},generated('{}','MAX_TOKENS'),generated('{}','SAFETY'),generated('null'),generated('not json'),generated('{"answer":"x","source_ids":[99]}'),generated('{"answer":42,"source_ids":[]}'),{promptFeedback:{blockReason:'SAFETY'}}]) {
    const ai=createGemini(settings,async()=>response(value));
    await assert.rejects(()=>ai.answer('x',[{id:1,title:'x',content:'x'}],'en'),/AI_INVALID_OUTPUT/);
  }
  const ai=createGemini(settings,async()=>response(generated('{"answer":"","source_ids":[]}')));
  assert.deepEqual(await ai.answer('unrelated',[],'en'),{text:'',sourceIds:[]});
});
test('Gemini rejects corrupt vectors, absent keys and sanitized provider failures', async () => {
  for(const value of [null,{}, {embeddings:[]},{embeddings:[{values:[1]}]},{embeddings:[{values:Array(768).fill(0)}]},{embeddings:[{values:Array(768).fill(NaN)}]}]) {
    await assert.rejects(()=>createGemini(settings,async()=>response(value)).embed(['x']),/AI_INVALID_OUTPUT/);
  }
  await assert.rejects(()=>createGemini({ai:{key:''}},()=>{throw Error('must not call');}).embed(['x']),/AI_NOT_CONFIGURED/);
  for(const status of [400,401,403,429,500]) {
    await assert.rejects(()=>createGemini(settings,async()=>({ok:false,status})).embed(['x']),status===429?/AI_RATE_LIMITED/:/AI_UNAVAILABLE/);
  }
  await assert.rejects(()=>createGemini(settings,async()=>{throw Error('sensitive request details');}).embed(['x']),/^Error: AI_UNAVAILABLE$/);
});
