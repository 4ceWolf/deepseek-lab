"""Geometry, escaping, native drawing capture and export without commands/network."""
import json,tempfile,threading,unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from desktop import drawing,artifacts,artifact_html,transcript
from desktop.core import Core
from desktop.test_desktop import FakeCredentials
from desktop.web_artifacts import capture
PROGRAM='''canvas 800 320
title "An example workflow"
source "Illustrative fixture"
rect 40 100 220 100 surface grid 12
text 70 155 22 p0 "Input & evidence"
arrow 280 150 500 150 p1 3
circle 620 150 70 surface p1
text 570 155 20 title "Result"
line 40 250 700 250 muted 2
'''
class DrawingTests(unittest.TestCase):
    def test_program_renders_valid_xml_with_escape_and_tokens(self):
        spec=drawing.parse(PROGRAM);svg=artifacts.svg(spec);root=ET.fromstring(svg)
        self.assertTrue(root.tag.endswith('svg'));self.assertIn('Input &amp; evidence',svg);self.assertIn('data-stroke-role="grid"',svg);self.assertIn('<polygon',svg)
        self.assertEqual(len(artifacts.data_rows(spec)[1]),6)
    def test_unknown_commands_and_bad_geometry_are_rejected(self):
        for line in ('exec "rm -rf /"','image "https://example.com"','rect 0 0 900 20 surface p0 0','circle 0 0 20 surface p0','arrow 0 0 0 0 p0 2','text 10 10 20 red "No"','line NaN 0 2 2 p0 2'):
            with self.subTest(line=line),self.assertRaises(ValueError):drawing.parse(PROGRAM+'\n'+line)
        with self.assertRaises(ValueError):drawing.parse('canvas 800 320\n'+('text 10 10 20 p0 "x"\n'*81))
    def test_svg_text_injection_and_html_export(self):
        spec=drawing.parse(PROGRAM.replace('Input & evidence','<script>alert(1)</script>'));svg=artifacts.svg(spec)
        self.assertNotIn('<script>',svg);self.assertIn('&lt;script&gt;',svg);html=artifact_html.document(spec);self.assertIn("default-src 'none'",html);self.assertIn('data-stroke-role',html)
    def test_model_tool_and_website_capture_share_renderer(self):
        with tempfile.TemporaryDirectory() as folder:
            core=Core(folder,FakeCredentials());session=core.new_session();run=dict(config=core.workspace.settings(),session=session['id'])
            r=core.tool('draw_visual',{'commands':PROGRAM},run,threading.Event());self.assertEqual(core.store.get('artifact',r['id'])['spec']['kind'],'drawing')
            m=dict(role='assistant',content='```deepseek-draw\n'+PROGRAM+'\n```');capture(core,'website-fixture',[m]);capture(core,'website-fixture',[m]);self.assertEqual(len(core.store.list('web_artifact')),1);self.assertEqual(core.store.list('command'),[])
            self.assertIn('app-artifacts:',transcript.render([m],visuals=True));self.assertNotIn('rect 40',transcript.render([m],visuals=True))
    def test_invalid_drawing_remains_readable_in_transcript(self):
        raw='```deepseek-draw\nexec "x"\n```';self.assertIn('exec',transcript.render([dict(role='assistant',content=raw)],visuals=True))

    def test_plain_command_reply_is_rendered_without_model_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            core=Core(folder,FakeCredentials());m=dict(role='assistant',content=PROGRAM);capture(core,'plain-reply',[m]);self.assertEqual(len(core.store.list('web_artifact')),1);self.assertIn('app-artifacts:',transcript.render([m],visuals=True))
            capture(core,'invalid',[dict(role='assistant',content='canvas 800 400\nrun_shell "x"')]);self.assertEqual(len(core.store.list('web_artifact')),1)
