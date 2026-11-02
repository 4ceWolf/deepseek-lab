import json,re
from pathlib import Path
src=Path('/home/user/.var/app/io.github.rulin132.ChatGPT/.codex/sessions/2026/10/13/rollout-2026-10-13T19-08-27-01a13597-de49-76f2-95f8-d474f642429b.jsonl')
root=Path('/home/user/Projects/deepseek-lab');restored=[];results=[]
for line in src.read_text().splitlines():
 rec=json.loads(line);p=rec.get('payload',{})
 if p.get('type')=='custom_tool_call' and p.get('name')=='exec':
  s=p.get('input','')
  for hit in re.finditer(r'\bcmd\s*:\s*(?=")',s):
   try:cmd,_=json.JSONDecoder().raw_decode(s[hit.end():])
   except Exception:continue
   for h in re.finditer(r"cat > (outputs/deepseek-lab/[^\s]+|work/[^\s]+) <<'([A-Z]+)'\n(.*?)\n\2(?:\n|$)",cmd,re.S):
    target=h[1].replace('outputs/deepseek-lab/','');dest=root/target
    if not dest.resolve().is_relative_to(root):continue
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(h[3]+'\n');restored.append(target)
 if p.get('type')=='custom_tool_call_output':
  for part in p.get('output',[]):
   try:payload=json.loads(part.get('text',''))
   except Exception:continue
   if not isinstance(payload,dict):continue
   for sub in payload.get('output','').splitlines():
    try:r=json.loads(sub)
    except Exception:continue
    if isinstance(r,dict) and 'task'in r and 'run_id'in r and 'usage'in r:results.append(r)
unique={r['run_id']:r for r in results}
(root/'data/recovered-results.json').write_text(json.dumps({'provenance':'Recovered printed API result records from this chat execution log on 2026-10-14. Original SQLite database and full reasoning are not available. This is not a complete raw API log.','results':list(unique.values())},indent=2))
(root/'docs/RECOVERY.md').write_text('# Workspace recovery\n\nOn 2026-10-14 the prior temporary Documents/Codex workspace and its server were absent, including on the host. The lab source was recovered from this chat’s saved execution record into ~/Projects/deepseek-lab. The API key was held only in the terminated process and was not recovered.\n\nRecovered '+str(len(unique))+' printed result records (final answer, usage, timing, IDs, grades). Original full reasoning, raw response bodies, SQLite events, and unprinted review notes are unavailable; no reconstruction is presented as a complete original log. All future requests will be logged persistently here.\n')
print(json.dumps({'restored_files':restored,'recovered_runs':len(unique)}))
