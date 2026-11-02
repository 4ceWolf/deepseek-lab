"""Learning gates use real command receipts and revision conflicts, never model self-scores."""
import tempfile,threading,time,unittest
from pathlib import Path
from desktop.core import Core
from desktop.test_desktop import FakeCredentials,reply
from desktop import reliability

class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.project=self.root/'project';self.project.mkdir();(self.project/'sample.py').write_text('value = 1\n')
        self.core=Core(self.root/'state',FakeCredentials(),lambda _:reply('Done'));self.core.workspace.update({'project':str(self.project),'docs':str(self.project)})
        self.session=self.core.new_session();self.run=self.core.store.put('run',dict(session=self.session['id'],config=self.core.workspace.settings(),status='completed',completed=[],remaining=[]))
    def tearDown(self):self.tmp.cleanup()
    def tool(self,name,args):return self.core.tool(name,args,self.run,threading.Event())
    def check(self):
        c=self.core.commands.request("python3 -c 'assert 1 + 1 == 2'",self.project,'full',self.run['id'],10,project=str(self.project),check={'before':reliability.snapshots(self.core.workspace,str(self.project),['sample.py'])})
        until=time.monotonic()+5
        while time.monotonic()<until:
            c=self.core.store.get('command',c['id'])
            if c['status']=='finished':return c['id']
            time.sleep(.02)
        self.fail('Command did not finish')
    def propose(self,checks):return self.tool('propose_ecu_lesson',dict(title='Inspect reconnect state',lesson='Check draft restoration when changing reconnect logic.',reason='A regression check protects unsent text; this is not proof of broad model improvement.',checks=checks))
    def test_memory_revisions_preserve_original_and_reject_stale(self):
        m=self.tool('save_memory',dict(title='Project test command',body='Use old command',scope='project'))
        n=self.tool('revise_memory',dict(id=m['id'],revision=1,title=m['title'],body='Use the verified command'))
        self.assertEqual(n['revision'],2);self.assertFalse(n['verified']);self.assertEqual(self.core.dispatch('memory_versions',{'id':m['id']})[0]['body'],'Use old command')
        with self.assertRaisesRegex(ValueError,'changed'):self.tool('revise_memory',dict(id=m['id'],revision=1,title='Stale',body='Wrong'))
        with self.assertRaisesRegex(ValueError,'project'):self.core.learning.revise_memory(m['id'],2,'Other','Wrong','/other','model')
    def test_user_memory_cannot_be_overwritten_by_model(self):
        m=self.core.workspace.remember('Preference','Keep my preference')
        with self.assertRaisesRegex(ValueError,'user-authored'):self.tool('revise_memory',dict(id=m['id'],revision=1,title='New',body='Overwrite'))
    def test_no_checks_cannot_activate(self):
        p=self.propose([])
        with self.assertRaisesRegex(ValueError,'fresh'):self.core.learning.change(p['id'],'active')
        self.assertNotIn(p['lesson'],self.core.instructions(self.core.workspace.settings()))
    def test_fresh_check_activation_rollback_and_stale_source_rejection(self):
        ident=self.check();p=self.propose([ident]);before=self.core.workspace.settings()
        self.core.learning.change(p['id'],'active');self.assertIn(p['lesson'],self.core.instructions(before));self.assertEqual(before,self.core.workspace.settings())
        self.core.learning.change(p['id'],'rolled_back');self.assertNotIn(p['lesson'],self.core.instructions(before))
        (self.project/'sample.py').write_text('value = 2\n')
        with self.assertRaisesRegex(ValueError,'fresh'):self.core.learning.change(p['id'],'active')
    def test_model_cannot_activate_or_use_unrelated_checks(self):
        ident=self.check();other=dict(self.run,id='other')
        with self.assertRaisesRegex(ValueError,'this task'):self.core.learning.propose(other,'Title','Lesson','Reason',[ident])
        with self.assertRaisesRegex(ValueError,'Unknown tool'):self.tool('learning_change',{'id':'x','status':'active'})
    def test_active_task_blocks_policy_change_and_restart_preserves_lessons(self):
        p=self.propose([self.check()]);r=dict(self.run,status='running');self.core.store.put('run',r)
        with self.assertRaisesRegex(ValueError,'active tasks'):self.core.learning.change(p['id'],'active')
        self.core.store.put('run',self.run);self.core.learning.change(p['id'],'active')
        restarted=Core(self.root/'state',FakeCredentials());self.assertIn(p['lesson'],restarted.instructions(restarted.workspace.settings()))

    def test_user_edit_preserves_id_and_revision_history(self):
        m=self.core.workspace.remember('Preference','Old preference')
        r=self.core.dispatch('edit_memory',{'id':m['id'],'revision':1,'title':'Preference','body':'New preference'})
        self.assertEqual(r['id'],m['id']);self.assertEqual(r['revision'],2)
        self.assertEqual(self.core.dispatch('memory_versions',{'id':m['id']})[0]['body'],'Old preference')
