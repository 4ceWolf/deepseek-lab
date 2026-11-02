"""Five-task exhibition: assistant answers frozen before DeepSeek responses.

The assistant authored the tasks/oracles and has more surrounding context:
this is a diagnostic challenge, not an unbiased model ranking.
"""
import datetime, hashlib, itertools, json, random
from pathlib import Path
from broad_v3 import call, grade, ROOT

ANSWERS={
 'shortest':'''def shortest_at_least(nums, target):
    prefix = [0]
    for x in nums:
        prefix.append(prefix[-1] + x)
    queue = []
    head = 0
    best = len(nums) + 1
    for i, value in enumerate(prefix):
        while head < len(queue) and value - prefix[queue[head]] >= target:
            best = min(best, i - queue[head])
            head += 1
        while len(queue) > head and prefix[queue[-1]] >= value:
            queue.pop()
        queue.append(i)
    return best if best <= len(nums) else -1
''',
 'weighted':'''def best_jobs(jobs):
    ordered = sorted(jobs, key=lambda job: job[1])
    ends = [job[1] for job in ordered]
    dp = [0]
    for i, job in enumerate(ordered):
        start, end, reward = job
        lo, hi = 0, i
        while lo < hi:
            mid = (lo + hi) // 2
            if ends[mid] <= start:
                lo = mid + 1
            else:
                hi = mid
        dp.append(max(dp[-1], reward + dp[lo]))
    return dp[-1]
''',
 'topology':'''def order_nodes(n, edges):
    adjacency = [set() for _ in range(n)]
    indegree = [0] * n
    for a, b in edges:
        if b not in adjacency[a]:
            adjacency[a].add(b)
            indegree[b] += 1
    ready = [i for i in range(n) if indegree[i] == 0]
    answer = []
    while ready:
        ready.sort(reverse=True)
        a = ready.pop()
        answer.append(a)
        for b in adjacency[a]:
            indegree[b] -= 1
            if indegree[b] == 0:
                ready.append(b)
    return answer if len(answer) == n else None
''',
 'conditional':'{"numerator":9,"denominator":17}',
 'linux_race':'{"race_free":false,"final_component_nofollow_protects_ancestors":false,"need_directory_anchored_resolution":true}'
}

