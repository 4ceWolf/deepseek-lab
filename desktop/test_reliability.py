"""Adversarial offline checks for admission, recovery, context and execution evidence."""
import json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from desktop.core import Core
from desktop.commands import Commands
from desktop.test_desktop import FakeCredentials,reply,tool
from desktop import reliability

class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.project=self.root/'project';self.project.mkdir();self.file=self.project/'module.py';self.file.write_text('answer=42\n');self.core=Core(self.root/'state',FakeCredentials(),lambda _:reply());self.core.workspace.update({'project':str(self.project)})
    def tearDown(self):
        for event in list(self.core.cancels.values()):event.set()
        self.temp.cleanup()
    def wait(self,ident):
        until=time.monotonic()+6
        while time.monotonic()<until:
            run=self.core.store.get('run',ident)
            if run['status'] not in ('running','waiting_approval','stopping'):return run
            time.sleep(.02)
        self.fail('Run timed out')
    def session(self):return self.core.new_session()
    def test_queued_stop_cannot_launch_and_old_approvals_expire(self):
        with patch.object(self.core.commands,'_launch') as launch:
            command=self.core.commands.request('touch marker',self.project,'full');self.core.commands.stop(command['id']);self.core.commands._run(launch.call_args.args[0])
        self.assertFalse((self.project/'marker').exists());self.assertEqual(self.core.store.get('command',command['id'])['status'],'cancelled')
        pending=self.core.commands.request('echo old',self.project,'approve');Commands(self.core.store)
        self.assertEqual(self.core.store.get('command',pending['id'])['status'],'interrupted')
        with self.assertRaises(ValueError):self.core.commands.decide(pending['id'],True,pending['fingerprint'])
    def test_checkpoint_claims_and_fresh_source_evidence_are_distinct(self):
        self.core.workspace.update({'permission':'full'});responses=iter([reply('',[tool('task_checkpoint',dict(completed=['Implemented'],remaining=['Review integration'],requirements=['Keep existing behavior']))]),reply('',[tool('run_check',dict(command='python3 -c "assert 1+1==2"',cwd='.',timeout=5,paths=['module.py']))]),reply('Done.')]);self.core.provider=lambda _:next(responses)
        session=self.session();run=self.wait(self.core.submit(session['id'],'Check this file')['id']);self.assertEqual(run['status'],'completed');self.assertEqual(run['remaining'],['Review integration'])
        receipt=reliability.receipt(self.core,session['id']);self.assertEqual(receipt['checks'][0]['result'],'command exited 0; scoped sources unchanged');self.assertTrue(receipt['model_claims_unverified'])
        self.file.write_text('answer=43\n');self.assertEqual(reliability.receipt(self.core,session['id'])['checks'][0]['result'],'not established')
    def test_no_provider_call_when_budget_cannot_admit_request(self):
        self.core.workspace.update({'max_total_tokens':1});calls=[];self.core.provider=lambda p:calls.append(p) or reply();run=self.wait(self.core.submit(self.session()['id'],'Hello')['id']);self.assertEqual(run['status'],'budget_limit');self.assertEqual(calls,[])
    def test_usd_budget_requires_prices_and_rejects_unaffordable_request(self):
        with self.assertRaises(ValueError):self.core.workspace.update({'max_task_usd':1})
        self.core.workspace.update({'pricing':{'deepseek-flash':{'input':100,'output':100}},'max_task_usd':.0001});calls=[];self.core.provider=lambda p:calls.append(p) or reply();run=self.wait(self.core.submit(self.session()['id'],'Hello')['id']);self.assertEqual(run['status'],'budget_limit');self.assertFalse(calls)
    def test_cheap_route_requires_supplied_price_advantage(self):
        rates={'deepseek-flash':dict(input=1.,output=2.),'deepseek-v4-pro':dict(input=3.,output=4.)};self.core.workspace.update({'model':'deepseek-v4-pro','pricing':rates,'economy_routing':True});calls=[];self.core.provider=lambda p:calls.append(p) or reply();run=self.wait(self.core.submit(self.session()['id'],'hello')['id']);self.assertEqual(run['config']['model'],'deepseek-flash');self.assertEqual(calls[0]['model'],'deepseek-flash');self.assertAlmostEqual(run['accounting']['usd'],.00004)
    def test_uncertain_provider_charge_is_preserved_and_recovery_never_replays(self):
        self.core.provider=lambda _:(_ for _ in ()).throw(OSError('Connection lost after request'));sid=self.session()['id'];parent=self.wait(self.core.submit(sid,'Implement safely')['id']);report=self.core.dispatch('recovery_report',{'session':sid});self.assertTrue(report['uncertainties']);self.assertIn('reservation',parent)
        with self.assertRaises(ValueError):self.core.dispatch('recover_session',{'session':sid,'expected_run':parent['id']})
        with self.assertRaises(ValueError):self.core.submit(sid,'Continue without reviewing uncertainty')
        self.core.workspace.update({'max_total_tokens':1});self.core.provider=lambda _:reply('Continue after reviewing evidence.');child=self.wait(self.core.dispatch('recover_session',{'session':sid,'expected_run':parent['id'],'acknowledge_uncertain':True})['id']);self.assertEqual(child['parent'],parent['id']);self.assertEqual(child['config']['max_total_tokens'],0);self.assertEqual(child['accounting']['tokens'],parent['reservation']['tokens']+30);self.assertEqual(self.core.store.list('command'),[])
        with self.assertRaises(ValueError):self.core.dispatch('recover_session',{'session':sid,'expected_run':parent['id'],'acknowledge_uncertain':True})
    def test_recovery_retains_budget_across_requests(self):
        self.core.workspace.update({'max_total_tokens':100000});self.core.provider=lambda _:(_ for _ in ()).throw(OSError('Unknown billing'));sid=self.session()['id'];parent=self.wait(self.core.submit(sid,'Start')['id']);parent['reservation']['tokens']=100000;self.core.store.put('run',parent);calls=[];self.core.provider=lambda p:calls.append(p) or reply();child=self.wait(self.core.dispatch('recover_session',dict(session=sid,expected_run=parent['id'],acknowledge_uncertain=True))['id']);self.assertEqual(child['status'],'budget_limit');self.assertFalse(calls)
    def test_missing_usage_retains_reservation_and_stops(self):
        self.core.provider=lambda _:dict(reply(),usage={});run=self.wait(self.core.submit(self.session()['id'],'hello')['id']);self.assertEqual(run['status'],'error');self.assertIn('reservation',run)
    def test_context_keeps_user_messages_and_atomic_tool_groups(self):
        messages=[]
        for i in range(8):messages += [dict(role='user',content='Requirement '+str(i)),dict(role='assistant',content='x'*5000,tool_calls=[tool('list_files',{},str(i))]),dict(role='tool',tool_call_id=str(i),content='files')]
        kept,info=reliability.context(messages,23000);self.assertTrue(info['compacted']);self.assertEqual([m for m in kept if m['role']=='user'],[m for m in messages if m['role']=='user']);ids={c['id'] for m in kept for c in m.get('tool_calls',[])};self.assertTrue(all(m['tool_call_id'] in ids for m in kept if m['role']=='tool'));self.assertEqual(len(messages),24)
        with self.assertRaises(ValueError):reliability.context([dict(role='user',content='x'*50000)],20000)
    def test_patch_backup_mode_rollback_and_stale_guard(self):
        self.file.chmod(0o755);proposal=self.core.workspace.proposal('module.py','answer=7\n');self.core.workspace.apply_proposal(proposal['id']);self.assertEqual(self.file.stat().st_mode&0o777,0o755);self.core.workspace.rollback_proposal(proposal['id']);self.assertEqual(self.file.read_text(),'answer=42\n')
        proposal=self.core.workspace.proposal('module.py','answer=8\n');self.core.workspace.apply_proposal(proposal['id']);self.file.write_text('user edit\n')
        with self.assertRaises(ValueError):self.core.workspace.rollback_proposal(proposal['id'])
        self.assertEqual(self.file.read_text(),'user edit\n')
    def test_state_queries_are_project_scoped_and_limited_in_sql(self):
        other=self.root/'other';other.mkdir();self.core.commands.request('echo other',other,'disabled');self.core.commands.request('echo own',self.project,'disabled');state=self.core.dispatch('state',{});self.assertEqual([c['command'] for c in state['commands']],['echo own'])
        for i in range(10):self.core.store.put('fixture',{'value':i,'project':str(self.project)})
        self.assertEqual(len(self.core.store.list('fixture',limit=3,project=str(self.project))),3)
    def test_worktree_creation_obeys_command_approval_and_disabled_modes(self):
        result=self.core.dispatch('create_worktree',{});command=self.core.store.get('command',result['command']);self.assertEqual(command['status'],'awaiting_approval');self.assertFalse(Path(result['path']).exists())
        with self.assertRaises(ValueError):self.core.dispatch('open_worktree',{'id':result['id']})
        self.core.commands.decide(command['id'],False,command['fingerprint']);self.core.workspace.update({'permission':'disabled'});record=self.core.dispatch('create_worktree',{});self.assertEqual(self.core.store.get('command',record['command'])['status'],'denied')
    def test_real_git_worktree_preserves_dirty_original_checkout(self):
        import shutil,subprocess
        if not shutil.which('git'):self.skipTest('Git unavailable')
        env=dict(os.environ,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null')
        def git(*args):subprocess.run(['git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','-c','user.name=Offline test','-c','user.email=offline@example.invalid',*args],cwd=self.project,env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        git('init');git('add','module.py');git('commit','-m','fixture');self.file.write_text('uncommitted user work\n');record=self.core.dispatch('create_worktree',{});command=self.core.store.get('command',record['command']);self.core.dispatch('decide_command',dict(id=command['id'],approved=True,fingerprint=command['fingerprint']));result=self.core.commands.wait(command['id']);self.assertEqual(result['exit_code'],0,result['output']);config=self.core.dispatch('open_worktree',{'id':record['id']});self.assertEqual(Path(config['project']+'/module.py').read_text(),'answer=42\n');self.assertEqual(self.file.read_text(),'uncommitted user work\n')
    def test_compaction_reaches_provider_and_large_history_can_be_retrieved(self):
        session=self.session();history=[]
        for i in range(8):history += [dict(role='user',content='Preserve requirement '+str(i)),dict(role='assistant',content='x'*30000)]
        session['messages']=history;self.core.store.put('session',session);calls=[];self.core.provider=lambda p:calls.append(p) or reply();run=self.wait(self.core.submit(session['id'],'Continue')['id']);self.assertEqual(run['status'],'completed');self.assertTrue(run['context']['compacted']);self.assertEqual(sum(m['role']=='user' for m in calls[0]['messages']),9);self.assertEqual(len(self.core.store.get('session',session['id'])['messages']),18)
        first=self.core.tool('read_history',dict(offset=1,limit=1),run,None);second=self.core.tool('read_history',dict(offset=first['next_offset'],character_offset=first['next_character_offset'],limit=1),run,None);decoded=json.loads(first['serialized_message_chunk']+second['serialized_message_chunk']);self.assertEqual(decoded['content'],'x'*30000)
        self.core.workspace.update({'compact_context':False,'context_limit':20000});blocked=self.wait(self.core.submit(session['id'],'Continue with strict context')['id']);self.assertEqual(blocked['status'],'context_limit');self.assertEqual(len(calls),1)
    def test_disabled_permission_cancels_queued_work_and_blocks_late_approval(self):
        with patch.object(self.core.commands,'_launch'):
            queued=self.core.commands.request('echo queued',self.project,'full')
        pending=self.core.commands.request('echo pending',self.project,'approve')
        with self.assertRaises(ValueError):self.core.dispatch('settings',{'project':str(self.root)})
        self.core.dispatch('settings',{'permission':'disabled'});self.assertEqual(self.core.store.get('command',queued['id'])['status'],'cancelled');self.assertEqual(self.core.store.get('command',pending['id'])['status'],'denied')
        with self.assertRaises(ValueError):self.core.dispatch('decide_command',dict(id=pending['id'],approved=True,fingerprint=pending['fingerprint']))
    def test_followup_keeps_requirements_and_task_spending_without_double_counting(self):
        sid=self.session()['id'];responses=iter([reply('',[tool('task_checkpoint',dict(completed=['Part A'],remaining=['Part B'],requirements=['Do not change the public API']))]),reply('Part A finished.')]);self.core.provider=lambda _:next(responses);first=self.wait(self.core.submit(sid,'Build two parts')['id']);self.assertEqual(first['accounting']['tokens'],60)
        payloads=[];self.core.provider=lambda p:payloads.append(p) or reply('Part B still needs review.');second=self.wait(self.core.submit(sid,'Continue')['id']);self.assertEqual(second['accounting']['tokens'],90);self.assertEqual(second['requirements'],['Do not change the public API']);self.assertEqual(second['remaining'],['Part B']);self.assertIn('Do not change the public API',payloads[0]['messages'][0]['content'])
    def test_model_success_claim_does_not_override_failed_check(self):
        self.core.workspace.update({'permission':'full'});responses=iter([reply('',[tool('run_check',dict(command='python3 -c "raise SystemExit(1)"',cwd='.',timeout=5,paths=['module.py']))]),reply('All tests pass.')]);self.core.provider=lambda _:next(responses);sid=self.session()['id'];run=self.wait(self.core.submit(sid,'Run verification')['id']);self.assertEqual(run['status'],'completed');receipt=reliability.receipt(self.core,sid);self.assertTrue(receipt['model_claims_unverified']);self.assertEqual(receipt['checks'][0]['exit_code'],1);self.assertEqual(receipt['checks'][0]['result'],'not established')
    def test_patch_interruption_reconciliation_and_exact_byte_restore(self):
        from desktop.workspace import Workspace
        original=b'answer=42\r\n';self.file.write_bytes(original);proposal=self.core.workspace.proposal('module.py','answer=7\n');applied=self.core.workspace.apply_proposal(proposal['id']);applied['status']='applying';self.core.store.put('proposal',applied);Workspace(self.core.store);self.assertEqual(self.core.store.get('proposal',applied['id'])['status'],'applied');self.core.workspace.rollback_proposal(applied['id']);self.assertEqual(self.file.read_bytes(),original)
        proposal=self.core.workspace.proposal('module.py','answer=8\n');applied=self.core.workspace.apply_proposal(proposal['id']);applied['status']='rolling_back';self.core.store.put('proposal',applied);self.file.write_bytes(original);Workspace(self.core.store);self.assertEqual(self.core.store.get('proposal',applied['id'])['status'],'rolled_back')
        applied['status']='applying';self.core.store.put('proposal',applied);self.file.write_text('unrelated user change\n');Workspace(self.core.store);self.assertEqual(self.core.store.get('proposal',applied['id'])['status'],'conflicted');self.assertEqual(self.file.read_text(),'unrelated user change\n')
if __name__=='__main__':unittest.main()
