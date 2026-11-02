import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createGateway,chatPayload } from './server.mjs';
const payload={model:'deepseek-v4-flash',messages:[{role:'user',content:'Hello'}],thinking_enabled:false,search_enabled:true};
test('payload rejects unsupported search and strips tools/untrusted fields',()=>{
 assert.throws(()=>chatPayload({...payload,model:'deepseek-v4-pro'}));
 const clean=chatPayload({...payload,tools:[{name:'run_command'}],api_key:'never-forward',messages:[{role:'user',content:'Hi',tool_calls:['fake']}]});
 assert.equal(clean.tools,undefined);assert.equal(clean.api_key,undefined);assert.equal(clean.messages[0].tool_calls,undefined);
});
test('loopback gateway enforces auth, origin guard, login and safe streamed output',async()=>{
 let logins=0,requests=0;
 const server=createGateway({initialize:async()=>{logins++;},streamChat:async(body,emit)=>{requests++;assert.equal(body.tools,undefined);emit({choices:[{delta:{content:'Answer',tool_calls:[{name:'run_command'}]}}]});emit({conversation:'s1',choices:[{delta:{},finish_reason:'stop'}]});}},'test-secret');
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const url='http://127.0.0.1:'+server.address().port;
 const headers={Authorization:'Bearer test-secret','Content-Type':'application/json'};
 try{
  assert.equal((await fetch(url+'/status')).status,401);
  assert.equal((await fetch(url+'/status',{headers:{...headers,Origin:'https://untrusted.example'}})).status,401);
  assert.equal((await fetch(url+'/chat',{method:'POST',headers,body:JSON.stringify(payload)})).status,409);
  assert.equal(logins,0);assert.equal(requests,0);
  assert.equal((await fetch(url+'/login',{method:'POST',headers})).status,200);
  const response=await fetch(url+'/chat',{method:'POST',headers,body:JSON.stringify({...payload,tools:[{name:'run_command'}]})});const text=await response.text();
  assert.equal(response.status,200);assert.match(text,/Answer/);assert.match(text,/\[DONE\]/);assert.doesNotMatch(text,/run_command|tool_calls|test-secret/);assert.equal(logins,1);assert.equal(requests,1);
 }finally{await new Promise(r=>server.close(r));}
});
test('missing browser reports prerequisite without initializing the provider',async()=>{
 const server=createGateway({initialize:async()=>assert.fail('must not launch')},'key',()=>false);
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 try{const r=await fetch('http://127.0.0.1:'+server.address().port+'/login',{method:'POST',headers:{Authorization:'Bearer key'}});assert.equal(r.status,503);assert.match(await r.text(),/Nothing has been installed/);}
 finally{await new Promise(r=>server.close(r));}
});
test('upstream exceptions never expose credentials',async()=>{
 const server=createGateway({initialize:async()=>{throw Error('Bearer secret-cookie-token');}},'key');await new Promise(r=>server.listen(0,'127.0.0.1',r));
 try{const r=await fetch('http://127.0.0.1:'+server.address().port+'/login',{method:'POST',headers:{Authorization:'Bearer key'}});assert.equal(r.status,502);assert.doesNotMatch(await r.text(),/secret-cookie-token/);}
 finally{await new Promise(r=>server.close(r));}
});

import { streamPlainChat } from './runtime/deepseek/chatStream.js';
function websiteStream(parts){return new Response(parts.join(''),{status:200});}
const ready='event: ready\ndata: {"request_message_id":1,"response_message_id":2}\n\n';
const fragment=(type,content)=>'data: '+JSON.stringify({p:'response/fragments',o:'APPEND',v:[{type,content}]})+'\n\n';
test('real stream mapper separates thought, final answer and terminal receipt',async()=>{
 const chunks=[];const result=await streamPlainChat({sessionId:'s1',publicModel:'deepseek-v4-flash',upstream:websiteStream([ready,fragment('THINK','Hidden thought'),fragment('RESPONSE','Visible answer'),'data: {"p":"response/status","v":"FINISHED"}\n\n'])},c=>chunks.push(c));
 assert.equal(result.finalText,'Visible answer');assert.equal(result.responseMessageId,2);
 const visible=chunks.map(c=>c.choices[0].delta.content||'').join('');assert.equal(visible,'Visible answer');assert.ok(chunks.some(c=>c.choices[0].finish_reason==='stop'));
});
test('truncated and thought-only streams cannot become completed answers',async()=>{
 for(const parts of [[ready,fragment('RESPONSE','Partial')],[ready,fragment('THINK','Hidden only'),'event: close\ndata: {}\n\n']]){
  const chunks=[];await assert.rejects(streamPlainChat({sessionId:'s1',publicModel:'deepseek-v4-flash',upstream:websiteStream(parts)},c=>chunks.push(c)),/Incomplete/);
  assert.equal(chunks.some(c=>c.choices[0].finish_reason==='stop'),false);assert.equal(chunks.some(c=>c.choices[0].delta.content==='Hidden only'),false);
 }
});
