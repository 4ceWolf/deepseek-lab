"""Native Auto effort selection; more effort is not a guarantee of correctness."""
import re
import engine

def choose(prompt,history_count,ceiling,previous=None):
    route=engine.route(prompt,history_count,ceiling)
    route['native_policy']='native-auto-v2'
    negated_max=re.search(r"\b(?:do not|don't|dont|never|avoid|without)\s+(?:(?:use|using|enable|enabling)\s+)?(?:maximum|max|deepest)\s+(?:reasoning|thinking|effort)\b|\b(?:do not|don't|dont|never)\s+think max\b",prompt,re.I)
    if not negated_max and re.search(r'\b(?:use |enable )?(?:maximum|max|deepest)\s+(?:reasoning|thinking|effort)\b|\bthink max\b',prompt,re.I):
        route.update(effort='max',reason='Explicit request for maximum reasoning; output and task budgets still apply.')
    elif route['effort']=='none':return route
    elif re.search(r'\b(?:prove|disprove|theorem|lemma|counterexample|formal verification|mathematical induction)\b',prompt,re.I):
        route.update(effort='high',reason='Proof or formal reasoning: use deeper deliberation and check assumptions/counterexamples.')
    elif (len(prompt)>6000 or len(re.findall(r'^\s*(?:[-*]|\d+[.)])\s+',prompt,re.M))>=4) and re.search(r'\b(?:implement|refactor|debug|algorithm|database|linux|system|architecture)\b',prompt,re.I):
        route.update(effort='high',reason='Detailed technical work with multiple constraints: preserve deeper reasoning.')
    elif previous and previous.get('verification_failed') and route['effort']!='none':
        route.update(effort='high',reason='Previous executable verification failed; use stronger reasoning for the follow-up.')
    return route

def observe_check(run,result):
    # Approval denial, timeout and network errors are not evidence that more thought is needed.
    if result['status']!='finished' or result.get('note'):return
    failed=type(result.get('exit_code')) is int and result['exit_code']>0
    run['verification_failed']=failed
    if failed and run['config']['effort']=='auto' and run['route']['effort'] in ('none','low'):
        run['route'].update(effort='high',reason='Executable verification failed; escalate remaining tool rounds to high effort.')
        run['reasoning_escalations']=run.get('reasoning_escalations',0)+1
