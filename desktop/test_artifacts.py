"""Offline validation, rendering, persistence and revision checks."""
import json,tempfile,threading,unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from desktop import artifacts
from desktop.core import Core
from desktop.test_desktop import FakeCredentials,reply,tool

def chart(kind='bar'):
    return dict(kind=kind,title='Task outcomes',source='Illustrative test fixture; not measured performance',labels=['Coding','Planning','Review'],series=[dict(name='Completed',values=[8,5,7])],unit='Tasks')

class ArtifactTests(unittest.TestCase):
    def test_appearance_validation_and_color_semantics(self):
        spec=chart();spec['style']=dict(palette=['#ff8800','#00aaff','#44ddaa'],text='#eeeeee',color_by='category');normalized=artifacts.validate(spec);root=ET.fromstring(artifacts.svg(spec));ns={'s':'http://www.w3.org/2000/svg'}
        bars=root.findall('.//s:rect[@data-color-index]',ns);self.assertEqual([b.attrib['fill'] for b in bars],normalized['style']['palette'])
        labels=root.findall('.//s:text[@data-color-index]',ns);self.assertEqual(labels[0].attrib['fill'],'#ff8800');spec['style']['match_labels']=False
        root=ET.fromstring(artifacts.svg(spec));self.assertEqual(root.findall('.//s:text[@data-color-index]',ns)[0].attrib['fill'],'#eeeeee')
        for style in (dict(text='red'),dict(background='url(https://example.com)'),dict(palette=[]),dict(match_labels='yes'),dict(script='alert(1)')):
            with self.assertRaises(ValueError):artifacts.validate({**chart(),'style':style})
        with self.assertRaises(ValueError):artifacts.validate({**chart('line'),'style':{'color_by':'category'}})
    def test_html_payload_and_csp_are_self_contained(self):
        from desktop import artifact_html
        import base64,hashlib
        spec=chart();spec['source']='</script><script>alert(1)</script>';html=artifact_html.document(spec)
        self.assertNotIn(spec['source'],html);self.assertIn('\\u003c/script\\u003e',html);self.assertEqual(html.count('<script'),2)
        digest=base64.b64encode(hashlib.sha256(artifact_html.SCRIPT.encode()).digest()).decode();self.assertIn("script-src 'sha256-"+digest+"'",html)
    def test_every_renderer_produces_standalone_xml(self):
        specs=[chart(k) for k in ('bar','line','donut')]+[dict(kind='flowchart',title='Workflow',nodes=[dict(id='a',label='Inspect'),dict(id='b',label='Verify')],edges=[{'from':'a','to':'b','label':'then'}]),dict(kind='table',title='Results',columns=['Task','State'],rows=[['Code','Done']])]
        for spec in specs:
            with self.subTest(kind=spec['kind']):self.assertTrue(ET.fromstring(artifacts.svg(spec)).tag.endswith('svg'))
        for values in ([0,0,0],[-2,0,3]):
            spec=chart();spec['series'][0]['values']=values;ET.fromstring(artifacts.svg(spec))
        spec=chart('donut');spec['labels']=['All'];spec['series'][0]['values']=[5];self.assertEqual(artifacts.svg(spec).count('<path'),2)
    def test_validation_rejects_bad_data(self):
        for value in (float('nan'),float('inf'),True,10**400):
            spec=chart();spec['series'][0]['values'][0]=value
            with self.assertRaises(ValueError):artifacts.validate(spec)
        for spec in [dict(kind='flowchart',title='Bad',nodes=[None]),dict(kind='flowchart',title='Bad',nodes=[dict(id='a')],edges=[{'from':[],'to':'a'}]),dict(kind='table',title='Bad',columns=['A'],rows=[[]])]:
            with self.assertRaises(ValueError):artifacts.validate(spec)
        spec=chart();spec['series'][0]['values']=[]
        with self.assertRaises(ValueError):artifacts.validate(spec)
    def test_text_is_escaped_and_csv_formulas_neutralized(self):
        spec=chart();spec['title']='<script>alert(1)</script>';svg=artifacts.svg(spec);self.assertNotIn('<script>',svg);self.assertIn('&lt;script&gt;',svg)
        spec=dict(kind='table',title='Export',columns=['=formula'],rows=[['@bad'],['-bad']]);self.assertIn("'=formula",artifacts.csv_text(spec));self.assertIn("'@bad",artifacts.csv_text(spec))
    def test_model_tool_persists_and_edits_with_project_and_revision_guards(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);project=root/'project';project.mkdir();responses=iter([reply('',[tool('create_artifact',{'spec':chart()})]),reply('See the artifact.')])
            core=Core(root/'state',FakeCredentials(),lambda _:next(responses));core.workspace.update({'project':str(project)})
            session=core.new_session();run=core.submit(session['id'],'Show a chart')
            import time
            until=time.monotonic()+5
            while core.store.get('run',run['id'])['status']=='running' and time.monotonic()<until:time.sleep(.01)
            self.assertEqual(core.store.get('run',run['id'])['status'],'completed')
            record=core.store.list('artifact')[0];self.assertEqual(record['session'],session['id'])
            spec=chart();spec['title']='Edited';edited=core.dispatch('edit_artifact',dict(id=record['id'],revision=1,spec=spec));self.assertEqual(edited['revision'],2)
            self.assertEqual(core.store.list('artifact_revision')[0]['spec']['title'],'Task outcomes')
            with self.assertRaises(ValueError):core.dispatch('edit_artifact',dict(id=record['id'],revision=1,spec=spec))
            restored=Core(root/'state',FakeCredentials(),lambda _:reply('Offline'));self.assertEqual(restored.dispatch('artifact',{'id':record['id']})['revision'],2)
            other=root/'other';other.mkdir();restored.workspace.update({'project':str(other)})
            with self.assertRaises(ValueError):restored.dispatch('artifact',{'id':record['id']})

if __name__=='__main__':unittest.main()
