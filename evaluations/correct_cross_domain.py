"""One paid corrective follow-up; not a held-out evaluation or weight training."""
import json,sys
from broad_v3 import ROOT,call
out=ROOT/'evaluations'/sys.argv[1]
rows=json.loads((out/'followup-results.json').read_text())
sid=next(r for r in rows if r['task']=='concrete')['session_id']
prompt='''Review and correct only your answers 1 and 3, at most 170 words total. For 1, the study did not specify that the same researchers delivered and scored it: separate possible confounds from known facts. A lack of observed benefit alone is not falsification; specify statistical precision and successful manipulation. Explain which people can be blinded when belief is manipulated. For 3, reflect each point of your proposed set across the vertical line Re(z)=1/2. Is your set invariant? Give a correct counterexample and explicitly acknowledge any mistake. Do not claim that these corrections update model weights.'''
(out/'correction-request.json').write_text(json.dumps({'prompt':prompt,'effort':'low','max_tokens':2048,'session_id':sid},indent=2))
m=call('run',{'session_id':sid,'prompt':prompt,'model':'deepseek-flash','effort':'low','context_mode':'none','task_mode':'general','max_tokens':2048,'demo':False})['session']['messages'][-1]
(out/'correction-result.json').write_text(json.dumps(m,indent=2))
print(json.dumps({'content':m['content'],'usage':m['usage'],'finish_reason':m['finish_reason']}))
