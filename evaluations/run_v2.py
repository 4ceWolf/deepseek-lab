import json,sys,subprocess,urllib.request,hashlib,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engine import INSTRUCTIONS,prepare
from suite_v2 import TASKS
BASE='http://127.0.0.1:8765/api/'
OUT=ROOT/'evaluations/v2-results.json'
def call(path,data=None):
 req=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=150) as r:return json.load(r)

def grade(t,content):
 if 'function'in t:
  result=subprocess.run([sys.executable,'-I',str(ROOT/'evaluations/python_check.py')],input=json.dumps({'code':content,'function':t['function'],'cases':t['cases']}),text=True,capture_output=True,timeout=6,env={'PATH':'/usr/bin:/bin'})
  try:return json.loads(result.stdout)
  except Exception:return {'pass':False,'error':'Evaluator failed or exceeded its resource limit','exit_code':result.returncode}
 try:
  obj=json.loads(content);fail=[]
  for key,val in t['expected'].items():
   actual=obj.get(key)
   if isinstance(actual,str):actual=actual.strip().strip('[]')
   if key=='full_upgrade_command' and actual=='pacman -Syu':actual='sudo pacman -Syu'
   if actual!=val:fail.append(key)
  if t['id']=='miku_history' and 'user'not in obj.get('evidence_type','').lower():fail.append('evidence_type')
  if t['id']=='snapshot_space' and 'snapshot'not in obj.get('leading_explanation','').lower():fail.append('leading_explanation')
  return {'pass':not fail,'failed_fields':fail}
 except Exception as e:return {'pass':False,'error':str(e)}

frozen={'created':'2026-10-14','tasks':TASKS,'instructions':INSTRUCTIONS,'cards':json.loads((ROOT/'knowledge/cards.json').read_text()),'comparison':'Same Flash model, same user tasks and system instructions. Baseline all reference cards/high effort vs ECU selected references/auto effort. Alternating order. One attempt each, 2048 token ceiling. No retries.','max_requests':24}
(ROOT/'evaluations/v2-frozen-suite.json').write_text(json.dumps(frozen,indent=2))
assert call('state')['connected']
results=[]
for index,t in enumerate(TASKS):
 for arm in (['ecu','baseline'] if index%2==0 else ['baseline','ecu']):
  sid=call('session',{'title':f'Coding/Arch v2 · {t["id"]} · {arm}'})['id']
  cfg={'session_id':sid,'prompt':t['prompt'],'instructions':INSTRUCTIONS,'model':'deepseek-flash','effort':'auto' if arm=='ecu' else 'high','context_mode':'auto' if arm=='ecu' else 'all','task_mode':t['focus'],'max_tokens':2048,'demo':False,'output_check':'python' if 'function'in t else 'json'}
  try:
   r=call('run',cfg);m=r['session']['messages'][-1];check=grade(t,m['content'])
   if m['finish_reason']!='stop':check={'pass':False,'error':'Response truncated','previous_check':check}
   row={'task':t['id'],'arm':arm,'session_id':sid,'run_id':m['run_id'],'content':m['content'],'usage':m['usage'],'seconds':m['elapsed_seconds'],'finish_reason':m['finish_reason'],'decision':m['decision'],'check':check}
   call('note',{'session_id':sid,'run_id':m['run_id'],'rating':'pass' if check['pass'] else 'fail','note':json.dumps({'evaluation':'coding-arch-v2','check':check})})
   results.append(row);OUT.write_text(json.dumps(results,indent=2));print(json.dumps({'task':t['id'],'arm':arm,'pass':check['pass'],'input':m['usage'].get('prompt_tokens'),'output':m['usage'].get('completion_tokens'),'seconds':m['elapsed_seconds'],'references':m['decision']['reference_ids'],'check':check}),flush=True)
  except Exception as e:
   results.append({'task':t['id'],'arm':arm,'error':str(e)});OUT.write_text(json.dumps(results,indent=2));print(str(e),flush=True);raise
print('BATCH COMPLETE',flush=True)
