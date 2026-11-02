"""Local comparison and readable report; no paid requests."""
import json
from broad_v3 import ROOT
from long_task_resume import bounded_check

tuned=ROOT/'evaluations/long-task-20261021T152155Z'
raw=ROOT/'evaluations/long-task-20261021T152411Z'
frozen=json.loads((tuned/'frozen.json').read_text());raw_frozen=json.loads((raw/'frozen.json').read_text())
for key in ('contract','stages','tests'):assert frozen[key]==raw_frozen[key],key
summary={}
for name,folder in [('ecu',tuned),('raw',raw)]:
 state=json.loads((folder/'state.json').read_text());assert state['status']=='finished'
 rows=state['rows'];messages=[json.loads((folder/f'response-{r["request"]}.json').read_text()) for r in rows]
 summary[name]={'stages_passed':sum(any(r['stage']==i and r['pass'] for r in rows) for i in range(1,9)),'requests':state['requests'],'repairs':state['repairs_used'],'total_tokens':sum(m['usage']['total_tokens'] for m in messages),'input_tokens':sum(m['usage']['prompt_tokens'] for m in messages),'output_tokens':sum(m['usage']['completion_tokens'] for m in messages),'reasoning_tokens':sum(m['usage'].get('completion_tokens_details',{}).get('reasoning_tokens',0) for m in messages),'response_seconds':round(sum(m['elapsed_seconds'] for m in messages),3),'truncated':sum(m['finish_reason']=='length' for m in messages),'final_cases':sum(c.get('cases',0) for c in rows[-1]['checks'].values())}
 lines=['# Long-task responses: '+name,'One conversation, eight connected implementation stages. Cumulative external checks after each reply.']
 for r,m in zip(rows,messages):lines += ['## Stage '+str(r['stage']),frozen['stages'][r['stage']-1],'```python\n'+m['content']+'\n```','Checks: '+json.dumps({k:v['pass'] for k,v in r['checks'].items()}),'Usage: '+json.dumps(m['usage'])]
 (folder/'ANSWERS.md').write_text('\n\n'.join(lines)+'\n')
stress=json.loads((tuned/'stress-frozen.json').read_text())
raw_state=json.loads((raw/'state.json').read_text());raw_code=(raw/f'module-{raw_state["requests"]}.py').read_text()
raw_stress={name:bounded_check(raw_code,name,cases) for name,cases in stress.items()}
(raw/'stress-results.json').write_text(json.dumps(raw_stress,indent=2))
summary['raw_unseen_stress']={k:{'pass':v['pass'],'cases':v['cases']} for k,v in raw_stress.items()}
summary['ecu_unseen_stress']={k:{'pass':v['pass'],'cases':v['cases']} for k,v in json.loads((tuned/'stress-results.json').read_text()).items()}
resume=json.loads((tuned/'resume-response.json').read_text());rescheck=json.loads((tuned/'resume-results.json').read_text())
summary['ecu_fresh_context_resume']={'pass':resume['finish_reason']=='stop' and all(v['pass'] for v in rescheck['checks'].values()),'cases':sum(v['cases'] for v in rescheck['checks'].values()),'tokens':resume['usage']['total_tokens']}
summary['comparison']={'total_token_reduction_percent':round(100*(1-summary['ecu']['total_tokens']/summary['raw']['total_tokens']),2),'response_time_reduction_percent':round(100*(1-summary['ecu']['response_seconds']/summary['raw']['response_seconds']),2),'limitations':'One sequential sample per profile; synthetic eight-stage module, not hours-long repository work. Resume test only performed for ECU.'}
summary['total_paid_tokens']=summary['ecu']['total_tokens']+summary['raw']['total_tokens']+resume['usage']['total_tokens']
(tuned/'comparison.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