def tasks():
 rng=random.Random(731042)
 short=[]
 for _ in range(80):
  nums=[rng.randrange(-8,10) for _ in range(rng.randrange(0,13))]
  target=rng.randrange(1,22)
  lengths=[j-i for i in range(len(nums)) for j in range(i+1,len(nums)+1) if sum(nums[i:j])>=target]
  short.append({'args':[nums,target],'expected':min(lengths) if lengths else -1,'immutable':True})
 weighted=[]
 for _ in range(55):
  jobs=[]
  for _ in range(rng.randrange(0,9)):
   start=rng.randrange(0,10);jobs.append([start,start+rng.randrange(1,6),rng.randrange(-5,16)])
  best=0
  for mask in range(1<<len(jobs)):
   chosen=[j for i,j in enumerate(jobs) if mask&(1<<i)]
   if all(a[1]<=b[0] or b[1]<=a[0] for a,b in itertools.combinations(chosen,2)):
    best=max(best,sum(j[2] for j in chosen))
  weighted.append({'args':[jobs],'expected':best,'immutable':True})
 topo=[]
 for _ in range(40):
  n=rng.randrange(0,7)
  edges=[[a,b] for a in range(n) for b in range(n) if rng.random()<.18]
  if edges:edges+=edges[:2]
  expected=None
  for perm in itertools.permutations(range(n)):
   pos={v:i for i,v in enumerate(perm)}
   if all(pos[a]<pos[b] for a,b in edges):
    expected=list(perm);break
  topo.append({'args':[n,edges],'expected':expected,'immutable':True})
 return [
  {'id':'shortest','prompt':'Implement shortest_at_least(nums, target). nums is a list of integers, including negatives; target is a positive integer. Return the length of the shortest NONEMPTY contiguous subarray whose sum is >= target, or -1 if none. Do not mutate input. Aim for O(n) time. Only Python source, no imports. Think deeply about edge cases.','function':'shortest_at_least','cases':short},
  {'id':'weighted','prompt':'Implement best_jobs(jobs). Each job is [start,end,reward], with integer start < end and possibly negative reward. Select nonoverlapping half-open intervals maximizing summed reward; choosing no jobs is allowed. Jobs may be unsorted or duplicated; touching endpoints are compatible. Return the maximum reward; do not mutate input. Aim for O(n log n). Only Python source, no imports. Think deeply about edge cases.','function':'best_jobs','cases':weighted},
  {'id':'topology','prompt':'Implement order_nodes(n, edges). Nodes are integers 0..n-1. Each [a,b] is a directed edge a->b; duplicate edges and self-loops are possible. Return the lexicographically smallest topological ordering, or None if a cycle exists. n=0 returns []. Do not mutate input. Only Python source, no imports. Think deeply about edge cases.','function':'order_nodes','cases':topo},
  {'id':'conditional','prompt':'An urn contains 4 red and 3 blue individually distinct balls. Three are drawn uniformly without replacement. Given that at least one drawn ball is red, what is the probability exactly two are red? Return only JSON with numerator and denominator as coprime positive integers. Think deeply.','expected':{'numerator':9,'denominator':17}},
  {'id':'linux_race','prompt':'On Linux, an untrusted process can rename directories and replace path components while your program operates. Your program checks realpath(path) is under a trusted root, then separately opens the original absolute path with O_NOFOLLOW on the final component only. Assess the design, assuming no other protections. Return only JSON with booleans: race_free, final_component_nofollow_protects_ancestors, need_directory_anchored_resolution. Think deeply.','expected':{'race_free':False,'final_component_nofollow_protects_ancestors':False,'need_directory_anchored_resolution':True}}
 ]

if __name__=='__main__':
 assert call('state')['connected'],'Connect the key first'
 suite=tasks()
 out=ROOT/'evaluations'/('duel-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
 out.mkdir()
 frozen={'tasks':suite,'assistant_answers':ANSWERS,'rules':'One answer per contestant/task; assistant answers frozen before provider calls. DeepSeek Flash with ECU Auto, 8192 cap, no references, no tools. Tests hidden from API. Assistant authored tasks and grader, so no unbiased ranking. Functional tests do not prove complexity. No repairs in scored round.','engine':(ROOT/'engine.py').read_text()}
 blob=json.dumps(frozen,indent=2)
 (out/'frozen.json').write_text(blob)
 print('Frozen answers SHA256 '+hashlib.sha256(blob.encode()).hexdigest(),flush=True)
 rows=[]
 for task in suite:
  own=grade(task,ANSWERS[task['id']])
  sid=call('session',{'title':'Duel · '+task['id']})['id']
  try:
   m=call('run',{'session_id':sid,'prompt':task['prompt'],'effort':'auto','model':'deepseek-flash','max_tokens':8192,'context_mode':'none','task_mode':'coding' if 'function' in task else 'general','output_check':'python' if 'function' in task else 'json','demo':False})['session']['messages'][-1]
   check=grade(task,m['content'])
   if m['finish_reason']!='stop':check={'pass':False,'error':'Incomplete response'}
   row={'task':task['id'],'assistant_check':own,'deepseek_check':check,'deepseek_result':m,'session_id':sid}
   call('note',{'session_id':sid,'run_id':m['run_id'],'rating':'pass' if check['pass'] else 'fail','note':json.dumps({'suite':'duel','check':check})})
  except Exception as e:
   row={'task':task['id'],'assistant_check':own,'error':str(e)}
   rows.append(row);(out/'results.json').write_text(json.dumps(rows,indent=2));raise
  rows.append(row);(out/'results.json').write_text(json.dumps(rows,indent=2))
  print(json.dumps({'task':task['id'],'assistant':own,'deepseek':check,'effort':m['effort'],'tokens':m['usage'].get('total_tokens')}),flush=True)
 print('Saved '+str(out),flush=True)
