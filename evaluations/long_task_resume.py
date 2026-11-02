"""Local unseen stress checks + one fresh-context continuation request."""
import json,random,sys
from broad_v3 import ROOT,call
from long_task import apply_ref,replay_ref,audit_ref,diff_ref,checks,CONTRACT,STAGES
from executor import verify

def bounded_check(code,name,cases):
 batches=[verify(code,name,cases[i:i+10]) for i in range(0,len(cases),10)]
 return {'pass':all(b['pass'] for b in batches),'cases':len(cases),'batches':batches}

if __name__=='__main__':
 out=ROOT/'evaluations'/sys.argv[1];state=json.loads((out/'state.json').read_text())
 assert state['status']=='finished'
 code=(out/f'module-{state["requests"]}.py').read_text()
 rng=random.Random(50019);samples=[]
 for i in range(60):
  initial={k:rng.randrange(-20,21) for k in ['a','b','c']};events=[]
  for j in range(40):
   op=rng.choice(['put','add','delete']);e={'op':op,'key':rng.choice(['a','b','c','d','e']),'value':rng.randrange(-9,10)}
   if j%7==0:e={'op':'batch','events':[{'op':'batch','events':[e]}]}
   events.append(e)
  samples.append((initial,events))
 tests={name:[{'args':[initial,events],'expected':fn(initial,events),'immutable':True} for initial,events in samples] for name,fn in [('apply_events',apply_ref),('replay',replay_ref),('audit',audit_ref)]}
 tests['diff_events']=[{'args':[initial,apply_ref(initial,events)],'expected':diff_ref(initial,apply_ref(initial,events)),'immutable':True} for initial,events in samples]
 (out/'stress-frozen.json').write_text(json.dumps(tests,indent=2))
 stress={name:bounded_check(code,name,cases) for name,cases in tests.items()}
 probe=code+'''\ndef ownership_probe(initial,events):
    result=apply_events(initial,events)
    result['probe']=123
    snapshots=replay(initial,events)
    if snapshots:
        snapshots[0]['probe']=123
        if len(snapshots)>1 and 'probe' in snapshots[-1]:return False
    return 'probe' not in initial
'''
 stress['ownership_probe']=verify(probe,'ownership_probe',[{'args':[{'a':1},[]],'expected':True,'immutable':True},{'args':[{'a':1},[{'op':'put','key':'a','value':2},{'op':'put','key':'a','value':3}]],'expected':True,'immutable':True}])
 (out/'stress-results.json').write_text(json.dumps(stress,indent=2))
 print('STRESS '+json.dumps({k:v['pass'] for k,v in stress.items()}),flush=True)
 prompt='Continue a task from a saved checkpoint. You have no earlier conversation history. Saved requirements:\n'+CONTRACT+'\n'+'\n'.join(STAGES)+'\nSaved latest module:\n'+code+'\nNew requirement: add compact_events(initial, events), returning diff_events(initial, apply_events(initial, events)). It represents the same final state with only sorted delete/put events. Retain ALL earlier public functions and contracts. Return the complete module only.'
 (out/'resume-request.json').write_text(json.dumps({'prompt':prompt,'max_requests':1,'max_tokens':4096},indent=2))
 if (out/'resume-response.json').exists():raise RuntimeError('Refusing to rerun completed paid continuation')
 sid=call('session',{'title':'Long task · resume from saved checkpoint'})['id']
 m=call('run',{'session_id':sid,'prompt':prompt,'model':'deepseek-flash','effort':'auto','task_mode':'coding','context_mode':'none','output_check':'python','max_tokens':4096,'demo':False})['session']['messages'][-1]
 (out/'resume-response.json').write_text(json.dumps(m,indent=2));(out/'resumed-module.py').write_text(m['content'])
 resumed=checks(m['content'],7)
 resumed['compact_events']=bounded_check(m['content'],'compact_events',[{'args':[initial,events],'expected':diff_ref(initial,apply_ref(initial,events)),'immutable':True} for initial,events in samples])
 (out/'resume-results.json').write_text(json.dumps({'finish_reason':m['finish_reason'],'checks':resumed,'session_id':sid},indent=2))
 print('RESUME '+json.dumps({'checks':{k:v['pass'] for k,v in resumed.items()},'finish_reason':m['finish_reason'],'usage':m['usage']}),flush=True)
