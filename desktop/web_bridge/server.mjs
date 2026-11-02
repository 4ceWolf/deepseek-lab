/** Workspace's private chat-only gateway. Credentials never cross into Python/UI. */
import http from 'node:http';
import {historyClient} from './history.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { timingSafeEqual } from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { ChromeManager } from './runtime/browser/chrome.js';
import { LoginManager } from './runtime/browser/login.js';
import { findChromeExecutable } from './runtime/browser/chromePaths.js';
import { DeepSeekClient } from './runtime/deepseek/client.js';
import { SessionStore } from './runtime/deepseek/sessionStore.js';
import { DEFAULT_POW_WORKER_URL, CLIENT_HEADERS } from './runtime/config/constants.js';

export function chatPayload(body) {
 if(!body || !Array.isArray(body.messages) || !body.messages.length || body.messages.length>300)throw Error('Invalid messages');
 const messages=body.messages.map(m=>{
  if(!['user','assistant','system'].includes(m.role)||typeof m.content!=='string')throw Error('Invalid message');
  return {role:m.role,content:m.content};
 });
 if(!['deepseek-v4-flash','deepseek-v4-pro'].includes(body.model))throw Error('Invalid model');
 if(typeof body.thinking_enabled!=='boolean'||typeof body.search_enabled!=='boolean')throw Error('Invalid switches');
 if(body.search_enabled && body.model==='deepseek-v4-pro')throw Error('Search is available on Flash only');
 return {messages,model:body.model,thinking_enabled:body.thinking_enabled,search_enabled:body.search_enabled,
  ...(typeof body.conversation==='string' && body.conversation.length<128 ? {conversation:body.conversation}:{} )};
}
export function createGateway(client,key,probeBrowser=()=>true,history=null) {
 let ready=false,busy=false;
 const server=http.createServer(async(req,res)=>{
  const send=(status,value)=>{if(!res.headersSent)res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(value));};
  const supplied=Buffer.from(String(req.headers.authorization||'')),expected=Buffer.from('Bearer '+key);
  if(req.headers.origin || supplied.length!==expected.length || !timingSafeEqual(supplied,expected)){send(401,{error:'Unauthorized'});return;}
  if(req.method==='GET' && req.url==='/status'){send(200,{ready,busy,browser_available:probeBrowser()});return;}
  const historyRoute=req.method==='GET' && (req.url==='/history' || req.url.startsWith('/history/'));
  if(!historyRoute && (req.method!=='POST'||!['/login','/chat'].includes(req.url))){send(404,{error:'Not found'});return;}
  if(busy){send(409,{error:'Website connection is busy'});return;}
  busy=true;
  try {
   if(req.url==='/login'){
    if(!probeBrowser()){send(503,{error:'A system Chrome or Chromium browser is required. Nothing has been installed.'});return;}
    await client.initialize();ready=true;send(200,{ready:true});return;
   }
   if(!ready){send(409,{error:'Sign in to your website account first'});return;}
   if(historyRoute){if(!history)throw Error('History unavailable');send(200,req.url==='/history'?await history.list():await history.read(decodeURIComponent(req.url.slice(9))));return;}
   let raw='';for await(const chunk of req){raw+=chunk;if(Buffer.byteLength(raw)>1_000_000)throw Error('Request too large');}
   const payload=chatPayload(JSON.parse(raw));
   res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-store','X-Accel-Buffering':'no'});
   await client.streamChat(payload,chunk=>{
    // Neither compatibility tool calls nor provider credentials can reach execution.
    const choice=chunk.choices?.[0];const delta=choice?.delta||{};
    const event={content:typeof delta.content==='string'?delta.content:'',reasoning:typeof delta.reasoning_content==='string'?delta.reasoning_content:'',
     ...(chunk.conversation?{conversation:chunk.conversation}:{}),finish:choice?.finish_reason==='stop'};
    res.write('data: '+JSON.stringify(event)+'\n\n');
   });
   res.write('data: [DONE]\n\n');res.end();
  }catch{
   // Never forward upstream exceptions: they may include auth or browser diagnostics.
   if(!historyRoute)ready=false;
   const error=historyRoute?'Website history could not be loaded. Your saved chats are unchanged. Try refreshing history after reconnecting.':'Website request failed or login expired. Partial output is saved. Reconnect and start a new chat before retrying.';
   if(res.headersSent){res.write('data: '+JSON.stringify({error})+'\n\n');res.end();}else send(502,{error});
  }finally{busy=false;}
 });
 return server;
}

async function main(){
 process.umask(0o077);
 // Bootstrap over a private pipe, not process arguments or environment secrets.
 let raw='';const bootstrap=await new Promise((resolve,reject)=>{
  process.stdin.setEncoding('utf8');process.stdin.on('data',chunk=>{raw+=chunk;if(raw.length>16000)reject(Error('Invalid bootstrap'));const end=raw.indexOf('\n');if(end>=0)resolve(JSON.parse(raw.slice(0,end)));});
 });
 const dir=path.resolve(bootstrap.directory);fs.mkdirSync(dir,{recursive:true,mode:0o700});fs.chmodSync(dir,0o700);
 const config={port:0,host:'127.0.0.1',dataDir:dir,authFile:path.join(dir,'auth.json'),apiKeyFile:path.join(dir,'.unused-key'),sessionsFile:path.join(dir,'sessions.json'),chromeProfileDir:path.join(dir,'browser-profile'),
  chromePath:bootstrap.browser||undefined,cdpEndpoint:'http://127.0.0.1:0',powWorkerUrl:DEFAULT_POW_WORKER_URL,baseUrl:'https://chat.deepseek.com',debug:false,toolReasoning:'hidden',showBrowser:false};
 // Silence all upstream logs. Native service records safe operation metadata only.
 const logger={debug(){},info(){},warn(){},error(){}};
 const chrome=new ChromeManager(config,logger),login=new LoginManager(chrome,config,logger),sessions=new SessionStore(config.sessionsFile,logger);
 const client=new DeepSeekClient(config,login,sessions,logger);
 const server=createGateway(client,bootstrap.key,()=>{try{findChromeExecutable(config.chromePath);return true;}catch{return false;}},historyClient(login));
 server.requestTimeout=660_000;server.headersTimeout=10_000;server.maxConnections=8;
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
 process.stdout.write(JSON.stringify({port:server.address().port})+'\n');
 let closing=false;
 const close=async()=>{if(closing)return;closing=true;setTimeout(()=>process.exit(0),3000).unref();server.close();try{await chrome.browser?.close();}catch{}process.exit(0);};
 process.stdin.on('end',close);process.on('SIGTERM',close);process.on('SIGINT',close);
}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href){main().catch(()=>{process.stderr.write('Website bridge could not start. Check bundled files and Node 22+.\n');process.exit(1);});}
