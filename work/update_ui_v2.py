from pathlib import Path
p=Path('app.js');s=p.read_text();s=s.split('/* ECU_PROFILE_END */',1)[1]
s=s.replace('historyCount=0;', 'historyCount=0,defaultInstructions="";')
s=s.replace("if(!$('instructions').value)$('instructions').value=ECU_PROFILE.instructions;", "defaultInstructions=s.defaults;if(!$('instructions').value)$('instructions').value=s.defaults;")
s=s.replace("instructions:$('instructions').value,demo:$('demo').checked", "instructions:$('instructions').value,demo:$('demo').checked,task_mode:$('focus').value,context_mode:$('contextMode').value,output_check:$('outputCheck').value")
s=s.replace("const cfg=resolveSettings(prompt,settings(),historyCount);await recordDecision(current,cfg.decision);", "const cfg=settings();")
s=s.replace("const chosen=resolveSettings(prompt,{...cfg,effort:mode},0);await recordDecision(id,chosen.decision);", "const chosen={...cfg,effort:mode};")
s=s.replace("box.append(reviewBox(m,session.id))", "if(m.decision){box.append(element('div',`ECU: ${m.decision.reason} References: ${(m.decision.reference_ids||[]).join(', ')||'none'}.`,'metrics'));}if(m.validation&&m.validation.status!=='not_requested'){box.append(element('div',`Output check: ${m.validation.status}. ${m.validation.scope||m.validation.error||''}`,'metrics'));}box.append(reviewBox(m,session.id))")
start=s.index('function routeTask(')
s=s[:start]+'''let previewTimer=null,previewGeneration=0;
function previewRoute(){clearTimeout(previewTimer);const generation=++previewGeneration;previewTimer=setTimeout(async()=>{try{const p=await api('preview',{...settings(),session_id:current,prompt:$('prompt').value||'New task'});if(generation!==previewGeneration)return;const d=p.decision;$('routePreview').textContent=`${d.version} → ${d.effort==='none'?'thinking off':d.effort} · ${d.reference_ids.length} references · ${d.reference_characters} reference characters. ${d.reason}`;}catch(e){if(generation===previewGeneration)$('routePreview').textContent=e.message;}},250);}
$('applyProfile').onclick=()=>{$('instructions').value=defaultInstructions;$('effort').value='auto';$('contextMode').value='auto';previewRoute();notice('ECU v2 applied. Reference selection and routing are recorded by the server.');};
for(const id of ['prompt','effort','cap','focus','contextMode'])$(id).addEventListener('input',previewRoute);
$('showKnowledge').onclick=async()=>{try{const result=await api('knowledge');$('knowledgeCards').replaceChildren();for(const card of result.cards){const details=element('details');details.append(element('summary',card.title),element('p',card.text),element('p','Sources: '+card.sources.join(', '),'hint'));$('knowledgeCards').append(details);}$('knowledgeDialog').showModal();}catch(e){notice(e.message)}};
$('closeKnowledge').onclick=()=>$('knowledgeDialog').close();
previewRoute();
'''
p.write_text(s)
p=Path('index.html');s=p.read_text().replace('ECU v1','ECU v2').replace('Your next experiment','Coding & Arch workbench').replace('Tune instructions and reasoning. Keep the evidence.','Focused code help. Grounded machine knowledge. Less repeated context.')
s=s.replace('<label for="model">Engine</label>', '<label for="focus">Task focus</label><select id="focus"><option value="auto">Auto · coding & OS</option><option value="coding">Coding</option><option value="arch">Arch Linux / boot care</option><option value="general">General</option></select><label for="model">Engine</label>')
s=s.replace('<label for="instructions">Operating instructions</label>', '<label for="instructions">Operating instructions</label>')
s=s.replace('<div class="profileActions">', '<label for="contextMode">Reference context</label><select id="contextMode"><option value="auto">Relevant references only</option><option value="all">All references · comparison baseline</option><option value="none">No reference context</option></select><label for="outputCheck">Local output check</label><select id="outputCheck"><option value="none">None</option><option value="python">Python syntax · no execution</option><option value="json">JSON syntax</option></select><button id="showKnowledge">Inspect Arch & boot-care knowledge</button><div class="profileActions">')
s=s.replace('<footer>', '<dialog id="knowledgeDialog"><div class="panelHeading"><h2>Arch & boot-care reference library</h2><button id="closeKnowledge">Close</button></div><p class="muted">Historical records with source references. This is not a live machine inspection.</p><div id="knowledgeCards"></div></dialog><footer>')
s=s.replace('A control lab, not weight training.', 'Coding and OS control layer.').replace('Conversations do not train model weights. Start with your tasks, compare results, and keep the settings that earn their cost.', 'Uses selected local reference cards, bounded reasoning, and optional syntax checks. It proposes code and commands; it does not execute host changes. Model weights are unchanged.')
p.write_text(s)
