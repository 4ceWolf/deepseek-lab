"""Headless Qt interaction checks; never launches the installed desktop UI."""
import json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from desktop.core import Core
from desktop.ui import Window,OFFICIAL_CHAT_URL
from desktop.test_desktop import FakeCredentials,reply

class NativeWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([]);cls.app.setStyle('Fusion')
        cls.app.setStyleSheet((Path(__file__).parent/'theme.qss').read_text())
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);project=self.root/'project';project.mkdir();docs=self.root/'docs';docs.mkdir()
        (project/'sample.py').write_text('answer = 42\n');(docs/'guide.md').write_text('# Working notes\nVerify before accepting a fix.')
        self.core=Core(self.root/'state',FakeCredentials(),lambda _:reply('Offline test reply.'))
        self.core.workspace.update(dict(project=str(project),docs=str(docs)))
        self.mock=patch('desktop.ui.client.call',side_effect=self.core.dispatch);self.mock.start()
        self.window=Window();self.window.show();self.wait(lambda:self.window.loaded_config)
    def tearDown(self):
        self.window.timer.stop();self.window.draft_timer.stop();self.window.close()
        self.wait(lambda:not self.window.jobs);self.mock.stop();self.temp.cleanup()
    def wait(self,predicate,timeout=4000):
        end=time.monotonic()+timeout/1000
        while time.monotonic()<end:
            self.app.processEvents()
            if predicate():return
            QTest.qWait(15)
        self.fail('Qt interaction timed out')
    def test_new_task_send_and_reload_state(self):
        self.window.new_task();self.wait(lambda:self.window.sid is not None and not getattr(self.window,'loading_session',False))
        self.window.prompt.setPlainText('Inspect this project');QTest.mouseClick(self.window.send_button,Qt.MouseButton.LeftButton)
        self.wait(lambda:bool(self.core.store.list('run')))
        self.wait(lambda:self.core.store.list('run')[0]['status']=='completed')
        self.window.poll();self.wait(lambda:'Offline test reply.' in self.window.chat.toPlainText())
        self.assertEqual(self.core.store.list('run')[0]['usage']['total_tokens'],30)
        original=self.window.sid
        self.window.sid=None;self.window.poll();self.wait(lambda:self.window.sid==original)
    def test_command_approval_console_and_elapsed_time(self):
        self.window.manual_command.setText('printf native-test');self.window.request_command()
        self.wait(lambda:self.window.current_command is not None)
        self.window.poll();self.wait(lambda:self.window.approve.isEnabled())
        self.assertIn('printf native-test',self.window.command_details.text())
        QTest.mouseClick(self.window.approve,Qt.MouseButton.LeftButton)
        self.wait(lambda:self.core.store.list('command')[0]['status']=='finished')
        self.window.poll();self.wait(lambda:'native-test' in self.window.console.toPlainText() and 'exit 0' in self.window.command_time.text())
        self.assertIn('exit 0',self.window.command_time.text())
    def test_docs_memory_settings_and_keyboard_controls(self):
        self.window.context_dock.show()
        self.wait(lambda:self.window.docs.count()==1 and self.window.files.count()==1)
        self.window.read_document(self.window.docs.item(0),True);self.wait(lambda:'Working notes' in self.window.doc_preview.toPlainText())
        self.core.workspace.remember('Style','Keep answers concise','personal');self.window.refresh_memory();self.wait(lambda:self.window.memories.count()==1)
        self.window.show_memory(self.window.memories.item(0));self.assertIn('Unverified',self.window.memory_preview.toPlainText())
        self.window.permission.setCurrentIndex(self.window.permission.findData('disabled'));self.window.save_settings()
        self.wait(lambda:self.core.workspace.settings()['permission']=='disabled')
        self.window.prompt.setFocus();self.assertTrue(self.window.prompt.hasFocus())
        self.assertTrue(self.window.prompt.accessibleName());self.assertTrue(self.window.command_list.accessibleName())
    def test_render_build_preview(self):
        session=self.core.new_session('Build a dependable workspace')
        session['messages']=[dict(role='user',content='Inspect the project and propose a small repair. Keep the changes reviewable.'),dict(role='assistant',content='I’ll inspect the relevant files, prepare a patch, and check the result before calling it complete.\n\nYou can review each command and its output in the activity panel below.')]
        self.core.store.put('session',session);self.window.load_session(session['id'])
        self.core.workspace.remember('Project workflow','Keep changes small. Run the relevant checks and preserve user edits.','project')
        command=self.core.commands.request('python3 -m unittest tests.test_parser -v',self.core.workspace.settings()['project'],'approve')
        self.window.current_command=command['id'];self.window.poll();self.wait(lambda:self.window.approve.isEnabled())
        self.window.notice.setText('Offline build preview · fixture data · no API request');self.window.notice.show()
        self.window.resize(1460,960);QTest.qWait(80)
        artifacts=Path(__file__).resolve().parents[1]/'build/previews';artifacts.mkdir(parents=True,exist_ok=True)
        self.assertTrue(self.window.grab().save(str(artifacts/'desktop-wide.png')))
        self.window.context_dock.hide();self.window.resize(1000,720);QTest.qWait(40)
        self.assertTrue(self.window.grab().save(str(artifacts/'desktop-compact.png')))
        self.assertTrue(self.window.send_button.isVisible())
    def test_failures_can_be_reported_in_the_active_dialog(self):
        errors=[];self.window.request('unknown-method',{},error=errors.append)
        self.wait(lambda:bool(errors));self.assertIn('Unknown method',errors[0])
    def test_artifact_edit_export_and_task_isolation(self):
        from desktop.test_artifacts import chart
        from PySide6.QtGui import QImage
        import threading
        session=self.core.new_session('Explore task outcomes');self.window.load_session(session['id'])
        run=dict(session=session['id'],config=self.core.workspace.settings())
        self.core.tool('create_artifact',{'spec':chart()},run,threading.Event());self.window.poll()
        self.wait(lambda:self.window.artifact_view.record is not None)
        viewer=self.window.artifact_view;self.assertEqual(viewer.table.item(0,1).text(),'8');self.assertTrue(viewer.visual.renderer().isValid())
        spec=json.loads(viewer.spec.toPlainText());spec['title']='Edited outcomes';viewer.spec.setPlainText(json.dumps(spec));viewer.save_spec();self.wait(lambda:viewer.record['revision']==2)
        viewer.spec.setPlainText('invalid');viewer.save_spec();self.assertIn('Not saved',viewer.message.text());self.assertEqual(viewer.spec.toPlainText(),'invalid')
        for kind in ('SVG','PNG','CSV','JSON'):
            path=self.root/('export.'+kind.lower());viewer.export_to(path,kind);self.assertGreater(path.stat().st_size,20)
        self.assertFalse(QImage(str(self.root/'export.png')).isNull())
        viewer.load(viewer.record);self.window.work_tabs.setCurrentIndex(1);self.window.command_panel.hide();self.window.context_dock.hide();self.window.resize(1280,880);QTest.qWait(70);viewer.resize_visual();self.window.poll();QTest.qWait(60)
        previews=Path(__file__).resolve().parents[1]/'build/previews';previews.mkdir(parents=True,exist_ok=True);self.assertTrue(self.window.grab().save(str(previews/'desktop-artifacts.png')))
        self.window.load_session(self.core.new_session('Another task')['id']);self.window.poll();self.wait(lambda:not self.window.artifact_list.count());self.assertIsNone(viewer.record)
    def test_account_chat_works_without_api_and_opens_only_official_browser_url(self):
        self.core.key='';before=len(self.core.store.list('run'))
        dialog=self.window.build_account_chat_dialog();dialog.show();QTest.qWait(20)
        with patch('desktop.ui.QDesktopServices.openUrl',return_value=True) as opened:
            QTest.mouseClick(dialog.open_chat_button,Qt.MouseButton.LeftButton)
            self.assertEqual(opened.call_count,1);self.assertEqual(opened.call_args.args[0].toString(),OFFICIAL_CHAT_URL)
        self.assertEqual(len(self.core.store.list('run')),before)
        self.assertFalse(self.core.key);dialog.close()
    def test_all_visual_types_render_in_qt(self):
        from desktop.test_artifacts import chart
        from desktop import artifacts
        specs=[chart('line'),chart('donut'),dict(kind='table',title='Checks',columns=['Check','Result'],rows=[['Unit tests','Pass']]),dict(kind='flowchart',title='Working process',nodes=[dict(id='inspect',label='Inspect evidence'),dict(id='edit',label='Make a change'),dict(id='test',label='Verify result')],edges=[{'from':'inspect','to':'edit'},{'from':'edit','to':'test'}])]
        for spec in specs:
            self.window.artifact_view.load(dict(id='fixture',revision=1,spec=artifacts.validate(spec)))
            self.assertTrue(self.window.artifact_view.visual.renderer().isValid(),spec['kind'])
            self.assertGreater(self.window.artifact_view.table.rowCount(),0)
    def test_inline_images_and_save_fallback(self):
        from PySide6.QtGui import QImage,QColor
        from PySide6.QtCore import QUrl
        from desktop.image_view import ImageDialog
        import base64
        session=self.core.new_session('Inspect a local screenshot');self.window.load_session(session['id']);image=QImage(800,420,QImage.Format.Format_RGB32);image.fill(QColor('#476c97'));path=Path(self.core.workspace.settings()['project'])/'preview.png';self.assertTrue(image.save(str(path)))
        result=self.core.dispatch('publish_image',dict(session=session['id'],path=str(path),title='Local screenshot fixture'));self.window.poll();self.wait(lambda:result['id'] in self.window.image_cache)
        self.wait(lambda:'Open image / Save original' in self.window.chat.toPlainText());self.assertIn('image://'+result['id'],self.window.chat.images)
        self.assertTrue(self.window.chat.loadResource(2,QUrl('file:///etc/passwd')).isEmpty());self.assertTrue(self.window.chat.loadResource(2,QUrl('https://example.com/a.png')).isEmpty())
        record=self.window.image_cache[result['id']];dialog=ImageDialog(record,self.window);out=self.root/'saved.png';dialog.save_to(out);self.assertEqual(out.read_bytes(),path.read_bytes());dialog.close()
        damaged=dict(record,content=base64.b64encode(b'broken').decode());dialog=ImageDialog(damaged,self.window);self.assertTrue(dialog.image.isNull());dialog.save_to(self.root/'original.bin');self.assertEqual((self.root/'original.bin').read_bytes(),b'broken');dialog.close()
        self.window.context_dock.hide();self.window.command_panel.hide();self.window.resize(1280,880);QTest.qWait(60)
        previews=Path(__file__).resolve().parents[1]/'build/previews';previews.mkdir(parents=True,exist_ok=True);self.assertTrue(self.window.grab().save(str(previews/'desktop-images.png')))
    def test_artifact_appearance_preview_save_and_html_export(self):
        from desktop.test_artifacts import chart
        from PySide6.QtGui import QColor
        import threading
        session=self.core.new_session('Style a chart');self.window.load_session(session['id']);self.core.tool('create_artifact',{'spec':chart()},dict(session=session['id'],config=self.core.workspace.settings()),threading.Event());self.window.poll();self.wait(lambda:self.window.artifact_view.record is not None)
        viewer=self.window.artifact_view;original=viewer.record['id'];viewer.apply_style(color_by='category');viewer.palette_index.setCurrentIndex(1)
        with patch('desktop.artifact_view.QColorDialog.getColor',return_value=QColor('#ff9944')):viewer.choose_color('palette')
        self.assertEqual(json.loads(viewer.spec.toPlainText())['style']['palette'][1],'#ff9944');self.assertEqual(self.core.dispatch('artifact',{'id':original})['revision'],1)
        self.assertTrue(viewer.visual.renderer().isValid());viewer.match_labels.setChecked(False);self.assertFalse(json.loads(viewer.spec.toPlainText())['style']['match_labels']);viewer.preset('Light');viewer.match_labels.setChecked(True);viewer.save_spec();self.wait(lambda:viewer.record['revision']==2)
        self.assertEqual(viewer.record['spec']['style']['background'],'#fafbfe');viewer.export_to(self.root/'chart.html','HTML');self.assertIn('<input id="match"', (self.root/'chart.html').read_text())
        self.window.work_tabs.setCurrentIndex(1);self.window.context_dock.hide();self.window.command_panel.hide();self.window.resize(1280,950);viewer.tabs.setCurrentIndex(3);QTest.qWait(50)
        previews=Path(__file__).resolve().parents[1]/'build/previews';self.assertTrue(self.window.grab().save(str(previews/'desktop-appearance.png')))
        viewer.tabs.setCurrentIndex(0);viewer.resize_visual();QTest.qWait(40);self.assertTrue(self.window.grab().save(str(previews/'desktop-artifact-light.png')))
    def test_model_restyles_existing_artifact_without_overwriting_manual_edits(self):
        from desktop.test_artifacts import chart
        import threading
        session=self.core.new_session('Restyle from chat');self.window.load_session(session['id']);run=dict(session=session['id'],config=self.core.workspace.settings());result=self.core.tool('create_artifact',{'spec':chart()},run,threading.Event());self.window.poll();self.wait(lambda:self.window.artifact_view.record is not None);viewer=self.window.artifact_view
        spec=self.core.tool('get_artifact',{'id':result['id']},run,threading.Event())['spec'];spec['style']['text']='#ffaabb';self.core.tool('update_artifact',dict(id=result['id'],revision=1,spec=spec),run,threading.Event());self.window.poll();self.wait(lambda:viewer.record['revision']==2);self.assertEqual(viewer.record['spec']['style']['text'],'#ffaabb')
        draft=json.loads(viewer.spec.toPlainText());draft['title']='Keep my edits';viewer.spec.setPlainText(json.dumps(draft));spec['style']['background']='#202020';self.core.tool('update_artifact',dict(id=result['id'],revision=2,spec=spec),run,threading.Event());self.window.poll();self.wait(lambda:'newer revision' in viewer.message.text());self.assertIn('Keep my edits',viewer.spec.toPlainText());self.assertEqual(viewer.record['revision'],2)
        viewer.save_spec();self.wait(lambda:'Artifact changed' in viewer.message.text());self.assertIn('Keep my edits',viewer.spec.toPlainText())
        self.window.select_artifact(self.window.artifact_list.currentItem());self.wait(lambda:viewer.record['revision']==3)
    def test_review_recovery_requires_acknowledgment_and_keeps_receipts(self):
        self.core.provider=lambda _:(_ for _ in ()).throw(OSError('Unknown request outcome'));session=self.core.new_session('Recover interrupted work');run=self.core.submit(session['id'],'Continue carefully');self.wait(lambda:self.core.store.get('run',run['id'])['status']=='error');self.window.load_session(session['id']);self.window.work_tabs.setCurrentIndex(2);self.window.review.refresh();self.wait(lambda:self.window.review.report is not None);self.assertIn('Unsettled request reservation',self.window.review.view.toPlainText())
        report=self.core.dispatch('recovery_report',{'session':session['id']});dialog=self.window.review.build_recovery_dialog(report);dialog.show();QTest.qWait(30);self.assertFalse(dialog.resume.isEnabled());dialog.ack.setChecked(True);self.assertTrue(dialog.resume.isEnabled());self.core.provider=lambda _:reply('Inspected saved state; no commands replayed.');QTest.mouseClick(dialog.resume,Qt.MouseButton.LeftButton);self.wait(lambda:not dialog.isVisible());self.wait(lambda:self.core.store.list('run')[0]['status']=='completed');self.assertEqual(self.core.store.list('run')[0]['parent'],run['id']);self.assertEqual(self.core.store.list('command'),[])
        self.window.context_dock.hide();self.window.command_panel.hide();self.window.resize(1280,930);self.window.poll();self.wait(lambda:'reply finished' in self.window.run_status.text());self.window.review.refresh();self.wait(lambda:not self.window.review.loading);self.window.notice.setText('Offline recovery preview · fixture data · no API request');self.window.notice.show();QTest.qWait(40);previews=Path(__file__).resolve().parents[1]/'build/previews';self.assertTrue(self.window.grab().save(str(previews/'desktop-review.png')))
    def test_budget_dialog_saves_explicit_rates_and_context_controls(self):
        from desktop.review_panel import budget_dialog
        dialog=budget_dialog(self.window);dialog.show();fields=dialog.controls;self.assertFalse(fields['rates']['deepseek-flash']['input'].isEnabled());fields['priced'].setChecked(True)
        for model,rates in fields['rates'].items():
            for field in rates.values():field.setValue(1 if model=='deepseek-flash' else 3)
        fields['tokens'].setValue(100000);fields['usd'].setValue(1);fields['economy'].setChecked(True);fields['context'].setValue(50000);QTest.mouseClick(fields['save'],Qt.MouseButton.LeftButton);self.wait(lambda:not dialog.isVisible());cfg=self.core.workspace.settings();self.assertEqual(cfg['max_total_tokens'],100000);self.assertEqual(cfg['max_task_usd'],1);self.assertTrue(cfg['economy_routing']);self.assertEqual(cfg['context_limit'],50000)
    def test_worktree_ui_requests_normal_command_approval(self):
        self.window.review.create_worktree();self.wait(lambda:self.window.current_command is not None);self.window.poll();self.wait(lambda:self.window.approve.isEnabled());self.assertIn('worktree add',self.window.command_details.text());self.assertEqual(self.core.store.list('command')[0]['status'],'awaiting_approval');self.window.decide(False);self.wait(lambda:self.core.store.list('command')[0]['status']=='denied')
    def test_account_chat_browser_failure_has_visible_recovery(self):
        from PySide6.QtWidgets import QLabel
        dialog=self.window.build_account_chat_dialog();dialog.show();QTest.qWait(20)
        with patch('desktop.ui.QDesktopServices.openUrl',return_value=False):QTest.mouseClick(dialog.open_chat_button,Qt.MouseButton.LeftButton)
        text=' '.join(label.text() for label in dialog.findChildren(QLabel))
        self.assertIn('could not be opened',text);self.assertIn(OFFICIAL_CHAT_URL,text);dialog.close()

    def test_native_website_chat_controls_stream_and_no_api_key(self):
        from desktop.test_webchat import FakeBridge
        self.core.key='';self.core.web.bridge=FakeBridge();self.core.web.connection_status='connected'
        self.window.normal_chat();view=self.window.website_chat
        self.wait(lambda:view.state.get('connection')=='connected');view.new_chat();self.wait(lambda:view.sid is not None)
        self.wait(lambda:view.send_button.isEnabled());view.search.setChecked(True);view.prompt.setPlainText('Search the web for this example')
        view.prompt.setFocus();QTest.keyClick(view.prompt,Qt.Key.Key_Return,Qt.KeyboardModifier.ControlModifier)
        self.wait(lambda:bool(self.core.web.bridge.calls));self.wait(lambda:not self.core.web.active);view.poll();self.wait(lambda:'Checked answer' in view.transcript.toPlainText())
        self.assertTrue(self.core.web.bridge.calls[0]['search_enabled']);self.assertNotIn('Private reasoning',view.transcript.toPlainText());self.assertIn('usage unknown',view.status.text());self.assertEqual(self.core.store.list('command'),[])
        self.wait(lambda:view.model.isEnabled() and 'completed' in view.status.text().lower());view.model.setCurrentIndex(1);self.assertFalse(view.search.isChecked());self.assertFalse(view.search.isEnabled());view.model.setCurrentIndex(0);self.assertTrue(view.search.isEnabled())
        view.timer.stop();view.notice.setText('Offline build preview · sample response · no provider request')
        preview=Path(__file__).resolve().parents[1]/'build/previews/desktop-website-chat.png'
        self.window.resize(1120,900);QTest.qWait(60);self.assertTrue(self.window.grab().save(str(preview)))
        self.window.resize(900,850);QTest.qWait(30);self.assertTrue(view.send_button.isVisible());self.assertTrue(self.window.grab().save(str(preview.with_name('desktop-website-compact.png'))))
        self.window.mode.setCurrentIndex(self.window.mode.findData('code'))
    def test_website_draft_reopens_and_login_failure_is_visible(self):
        from desktop.test_webchat import FakeBridge
        self.core.web.bridge=FakeBridge();self.window.normal_chat();view=self.window.website_chat
        view.new_chat();self.wait(lambda:view.sid is not None and not view.loading);sid=view.sid
        view.prompt.setPlainText('Keep this draft');view.instructions.setPlainText('Be concise');view.thinking.setCurrentIndex(view.thinking.findData('on'));view.save_draft();self.wait(lambda:self.core.web.session(sid)['draft']=='Keep this draft')
        self.window.mode.setCurrentIndex(self.window.mode.findData('code'));self.window.normal_chat();self.assertEqual(view.prompt.toPlainText(),'Keep this draft');self.assertEqual(self.core.web.session(sid)['instructions'],'Be concise');self.assertEqual(self.core.web.session(sid)['options']['thinking'],'on')
        self.assertFalse(view.send_button.isEnabled());self.assertTrue(view.connect_button.accessibleName() or view.connect_button.text())
        def unavailable(browser=''):raise ValueError('A system Chrome or Chromium browser is required. Nothing has been installed.')
        self.core.web.bridge.start=unavailable;view.connect_account();self.wait(lambda:not self.core.web.login_active);view.poll()
        self.wait(lambda:'Nothing has been installed' in view.notice.text());self.assertFalse(view.send_button.isEnabled());self.window.mode.setCurrentIndex(self.window.mode.findData('code'))

    def test_quiet_layout_mode_switch_and_settings_disclosure(self):
        self.assertFalse(self.window.context_dock.isVisible());self.assertFalse(self.window.command_panel.isVisible())
        preview=Path(__file__).resolve().parents[1]/'build/previews/desktop-quiet-code.png';self.window.resize(1120,850);QTest.qWait(30);self.assertTrue(self.window.grab().save(str(preview)))
        self.window.toggle_workspace();self.assertTrue(self.window.context_dock.isVisible());self.window.toggle_workspace()
        self.window.normal_chat();view=self.window.website_chat
        self.wait(lambda:not self.window.project.isVisible());self.assertIs(self.window.pages.currentWidget(),view);self.assertFalse(self.window.project.isVisible());self.assertFalse(self.window.command_toggle.isVisible());self.assertFalse(self.window.workspace_toggle.isVisible());self.assertFalse(self.window.tasks_dock.isVisible())
        self.assertFalse(view.instructions.isVisible());self.assertFalse(view.browser.isVisible());view.open_settings();QTest.qWait(30)
        self.assertTrue(view.instructions.isVisible());self.assertTrue(view.browser.isVisible());QTest.keyClick(view.settings_dialog,Qt.Key.Key_Escape);self.assertFalse(view.settings_dialog.isVisible())
        self.window.mode.setCurrentIndex(self.window.mode.findData('code'));self.wait(lambda:self.window.project.isVisible());self.assertTrue(self.window.project.isVisible());self.assertTrue(self.window.tasks_dock.isVisible());self.assertFalse(self.window.context_dock.isVisible())
    def test_tool_details_disclosure_preserves_complete_history(self):
        session=self.core.new_session('Inspect a source file');session['messages']=[dict(role='assistant',content='I checked the file.',tool_calls=[{'id':'call1','type':'function','function':{'name':'read_file','arguments':'{"path":"sample.py"}'}}]),dict(role='tool',tool_call_id='call1',content='{"content":"PRIVATE_TOOL_DETAIL"}')]
        self.core.store.put('session',session);self.window.load_session(session['id']);self.wait(lambda:'I checked the file.' in self.window.chat.toPlainText())
        self.assertIn('Work',self.window.chat.toPlainText());self.assertNotIn('PRIVATE_TOOL_DETAIL',self.window.chat.toPlainText())
        self.window.details_action.setChecked(True);self.assertIn('PRIVATE_TOOL_DETAIL',self.window.chat.toPlainText());self.window.details_action.setChecked(False)
        self.assertEqual(self.core.store.get('session',session['id'])['messages'],session['messages'])

    def test_chat_mode_surfaces_code_approval_without_executing_it(self):
        receipt=self.core.commands.request('printf permission-check',self.core.workspace.settings()['project'],'approve')
        self.window.poll();self.wait(lambda:self.window.pending_approvals);self.window.normal_chat()
        self.wait(lambda:self.window.approval_badge.isVisible());QTest.mouseClick(self.window.approval_badge,Qt.MouseButton.LeftButton)
        self.wait(lambda:self.window.mode.currentData()=='code');self.assertTrue(self.window.command_panel.isVisible());self.assertEqual(self.core.store.get('command',receipt['id'])['status'],'awaiting_approval')

    def test_native_motion_and_reduced_motion(self):
        from desktop import motion
        self.app.setProperty('reduceMotion',False)
        motion.reveal(self.window.prompt,60);self.assertIsNotNone(self.window.prompt.graphicsEffect());QTest.qWait(100);self.assertIsNone(self.window.prompt.graphicsEffect())
        self.app.setProperty('reduceMotion',True);motion.reveal(self.window.prompt);self.assertIsNone(self.window.prompt.graphicsEffect())
        self.app.setProperty('reduceMotion',None)
    def test_imported_website_history_is_read_only_and_preserves_draft(self):
        from desktop.test_webchat import FakeBridge
        self.core.web.bridge=FakeBridge();self.core.web.connect();self.wait(lambda:not self.core.web.login_active)
        self.window.normal_chat();view=self.window.website_chat;view.new_chat();self.wait(lambda:bool(view.sid) and not view.loading)
        local=view.sid;view.prompt.setPlainText('Preserve my draft');view.save_draft();self.wait(lambda:self.core.web.session(local)['draft']=='Preserve my draft')
        view.poll();self.wait(lambda:any(view.history.item(i).data(Qt.ItemDataRole.UserRole+1) for i in range(view.history.count())))
        remote=next(view.history.item(i) for i in range(view.history.count()) if view.history.item(i).data(Qt.ItemDataRole.UserRole+1))
        view.select(remote);self.wait(lambda:'An older answer' in view.transcript.toPlainText());self.assertFalse(view.send_button.isEnabled());self.assertFalse(view.prompt.isEnabled());self.assertTrue(view.open_original.isVisible())
        view.load(local);self.wait(lambda:not view.loading);self.assertEqual(view.prompt.toPlainText(),'Preserve my draft')
    def test_islands_learning_entry_and_populated_preview(self):
        self.window.open_context('Learning');self.assertEqual(self.window.context_tabs.tabText(self.window.context_tabs.currentIndex()),'Learning');self.wait(lambda:'No lessons yet' in self.window.learning_view.detail.toPlainText());self.window.context_dock.hide()
        session=self.core.new_session('Fix reconnect without losing drafts');session['messages']=[dict(role='user',content='Fix reconnect without losing my draft. Add a regression test.'),dict(role='assistant',content='## The draft now survives reconnects.\n\nThe connection can restart without replacing the editor. Your unsent text stays in the conversation until you send it.\n\n- Draft preserved after reconnect\n- No duplicate message on retry\n- Regression checks passed — illustrative fixture\n\nThe changes are ready to review.')]
        self.core.store.put('session',session);self.window.load_session(session['id']);self.wait(lambda:'draft now' in self.window.chat.toPlainText());self.window.resize(1440,960);self.window.heading.setFocus();QTest.qWait(220)
        self.assertTrue(self.window.grab().save(str(Path(__file__).resolve().parents[1]/'build/previews/desktop-islands.png')))

    def test_enter_send_shift_enter_newline_and_chat_artifacts(self):
        from desktop.test_webchat import FakeBridge
        from desktop.test_artifacts import chart
        self.core.web.bridge=FakeBridge();self.core.web.connection_status='connected';self.window.normal_chat();v=self.window.website_chat
        self.wait(lambda:bool(v.sid) and v.send_button.isEnabled());v.prompt.setFocus();v.prompt.setPlainText('First line');QTest.keyClick(v.prompt,Qt.Key.Key_Return,Qt.KeyboardModifier.ShiftModifier);self.assertIn('\n',v.prompt.toPlainText());v.prompt.insertPlainText('Second line');QTest.keyClick(v.prompt,Qt.Key.Key_Return)
        self.wait(lambda:bool(self.core.web.bridge.calls));self.wait(lambda:not self.core.web.active);self.assertEqual(len(self.core.web.bridge.calls),1)
        self.core.web.dispatch('web_import_artifact',{'session':v.sid,'spec':chart()});v.refresh_artifacts();self.wait(lambda:v.artifact_view.record is not None);self.assertEqual(v.artifact_list.count(),1);self.assertTrue(v.artifact_view.visual.renderer().isValid())
    def test_inline_thinking_and_tool_activity_preserve_raw_messages(self):
        from PySide6.QtCore import QUrl
        s=self.core.new_session('Expandable work');s['messages']=[dict(role='assistant',content='Finished',reasoning_content='PROVIDER_THINKING_FIXTURE',tool_calls=[dict(id='tool1',type='function',function=dict(name='read_file',arguments='{"path":"sample.py"}'))]),dict(role='tool',tool_call_id='tool1',content='TOOL_RESULT_FIXTURE')]
        self.core.store.put('session',s);self.window.load_session(s['id']);self.wait(lambda:'Finished' in self.window.chat.toPlainText())
        self.assertNotIn('PROVIDER_THINKING_FIXTURE',self.window.chat.toPlainText());self.assertNotIn('TOOL_RESULT_FIXTURE',self.window.chat.toPlainText())
        self.window.open_transcript_link(QUrl('app-thinking:0'));self.assertIn('PROVIDER_THINKING_FIXTURE',self.window.chat.toPlainText());self.window.open_transcript_link(QUrl('app-activity:0'));self.assertIn('TOOL_RESULT_FIXTURE',self.window.chat.toPlainText())
        self.assertEqual(self.core.store.get('session',s['id'])['messages'],s['messages']);self.assertNotIn(self.window.command_toggle,[self.window.toolbar.widgetForAction(a) for a in self.window.toolbar.actions()])

    def test_delayed_web_send_preserves_followup_draft(self):
        from desktop.test_webchat import FakeBridge
        self.core.web.bridge=FakeBridge();self.core.web.connection_status='connected';self.window.normal_chat();v=self.window.website_chat;self.wait(lambda:bool(v.sid) and v.send_button.isEnabled());v.timer.stop();v.draft_timer.stop()
        old=v.request;pending=[]
        def delayed(method,data,callback=None,error=None):
            if method=='web_send':pending.append(callback)
            else:old(method,data,callback,error)
        v.request=delayed;v.prompt.setPlainText('First message');v.send();self.assertEqual(len(pending),1);v.prompt.setPlainText('Follow-up draft');pending[0](self.core.web.session(v.sid));self.assertEqual(v.prompt.toPlainText(),'Follow-up draft');self.assertTrue(v.dirty);v.request=old
    def test_artifact_save_reply_cannot_replace_another_selection(self):
        from desktop.test_artifacts import chart
        import copy
        v=self.window.artifact_view;first=dict(id='one',revision=1,spec=chart());second=dict(id='two',revision=1,spec=chart());v.load(first);spec=chart();spec['title']='Changed';v.spec.setPlainText(json.dumps(spec));pending=[];original=v.request
        v.request=lambda method,data,callback=None,error=None:pending.append(callback);v.save_spec();v.load(second);pending[0](dict(first,revision=2,spec=spec));self.assertEqual(v.record['id'],'two')
        v.load(first);v.spec.setPlainText(json.dumps(spec));v.save_spec();newer=dict(spec,title='Newer unsaved edit');v.spec.setPlainText(json.dumps(newer));pending[1](dict(first,revision=2,spec=spec));self.assertEqual(json.loads(v.spec.toPlainText())['title'],'Newer unsaved edit');self.assertEqual(v.record['revision'],2);v.request=original
    def test_switching_task_stops_old_draft_timer(self):
        one=self.core.new_session('One');two=self.core.new_session('Two');two['draft']='Second draft';self.core.store.put('session',two);self.window.load_session(one['id']);self.wait(lambda:not self.window.loading_session);self.window.prompt.setPlainText('First draft');self.window.save_draft();self.window.load_session(two['id']);self.wait(lambda:not self.window.loading_session);QTest.qWait(650);self.assertEqual(self.window.prompt.toPlainText(),'Second draft');self.assertEqual(self.core.store.get('session',one['id'])['draft'],'First draft');self.assertEqual(self.core.store.get('session',two['id'])['draft'],'Second draft')

    def test_native_drawing_export_has_opaque_full_canvas(self):
        from desktop.test_drawing import PROGRAM
        from desktop.drawing import parse
        from PySide6.QtGui import QImage
        v=self.window.artifact_view;spec=parse(PROGRAM);v.load(dict(id='drawing-preview',revision=1,spec=spec));self.assertTrue(v.visual.renderer().isValid());path=self.root/'drawing.png';v.export_to(path,'PNG');im=QImage(str(path));self.assertEqual(im.pixelColor(im.width()-5,im.height()-5).alpha(),255);self.assertEqual(im.pixelColor(im.width()-5,im.height()-5).name(),spec['style']['background'])
    def test_long_transcript_keeps_overflow_reachable(self):
        self.window.chat.setPlainText('Long task log\n'*4000);QTest.qWait(30);self.assertGreater(self.window.chat.verticalScrollBar().maximum(),0);self.assertEqual(self.window.chat.verticalScrollBarPolicy(),Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def test_interactive_card_is_inline_and_local_controls_work(self):
        from desktop.test_interactive import wave
        from desktop import artifacts
        from desktop.interactive_view import InteractiveCard
        spec=artifacts.validate(wave());s=self.core.new_session('Explore waves');s['messages']=[dict(role='user',content='Show me how two waves combine.'),dict(role='assistant',content='Move the controls and drag the probe.\n\n```deepseek-visual\n'+json.dumps(spec)+'\n```\n\nThe sum changes immediately.')];self.core.store.put('session',s);self.window.load_session(s['id']);self.wait(lambda:bool(self.window.chat.cards));self.wait(lambda:all(c.isVisible() for c in self.window.chat.cards.values()))
        card=next(iter(self.window.chat.cards.values()));self.assertIsInstance(card,InteractiveCard);self.assertGreater(self.window.chat.document().size().height(),card.height());self.assertFalse(self.window.work_tabs.isTabVisible(1));self.assertEqual(self.core.store.list('run'),[])
        before=card.readout.text();card.bindings['amplitude'][0].setValue(25);self.assertEqual(card.values['amplitude'],2.5);self.assertNotEqual(before,card.readout.text());card.bindings['show_second'][0].setChecked(False);self.assertFalse(card.values['show_second'])
        p=card.scene.point(card.values['probe_x'],card.values['probe_y']).toPoint();QTest.mousePress(card.scene,Qt.MouseButton.LeftButton,pos=p);QTest.mouseMove(card.scene,p+__import__('PySide6.QtCore',fromlist=['QPoint']).QPoint(45,-20));QTest.mouseRelease(card.scene,Qt.MouseButton.LeftButton,pos=p);self.assertNotEqual(card.values['probe_x'],1)
        self.window.chat.flush_visual_state();self.wait(lambda:bool(self.core.dispatch('visual_states',{'context':'api:'+s['id']})));self.assertEqual(self.core.store.list('command'),[])
        preview=Path(__file__).resolve().parents[1]/'build/previews/desktop-interactive-inline.png';self.window.resize(1440,1100);QTest.qWait(100);self.assertTrue(self.window.grab().save(str(preview)))
    def test_inline_card_reuses_state_during_reply_updates_and_switches(self):
        from desktop.test_interactive import wave
        from desktop import artifacts,interactive
        spec=artifacts.validate(wave());s=self.core.new_session('Keep sliders');s['messages']=[dict(role='assistant',content='```deepseek-visual\n'+json.dumps(spec)+'\n```')];self.core.store.put('session',s);self.window.load_session(s['id']);self.wait(lambda:bool(self.window.chat.cards));card=next(iter(self.window.chat.cards.values()));card.set_value('amplitude',2.3);self.window.chat.flush_visual_state();self.wait(lambda:bool(self.core.dispatch('visual_states',{'context':'api:'+s['id']})))
        s['messages'][0]['content']+='\nMore explanation.';self.core.store.put('session',s);self.window.receive_session(s);self.assertIs(card,next(iter(self.window.chat.cards.values())));self.assertEqual(card.values['amplitude'],2.3)
        other=self.core.new_session('Other');self.window.load_session(other['id']);self.wait(lambda:not self.window.loading_session);self.window.load_session(s['id']);self.wait(lambda:bool(self.window.chat.cards));self.wait(lambda:next(iter(self.window.chat.cards.values())).values['amplitude']==2.3)
    def test_interactive_website_reply_renders_inside_conversation(self):
        from desktop.test_webchat import FakeBridge
        from desktop.test_interactive import wave
        bridge=FakeBridge(events=[{'content':'Explore this:\n```deepseek-visual\n'+json.dumps(wave())+'\n```'},{'finish':True,'conversation':'interactive-thread'}]);self.core.web.bridge=bridge;self.core.web.connection_status='connected';self.window.normal_chat();v=self.window.website_chat;self.wait(lambda:bool(v.sid) and v.send_button.isEnabled());v.prompt.setPlainText('Explain waves interactively');v.send();self.wait(lambda:not self.core.web.active);v.poll();self.wait(lambda:bool(v.transcript.cards));self.assertEqual(v.chat_tabs.currentIndex(),0);self.assertFalse(v.chat_tabs.isTabVisible(1));self.assertEqual(len(bridge.calls),1)
        card=next(iter(v.transcript.cards.values()));card.set_value('phase',3);self.assertEqual(len(bridge.calls),1);self.assertEqual(len(self.core.store.list('web_artifact')),1)

    def test_multiple_inline_visuals_scroll_and_keep_context_separate(self):
        from desktop.test_interactive import wave
        from desktop import artifacts
        spec=artifacts.validate(wave());b=self.window.chat;b.set_context('api:inline-a');block='```deepseek-visual\n'+json.dumps(spec)+'\n```';b.setMarkdown('Before\n\n'+block+'\nBetween\n'+block+'\nAfter');self.app.processEvents();self.assertEqual(len(b.cards),2);self.assertEqual(len(b.positions),2);self.assertNotIn('INLINEVISUAL',b.toPlainText());self.assertLess(b.positions[0][1],b.positions[1][1]);self.assertGreater(b.document().size().height(),1000)
        first=next(iter(b.cards.values()));first.set_value('amplitude',2);b.flush_visual_state();self.wait(lambda:bool(self.core.dispatch('visual_states',{'context':'api:inline-a'})));b.set_context('api:inline-b');self.assertEqual(b.original_markdown,'');self.assertFalse(b.cards);self.assertEqual(self.core.dispatch('visual_states',{'context':'api:inline-b'}),{})
    def test_native_animation_and_reduced_motion_scrubbing(self):
        from desktop.test_interactive import wave
        from desktop import artifacts,motion
        b=self.window.chat;b.setMarkdown('```deepseek-visual\n'+json.dumps(artifacts.validate(wave()))+'\n```');self.wait(lambda:bool(b.cards));card=next(iter(b.cards.values()));self.app.setProperty('reduceMotion',False);card.toggle_play();self.assertTrue(card.clock.isActive());card.last_tick=time.monotonic()-.1;card.tick();self.assertGreater(card.values['t'],0);card.toggle_play();self.assertFalse(card.clock.isActive());self.app.setProperty('reduceMotion',True);card.toggle_play();self.assertFalse(card.clock.isActive());card.time_slider.setValue(500);self.assertEqual(card.values['t'],6);card.reset();self.assertEqual(card.values['t'],0);self.app.setProperty('reduceMotion',None)

if __name__=='__main__':unittest.main()
