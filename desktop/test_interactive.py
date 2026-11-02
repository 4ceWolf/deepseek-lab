"""Interactive visual validation, expression safety and durable state."""
import copy,json,tempfile,threading,unittest
from desktop import artifacts,interactive,interactive_html
from desktop.core import Core
from desktop.test_desktop import FakeCredentials

def wave():
    return dict(kind='interactive',title='Explore wave interference',description='Move the controls to compare two waves. Drag the probe to measure their sum.',source='Illustrative mathematical model: sum of two sine waves; no measured data.',controls=[dict(id='amplitude',label='Amplitude',type='slider',min=0,max=3,step=.1,value=1,unit='m'),dict(id='phase',label='Phase',type='slider',min=0,max=6.28,step=.01,value=0,unit='rad'),dict(id='show_second',label='Second wave',type='toggle',value=True),dict(id='probe',label='Probe',type='point',x=1,y=0)],scene=dict(x=[-8,8],y=[-4,4],axes=True,layers=[dict(type='curve',x='u',y='amplitude*sin(u-t)',u=[-8,8],samples=200,color='p0',label='First wave'),dict(type='curve',x='u',y='amplitude*sin(u-t+phase)',u=[-8,8],samples=200,color='p1',label='Second wave',visible='show_second'),dict(type='curve',x='u',y='amplitude*sin(u-t)+(amplitude*sin(u-t+phase) if show_second else 0)',u=[-8,8],samples=200,color='p2',label='Sum')]),readouts=[dict(label='Sum at probe',expr='amplitude*sin(probe_x-t)+(amplitude*sin(probe_x-t+phase) if show_second else 0)',unit='m')],animation=dict(duration=12,speed=1))

class InteractiveTests(unittest.TestCase):
    def test_expression_arithmetic_comparisons_and_domains(self):
        v=dict(interactive.defaults(artifacts.validate(wave())),u=2)
        for expr,result in [('2**3',8),('min(2)',2),('max(2,3)',3),('1 if amplitude > 0 else 2',1),('sin(pi/2)',1),('-3 % 2',1)]:self.assertAlmostEqual(interactive.evaluate(expr,v),result)
        for expr in ['1/0','sqrt(-1)','10**100']:
            with self.assertRaises(ValueError):interactive.evaluate(expr,v)
    def test_unsupported_operations_and_calls_cannot_execute(self):
        names=tuple(sorted(interactive.defaults(artifacts.validate(wave()))))
        for expr in ["__import__('os')",'amplitude.real','[1][0]','sum([1,2])','sin(1,2)','unknown+1','(lambda: 1)()', 'u'*300]:
            with self.subTest(expr=expr),self.assertRaises(ValueError):interactive.expression(expr,names)
    def test_bounds_identifiers_and_sample_budgets(self):
        for control in [dict(id='t',type='slider'),dict(id='class',type='slider'),dict(id='bad-id',type='slider'),dict(id='a',type='slider',min=1,max=0),dict(id='a',type='slider',min=0,max=100,step=.000001)]:
            spec=wave();spec['controls'].append(control)
            with self.assertRaises(ValueError):artifacts.validate(spec)
        spec=wave();spec['scene']['layers']*=4
        with self.assertRaises(ValueError):artifacts.validate(spec)
        spec=wave();spec['scene']['layers'][0]['y']='u.__class__'
        with self.assertRaises(ValueError):artifacts.validate(spec)
    def test_tools_and_state_survive_core_restart_without_model_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            core=Core(folder,FakeCredentials(),lambda _:self.fail('No provider calls expected'));s=core.new_session();r=core.tool('create_interactive_visual',{'spec':wave()},dict(session=s['id'],config=core.workspace.settings()),threading.Event());spec=core.store.get('artifact',r['id'])['spec'];key=interactive.identity(spec);context='api:'+s['id']
            core.dispatch('save_visual_state',dict(context=context,key=key,spec=spec,state={'amplitude':2.5,'show_second':False,'probe_x':3,'probe_y':1,'t':4}));restored=Core(folder,FakeCredentials());state=restored.dispatch('visual_states',{'context':context})[key];self.assertEqual(state['amplitude'],2.5);self.assertFalse(state['show_second']);self.assertEqual(restored.dispatch('visual_states',{'context':'api:other'}),{})
            with self.assertRaises(ValueError):core.dispatch('save_visual_state',dict(context=context,key=key,spec=spec,state={'amplitude':99}))
    def test_export_uses_fixed_runtime_and_escaped_data(self):
        spec=wave();spec['title']='</script><script>BAD</script>';spec=artifacts.validate(spec);doc=interactive_html.document(spec)
        self.assertNotIn(spec['title'],doc);self.assertIn('\\u003c/script\\u003e',doc);self.assertIn("default-src 'none'",doc);self.assertNotIn('eval(',interactive_html.SCRIPT);self.assertNotIn('new Function',interactive_html.SCRIPT);self.assertIn('pointermove',doc)
    def test_static_fallback_is_valid_xml(self):
        from xml.etree import ElementTree as ET
        s=artifacts.validate(wave());ET.fromstring(artifacts.svg(s));self.assertIn('Interactive visual',artifacts.svg(s))
