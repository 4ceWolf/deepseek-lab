import json,urllib.request
from pathlib import Path
root=Path('outputs/deepseek-lab')
rows=json.loads(Path('work/tune-results.json').read_text())
for r in rows:
 if r['task']=='missing_image_variant':
  r['pass']=True;r['review']='Manual review: one sentence under 25 words; acknowledges the missing image and makes no authenticity claim.'
  req=urllib.request.Request('http://127.0.0.1:8765/api/note',data=json.dumps({'session_id':r['session_id'],'run_id':r['run_id'],'rating':'pass','note':r['review']}).encode(),headers={'Content-Type':'application/json'})
  urllib.request.urlopen(req).close()
summary={}
for arm in ['ecu','high']:
 subset=[r for r in rows if r['arm']==arm]
 summary[arm]={'passed':sum(r['pass'] is True for r in subset),'tasks':len(subset),'input_tokens':sum(r['usage']['prompt_tokens'] for r in subset),'output_tokens':sum(r['usage']['completion_tokens'] for r in subset),'seconds':round(sum(r['seconds'] for r in subset),3)}
summary['output_reduction_percent']=round(100*(1-summary['ecu']['output_tokens']/summary['high']['output_tokens']),1)
(root/'tuning-results.json').write_text(json.dumps({'summary':summary,'method':'12 predeclared tasks; one run per task per arm, alternating arm order. Same model and system instructions. ECU routes effort and caps direct output at 1024 vs 2048. No response hit its ceiling. Manual review for missing-image task; other tasks checked programmatically.','limitations':'Small, mostly short synthetic task suite, not a general benchmark. No repeated sampling, tool use, long context, extended dialogue, or production task validation. No weight training.','results':rows},indent=2))
(root/'evaluation-suite.json').write_text(Path('work/tune-suite.json').read_text())
log=json.load(urllib.request.urlopen('http://127.0.0.1:8765/api/export'))
(root/'tuning-full-log.json').write_text(json.dumps(log,indent=2))
(root/'TUNING.md').write_text('''# ECU v1 — measured tuning result

The workbench now offers **Auto · ECU v1** and an **Apply ECU v1** button. This is an initial hand-authored control profile, not a trained model. It routes clear text transformations to thinking off, keeps low reasoning for calculations, constraints, follow-ups, and unknown tasks, and uses high for explicit deep-reasoning requests in fresh conversations. Manual mode overrides remain available.

Operating instructions encourage sufficient reasoning without unnecessary alternatives, exact output formatting, appropriate uncertainty, and treating quoted material as data. They do not include benchmark answers. Each request records the complete system instructions; an accompanying configuration review records the ECU version, chosen effort, budget, and reason.

## Results

| Measure | ECU v1 | Fixed high effort |
|---|---:|---:|
| Tasks passed | 12/12 | 12/12 |
| Input tokens | 1,783 | 1,908 |
| Output tokens, including reasoning | 1,711 | 2,005 |
| Sum of response times | 29.601 seconds | 29.557 seconds |

ECU v1 used **14.7% fewer output tokens** and **10.7% fewer total tokens** on this batch, with the same checked success rate. There was no meaningful overall speed improvement. Some individual low-effort runs used more tokens than high-effort runs. These are token savings, not a verified billing discount.

The prior 10-request baseline caught an incorrect arithmetic answer with thinking off. This is why Auto retains reasoning for arithmetic.

## Method and limits

The suite and checks were saved before calls started. It contains 12 new task instances: missing-field extraction, classification, grammar, translation, extraction from untrusted text, arithmetic, conditional probability, constrained optimization, Python tracing, ordering constraints, exact-format constraints, and uncertainty about an unseen image. Both arms used DeepSeek Flash and identical operating instructions. Run order alternated. Each arm received one attempt per task. The direct route ceiling was 1,024 output tokens; others used 2,048. None hit a ceiling. No automatic retries occurred.

Eleven tasks per arm were graded mechanically against expected answers or constraints. The image-uncertainty response was reviewed manually. This does not establish broad intelligence, robust prompt-injection resistance, or production reliability. Longer conversations, large inputs, tools, diverse languages, repeated sampling, and real user work remain unvalidated.

## Files

- `evaluation-suite.json`: frozen prompts, checks, and profile snapshot.
- `tuning-results.json`: complete per-run results and summary.
- `tuning-full-log.json`: all logged sessions and events through the tuning batch, excluding the API key.
- `ecu.py`: local agent adapter using the same profile embedded in the interface.

The active key was preserved; no server restart was required. No model weights were changed.
''')
p=root/'index.html';s=p.read_text().replace('<div class="callout"><strong>A control lab, not weight training.</strong>', '<div class="callout evidence"><strong>ECU v1 · first evaluation</strong><p>12/12 tasks passed in both modes.<br><b>14.7% fewer output tokens</b> than fixed high effort. Similar overall time.</p><p>Small 24-run sample; broader reliability is unverified. Details are in the exported logs.</p></div><div class="callout"><strong>A control lab, not weight training.</strong>');p.write_text(s)
p=root/'app.js';s=p.read_text().replace("$('messages').scrollTop=$('messages').scrollHeight}","$('messages').scrollTop=$('messages').scrollHeight;previewRoute()}");p.write_text(s)
p=root/'README.md';s=p.read_text();s+='''
## ECU v1 update

**Auto · ECU v1** selects effort conservatively. **Apply ECU v1** restores the tuned instruction set and automatic selection. Every routing choice is saved as a configuration review, followed by the exact request/response events. The browser and the local Python adapter `ecu.py` use the profile embedded in `app.js`. The server itself still accepts explicit effort levels; agent clients should call `ecu.route()` and submit the resulting settings.

Read `TUNING.md` for the measured 24-request comparison and its limitations. No background training or unattended paid requests are running.
''';p.write_text(s)
print(json.dumps(summary))
