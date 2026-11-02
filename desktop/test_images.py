"""Local image snapshots, project boundaries and model-context isolation."""
import base64,tempfile,unittest
from pathlib import Path
from desktop.core import Core
from desktop.test_desktop import FakeCredentials,reply

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aL1sAAAAASUVORK5CYII=')
class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.project=self.root/'project';self.project.mkdir();self.core=Core(self.root/'state',FakeCredentials(),lambda _:reply('Offline'));self.core.workspace.update({'project':str(self.project)});self.session=self.core.new_session();(self.project/'shot.png').write_bytes(PNG)
    def tearDown(self):self.temp.cleanup()
    def publish(self,path='shot.png'):return self.core.dispatch('publish_image',dict(session=self.session['id'],path=path,title='Screenshot'))
    def test_snapshot_survives_source_removal_and_metadata_excludes_bytes(self):
        record=self.publish();(self.project/'shot.png').unlink();loaded=self.core.dispatch('image',{'id':record['id']});self.assertEqual(base64.b64decode(loaded['content']),PNG)
        state=self.core.dispatch('state',{});self.assertNotIn('content',state['images'][0]);self.assertNotIn('content',record);self.assertEqual(self.core.store.get('session',self.session['id'])['messages'],[])
        restarted=Core(self.root/'state',FakeCredentials(),lambda _:reply());self.assertEqual(restarted.dispatch('image',{'id':record['id']})['content'],loaded['content'])
    def test_paths_signatures_and_project_guards(self):
        outside=self.root/'outside.png';outside.write_bytes(PNG);(self.project/'link.png').symlink_to(outside)
        for path in ('../outside.png','link.png'):
            with self.assertRaises(ValueError):self.publish(path)
        (self.project/'bad.png').write_text('not an image')
        with self.assertRaises(ValueError):self.publish('bad.png')
        record=self.publish();other=self.root/'other';other.mkdir();self.core.workspace.update({'project':str(other)})
        with self.assertRaises(ValueError):self.core.dispatch('image',{'id':record['id']})
        with self.assertRaises(ValueError):self.publish()
    def test_model_tool_returns_metadata_only(self):
        import threading
        result=self.core.tool('publish_image',dict(path='shot.png',title='Screenshot'),dict(session=self.session['id'],config=self.core.workspace.settings()),threading.Event());self.assertEqual(result['bytes'],len(PNG));self.assertNotIn('content',result)
if __name__=='__main__':unittest.main()
