"""Correct underspecified interval representation scoring, without API calls."""
import json,sys
from pathlib import Path
from broad_v3 import grade
folder=Path(sys.argv[1])
frozen=json.loads((folder/'frozen.json').read_text())
tasks={t['id']:t for t in frozen['tasks']}
for case in tasks['subtract_interval']['cases']:
 case['json_equivalent']=True
rows=json.loads((folder/'results.json').read_text())
checks=[]
summary={}
for row in rows:
 check=grade(tasks[row['task']],row['result']['content'])
 if row['result']['finish_reason']!='stop':check={'pass':False,'error':'Incomplete'}
 checks.append({'task':row['task'],'arm':row['arm'],'original':row['check'],'corrected':check})
 arm=summary.setdefault(row['arm'],{'passed':0,'tasks':0,'total_tokens':0})
 arm['passed']+=int(check['pass']);arm['tasks']+=1;arm['total_tokens']+=row['result']['usage']['total_tokens']
summary['note']='Interval prompt did not require list versus tuple elements. Accept equivalent JSON sequence representations for this task only; original results preserved. Other test contracts unchanged.'
summary['candidate_promoted']=False
(folder/'corrected.json').write_text(json.dumps({'checks':checks,'summary':summary},indent=2))
print(json.dumps(summary,indent=2))
