"""Native website-account conversation panel; no API tools or command execution."""
import json,time
from . import motion,transcript
from .composer import MessageEdit
from .artifact_view import ArtifactView
from PySide6.QtCore import Qt,QTimer,QUrl
from PySide6.QtGui import QDesktopServices,QKeySequence,QShortcut
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QComboBox,QCheckBox,QPlainTextEdit,QLineEdit,QListWidget,QListWidgetItem,QSplitter,QFileDialog,QMessageBox,QDialog,QFormLayout,QDialogButtonBox,QTabWidget,QInputDialog

class WebsiteChat(QWidget):
    def __init__(self,request,parent=None,embedded=False):
        super().__init__(parent)
        from .ui import SafeBrowser,button,label
        from .inline_visuals import InlineBrowser
        self.request=request;self.sid=None;self.polling=False;self.loading=False;self.signature=None;self.sessions_signature=None;self.rendered_options=None;self.chat_status='';self.state={};self.dirty=False;self.browser_loaded=False
        outer=QHBoxLayout(self);outer.setContentsMargins(8,8,8,8);outer.setSpacing(10)
        self.history_panel=QWidget();self.history_panel.setObjectName('WebsiteHistory');self.history_panel.setFixedWidth(242);lv=QVBoxLayout(self.history_panel);lv.setContentsMargins(16,22,16,22)
        lv.addWidget(label('d /   deepseek lab','Brand'));lv.addSpacing(16);lv.addWidget(button('＋ New conversation',self.new_chat));lv.addSpacing(18);lv.addWidget(label('CONVERSATIONS','Eyebrow'))
        self.history=QListWidget();self.history.setWordWrap(True);self.history.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.history.setAccessibleName('Saved website chats');self.history.itemClicked.connect(self.select);lv.addWidget(self.history,1)
        self.sync_button=button('Refresh website history',lambda:self.request('web_history_sync',{},lambda _:self.poll(),self.fail),'Quiet');lv.addWidget(self.sync_button)
        self.open_original=button('Open original on website ↗',self.open_original_chat,'Quiet');self.open_original.hide();lv.addWidget(self.open_original)
        lv.addWidget(button('Account & chat settings',self.open_settings,'Quiet'));lv.addWidget(label('Website account · local tools off','Muted'));outer.addWidget(self.history_panel)
        self.main_panel=QWidget();self.main_panel.setObjectName('WebsiteMain');layout=QVBoxLayout(self.main_panel);layout.setContentsMargins(28,18,28,20);layout.setSpacing(12);outer.addWidget(self.main_panel,1)
        row=QHBoxLayout();self.sidebar_button=button('History',self.toggle_history);self.sidebar_button.setAccessibleName('Toggle chat history');row.addWidget(self.sidebar_button)
        self.title=label('A fresh conversation','ConversationTitle');row.addWidget(self.title,1);self.connection=label('Not connected','Muted');row.addWidget(self.connection)
        self.connect_button=button('Sign in',self.connect_account);row.addWidget(self.connect_button);row.addWidget(button('Settings',self.open_settings,'Quiet'));layout.addLayout(row)
        self.notice=label('Sign in to start chatting.','Notice');self.notice.setAccessibleName('Website connection status');layout.addWidget(self.notice)
        self.transcript=InlineBrowser();self.transcript.bind_state(self.request);self.transcript.setMaximumWidth(850);self.transcript.setAccessibleName('Website conversation');self.transcript.document().setDefaultStyleSheet('h3 { margin-top:28px; margin-bottom:12px; font-size:14px; } p { margin-bottom:18px; line-height:150%; }');self.transcript.anchorClicked.connect(self.open_transcript_link)
        self.chat_tabs=QTabWidget();reading_widget=QWidget();reading_widget.setObjectName('ReadingFrame');reading=QHBoxLayout(reading_widget);reading.addStretch();reading.addWidget(self.transcript,1);reading.addStretch();self.chat_tabs.addTab(reading_widget,'Conversation');layout.addWidget(self.chat_tabs,1)
        visual_panel=QWidget();visual_layout=QVBoxLayout(visual_panel);visual_layout.addWidget(button('Import visual…',self.import_artifact,'Quiet'));visual_split=QSplitter();self.artifact_list=QListWidget();self.artifact_list.setMaximumWidth(220);self.artifact_list.setAccessibleName('Chat artifacts');self.artifact_list.itemClicked.connect(self.select_artifact);visual_split.addWidget(self.artifact_list);self.artifact_view=ArtifactView(self.artifact_request);visual_split.addWidget(self.artifact_view);visual_split.setStretchFactor(1,1);visual_layout.addWidget(visual_split);self.chat_tabs.addTab(visual_panel,'Artifacts');self.chat_tabs.setTabVisible(1,False);self.chat_tabs.tabBar().hide();self.artifact_signature=None;self.artifact_key=None;self.display_messages=[];self.thinking_expanded=set();self.activity_expanded=set()

        self.remote_id=None;self.history_loading=False
        self.settings_dialog=QDialog(self);self.settings_dialog.setWindowTitle('Chat settings');self.settings_dialog.resize(540,430)
        form=QFormLayout(self.settings_dialog);form.setSpacing(14)
        form.addRow(label('Website account','Heading'));form.addRow(label('Experimental website connection. Website limits apply; commands and local tools are available in Code mode.','Muted'))
        self.browser=QLineEdit();self.browser.setPlaceholderText('Auto-detect Chromium');self.browser.setAccessibleName('Website login browser executable');form.addRow('Browser executable',self.browser);form.addRow(button('Choose browser…',self.choose_browser));self.reconnect_button=button('Reconnect account',self.connect_account);form.addRow(self.reconnect_button)
        self.instructions=QPlainTextEdit();self.instructions.setMaximumHeight(110);self.instructions.setPlaceholderText('Tone, format or useful background');self.instructions.setAccessibleName('Website chat instructions');form.addRow('Chat instructions',self.instructions)
        actions=QHBoxLayout();self.forget_button=button('Forget login',self.forget);actions.addWidget(self.forget_button);actions.addWidget(button('Official website ↗',lambda:QDesktopServices.openUrl(QUrl('https://chat.deepseek.com/'))));form.addRow(actions)
        close=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);close.rejected.connect(self.settings_dialog.reject);form.addRow(close)
        composer=QWidget();composer.setObjectName('ComposerIsland');cl=QVBoxLayout(composer);cl.setContentsMargins(12,8,12,8)
        self.prompt=MessageEdit();self.prompt.submitted.connect(self.send);self.prompt.setObjectName('Prompt');self.prompt.setFixedHeight(68);self.prompt.setPlaceholderText('Message DeepSeek… Enter to send · Shift+Enter for a new line');self.prompt.setAccessibleName('Website chat message');cl.addWidget(self.prompt)
        controls=QHBoxLayout();self.model=QComboBox();self.model.addItem('Flash','deepseek-v4-flash');self.model.addItem('Pro','deepseek-v4-pro');self.model.setAccessibleName('Website chat model');controls.addWidget(self.model)
        self.thinking=QComboBox();self.thinking.addItem('Thinking: Auto','auto');self.thinking.addItem('Thinking: On','on');self.thinking.addItem('Thinking: Off','off');self.thinking.setAccessibleName('Website thinking');self.thinking.setToolTip('Website mode supports thinking on/off. Auto chooses for you.');controls.addWidget(self.thinking)
        self.search=QCheckBox('Search');self.search.setObjectName('WebsiteSearch');self.search.setAccessibleName('Website search');self.search.setToolTip('Web search · Flash only');controls.addWidget(self.search);controls.addStretch()
        self.stop_button=button('Stop',lambda:self.request('web_stop',{},lambda _:self.poll()));controls.addWidget(self.stop_button);self.send_button=button('Send ↑',self.send,'Primary');self.send_button.setEnabled(False);controls.addWidget(self.send_button);cl.addLayout(controls);composer.setMaximumWidth(850);composer_row=QHBoxLayout();composer_row.addStretch();composer_row.addWidget(composer,1);composer_row.addStretch();layout.addLayout(composer_row)
        self.status=label('Website account · no API key','Muted');self.status.setToolTip('Token usage is not measured in website mode. Local tools are disabled. Enter sends; Shift+Enter adds a line.');layout.addWidget(self.status)
        self.model.currentIndexChanged.connect(self.model_changed);self.model.currentIndexChanged.connect(self.draft_changed);self.thinking.currentIndexChanged.connect(self.draft_changed);self.search.toggled.connect(self.draft_changed);self.instructions.textChanged.connect(self.draft_changed);self.prompt.textChanged.connect(self.draft_changed)
        self.draft_timer=QTimer(self);self.draft_timer.setSingleShot(True);self.draft_timer.setInterval(600);self.draft_timer.timeout.connect(self.save_draft)
        if not embedded:QShortcut(QKeySequence('Ctrl+Return'),self,activated=self.send)
        self.timer=QTimer(self);self.timer.setInterval(900);self.timer.timeout.connect(self.poll);self.timer.start();self.poll()
    def artifact_request(self,method,data,callback=None,error=None):
        self.request({'edit_artifact':'web_edit_artifact','artifact':'web_artifact'}.get(method,method),data,callback,error or self.fail)
    def artifact_session(self):return 'remote:'+self.remote_id if self.remote_id else self.sid
    def refresh_artifacts(self):
        key=self.artifact_session()
        if not key:return
        if key!=self.artifact_key:self.artifact_key=key;self.artifact_signature=None;self.artifact_view.clear();self.artifact_list.clear()
        def got(rows):
            if key!=self.artifact_session():return
            signature=[(r['id'],r['revision']) for r in rows]
            if signature==self.artifact_signature:return
            self.artifact_signature=signature;self.artifact_list.clear()
            for r in rows:
                item=QListWidgetItem(r['spec']['title']);item.setData(Qt.ItemDataRole.UserRole,r);self.artifact_list.addItem(item)
            self.transcript.set_artifacts([r['spec'] for r in rows]);self.chat_tabs.setTabText(1,'Artifacts ('+str(len(rows))+')')
            if rows and self.artifact_view.record is None:self.artifact_view.load(rows[0])
        self.request('web_artifacts',{'session':key},got,self.fail)
    def select_artifact(self,item):self.artifact_view.load(item.data(Qt.ItemDataRole.UserRole))
    def import_artifact(self):
        if not self.artifact_session():self.fail('Choose or create a conversation first.');return
        text,ok=QInputDialog.getMultiLineText(self,'Import visual','Paste drawing commands, or a chart/table/diagram JSON specification:')
        if ok:
            try:spec=json.loads(text)
            except ValueError:
                try:
                    from .drawing import parse
                    spec=parse(text)
                except ValueError as exc:self.fail(str(exc));return
            self.request('web_import_artifact',{'session':self.artifact_session(),'spec':spec},lambda _:self.refresh_artifacts(),self.fail)
    @staticmethod
    def wrap_bare_drawing(message):
        if message['role']=='assistant' and message.get('content','').lstrip().startswith('canvas '):return dict(message,content='```deepseek-draw\n'+message['content']+'\n```')
        return message
    def load_visual_state(self):
        key=self.artifact_session()
        if not key:return
        context='web:'+key;self.transcript.set_context(context)
        self.request('visual_states',{'context':context},lambda states:self.transcript.set_context(context,states) if self.artifact_session()==key else None,self.fail)
    def render_messages(self,messages):
        self.display_messages=messages;self.transcript.setMarkdown(transcript.render([self.wrap_bare_drawing(m) for m in messages],self.thinking_expanded,self.activity_expanded,visuals=False) or '## A fresh conversation\n\nSend a message to start.');self.transcript.polish_transcript()
    def open_transcript_link(self,url):
        if url.scheme() in ('app-thinking','app-activity'):
            try:index=int(url.path())
            except ValueError:return
            values=self.thinking_expanded if url.scheme()=='app-thinking' else self.activity_expanded
            if index in values:values.remove(index)
            else:values.add(index)
            position=self.transcript.verticalScrollBar().value();self.render_messages(self.display_messages);self.transcript.verticalScrollBar().setValue(position)
        elif url.scheme()=='app-artifacts':self.chat_tabs.setCurrentIndex(0);self.refresh_artifacts();self.transcript.scroll_to_visual()
        elif url.scheme() in ('https','http'):QDesktopServices.openUrl(url)
    def toggle_history(self):
        self.history_panel.setVisible(not self.history_panel.isVisible());motion.reveal(self.history_panel)
    def open_settings(self):
        self.settings_dialog.show();self.settings_dialog.raise_();self.settings_dialog.activateWindow();motion.reveal(self.settings_dialog)
    def set_notice(self,text):
        self.notice.setText(text);self.notice.setVisible(bool(text))
    def choose_browser(self):
        path,_=QFileDialog.getOpenFileName(self,'Choose Chrome or Chromium executable','/usr/bin')
        if path:self.browser.setText(path)
    def model_changed(self):
        supported=self.model.currentData()=='deepseek-v4-flash'
        if not supported:self.search.setChecked(False)
        self.search.setEnabled(supported and not self.state.get('active'))
    def fail(self,message):self.set_notice(message);self.polling=False
    def connect_account(self):
        self.set_notice('Finish signing in in the browser window.')
        self.request('web_connect',{'browser':self.browser.text().strip()},lambda _:self.poll(),self.fail)
    def forget(self):
        if QMessageBox.question(self,'Forget website login?','Remove this app’s saved website session and dedicated browser profile? Saved chat text stays here. Existing chats cannot be continued through the removed session.')!=QMessageBox.StandardButton.Yes:return
        self.request('web_forget',{},lambda _:self.poll(),self.fail)
    def new_chat(self):
        if getattr(self,'creating',False):return
        self.creating=True;self.save_draft()
        def created(s):self.creating=False;self.load(s['id'])
        def failed(e):self.creating=False;self.loading=False;self.fail(e)
        self.request('web_new',{},created,failed)
    def open_original_chat(self):
        if self.remote_id:QDesktopServices.openUrl(QUrl('https://chat.deepseek.com/a/chat/s/'+self.remote_id))
    def select(self,item):
        self.save_draft()
        remote=item.data(Qt.ItemDataRole.UserRole+1)
        if not remote:self.load(item.data(Qt.ItemDataRole.UserRole));return
        self.prompt.blockSignals(True);self.prompt.clear();self.prompt.blockSignals(False);self.sid=None;self.thinking_expanded=set();self.activity_expanded=set();self.remote_id=remote;self.load_visual_state();self.title.setText(item.text());self.history_loading=True;self.prompt.setEnabled(False);self.send_button.setEnabled(False);self.open_original.show();self.transcript.setPlainText('Loading website conversation…')
        def got(result):
            if self.remote_id!=remote:return
            self.history_loading=False;self.render_messages(result['messages']);self.refresh_artifacts();self.status.setText(result['notice']);self.set_notice('Imported history · read-only. Use Open original on website to continue this conversation.');motion.reveal(self.transcript)
        def failed(error):
            if self.remote_id==remote:self.history_loading=False;self.transcript.setPlainText('Could not load this conversation. Refresh website history and select it again.');self.fail(error)
        self.request('web_history_read',{'id':remote},got,failed)
    def load(self,sid):
        self.draft_timer.stop();self.remote_id=None;self.thinking_expanded=set();self.activity_expanded=set();self.open_original.hide();self.sid=sid;self.load_visual_state();self.loading=True;self.prompt.setEnabled(False);self.signature=None;self.rendered_options=None
        self.request('web_session',{'id':sid},lambda s:self.receive(s,True) if self.sid==sid else None,self.fail)
    def draft_changed(self,*_):
        if not self.loading:self.dirty=True;self.draft_timer.start()
    def save_draft(self):
        self.transcript.flush_visual_state()
        if self.sid and self.dirty and not self.loading:
            self.dirty=False;self.request('web_draft',{'id':self.sid,'text':self.prompt.toPlainText(),'options':dict(model=self.model.currentData(),thinking=self.thinking.currentData(),search=self.search.isChecked()),'instructions':self.instructions.toPlainText()},None,self.fail)
    def poll(self):
        if self.polling:return
        self.polling=True;self.request('web_state',{},self.receive_state,self.fail)
    def receive_state(self,state):
        self.polling=False;self.state=state
        if not self.browser_loaded:
            if not self.browser.text():self.browser.setText(state.get('browser',''))
            self.browser_loaded=True
        connection=state['connection'];self.connection.setText({'connected':'Website account','connecting':'Waiting for browser sign-in…','disconnected':'Not connected'}.get(connection,connection))
        busy=bool(state['active']) or bool(state.get('history_syncing'));connecting=bool(state.get('login_active'));self.sync_button.setEnabled(connection=='connected' and not busy and not connecting)
        self.connect_button.setEnabled(not busy and not connecting);self.connect_button.setVisible(connection!='connected');self.reconnect_button.setEnabled(not busy and not connecting);self.forget_button.setEnabled(not busy and not connecting);self.stop_button.setEnabled(busy or connecting);self.stop_button.setVisible(busy or connecting)
        self.model.setEnabled(not busy);self.thinking.setEnabled(not busy);self.instructions.setEnabled(not busy);self.model_changed()
        self.send_button.setEnabled(connection=='connected' and not busy and bool(self.sid) and not self.loading and self.chat_status not in ('failed','interrupted','cancelled'))
        if state['error']:self.set_notice(state['error'])
        elif connection=='connecting':self.set_notice('Finish signing in in the browser window. You can stop this attempt below.')
        elif state.get('history_error'):self.set_notice(state['history_error'])
        elif self.remote_id:self.set_notice('Imported history · read-only. Continue the original on the website.')
        elif connection=='connected':self.set_notice('')
        signature=json.dumps([state['sessions'],state.get('remote_sessions',[])])
        if signature!=self.sessions_signature:
            self.sessions_signature=signature;self.history.clear()
            for s in state['sessions']:
                item=QListWidgetItem(s['title']);item.setData(Qt.ItemDataRole.UserRole,s['id']);self.history.addItem(item)
                if self.sid==s['id']:self.history.setCurrentItem(item)
            local_ids={s.get('conversation') for s in state['sessions']}
            for row in state.get('remote_sessions',[]):
                item=QListWidgetItem('☁  '+row['title']);item.setData(Qt.ItemDataRole.UserRole+1,row['id']);self.history.addItem(item)
                if self.remote_id==row['id']:self.history.setCurrentItem(item)
            self.sync_button.setToolTip('Latest 100 website conversations. Open original website for older chats.' if state.get('history_limited') else 'Refresh conversations from your signed-in website account')
        self.refresh_artifacts()
        if self.sid:
            sid=self.sid;self.request('web_session',{'id':sid},lambda s:self.receive(s) if self.sid==sid else None,self.fail)
        elif state['sessions'] and not self.remote_id:self.load(state['sessions'][0]['id'])
        elif not self.remote_id and not self.loading:
            self.loading=True;self.new_chat()
    def receive(self,s,initial=False):
        self.chat_status=s['status'];self.title.setText(s['title'])
        if initial:
            self.prompt.setEnabled(True)
            self.prompt.blockSignals(True);self.prompt.setPlainText(s.get('draft',''));self.prompt.blockSignals(False);self.dirty=False
            options=s['options'];self.model.setCurrentIndex(self.model.findData(options['model']));self.thinking.setCurrentIndex(self.thinking.findData(options['thinking']));self.search.setChecked(options['search']);self.instructions.setPlainText(s.get('instructions',''));self.model_changed();self.loading=False
        signature=json.dumps(s['messages'])
        if signature!=self.signature:
            new_turn=len(s['messages'])!=getattr(self,'_message_count',0);self._message_count=len(s['messages']);self.signature=signature;lines=[]
            bar=self.transcript.verticalScrollBar();position=bar.value();follow=initial or bar.maximum()-position<60;before=self.transcript.visual_keys
            self.render_messages(s['messages'])
            self.transcript.polish_transcript()
            if follow and self.transcript.visual_keys-before:QTimer.singleShot(0,self.transcript.scroll_to_visual)
            elif follow:bar.setValue(bar.maximum())
            else:bar.setValue(position)
            if new_turn:motion.reveal(self.transcript)
        duration=(s.get('finished') or time.time())-s.get('started',time.time())
        self.status.setText(f"{s['status'].replace('_',' ').capitalize()} · {max(0,duration):.1f}s · usage unknown" if s['messages'] else 'Website account · no API key')
        if s.get('error'):self.set_notice(s['error'])
        self.send_button.setEnabled(self.state.get('connection')=='connected' and not self.state.get('active') and s['status'] not in ('failed','interrupted','cancelled','running'))
    def send(self):
        text=self.prompt.toPlainText().strip()
        if not text or not self.send_button.isEnabled():return
        sid=self.sid;original=self.prompt.toPlainText();self.send_button.setEnabled(False);self.draft_timer.stop()
        def sent(s):
            if self.sid==sid:
                if self.prompt.toPlainText()==original:self.prompt.blockSignals(True);self.prompt.clear();self.prompt.blockSignals(False);self.dirty=False
                else:self.dirty=True;self.draft_timer.start()
                self.receive(s)
            self.poll()
        self.request('web_send',dict(id=sid,text=text,model=self.model.currentData(),thinking=self.thinking.currentData(),search=self.search.isChecked(),instructions=self.instructions.toPlainText()),sent,self.fail)
