"""Durable recovery/evidence, conservative request admission and loss-aware context."""
import copy,hashlib,json,time
from pathlib import Path

TERMINAL_COMMANDS={'finished','denied','error','interrupted','cancelled'}
def size(value):return len(json.dumps(value,ensure_ascii=False).encode())
def snapshots(workspace,project,paths):
    if not isinstance(paths,list) or not 1<=len(paths)<=20 or not all(isinstance(p,str) for p in paths):raise ValueError('Checks require 1–20 project file paths')
    result={}
    for name in paths:
        path=workspace.inside(project,name)
        if path.is_file():
            with path.open('rb') as stream:data=stream.read(1_000_001)
            if len(data)>1_000_000:raise ValueError('Checked files must be at most 1 MB each')
            result[name]=hashlib.sha256(data).hexdigest()
        elif not path.exists():result[name]=None
        else:raise ValueError('Check scope must contain files')
    return result

def receipt(core,sid):
    session=core.store.get('session',sid);core.settings_for(session)
    runs=core.store.list('run',session=sid);run=runs[0] if runs else None
    commands=core.store.list('command',limit=300,project=session['project']);linked=[c for c in commands if c.get('task') in {r['id'] for r in runs}]
    checks=[];current_hashes={}
    for c in linked:
        if not c.get('check'):continue
        evidence=c['check'];fresh=False
        try:
            for name in evidence['before']:
                if name not in current_hashes:
                    if len(current_hashes)>=200:raise ValueError('Receipt freshness scope limit')
                    current_hashes.update(snapshots(core.workspace,session['project'],[name]))
            fresh=all(current_hashes[name]==value for name,value in evidence['before'].items())
        except (OSError,ValueError):pass
        checks.append(dict(command_id=c['id'],command=c['command'],status=c['status'],exit_code=c['exit_code'],scope=evidence['before'],sources_unchanged=fresh,result='command exited 0; scoped sources unchanged' if c['status']=='finished' and c['exit_code']==0 and not c.get('note') and fresh else 'not established',output_tail=c['output'][-2000:]))
    patches=core.store.list('proposal',limit=100,session=sid)
    return dict(session=sid,run=run,model_claims_unverified=True,checks=checks,patches=[{k:p.get(k) for k in ('id','path','status','old_sha','applied_sha')} for p in patches],commands=[{k:c.get(k) for k in ('id','command','cwd','status','exit_code','note','error','started','finished')} for c in linked],limits='Receipt lists up to 300 recent project commands and 100 task patches; freshness checks hash at most 200 distinct scoped files. Exit 0 is command evidence, not proof of overall correctness. Manual commands are not automatically attributed to this task.')

def recovery(core,sid):
    report=receipt(core,sid);run=report['run']
    if not run:raise ValueError('No saved run to recover')
    if core.active_for(sid):raise ValueError('This task is still active')
    commands=core.store.list('command',task=run['id'])
    if any(c['status'] not in TERMINAL_COMMANDS for c in commands):raise ValueError('Finish or deny this run’s commands before recovery')
    uncertainty=[c['id'] for c in commands if c['status']=='interrupted']
    if run.get('reservation'):uncertainty.append('Provider request may have been billed; retained reservation counts against recovery budgets')
    return dict(session=sid,expected_run=run['id'],completed_claims=run['completed'],remaining=run['remaining'],requirements=run.get('requirements',[]),uncertainties=uncertainty,receipt=report,note='Recovery starts a new model request using saved evidence. The service does not replay commands. The resumed model can request new commands under your current permission mode. Inspect uncertain process state before repeating an action.')

def context(messages,limit):
    """Keep all user instructions; omit only entire older assistant/tool groups."""
    if size(messages)<=limit:return messages,dict(compacted=False,omitted=0)
    starts=[i for i,m in enumerate(messages) if m['role']=='user'];cut=starts[-2] if len(starts)>1 else 0
    kept=[m for i,m in enumerate(messages) if i>=cut or m['role']=='user'];omitted=len(messages)-len(kept)
    if not omitted or size(kept)>limit:raise ValueError('Context limit: retained user instructions and recent complete exchanges exceed the cap. Start a reviewed continuation; nothing was silently truncated.')
    return kept,dict(compacted=True,omitted=omitted,note='Older assistant/tool exchanges omitted from this request; all user messages retained. Complete history remains stored and is available through read_history.')

def reserve(run,payload):
    cfg=run['config'];account=run.setdefault('accounting',dict(tokens=0,usd=0.0,priced=True));prior=run.get('reservation')
    if prior:raise ValueError('Unsettled provider reservation; review before another request')
    # UTF-8 bytes plus protocol allowance is an admission estimate, not a tokenizer/billing guarantee.
    tokens=size(payload['messages'])+size(payload['tools'])+128*len(payload['messages'])+cfg['max_tokens']
    rates=cfg.get('pricing',{}).get(cfg['model']);usd=None if rates is None else ((tokens-cfg['max_tokens'])*rates['input']+cfg['max_tokens']*rates['output'])/1e6
    run['next_request_estimate']=dict(tokens=tokens,usd=usd)
    if cfg.get('max_total_tokens',0) and account['tokens']+tokens>cfg['max_total_tokens']:raise ValueError('Token budget: estimated next request would exceed this task budget')
    if cfg.get('max_task_usd',0) and (usd is None or not account.get('priced',True) or account['usd']+usd>cfg['max_task_usd']):raise ValueError('Cost budget: estimated next request cannot fit the supplied price budget')
    return dict(tokens=tokens,usd=usd,estimate=True)

def settle(run,usage):
    reserved=run.pop('reservation');account=run['accounting'];valid=isinstance(usage,dict) and all(type(usage.get(k)) is int and usage[k]>=0 for k in ('prompt_tokens','completion_tokens','total_tokens')) and usage['total_tokens']>=usage['prompt_tokens']+usage['completion_tokens']
    if not valid:
        run['reservation']=reserved;raise ValueError('Provider usage missing or inconsistent; request may be billed. Reservation retained; no automatic retry.')
    rates=run['config'].get('pricing',{}).get(run['config']['model']);usd=None if rates is None else (usage['prompt_tokens']*rates['input']+usage['completion_tokens']*rates['output'])/1e6
    account['tokens']+=usage['total_tokens'];account['priced']=account.get('priced',True) and usd is not None
    if usd is not None:account['usd']+=usd

def carry(run):
    account=copy.deepcopy(run.get('accounting',dict(tokens=run.get('usage',{}).get('total_tokens',0),usd=0.,priced=False)))
    if run.get('reservation'):
        r=run['reservation'];account['tokens']+=r['tokens'];account['priced']=account.get('priced',True) and r['usd'] is not None
        if r['usd'] is not None:account['usd']+=r['usd']
        account.setdefault('uncertain_requests',[]).append(run['id'])
    return account
