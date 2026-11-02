"""12 development + 12 held-out paid calls maximum, one attempt each.
Run development first; explicitly select heldout tuned or candidate afterwards.
"""
import datetime,hashlib,json,sys
from broad_v3 import ROOT,call,grade
from reliability_suite import TASKS,REPOS

def checked(task,content):
 if task['check']=='none':
  limit=60 if task['id']=='style_frustration' else 45
  words=len(content.split())
  return {'pass':None,'manual_review_required':True,'words':words,'within_word_limit':words<=limit,'rubric':task['rubric']}
 return grade(task,content)

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='development':
  out=ROOT/'evaluations'/('reliability-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));out.mkdir()
  frozen={'tasks':TASKS,'engine':(ROOT/'engine.py').read_text(),'rules':'Development: raw user-only/high vs current ECU/auto vs candidate direct Python. Heldout: raw vs selected ECU. Same model, cap4096, one request per task/arm, no retries; rotating arm order. Manual style review not blinded. Hidden checks excluded from prompts. Synthetic repo repair, not autonomous repository execution. 24 requests maximum.'}
  blob=json.dumps(frozen,indent=2);(out/'frozen.json').write_text(blob)
  print('FROZEN '+str(out)+' '+hashlib.sha256(blob.encode()).hexdigest(),flush=True)
  local={}
  for t in TASKS:
   if 'function' in t:
    local[t['id']]={'reference':grade(t,t['reference']),'seeded_bug':grade(t,t['buggy'])}
    assert local[t['id']]['reference']['pass'] and not local[t['id']]['seeded_bug']['pass'],local[t['id']]
    folder=out/'fixtures'/t['id'];folder.mkdir(parents=True)
    (folder/'module.py').write_text(t['buggy'])
    (folder/'README.md').write_text(REPOS[t['id'][5:]]['spec'])
    (folder/'visible-tests.json').write_text(json.dumps(REPOS[t['id'][5:]]['visible'],indent=2))
  (out/'grader-preflight.json').write_text(json.dumps(local,indent=2))
  arms=['raw','tuned','candidate'];phase='development'
 elif mode=='heldout':
  out=ROOT/'evaluations'/sys.argv[2];selected=sys.argv[3]
  assert selected in ('tuned','candidate')
  frozen=json.loads((out/'frozen.json').read_text())
  arms=['raw',selected];phase='heldout'
  (out/'selection.json').write_text(json.dumps({'selected':selected,'engine':(ROOT/'engine.py').read_text(),'note':'Selection made after development, before heldout responses.'},indent=2))
 else:raise ValueError('Choose development or heldout')
 assert call('state')['connected'],'Connect key first'
 result_path=out/(phase+'-results.json')
 if result_path.exists():raise ValueError('Refusing accidental repeated paid run')
 rows=[]
 for i,t in enumerate(t for t in frozen['tasks'] if t['phase']==phase):
  order=arms[i%len(arms):]+arms[:i%len(arms)]
  for arm in order:
   sid=call('session',{'title':f'Reliability · {phase} · {t["id"]} · {arm}'})['id']
   try:
    m=call('run',{'session_id':sid,'prompt':t['prompt'],'model':'deepseek-flash','evaluation_profile':arm,'effort':'auto','context_mode':'auto','task_mode':t['focus'],'max_tokens':4096,'output_check':t['check'],'demo':False})['session']['messages'][-1]
    check=checked(t,m['content'])
    if m['finish_reason']!='stop':check.update({'pass':False,'incomplete':True})
    row={'task':t['id'],'arm':arm,'session_id':sid,'result':m,'check':check}
   except Exception as exc:
    row={'task':t['id'],'arm':arm,'session_id':sid,'error':str(exc)}
    rows.append(row);result_path.write_text(json.dumps(rows,indent=2));raise
   rows.append(row);result_path.write_text(json.dumps(rows,indent=2))
   print(json.dumps({'task':t['id'],'arm':arm,'check':check,'usage':m['usage'],'seconds':m['elapsed_seconds'],'content':m['content'] if t['check']=='none' else None}),flush=True)
 print('SAVED '+str(out),flush=True)
