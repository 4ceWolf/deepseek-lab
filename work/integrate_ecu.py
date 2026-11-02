from pathlib import Path
p=Path('outputs/deepseek-lab/app.js');s=p.read_text()
s=s.replace('let current=null,connected=false,busy=false;', 'let current=null,connected=false,busy=false,historyCount=0;')
s=s.replace("if(!$('instructions').value)$('instructions').value=s.defaults;", "if(!$('instructions').value)$('instructions').value=ECU_PROFILE.instructions;")
s=s.replace('function render(session){', 'function render(session){historyCount=session.messages.length;')
s=s.replace(" / output ${u.completion_tokens??'?'} tokens · cache hits", " / output ${u.completion_tokens??'?'} tokens (reasoning ${u.completion_tokens_details?.reasoning_tokens??0}) · cache hits")
s=s.replace("const r=await api('run',{session_id:current,prompt,...settings()});", "const cfg=resolveSettings(prompt,settings(),historyCount);await recordDecision(current,cfg.decision);const r=await api('run',{session_id:current,prompt,...cfg});")
s=s.replace("for(const [name,effort]of [['A',$('effortA').value],['B',$('effortB').value]])", "for(const [name,mode]of [['A',$('effortA').value],['B',$('effortB').value]])")
s=s.replace("title:`Compare ${name} · ${effort} · ${prompt.slice(0,30)}`", "title:`Compare ${name} · ${mode} · ${prompt.slice(0,30)}`")
s=s.replace("`${name} / ${effort}`", "`${name} / ${mode}`")
s=s.replace("const r=await api('run',{...cfg,session_id:id,prompt,effort});", "const chosen=resolveSettings(prompt,{...cfg,effort:mode},0);await recordDecision(id,chosen.decision);const r=await api('run',{...chosen,session_id:id,prompt});")
extra='''
function routeTask(prompt,history=0,ceiling=2048){
  if(history)return {version:ECU_PROFILE.version,effort:'low',max_tokens:ceiling,reason:'Conversation context: retain low reasoning for follow-up messages.'};
  for(const rule of ECU_PROFILE.rules){if(new RegExp(rule.pattern,'i').test(prompt))return {version:ECU_PROFILE.version,effort:rule.effort,max_tokens:rule.effort==='none'?Math.min(ceiling,ECU_PROFILE.direct_cap):ceiling,reason:rule.reason};}
  return {version:ECU_PROFILE.version,effort:ECU_PROFILE.default_effort,max_tokens:ceiling,reason:'Conservative default: low reasoning for unclassified tasks.'};
}
function resolveSettings(prompt,cfg,history){
 const decision=cfg.effort==='auto'?routeTask(prompt,history,cfg.max_tokens):{version:'manual',effort:cfg.effort,max_tokens:cfg.max_tokens,reason:'User-selected effort.'};
 return {...cfg,effort:decision.effort,max_tokens:decision.max_tokens,decision};
}
async function recordDecision(sid,decision){await api('note',{session_id:sid,rating:'configuration',note:JSON.stringify({ecu:decision})});}
function previewRoute(){const d=resolveSettings($('prompt').value,settings(),historyCount).decision;$('routePreview').textContent=`${d.version} → ${d.effort==='none'?'thinking off':d.effort} · ceiling ${d.max_tokens} tokens. ${d.reason}`;}
$('applyProfile').onclick=()=>{$('instructions').value=ECU_PROFILE.instructions;$('effort').value='auto';previewRoute();notice('ECU v1 applied. New runs will log the selected effort and why it was chosen.');};
for(const id of ['prompt','effort','cap'])$(id).addEventListener('input',previewRoute);
previewRoute();
'''
s += extra
p.write_text(s)
p=Path('outputs/deepseek-lab/index.html');s=p.read_text()
s=s.replace('<select id="effort"><option', '<select id="effort"><option value="auto" selected>Auto · ECU v1</option><option')
s=s.replace('<option value="low" selected>', '<option value="low">')
s=s.replace('<label for="cap">', '<p id="routePreview" class="hint" aria-live="polite"></p><label for="cap">')
s=s.replace('<label for="instructions">Operating instructions</label>', '<div class="profileActions"><label for="instructions">Operating instructions</label><button id="applyProfile" type="button">Apply ECU v1</button></div>')
s=s.replace('<select id="effortA"><option value="none">Thinking off</option><option selected>low</option>', '<select id="effortA"><option value="auto" selected>Auto · ECU v1</option><option value="none">Thinking off</option><option>low</option>')
s=s.replace('Same task. Two effort levels.', 'Same task. Two operating modes.')
s=s.replace('This sends two requests when Demo is off.', 'Auto uses the ECU selector. This sends two requests when Demo is off.')
p.write_text(s)
p=Path('outputs/deepseek-lab/style.css');s=p.read_text();s+='\n.profileActions{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:5px 0 8px}.profileActions label{margin:0}.profileActions button{font-size:10px;padding:5px 8px}.settings #routePreview{color:var(--green);background:var(--soft);padding:9px;border-radius:6px}nav{max-height:46vh;overflow:auto}\n';p.write_text(s)
