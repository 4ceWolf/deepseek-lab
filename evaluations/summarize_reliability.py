"""Local reproducible aggregation and readable answer archive; no API calls."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rel=ROOT/'evaluations/reliability-20261021T103540Z'
compact=ROOT/'evaluations/compact-20261021T103819Z'
def totals(rows):
 return {'requests':len(rows),'objective_passed':sum(r['check']['pass'] is True for r in rows),'objective_scored':sum(r['check']['pass'] is not None for r in rows),'input_tokens':sum(r['result']['usage']['prompt_tokens'] for r in rows),'output_tokens':sum(r['result']['usage']['completion_tokens'] for r in rows),'total_tokens':sum(r['result']['usage']['total_tokens'] for r in rows),'reasoning_tokens':sum(r['result']['usage'].get('completion_tokens_details',{}).get('reasoning_tokens',0) for r in rows),'seconds':round(sum(r['result']['elapsed_seconds'] for r in rows),3),'truncated':sum(r['result']['finish_reason']=='length' for r in rows)}
summary={};allrows=[]
for folder,files in [(rel,['development-results.json','heldout-results.json']),(compact,['results.json'])]:
 frozen=json.loads((folder/'frozen.json').read_text());lines=['# Responses and grades','Raw means a fresh user-message-only DeepSeek request, with high reasoning matching the documented default. Earlier starting responses are preserved separately in ORIGINAL-BASELINE.md. These samples do not establish a general model ranking.']
 for filename in files:
  rows=json.loads((folder/filename).read_text());allrows+=rows
  summary[folder.name+'/'+filename]={a:totals([r for r in rows if r['arm']==a]) for a in sorted({r['arm'] for r in rows})}
  for r in rows:
   task=next(t for t in frozen['tasks'] if t['id']==r['task']);m=r['result']
   lines+=['## '+r['task']+' / '+r['arm'],'### Question',task['prompt'],'### Answer',m['content'],'### Check',json.dumps(r['check'],indent=2),'Usage: '+json.dumps(m['usage'])+'; elapsed '+str(m['elapsed_seconds'])+' seconds; finish '+m['finish_reason']]
 (folder/'ANSWERS.md').write_text('\n\n'.join(lines)+'\n')
summary['entire_turn']=totals(allrows)
rows=json.loads((compact/'results.json').read_text())
code={a:totals([r for r in rows if r['arm']==a and r['task'] in ('chunks','counts')]) for a in ['raw','compact']}
code['total_token_reduction_percent']=round(100*(1-code['compact']['total_tokens']/code['raw']['total_tokens']),2)
code['elapsed_reduction_percent']=round(100*(1-code['compact']['seconds']/code['raw']['seconds']),2)
summary['compact_coding_only']=code
(ROOT/'evaluations/RELIABILITY-SUMMARY.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
