/** Bounded, read-only website history. Never returns auth, arbitrary URLs or raw provider payloads. */
import {CLIENT_HEADERS} from './runtime/config/constants.js';
export function sessionId(value){if(typeof value!=='string'||! /^[a-zA-Z0-9_-]{1,128}$/.test(value))throw Error('Invalid conversation ID');return value;}
export function unwrap(value){if(value?.code!==0||(value.data?.biz_code!==undefined&&value.data.biz_code!==0)||!value.data?.biz_data)throw Error('History unavailable');return value.data.biz_data;}
export function directory(value){const data=unwrap(value);if(!Array.isArray(data.chat_sessions))throw Error('Unknown directory format');if(data.chat_sessions.length>100)throw Error('Directory limit');return {sessions:data.chat_sessions.map(s=>({id:sessionId(s.id),title:typeof s.title==='string'?s.title.slice(0,200):'Website conversation',updated:typeof s.updated_at==='number'?s.updated_at:0})),limited:data.chat_sessions.length===100};}
export function transcript(value){const data=unwrap(value);const rows=data.chat_messages??data.messages;if(!Array.isArray(rows)||rows.length>2000)throw Error('Unknown history format or limit');let total=0;const messages=rows.map(m=>{
 const role=String(m.role||'').toLowerCase();if(!['user','assistant'].includes(role))throw Error('Unsupported message role');
 let content=typeof m.content==='string'?m.content:null;
 if(Array.isArray(m.fragments))content=m.fragments.filter(f=>['RESPONSE','REQUEST','TEXT'].includes(String(f.type).toUpperCase())).map(f=>typeof f.content==='string'?f.content:'').join('\n');
 if(content===null)throw Error('Unsupported message content');total+=content.length;if(total>500000)throw Error('History display limit');
 return {role,content};
 });return {messages,read_only:true,notice:'Imported website history · read-only. Continue the original conversation on the official website. Attachments and reasoning are not imported.'};}
export function historyClient(login,fetcher=fetch){
 async function get(route){const auth=await login.dumpCurrent();const response=await fetcher('https://chat.deepseek.com'+route,{headers:{...CLIENT_HEADERS,authorization:'Bearer '+auth.token,cookie:auth.cookie,referer:'https://chat.deepseek.com/'},redirect:'error',signal:AbortSignal.timeout(30000)});if(!response.ok)throw Error('History request failed');let raw='',bytes=0;const decoder=new TextDecoder();for await(const chunk of response.body){bytes+=chunk.length;if(bytes>3_000_000)throw Error('History response too large');raw+=decoder.decode(chunk,{stream:true});}raw+=decoder.decode();return JSON.parse(raw);}
 return {list:async()=>directory(await get('/api/v0/chat_session/fetch_page?count=100')),read:async id=>transcript(await get('/api/v0/chat/history_messages?chat_session_id='+encodeURIComponent(sessionId(id))))};
}
