// Build vendored TypeScript with Node's compiler; no package installation.
import fs from 'node:fs';
import path from 'node:path';
import { stripTypeScriptTypes } from 'node:module';
const base=path.dirname(new URL(import.meta.url).pathname);
const source=path.join(base,'upstream/src'),target=path.join(base,'runtime');
function walk(folder){return fs.readdirSync(folder,{withFileTypes:true}).flatMap(e=>e.isDirectory()?walk(path.join(folder,e.name)):[path.join(folder,e.name)]);}
for(const file of walk(source).filter(f=>f.endsWith('.ts'))){
 let code=fs.readFileSync(file,'utf8');
 // Only connect to this app's managed browser. Never attach to a personal CDP session.
 if(file.endsWith('/browser/chrome.ts'))code=code.replace('push(this.config.cdpEndpoint);','// Foreign browser attachment disabled by Workspace.');
 // Bound interactive login, which upstream otherwise waits for indefinitely.
 if(file.endsWith('/browser/login.ts'))code=code.replace('while (true) {','const deadline = Date.now() + 300_000;\n    while (true) {\n      if (Date.now() > deadline) throw new Error(\"Login timed out\");');
 // Never promote hidden thinking to an answer or accept a disconnected stream as complete.
 if(file.endsWith('/deepseek/chatStream.ts')){
  code=code.replace('  let responseMessageId: MessageId = null;', '  let responseMessageId: MessageId = null;\n  let closed = false;');
  code=code.replace('    if (update.type === "ready") {','    if (update.type === "close") closed = true;\n    if (update.type === "ready") {');
  code=code.replace('  const finalText = responseText.trim() ? responseText : reasoningText;\n  if (!responseText.trim() && reasoningText) writeDelta({ content: reasoningText });', '  if (!closed || !responseText.trim() || responseMessageId === null) throw new Error("Incomplete website answer");\n  const finalText = responseText;');
 }
 if(file.endsWith('/deepseek/updates.ts')){
  code=code.replace('    const responseData = nestedResponse(data);', '    if (data.p === "response/status" && data.v === "FINISHED") { yield { type: "close" }; break; }\n    const responseData = nestedResponse(data);');
  code=code.replace('      continue;\n    }\n\n    if (data.p === "response/fragments"', '      if (responseData.status === "FINISHED") { yield { type: "close" }; break; }\n      continue;\n    }\n\n    if (data.p === "response/fragments"');
  code=code.replace('      for (const patch of data.v) {', '      for (const patch of data.v) {\n        if (isRecord(patch) && (patch.p === "status" || patch.p === "quasi_status") && patch.v === "FINISHED") yield { type: "close" };');
 }
 if(file.endsWith('/deepseek/sse.ts'))code=code.replace('    this.buffer += chunk;', '    this.buffer += chunk;\n    if (this.buffer.length > 1_000_000) throw new Error("Website stream frame limit");');
 code=code.replace(/constructor\(([^)]*)\)\s*\{/g,(_,params)=>{
  const names=[...params.matchAll(/(?:private|public|protected)\s+(?:readonly\s+)?(\w+)\s*:/g)].map(m=>m[1]);
  const plain=params.replace(/\b(?:private|public|protected|readonly)\s+/g,'');
  return 'constructor('+plain+') {'+names.map(n=>'this.'+n+' = '+n+';').join('');
 });
 let js=stripTypeScriptTypes(code,{mode:'strip',sourceMap:false});
 if(file.endsWith('/browser/chrome.ts'))js=js.replace('from "playwright-core"','from "../../vendor/playwright-core/index.mjs"');
 const out=path.join(target,path.relative(source,file).replace(/\.ts$/,'.js'));fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,js);
}
console.log('Built website bridge runtime. No browser or package installation.');
