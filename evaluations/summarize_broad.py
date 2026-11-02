"""Regrade saved responses without provider calls; preserve original grades."""
import json, sys
from pathlib import Path
from broad_v3 import TASKS, grade

folder=Path(sys.argv[1])
rows=json.loads((folder/'results.json').read_text())
tasks={t['id']:t for t in TASKS}
regraded=[]
summary={}
for row in rows:
 check=grade(tasks[row['task']],row['result']['content'])
 if row['result']['finish_reason']!='stop':check={'pass':False,'error':'Incomplete'}
 regraded.append({'task':row['task'],'arm':row['arm'],'original_check':row['check'],'corrected_check':check})
 arm=summary.setdefault(row['arm'],{'passed':0,'tasks':0,'input_tokens':0,'output_tokens':0,'seconds':0})
 arm['tasks']+=1;arm['passed']+=int(check['pass'])
 arm['input_tokens']+=row['result']['usage']['prompt_tokens']
 arm['output_tokens']+=row['result']['usage']['completion_tokens']
 arm['seconds']+=row['result']['elapsed_seconds']
for arm in summary.values():
 arm['total_tokens']=arm['input_tokens']+arm['output_tokens']
 arm['seconds']=round(arm['seconds'],3)
summary['total_token_reduction_percent']=round(100*(1-summary['auto']['total_tokens']/summary['high']['total_tokens']),2)
summary['output_token_reduction_percent']=round(100*(1-summary['auto']['output_tokens']/summary['high']['output_tokens']),2)
summary['limitations']='Eight small tasks, one sample per mode. Original evaluator omitted iter/next/StopIteration; original grades preserved and all answers regraded. No proof of broad reliability or model learning. No extra API calls for regrading.'
(folder/'regraded.json').write_text(json.dumps(regraded,indent=2))
(folder/'summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
