"""Two additional paid diagnostic requests; no automatic retries or promotion."""
import json, sys
from broad_v3 import ROOT,call

if __name__=='__main__':
 out=ROOT/'evaluations'/sys.argv[1]
 frozen=json.loads((out/'frozen.json').read_text())
 plan={'engine':(ROOT/'engine.py').read_text(),'requests':[{'task':'concrete','effort':'none','reason':'Isolate explicit thinking disable after low exhausted the cap; style also changed so not a pure A/B.'},{'task':'style_and_access','effort':'low','reason':'Check reduced canned empathy after style edit.'}],'max_requests':2,'cap':4096}
 (out/'followup-plan.json').write_text(json.dumps(plan,indent=2))
 rows=[]
 for item in plan['requests']:
  task=next(t for t in frozen['tasks'] if t['id']==item['task'])
  sid=call('session',{'title':'Cross-domain followup · '+task['id']})['id']
  m=call('run',{'session_id':sid,'prompt':task['prompt'],'model':'deepseek-flash','effort':item['effort'],'context_mode':'none','task_mode':'general','max_tokens':4096,'demo':False})['session']['messages'][-1]
  rows.append({'task':task['id'],'session_id':sid,'result':m})
  (out/'followup-results.json').write_text(json.dumps(rows,indent=2))
  print(json.dumps({'task':task['id'],'content':m['content'],'usage':m['usage'],'finish_reason':m['finish_reason']}),flush=True)
