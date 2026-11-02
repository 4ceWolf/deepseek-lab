"""Local checks and readable answer archive; no API requests."""
import itertools,json,re,sys
from broad_v3 import ROOT,grade

out=ROOT/'evaluations'/sys.argv[1]
frozen=json.loads((out/'frozen.json').read_text())
initial=json.loads((out/'results.json').read_text())
followup=json.loads((out/'followup-results.json').read_text())
def oracle(s):
 s=''.join(c for c in s if c in '()[]{}')
 while True:
  new=s.replace('()','').replace('[]','').replace('{}','')
  if new==s:return not s
  s=new
strings=[''.join(p) for n in range(5) for p in itertools.product('()[]{}',repeat=n)]
strings+=['abc','a([{}])b','a([)]b','('*100+')'*100,'('*100+')'*99]
cases=[{'args':[s],'expected':oracle(s)} for s in strings]
own=next(t for t in frozen['tasks'] if t['id']=='concrete')['assistant_answer']
own_code=own.split('4.\n',1)[1].split('\nTime O(n)',1)[0]
ds=next(r for r in followup if r['task']=='concrete')['result']['content']
ds_code=re.search(r'```python\n(.*?)```',ds,re.S).group(1)
checks={name:grade({'function':'balanced','cases':cases},code) for name,code in [('assistant',own_code),('deepseek_thinking_off',ds_code)]}
checks['cases_per_implementation']=len(cases)
(out/'code-checks.json').write_text(json.dumps(checks,indent=2))
lines=['# Cross-domain answers — 2026-10-21','Assistant answers frozen before API calls. Author also reviews: this is not a blinded or independent benchmark. See REVIEW.md for caveats.']
for task in frozen['tasks']:
 lines+=['## '+task['id'],'### Question',task['prompt'],'### Frozen assistant answer',task['assistant_answer']]
 for label,rows in [('DeepSeek initial',initial),('DeepSeek follow-up',followup)]:
  for row in rows:
   if row['task']==task['id']:
    m=row['result'];lines+=['### '+label,f"Effort: {m['effort']}; finish: {m['finish_reason']}; usage: {json.dumps(m['usage'])}",m['content']]
(out/'ANSWERS.md').write_text('\n\n'.join(lines)+'\n')
print(json.dumps(checks))
print('Total API tokens:',sum(r['result']['usage']['total_tokens'] for r in initial+followup))
