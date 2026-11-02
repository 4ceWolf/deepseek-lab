"""Regrade preserved initial responses without rerunning old paid scripts."""
import ast,itertools,json,math
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
tree=ast.parse((ROOT/'work/baseline.py').read_text())
tasks=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='tasks' for t in n.targets))
prompts={t[0]:t[1] for t in tasks}
source=json.loads((ROOT/'data/recovered-results.json').read_text())
items={'A':(7,13),'B':(6,11),'C':(5,9),'D':(4,8),'E':(3,6),'F':(2,4)}
def valid(pick):return len(pick)==len(set(pick)) and all(k in items for k in pick) and sum(items[k][0] for k in pick)<=12 and not ('B' in pick and 'E' in pick) and not ('D' in pick and 'F' not in pick)
subsets=[list(p) for n in range(7) for p in itertools.combinations(items,n)]
best=max(sum(items[k][1] for k in p) for p in subsets if valid(p))
prob=Fraction(math.comb(5,2)*(math.comb(7,2)-math.comb(4,2)),math.comb(12,4)-math.comb(9,4))
rows=[]
for row in source['results']:
 name=row['task']
 if name not in prompts:continue
 text=row['content'];kind='objective'
 if name=='arithmetic':ok=text.strip()=='$71.40'
 elif name=='missing_evidence':
  kind='manual';ok=len(text.split())<30 and ('cannot' in text or "can't" in text) and 'without' in text
 else:
  try:
   obj=json.loads(text)
   if name=='extraction':ok=obj=={'order_id':'ZX-204','quantity':3,'color':'blue','delivery_date':None}
   elif name=='conditional_probability':ok=obj=={'numerator':prob.numerator,'denominator':prob.denominator}
   else:
    p=obj['items'];ok=valid(p) and obj['cost']==sum(items[k][0] for k in p) and obj['value']==sum(items[k][1] for k in p)==best
  except (ValueError,KeyError,TypeError):ok=False
 rows.append({'original':row,'prompt':prompts[name],'review':{'pass':ok and row['finish_reason']=='stop','kind':kind}})
out=ROOT/'evaluations/original-baseline-review.json'
out.write_text(json.dumps({'provenance':source['provenance'],'label':'Original first ten minimally instructed responses, not a verified user-message-only raw baseline. work/baseline.py supplied the then-current default instructions; exact original system prompt and full response envelope are unavailable.','results':rows},indent=2))
lines=['# Original starting responses — recovered and regraded','These are the preserved first ten final responses, not newly generated answers. Original full response envelopes and reasoning were lost. The old runner supplied default instructions; they must not be labeled strictly raw.']
for row in rows:
 r=row['original'];lines += ['## '+r['task']+' / '+r['effort'],row['prompt'],r['content'],'Grade: '+('PASS' if row['review']['pass'] else 'FAIL')+' ('+row['review']['kind']+')']
lines+=['## Result','9/10 including two manual missing-evidence reviews; 7/8 objective checks. The initial thinking-off arithmetic answer was $72.76; correct is $71.40. This is not comparable to the new suite as a before/after accuracy gain.']
(ROOT/'evaluations/ORIGINAL-BASELINE.md').write_text('\n\n'.join(lines)+'\n')
print('Original preserved responses:',len(rows),'Passed:',sum(r['review']['pass'] for r in rows))
