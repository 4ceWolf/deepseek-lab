"""Native Qt workspace. The window owns no model requests or shell processes."""
import hashlib,json,os,sys,time
from html import escape
from pathlib import Path
from PySide6.QtCore import Qt,QObject,Signal,QRunnable,QThreadPool,QTimer,QByteArray,QUrl
from PySide6.QtGui import QAction,QFont,QKeySequence,QShortcut,QTextCursor,QDesktopServices,QTextDocument
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QListWidgetItem,QTextBrowser,QPlainTextEdit,QLineEdit,QComboBox,QSpinBox,QCheckBox,QTabWidget,QSplitter,QDockWidget,QFileDialog,QDialog,QFormLayout,QDialogButtonBox,QInputDialog,QMessageBox,QScrollArea,QGroupBox,QStackedWidget,QMenu)
from . import client,motion,transcript
from .composer import MessageEdit
from .artifact_view import ArtifactView
from .image_view import ImageDialog,decode
from .review_panel import ReviewPanel,budget_dialog

OFFICIAL_CHAT_URL='https://chat.deepseek.com/'

class Signals(QObject):done=Signal(object);failed=Signal(str)
class SafeBrowser(QTextBrowser):
    """Untrusted Markdown never fetches embedded local or remote resources."""
    def __init__(self,*args):
        super().__init__(*args);self.setOpenExternalLinks(False);self.setOpenLinks(False);self.images={}
    def polish_transcript(self):
        block=self.document().begin()
        while block.isValid():
            cursor=QTextCursor(block);fmt=block.blockFormat();heading=fmt.headingLevel()
            fmt.setTopMargin(28 if heading else 5);fmt.setBottomMargin(12 if heading else 10);fmt.setLineHeight(145,1);cursor.setBlockFormat(fmt)
            block=block.next()
    def loadResource(self,kind,url):
        if kind==QTextDocument.ResourceType.ImageResource:return self.images.get(url.toString(),QByteArray())
        return QByteArray()
class Request(QRunnable):
    def __init__(self,method,data):super().__init__();self.method=method;self.data=data;self.signals=Signals()
    def run(self):
        try:self.signals.done.emit(client.restart_service() if self.method=='restart_service' else client.call(self.method,self.data))
        except Exception as exc:self.signals.failed.emit(str(exc))

def button(label,callback,kind=None):
    obj=QPushButton(label);obj.clicked.connect(callback)
    if kind:obj.setObjectName(kind)
    return obj
def label(text,kind=None):
    obj=QLabel(text);obj.setWordWrap(True)
    if kind:obj.setObjectName(kind)
    return obj
def text_editor(placeholder='',height=None):
    obj=QPlainTextEdit();obj.setPlaceholderText(placeholder)
    if height:obj.setMaximumHeight(height)
    return obj

class Window(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('DeepSeek Lab');self.resize(1460,960);self.setMinimumSize(860,600)
        self.sid=None;self.state={};self.session={};self.loaded_config=False;self.polling=False;self.jobs=set();self.message_signature=None;self.command_signature=None;self.last_session_ids=None;self.current_command=None;self.document_cache={}
        self.pool=QThreadPool.globalInstance();self.image_cache={};self.image_pending=set();self.image_allowed=set()
        self.build_toolbar();self.build_tasks();self.build_center();self.build_context()
        self.resizeDocks([self.tasks_dock,self.context_dock],[242,380],Qt.Orientation.Horizontal)
        self.api_workspace=self.takeCentralWidget();self.pages=QStackedWidget();self.pages.addWidget(self.api_workspace);self.setCentralWidget(self.pages)
        self.context_dock.hide();self.command_panel.hide();self.menuBar().hide();self.mode.currentIndexChanged.connect(self.switch_mode)
        self.statusBar().hide()
        self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(900)
        self.draft_timer=QTimer(self);self.draft_timer.setSingleShot(True);self.draft_timer.setInterval(600);self.draft_timer.timeout.connect(self.save_draft)
        self.prompt.textChanged.connect(lambda:self.draft_timer.start())
        QShortcut(QKeySequence('Ctrl+Return'),self,activated=self.send)
        QShortcut(QKeySequence('Ctrl+N'),self,activated=self.new_task)
        self.poll()
    def request(self,method,data=None,callback=None,error=None):
        job=Request(method,data or {});self.jobs.add(job)
        def finish(result):
            self.jobs.discard(job)
            if callback:callback(result)
        def fail(message):
            self.jobs.discard(job);self.polling=False
            if error:error(message)
            else:self.notice.setText(message);self.notice.show()
        job.signals.done.connect(finish);job.signals.failed.connect(fail);self.pool.start(job)
    def build_toolbar(self):
        toolbar=self.addToolBar('Workspace');self.toolbar=toolbar;toolbar.setMovable(False)
        toolbar.addWidget(button('☰',self.toggle_sidebar));toolbar.widgetForAction(toolbar.actions()[-1]).setAccessibleName('Toggle sidebar')
        self.mode=QComboBox();self.mode.addItem('Chat','chat');self.mode.addItem('Code','code');self.mode.setCurrentIndex(1);self.mode.setAccessibleName('Workspace mode');toolbar.addWidget(self.mode)
        self.project=button('Open project…',self.choose_project);toolbar.addWidget(self.project)
        spacer=QWidget();spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding,spacer.sizePolicy().Policy.Preferred);toolbar.addWidget(spacer)
        self.approval_badge=button('Code needs approval',self.show_pending_approval,'Approve');self.approval_badge.hide();self.approval_action=toolbar.addWidget(self.approval_badge);self.approval_action.setVisible(False)
        self.connection=label('Disconnected','Status');toolbar.addWidget(self.connection)
        self.command_toggle=button('▸ Activity · Commands',self.toggle_commands,'Quiet')
        self.workspace_toggle=button('Workspace',self.toggle_workspace);toolbar.addWidget(self.workspace_toggle)
        more=button('•••',lambda:None);more.setAccessibleName('More settings');menu=QMenu(more)
        self.motion_action=QAction('Reduce motion',self);self.motion_action.setCheckable(True);self.motion_action.setChecked(motion.reduced());self.motion_action.toggled.connect(motion.set_reduced);menu.addAction(self.motion_action)
        menu.addAction('Memory',lambda:self.open_context('Memory'));menu.addAction('Documentation',lambda:self.open_context('Docs'));menu.addAction('Learning',lambda:self.open_context('Learning'))
        for title,action in [('API key…',self.key_dialog),('Reload window',self.reload),('Complete task records',self.inspect_records)]:menu.addAction(title,action)
        self.details_action=QAction('Show tool details',self);self.details_action.setCheckable(True);self.details_action.setShortcut(QKeySequence('Ctrl+O'));self.details_action.toggled.connect(self.toggle_tool_details);menu.addAction(self.details_action);self.addAction(self.details_action)
        more.setMenu(menu);toolbar.addWidget(more)
    def toggle_sidebar(self):
        if self.mode.currentData()=='chat' and hasattr(self,'website_chat'):self.website_chat.toggle_history()
        else:self.tasks_dock.setVisible(not self.tasks_dock.isVisible())
    def show_pending_approval(self):
        self.mode.setCurrentIndex(self.mode.findData('code'));self.work_tabs.setCurrentIndex(0);self.command_panel.show();self.thread_scroll.ensureWidgetVisible(self.command_panel)
    def toggle_workspace(self):
        self.context_dock.setVisible(not self.context_dock.isVisible());motion.reveal(self.context_dock)
    def open_context(self,name):
        self.context_dock.show();self.context_tabs.setCurrentIndex(next((i for i in range(self.context_tabs.count()) if self.context_tabs.tabText(i)==name),0));motion.reveal(self.context_dock)
        if name=='Learning':self.learning_view.refresh()
    def switch_mode(self,*_):
        chatting=self.mode.currentData()=='chat'
        if chatting:
            self.save_draft()
            if not hasattr(self,'website_chat'):
                from .webchat_view import WebsiteChat
                self.website_chat=WebsiteChat(self.request,self.pages,embedded=True);self.website_chat.sidebar_button.hide();self.pages.addWidget(self.website_chat)
            self.pages.setCurrentWidget(self.website_chat);self.tasks_dock.hide();self.context_dock.hide();self.website_chat.poll()
        else:
            self.pages.setCurrentWidget(self.api_workspace);self.tasks_dock.show()
            if hasattr(self,'website_chat'):self.website_chat.save_draft();self.website_chat.settings_dialog.hide()
        for action in self.toolbar.actions():
            if self.toolbar.widgetForAction(action) in (self.project,self.connection,self.command_toggle,self.workspace_toggle):action.setVisible(not chatting)
        self.approval_action.setVisible(chatting and bool(getattr(self,'pending_approvals',False)));self.details_action.setVisible(not chatting);self.statusBar().hide();motion.reveal(self.pages.currentWidget())
    def build_tasks(self):
        self.tasks_dock=QDockWidget('TASKS',self);self.tasks_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea|Qt.DockWidgetArea.RightDockWidgetArea);self.tasks_dock.setTitleBarWidget(QWidget());self.tasks_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        container=QWidget();container.setObjectName('TaskIsland');layout=QVBoxLayout(container);layout.setContentsMargins(12,12,12,16)
        layout.addWidget(label('d /   deepseek lab','Brand'));layout.addSpacing(16);layout.addWidget(button('＋ New conversation',self.new_task));layout.addSpacing(12);layout.addWidget(label('PROJECT CONVERSATIONS','Eyebrow'))
        self.task_list=QListWidget();self.task_list.setWordWrap(True);self.task_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.task_list.setAccessibleName('Saved tasks');self.task_list.itemClicked.connect(self.select_task);layout.addWidget(self.task_list)
        for title,tab in [('Memory','Memory'),('Documentation','Docs'),('Learning','Learning'),('ECU & settings','ECU')]:layout.addWidget(button(title,lambda checked=False,t=tab:self.open_context(t),'Quiet'))
        layout.addSpacing(10);layout.addWidget(label('Personal workspace · saved locally','Muted'))
        self.tasks_dock.setWidget(container);self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,self.tasks_dock);self.tasks_dock.setMinimumWidth(190)
    def build_center(self):
        container=QWidget();container.setObjectName('MainIsland');layout=QVBoxLayout(container);layout.setContentsMargins(24,20,24,20);layout.setSpacing(12)
        header=QHBoxLayout();self.heading=label('New conversation','ConversationTitle');header.addWidget(self.heading,1)
        self.run_status=label('API workspace · commands require approval','Muted');header.addWidget(self.run_status);layout.addLayout(header)
        self.notice=label('','Notice');self.notice.hide();layout.addWidget(self.notice)
        
        from .inline_visuals import InlineBrowser
        self.work_tabs=QTabWidget();self.chat=InlineBrowser();self.chat.bind_state(self.request);self.chat.setAccessibleName('Conversation and tool activity');self.chat.document().setDefaultStyleSheet('h3 { margin-top:22px; margin-bottom:8px; } p { margin-top:8px; margin-bottom:14px; } pre { background-color:#10141a; padding:12px; } a { color:#accbfa; }');reading=QWidget();reading.setObjectName('ReadingFrame');reading_layout=QHBoxLayout(reading);reading_layout.setContentsMargins(0,8,0,8);reading_layout.addStretch()
        self.thread_content=QWidget();self.thread_content.setMaximumWidth(850);thread_layout=QVBoxLayout(self.thread_content);thread_layout.setContentsMargins(0,0,0,0);thread_layout.setSpacing(10);thread_layout.addWidget(self.chat);thread_layout.addWidget(self.command_toggle);reading_layout.addWidget(self.thread_content,1);reading_layout.addStretch()
        self.thread_scroll=QScrollArea();self.thread_scroll.setWidgetResizable(True);self.thread_scroll.setWidget(reading);self.work_tabs.addTab(self.thread_scroll,'Conversation');self.chat.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded);self.chat.document().documentLayout().documentSizeChanged.connect(lambda size:self.chat.setFixedHeight(min(30000,max(160,int(size.height())+50))))
        self.chat.setMarkdown('## What are we working on?\n\nChoose a project and tell DeepSeek what you want to build, fix or explore.');self.chat.polish_transcript()

        visuals=QSplitter();self.artifact_list=QListWidget();self.artifact_list.setAccessibleName('Task artifacts');self.artifact_list.setMaximumWidth(210);self.artifact_list.itemClicked.connect(self.select_artifact);visuals.addWidget(self.artifact_list);self.artifact_view=ArtifactView(self.request);visuals.addWidget(self.artifact_view);visuals.setStretchFactor(1,1);self.work_tabs.addTab(visuals,'Artifacts');self.work_tabs.setTabVisible(1,False);self.artifact_signature=None;self.inline_records={}
        self.review=ReviewPanel(self);self.work_tabs.addTab(self.review,'Review');self.work_tabs.currentChanged.connect(lambda index:self.review.refresh() if index==2 else None)
        command_panel=QWidget();self.command_panel=command_panel;self.inline_commands=command_panel;command_content=command_panel;command_content.setObjectName('InlineCommands');command_layout=QVBoxLayout(command_content);command_layout.setContentsMargins(12,12,12,12)
        command_header=QHBoxLayout();self.command_time=label('No command selected','Muted');command_header.addWidget(self.command_time);command_header.addStretch();command_layout.addLayout(command_header)
        commands_split=QSplitter();commands_split.setMinimumHeight(210);self.command_list=QListWidget();self.command_list.setWordWrap(True);self.command_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.command_list.setAccessibleName('Commands and approvals');self.command_list.itemClicked.connect(self.select_command);commands_split.addWidget(self.command_list)
        console_wrap=QWidget();console_layout=QVBoxLayout(console_wrap);console_layout.setContentsMargins(3,0,0,0)
        self.command_details=label('Exact command, working directory and approval will appear here.','Muted');console_layout.addWidget(self.command_details)
        self.console=text_editor();self.console.setMinimumHeight(70);self.console.setMaximumHeight(110);self.console.setObjectName('Console');self.console.setReadOnly(True);self.console.setAccessibleName('Command input and output');console_layout.addWidget(self.console)
        actions=QHBoxLayout();self.approve=button('Approve exact command',lambda:self.decide(True),'Approve');self.deny=button('Deny',lambda:self.decide(False),'Danger');self.stop_command=button('Stop command',self.stop_selected_command)
        for widget in (self.approve,self.deny,self.stop_command):actions.addWidget(widget)
        console_layout.insertLayout(1,actions)
        input_row=QHBoxLayout();self.command_input=QLineEdit();self.command_input.setPlaceholderText('Input for the running command');self.command_input.setAccessibleName('Command input');input_row.addWidget(self.command_input);input_row.addWidget(button('Send input',self.send_input));console_layout.addLayout(input_row)
        commands_split.addWidget(console_wrap);commands_split.setSizes([190,500]);command_layout.addWidget(commands_split)
        manual=QHBoxLayout();self.manual_command=QLineEdit();self.manual_command.setPlaceholderText('Run a command in the selected project…');self.manual_command.setAccessibleName('Host command');manual.addWidget(self.manual_command);manual.addWidget(button('Request command',self.request_command));command_layout.addLayout(manual)
        thread_layout.addWidget(command_panel);thread_layout.addStretch();layout.addWidget(self.work_tabs,1)
        composer=QWidget();composer.setObjectName('ComposerIsland');composer_layout=QVBoxLayout(composer);composer_layout.setContentsMargins(12,10,12,10);composer_layout.setSpacing(8)
        self.prompt=MessageEdit();self.prompt.setPlaceholderText('Message DeepSeek… Enter to send · Shift+Enter for a new line');self.prompt.submitted.connect(self.send);self.prompt.setFixedHeight(72);self.prompt.setAccessibleName('Message to DeepSeek');self.prompt.setObjectName('Prompt');composer_layout.addWidget(self.prompt)
        footer=QHBoxLayout();self.footer_status=label('Reasoning: Auto · saved tasks','Muted');footer.addWidget(self.footer_status);footer.addStretch();self.stop_task=button('Stop task',self.stop_active_task);footer.addWidget(self.stop_task);self.send_button=button('↑',self.send,'Primary');self.send_button.setAccessibleName('Send message');self.send_button.setToolTip('Send · Ctrl+Enter');footer.addWidget(self.send_button);composer_layout.addLayout(footer);composer.setMaximumWidth(850);composer_row=QHBoxLayout();composer_row.addStretch();composer_row.addWidget(composer,1);composer_row.addStretch();layout.addLayout(composer_row)
        footer.insertWidget(1,button('＋ Image',self.add_image,'Quiet'));self.chat.anchorClicked.connect(self.open_transcript_link)
        self.setCentralWidget(container)
    def build_context(self):
        self.context_dock=QDockWidget('WORKSPACE CONTROLS',self);self.context_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea|Qt.DockWidgetArea.RightDockWidgetArea)
        tabs=QTabWidget();self.context_tabs=tabs
        controls=QWidget();controls.setObjectName('ControlIsland');form=QFormLayout(controls);form.setSpacing(9);form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows);form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow);form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        self.permission=QComboBox()
        for text,value in [('Approve every command','approve'),('Ask when needed','ask'),('Full access','full'),('Commands disabled','disabled')]:self.permission.addItem(text,value)
        form.addRow('Command access',self.permission)
        self.permission.setToolTip('Ask automatically allows only pwd, ls and ls -la; other commands require exact approval.')
        form.addRow(label('Commands run on your laptop. File changes proposed by the model remain reviewable.','Muted'))
        self.model=QComboBox();self.model.addItems(['deepseek-flash','deepseek-v4-pro']);form.addRow('Model',self.model)
        self.effort=QComboBox()
        for text,value in [('Auto','auto'),('Thinking off','none'),('Low','low'),('High','high'),('Max','max')]:self.effort.addItem(text,value)
        form.addRow('Reasoning',self.effort)
        self.cap=QSpinBox();self.cap.setRange(128,131072);self.cap.setSingleStep(128);self.cap.setToolTip('Includes thinking and final output. Higher ceilings permit more generation and larger budget reservations; the saved default is unchanged.');form.addRow('Output ceiling',self.cap)
        self.rounds=QSpinBox();self.rounds.setRange(1,20);form.addRow('Tool rounds / turn',self.rounds)
        form.addRow(label('The output ceiling includes reasoning. A round is one model request; total usage can include several rounds.','Muted'))
        form.addRow(button('Budgets, routing & context…',lambda:budget_dialog(self).exec()))
        self.instructions=text_editor('Global operating instructions',150);self.instructions.setAccessibleName('Global operating instructions');form.addRow('Global instructions',self.instructions)
        self.project_instructions=text_editor('Additional project instructions',110);self.project_instructions.setAccessibleName('Project instructions');form.addRow('Project instructions',self.project_instructions)
        form.addRow(button('Save ECU controls',self.save_settings,'Primary'));form.addRow(button('Inspect effective instructions',self.effective_instructions))
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(controls);tabs.addTab(scroll,'ECU')
        files=QWidget();fl=QVBoxLayout(files);fl.addWidget(button('Refresh files',lambda:self.refresh_files(False)));self.files=QListWidget();self.files.setAccessibleName('Project files');self.files.itemClicked.connect(lambda item:self.read_document(item,False));fl.addWidget(self.files)
        self.file_preview=SafeBrowser();self.file_preview.setAccessibleName('Selected project file');fl.addWidget(self.file_preview);fl.addWidget(button('Attach selected text to message',self.attach_file));fl.addWidget(button('Review proposed patches',self.review_proposals));tabs.addTab(files,'Files')
        docs=QWidget();dl=QVBoxLayout(docs);dl.addWidget(button('Open docs directory…',self.choose_docs));self.doc_filter=QLineEdit();self.doc_filter.setPlaceholderText('Filter documentation');self.doc_filter.setAccessibleName('Filter documentation');self.doc_filter.textChanged.connect(self.filter_docs);dl.addWidget(self.doc_filter)
        self.docs=QListWidget();self.docs.setAccessibleName('Documentation directory');self.docs.itemClicked.connect(lambda item:self.read_document(item,True));dl.addWidget(self.docs);self.doc_preview=SafeBrowser();self.doc_preview.setAccessibleName('Document preview');self.doc_preview.anchorClicked.connect(self.open_doc_link);dl.addWidget(self.doc_preview);tabs.addTab(docs,'Docs')
        memory=QWidget();ml=QVBoxLayout(memory);ml.addWidget(label('Memory is retrieved on demand. Saved notes carry dates and remain unverified.','Muted'));self.memory_query=QLineEdit();self.memory_query.setPlaceholderText('Search project and personal memory');self.memory_query.setAccessibleName('Search memory');ml.addWidget(self.memory_query);ml.addWidget(button('Search memory',self.refresh_memory));self.memories=QListWidget();self.memories.setAccessibleName('Saved memories');self.memories.itemClicked.connect(self.show_memory);ml.addWidget(self.memories);self.memory_preview=QTextBrowser();ml.addWidget(self.memory_preview)
        mr=QHBoxLayout();mr.addWidget(button('New',lambda:self.add_memory(False)));mr.addWidget(button('Edit',lambda:self.add_memory(True)));mr.addWidget(button('Delete',self.delete_memory,'Danger'));ml.addLayout(mr);ml.addWidget(button('Version history',self.memory_versions,'Quiet'));tabs.addTab(memory,'Memory')
        dev=QWidget();dv=QVBoxLayout(dev);self.dev_mode=QCheckBox('Allow model to stage app changes');dv.addWidget(self.dev_mode);dv.addWidget(label('Edits go to a separate copy. The active agent service keeps running. Validate and review before activating a stage.','Muted'));dv.addWidget(button('Save Dev mode setting',lambda:self.request('settings',{'dev_mode':self.dev_mode.isChecked()},self.saved_settings)));dv.addWidget(button('Create development stage',lambda:self.request('new_stage',{},lambda _:self.poll())))
        self.stages=QListWidget();self.stages.setAccessibleName('App development stages');self.stages.itemClicked.connect(self.show_stage);dv.addWidget(self.stages)
        self.stage_info=QTextBrowser();dv.addWidget(self.stage_info)
        dv.addWidget(button('Preview staged window',self.preview_stage))
        for title,method in [('Check Python syntax','validate_stage'),('Activate reviewed stage','activate_stage'),('Roll back stage','rollback_stage')]:dv.addWidget(button(title,lambda checked=False,m=method:self.stage_action(m)))
        dv.addWidget(button('Restart idle agent service',self.restart_service))
        tabs.addTab(dev,'Dev');from .learning_view import LearningView
        self.learning_view=LearningView(self.request);tabs.addTab(self.learning_view,'Learning');tabs.currentChanged.connect(lambda index:self.learning_view.refresh() if tabs.tabText(index)=='Learning' else None);self.context_dock.setWidget(tabs);self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.context_dock);self.context_dock.setMinimumWidth(310)
        view=self.menuBar().addMenu('View');view.addAction(self.tasks_dock.toggleViewAction());view.addAction(self.context_dock.toggleViewAction())
        records=QAction('Inspect complete task records',self);records.triggered.connect(self.inspect_records);view.addAction(records)
    def poll(self):
        if self.polling:return
        self.polling=True;self.request('state',{},self.receive_state)
    def receive_state(self,state):
        self.polling=False;self.state=state;config=state['settings'];self.connection.setText('● Connected' if state['connected'] else '○ Key disconnected')
        permission_label={'approve':'Approve commands','ask':'Ask when needed','full':'Full access','disabled':'Commands off'}[config['permission']]
        self.footer_status.setText(config['effort'].capitalize()+' · '+permission_label)
        self.project.setText(Path(config['project']).name+'  ▾');self.project.setToolTip(config['project'])
        sessions=[s for s in state['sessions'] if s['project']==config['project']];signature=[(s['id'],s['title']) for s in sessions]
        if signature!=self.last_session_ids:
            self.task_list.clear()
            for s in sessions:
                item=QListWidgetItem(s['title']);item.setData(Qt.ItemDataRole.UserRole,s['id']);self.task_list.addItem(item)
                if s['id']==self.sid:self.task_list.setCurrentItem(item)
            self.last_session_ids=signature
        if not self.loaded_config:
            self.load_config(config);self.loaded_config=True;self.refresh_files(False);self.refresh_files(True);self.refresh_memory()
            if not state['connected']:self.normal_chat()
        if self.sid is None and sessions:self.load_session(sessions[0]['id'])
        if self.sid:
            requested=self.sid
            self.request('session',{'id':requested},lambda session:self.receive_session(session) if self.sid==requested else None)
        active=[r for r in state['runs'] if r['session']==self.sid];run=active[0] if active else None
        running=run and run['status'] in ('running','waiting_approval','stopping')
        self.send_button.setEnabled(not running);self.stop_task.setEnabled(bool(running));self.stop_task.setVisible(bool(running))
        if not run:self.run_status.setText('API workspace')
        if run:
            usage=run['usage'];duration=(run.get('finished') or time.time())-run['started']
            shown_status='reply finished · verification in Review' if run['status']=='completed' else run['status'].replace('_',' ')
            self.run_status.setText(f"{shown_status} · {duration:.1f}s · {usage.get('total_tokens',0):,} tokens");self.run_status.setToolTip(f"{run['rounds']} rounds · {usage.get('reasoning_tokens',0):,} reasoning tokens · {run['route']['effort']}: {run['route']['reason']}")
            self.statusBar().showMessage(f"{len(run['completed'])} saved steps · {len(run['remaining'])} remaining")
            if run.get('error'):self.notice.setText(run['error']);self.notice.show()
        self.render_commands(state['commands']);self.render_stages(state['stages']);self.render_artifacts(state.get('artifacts',[]));self.refresh_images(state.get('images',[]))
        if self.work_tabs.currentIndex()==2:
            signature=(self.sid,[(r['id'],r['status'],r['rounds'],r['usage'].get('total_tokens')) for r in state['runs'] if r['session']==self.sid],[(c['id'],c['status'],c.get('output_length')) for c in state['commands']],[(p['id'],p['status']) for p in state['proposals']])
            if signature!=getattr(self,'review_signature',None):self.review_signature=signature;self.review.refresh()
    def refresh_images(self,records):
        records=[r for r in records if r['session']==self.sid and r['project']==self.state['settings']['project']][:12]
        self.image_allowed={r['id'] for r in records};removed=set(self.image_cache)-self.image_allowed
        for ident in removed:self.image_cache.pop(ident);self.chat.images.pop('image://'+ident,None)
        if removed:
            self.message_signature=None
            if self.session.get('id')==self.sid:self.receive_session(self.session)
        for record in records:
            ident=record['id'];sid=self.sid
            if record['session']!=sid or record['project']!=self.state['settings']['project'] or ident in self.image_cache or ident in self.image_pending:continue
            self.image_pending.add(ident)
            def loaded(value,ident=ident,sid=sid):
                self.image_pending.discard(ident)
                if self.sid!=sid or ident not in self.image_allowed:return
                self.image_cache[ident]=value;self.message_signature=None
                if self.session.get('id')==sid:self.receive_session(self.session)
            def failed(message,ident=ident):self.image_pending.discard(ident);self.notice.setText(message);self.notice.show()
            self.request('image',{'id':ident},loaded,error=failed)
    def add_image(self):
        if not self.sid:self.notice.setText('Create a task before adding an image.');self.notice.show();return
        project=self.state['settings']['project'];path,_=QFileDialog.getOpenFileName(self,'Add project image',project,'Images (*.png *.jpg *.jpeg *.webp)')
        if path:self.request('publish_image',{'session':self.sid,'path':path,'title':Path(path).name},lambda _:self.poll())
    def open_transcript_link(self,url):
        if url.scheme() in ('app-thinking','app-activity'):
            try:index=int(url.path())
            except ValueError:return
            key='thinking_expanded' if url.scheme()=='app-thinking' else 'activity_expanded';values=getattr(self,key,set())
            if index in values:values.remove(index)
            else:values.add(index)
            setattr(self,key,values);position=self.thread_scroll.verticalScrollBar().value();self.message_signature=None;self.receive_session(self.session);self.thread_scroll.verticalScrollBar().setValue(position);return
        self.open_image(url)
    def open_image(self,url):
        if url.scheme()!='app-image':return
        record=self.image_cache.get(url.path())
        if record:ImageDialog(record,self).exec()
    def render_artifacts(self,records):
        records=[r for r in records if r['session']==self.sid and r['project']==self.state['settings']['project']]
        signature=[(r['id'],r['revision']) for r in records]
        if signature==self.artifact_signature:return
        for meta in records:
            cached=self.inline_records.get(meta['id'])
            if cached and cached['revision']==meta['revision']:continue
            sid=self.sid
            def inline_ready(record,sid=sid):
                if self.sid!=sid:return
                self.inline_records[record['id']]=record;self.message_signature=None
                if self.session.get('id')==sid:self.receive_session(self.session)
            self.request('artifact',{'id':meta['id']},inline_ready)
        selected=self.artifact_view.record;self.artifact_signature=signature;self.artifact_list.clear();self.work_tabs.setTabText(1,f'Artifacts ({len(records)})')
        for record in records:
            item=QListWidgetItem(record['title']+'\n'+record['kind']);item.setData(Qt.ItemDataRole.UserRole,record['id']);self.artifact_list.addItem(item)
            if selected and selected['id']==record['id']:
                self.artifact_list.setCurrentItem(item)
                if selected['revision']!=record['revision']:
                    if self.artifact_view.is_dirty():self.artifact_view.message.setText('A newer revision is available. Your edits are preserved. Select this artifact again to reload, or save to check for a conflict.')
                    else:self.select_artifact(item,preserve_edits=True)
        if not selected and records:self.artifact_list.setCurrentRow(0);self.select_artifact(self.artifact_list.item(0))
    def select_artifact(self,item,preserve_edits=False):
        ident=item.data(Qt.ItemDataRole.UserRole);sid=self.sid
        def loaded(record):
            current=self.artifact_list.currentItem()
            if sid==self.sid and current and current.data(Qt.ItemDataRole.UserRole)==ident:
                if preserve_edits and self.artifact_view.is_dirty():self.artifact_view.message.setText('A newer revision is available. Your edits are preserved; select the artifact again to reload.')
                else:self.artifact_view.load(record)
        self.request('artifact',{'id':ident},loaded)
    def load_config(self,c):
        self.permission.setCurrentIndex(self.permission.findData(c['permission']));self.model.setCurrentText(c['model']);self.effort.setCurrentIndex(self.effort.findData(c['effort']));self.cap.setValue(c['max_tokens']);self.rounds.setValue(c['max_rounds']);self.instructions.setPlainText(c['instructions']);self.project_instructions.setPlainText(c['project_instructions']);self.dev_mode.setChecked(c['dev_mode'])
    def saved_settings(self,c):self.load_config(c);self.notice.setText('Settings saved. Command permissions apply to new requests.');self.notice.show();self.poll()
    def save_settings(self):
        values=dict(permission=self.permission.currentData(),model=self.model.currentText(),effort=self.effort.currentData(),max_tokens=self.cap.value(),max_rounds=self.rounds.value(),instructions=self.instructions.toPlainText(),project_instructions=self.project_instructions.toPlainText())
        if values['permission']=='full' and self.state.get('settings',{}).get('permission')!='full':
            if QMessageBox.question(self,'Full host access','Allow commands to run on this laptop without individual approval?')!=QMessageBox.StandardButton.Yes:return
        self.request('settings',values,self.saved_settings)
    def new_task(self):
        if self.mode.currentData()=='chat' and hasattr(self,'website_chat'):self.website_chat.new_chat();return
        self.save_draft();self.request('new_session',{},lambda s:self.load_session(s['id']))
    def select_task(self,item):self.save_draft();self.load_session(item.data(Qt.ItemDataRole.UserRole))
    def load_session(self,sid):
        self.loading_session=True;self.draft_timer.stop();self.prompt.setEnabled(False);self.inline_records={};self.chat.set_context('api:'+sid)
        self.request('visual_states',{'context':'api:'+sid},lambda states:self.chat.set_context('api:'+sid,states) if self.sid==sid else None)
        self.image_cache.clear();self.chat.images.clear()
        self.current_command=None;self.command_signature=None;self.review.report=None;self.review.view.clear();self.console.clear();self.command_details.setText('Select a command to inspect its receipt.')
        self.sid=sid;self.artifact_signature=None;self.artifact_list.clear();self.artifact_view.clear();self.work_tabs.setTabText(1,'Artifacts');self.message_signature=None;self.notice.hide();self.request('session',{'id':sid},lambda s:self.receive_session(s,True) if s['id']==self.sid else None)
    def receive_session(self,session,load_draft=False):
        self.session=session;self.heading.setText(session['title'])
        if load_draft:
            self.loading_session=False;self.prompt.setEnabled(True)
            self.prompt.blockSignals(True);self.prompt.setPlainText(session.get('draft',''));self.prompt.blockSignals(False)
        scroll=self.thread_scroll.verticalScrollBar();follow=load_draft or scroll.maximum()-scroll.value()<60;scroll_position=scroll.value()
        signature=hashlib.sha256(json.dumps(session['messages']).encode()).hexdigest()
        if signature==self.message_signature:return
        new_turn=len(session['messages'])!=getattr(self,'_message_count',0);self._message_count=len(session['messages']);self.message_signature=signature;lines=[]
        if getattr(self,'disclosure_session',None)!=session['id']:
            self.disclosure_session=session['id'];self.thinking_expanded=set();self.activity_expanded=set()
        before_cards=self.chat.visual_keys
        self.chat.setMarkdown(transcript.render(session['messages'],getattr(self,'thinking_expanded',set()),getattr(self,'activity_expanded',set()),self.details_action.isChecked(),records=self.inline_records) or '## Start with a task\n\nDescribe what you want to build or fix.')
        cursor=QTextCursor(self.chat.document());cursor.movePosition(QTextCursor.MoveOperation.End)
        for record in sorted(self.image_cache.values(),key=lambda r:r['created']):
            cursor.insertBlock()
            ident=record['id'];uri='image://'+ident;title=escape(record['title']);preview='Preview unavailable. Use Open image / Save original below.'
            try:
                image=decode(record).scaled(max(120,min(640,self.chat.viewport().width()-65)),1200,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation);width=image.width();height=image.height();self.chat.images[uri]=image
                self.chat.document().addResource(QTextDocument.ResourceType.ImageResource,QUrl(uri),image);preview=f'<img src="{uri}" width="{width}" height="{height}" alt="{title}">'
            except (ValueError,TypeError):pass
            cursor.insertHtml(f'<h3>{title}</h3><p>{preview}</p><p><a href="app-image:{ident}">Open image / Save original</a> · Local image, not sent to the model</p>')
        block=self.chat.document().begin()
        while block.isValid():
            fmt=block.blockFormat()
            if fmt.headingLevel():fmt.setTopMargin(22);fmt.setBottomMargin(8);QTextCursor(block).setBlockFormat(fmt)
            block=block.next()
        self.chat.polish_transcript();self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())
        if follow and self.chat.visual_keys-before_cards:QTimer.singleShot(0,self.chat.scroll_to_visual)
        else:QTimer.singleShot(0,lambda:scroll.setValue(scroll.maximum() if follow else scroll_position))
        if new_turn:motion.reveal(self.chat)
    def toggle_tool_details(self,*_):
        self.message_signature=None
        if self.session:self.receive_session(self.session)
    def toggle_commands(self):
        self.command_panel.setVisible(not self.command_panel.isVisible());self.command_toggle.setText(('▾' if self.command_panel.isVisible() else '▸')+' Activity · Commands');motion.reveal(self.command_panel)
    def inspect_records(self):
        if not self.sid:return
        def display(session):
            dialog=QDialog(self);dialog.setWindowTitle('Complete saved task and tool results');dialog.resize(900,700);layout=QVBoxLayout(dialog);view=text_editor();view.setReadOnly(True);view.setPlainText(json.dumps(session,indent=2));layout.addWidget(view);layout.addWidget(button('Close',dialog.accept));dialog.exec()
        self.request('session',{'id':self.sid},display)
    def save_draft(self):
        if getattr(self,'loading_session',False):return
        self.chat.flush_visual_state()
        if self.sid:self.request('draft',{'id':self.sid,'text':self.prompt.toPlainText()})
    def send(self):
        if self.mode.currentData()=='chat' and hasattr(self,'website_chat'):self.website_chat.send();return
        if not self.send_button.isEnabled() or not self.prompt.toPlainText().strip():return
        if getattr(self,'loading_session',False):return
        if not self.sid:
            self.send_button.setEnabled(False);self.request('new_session',{},lambda s:self._send_to(s['id']));return
        self._send_to(self.sid)
    def _send_to(self,sid):
        self.sid=sid;text=self.prompt.toPlainText();self.send_button.setEnabled(False)
        def sent(_):
            if self.sid==sid and self.prompt.toPlainText()==text:self.prompt.clear()
            self.notice.hide();self.poll()
        self.request('submit',{'session':sid,'prompt':text},sent)
    def stop_active_task(self):
        for run in self.state.get('runs',[]):
            if run['session']==self.sid and run['status'] in ('running','waiting_approval'):self.request('stop_run',{'id':run['id']})
    def choose_project(self):
        path=QFileDialog.getExistingDirectory(self,'Open project',self.state.get('settings',{}).get('project',str(Path.home())))
        if path:
            def selected(c):self.sid=None;self.last_session_ids=None;self.saved_settings(c);self.refresh_files(False);self.refresh_memory();self.new_task()
            self.request('settings',{'project':path},selected)
    def choose_docs(self):
        path=QFileDialog.getExistingDirectory(self,'Open documentation directory',self.state.get('settings',{}).get('docs',''))
        if path:self.request('settings',{'docs':path},lambda _:self.refresh_files(True))
    def refresh_files(self,docs):
        target=self.docs if docs else self.files
        def filled(names):target.clear();target.addItems(names);self.filter_docs() if docs else None
        self.request('files',{'docs':docs},filled)
    def filter_docs(self):
        for i in range(self.docs.count()):self.docs.item(i).setHidden(self.doc_filter.text().lower() not in self.docs.item(i).text().lower())
    def read_document(self,item,docs):
        def display(doc):
            self.document_cache['docs' if docs else 'file']=doc
            target=self.doc_preview if docs else self.file_preview
            if doc['path'].lower().endswith('.md'):target.setMarkdown(doc['content'])
            else:target.setPlainText(doc['content'])
        self.request('read',{'path':item.text(),'docs':docs},display)
    def open_doc_link(self,url):
        current=self.document_cache.get('docs',{})
        if url.scheme() or not current:return
        path=str(Path(current['path']).parent/url.path())
        def shown(doc):self.document_cache['docs']=doc;self.doc_preview.setMarkdown(doc['content'])
        self.request('read',{'path':path,'docs':True},shown)
    def attach_file(self):
        doc=self.document_cache.get('file')
        if doc:self.prompt.appendPlainText('\nSelected file (reference data): '+doc['path']+'\n```\n'+doc['content']+'\n```')
    def refresh_memory(self):
        def filled(memories):
            self.memories.clear()
            for m in memories:
                item=QListWidgetItem(m['title']+'  · '+m['scope']);item.setData(Qt.ItemDataRole.UserRole,m);self.memories.addItem(item)
        self.request('memories',{'query':self.memory_query.text()},filled)
    def show_memory(self,item):
        m=item.data(Qt.ItemDataRole.UserRole);self.memory_preview.setPlainText(m['body']+'\n\nSource: '+m['source']+' · Unverified\nUpdated: '+time.strftime('%Y-%m-%d %H:%M',time.localtime(m['updated'])))
    def memory_versions(self):
        item=self.memories.currentItem()
        if not item:return
        memory=item.data(Qt.ItemDataRole.UserRole)
        def display(rows):
            dialog=QDialog(self);dialog.setWindowTitle('Memory version history');dialog.resize(600,500);layout=QVBoxLayout(dialog);view=QTextBrowser();view.setPlainText('\n\n'.join('Revision '+str(r.get('revision',1))+' · '+r['source']+'\n'+r['title']+'\n'+r['body'] for r in [memory]+rows));layout.addWidget(view);layout.addWidget(label('To restore a version, copy its text into Edit. The edit keeps this history.','Muted'));dialog.exec()
        self.request('memory_versions',{'id':memory['id']},display)
    def add_memory(self,edit=False):
        dialog=QDialog(self);dialog.setWindowTitle('Save memory');dialog.resize(480,400);form=QFormLayout(dialog)
        title=QLineEdit();body=text_editor();scope=QComboBox();scope.addItems(['project','personal']);old=self.memories.currentItem() if edit else None;old=old.data(Qt.ItemDataRole.UserRole) if old else None
        if old:title.setText(old['title']);body.setPlainText(old['body']);scope.setCurrentText(old['scope']);scope.setEnabled(False)
        form.addRow('Title',title);form.addRow('Scope',scope);form.addRow('Memory',body);buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec():
            if old:self.request('edit_memory',{'id':old['id'],'revision':old.get('revision',1),'title':title.text(),'body':body.toPlainText()},lambda _:self.refresh_memory())
            else:self.request('remember',{'title':title.text(),'body':body.toPlainText(),'scope':scope.currentText()},lambda _:self.refresh_memory())
    def delete_memory(self):
        item=self.memories.currentItem()
        if item and QMessageBox.question(self,'Delete memory','Delete this saved memory?')==QMessageBox.StandardButton.Yes:self.request('delete_memory',{'id':item.data(Qt.ItemDataRole.UserRole)['id']},lambda _:self.refresh_memory())
    def render_commands(self,commands):
        run_ids={r['id'] for r in self.state.get('runs',[]) if r['session']==self.sid};commands=[c for c in commands if c.get('task') is None or c.get('task') in run_ids]
        waiting=[c for c in commands if c['status']=='awaiting_approval'];self.pending_approvals=bool(waiting);self.approval_action.setVisible(self.mode.currentData()=='chat' and bool(waiting))
        fresh=set(c['id'] for c in waiting)-getattr(self,'shown_approvals',set())
        if fresh:
            self.command_panel.show();self.command_toggle.setText('▾ Activity · Approval needed');self.thread_scroll.ensureWidgetVisible(self.command_panel);self.shown_approvals=getattr(self,'shown_approvals',set())|fresh
        self.command_toggle.setVisible(bool(commands));self.command_toggle.setToolTip(f'{len(waiting)} awaiting approval · {len(commands)} command records')
        signature=[(c['id'],c['status']) for c in commands]
        if signature!=self.command_signature:
            self.command_list.clear()
            for c in commands:
                item=QListWidgetItem(c['status'].replace('_',' ')+'\n'+c['command'][:80]);item.setData(Qt.ItemDataRole.UserRole,c['id']);self.command_list.addItem(item)
                if c['id']==self.current_command:self.command_list.setCurrentItem(item)
            self.command_signature=signature
        if not self.current_command and commands:self.current_command=commands[0]['id']
        selected=next((c for c in commands if c['id']==self.current_command),None)
        if selected and selected.get('output_truncated'):
            cache=getattr(self,'command_cache',{})
            key=(selected['id'],selected['status'],selected.get('output_length'),len(selected['inputs']))
            if key in cache:selected=cache[key]
            else:
                def fetched(record):
                    self.command_cache={key:record}
                    if self.current_command==record['id']:self.render_commands(self.state.get('commands',[]))
                self.request('command_record',{'id':selected['id']},fetched)
        if selected:
            self.command_record=selected
            metadata=selected['cwd']+' · '+selected['environment']+' · '+selected['mode']
            if selected.get('process_id'):metadata+=' · PID '+str(selected['process_id'])
            detail=selected.get('error') or selected.get('note') or ''
            self.command_details.setText('$ '+selected['command']+'\n'+metadata+('\n'+detail if detail else ''))
            self.console.setPlainText(selected['output']+'\n'+''.join('\n[input] '+i['text'] for i in selected['inputs']))
            elapsed=(selected.get('finished') or time.time())-(selected.get('started') or selected['created'])
            self.command_time.setText(f"{selected['status'].replace('_',' ')} · {elapsed:.1f}s · exit {selected['exit_code'] if selected['exit_code'] is not None else '—'}")
            pending=selected['status']=='awaiting_approval';self.approve.setEnabled(pending);self.deny.setEnabled(pending);self.stop_command.setEnabled(selected['status']=='running')
        else:
            self.approve.setEnabled(False);self.deny.setEnabled(False);self.stop_command.setEnabled(False)
    def select_command(self,item):self.current_command=item.data(Qt.ItemDataRole.UserRole);self.render_commands(self.state.get('commands',[]))
    def decide(self,approved):
        c=getattr(self,'command_record',None)
        if c:self.request('decide_command',{'id':c['id'],'approved':approved,'fingerprint':c['fingerprint']},lambda _:self.poll())
    def stop_selected_command(self):
        if self.current_command:self.request('stop_command',{'id':self.current_command})
    def send_input(self):
        if self.current_command and self.command_input.text():self.request('command_input',{'id':self.current_command,'text':self.command_input.text()+'\n'});self.command_input.clear()
    def request_command(self):
        if self.manual_command.text().strip():self.request('command',{'command':self.manual_command.text(),'cwd':'.','timeout':120},lambda c:self.command_created(c))
    def command_created(self,c):self.current_command=c['id'];self.manual_command.clear();self.poll()
    def review_proposals(self):
        proposals=self.state.get('proposals',[])
        if not proposals:self.notice.setText('No proposed patches yet. Ask DeepSeek to inspect a file and propose a change.');self.notice.show();return
        names=[p['path']+' · '+p['status']+' · '+p['id'][:8] for p in proposals];name,ok=QInputDialog.getItem(self,'Review patch','Proposal',names,0,False)
        if not ok:return
        proposal=proposals[names.index(name)];dialog=QDialog(self);dialog.setWindowTitle('Review '+proposal['path']);dialog.resize(850,650);layout=QVBoxLayout(dialog);preview=text_editor();preview.setReadOnly(True);preview.setPlainText(proposal['diff']);layout.addWidget(preview);layout.addWidget(label('Apply only if the source still matches the version inspected.','Muted'))
        apply=button('Apply reviewed patch',lambda:self.apply_patch(proposal['id'],dialog),'Primary');apply.setEnabled(proposal['status']=='proposed');layout.addWidget(apply)
        rollback=button('Roll back this patch',lambda:self.request('rollback_proposal',{'id':proposal['id']},lambda _:(dialog.accept(),self.refresh_files(False),self.poll())));rollback.setEnabled(proposal['status']=='applied');layout.addWidget(rollback);layout.addWidget(button('Close',dialog.reject));dialog.exec()
    def apply_patch(self,ident,dialog):self.request('apply_proposal',{'id':ident},lambda _:(dialog.accept(),self.refresh_files(False),self.poll()))
    def render_stages(self,stages):
        old=self.stages.currentItem();ident=old.data(Qt.ItemDataRole.UserRole)['id'] if old else None
        signature=[(s['id'],s['status'],s['changed']) for s in stages]
        if getattr(self,'stage_signature',None)==signature:return
        self.stage_signature=signature;self.stages.clear()
        for stage in stages:
            item=QListWidgetItem(stage['id'][:8]+' · '+stage['status']);item.setData(Qt.ItemDataRole.UserRole,stage);self.stages.addItem(item)
            if stage['id']==ident:self.stages.setCurrentItem(item)
    def show_stage(self,item):
        stage=item.data(Qt.ItemDataRole.UserRole)
        self.request('stage_diff',{'id':stage['id']},lambda result:self.stage_info.setPlainText('Status: '+stage['status']+'\nWorking copy: '+stage['folder']+'\n\n'+result['diff']+'\n'+'\n'.join(stage.get('errors',[]))))
    def preview_stage(self):
        item=self.stages.currentItem()
        if not item:return
        stage=item.data(Qt.ItemDataRole.UserRole)
        def checked(result):
            if result['status']!='syntax_checked':self.notice.setText('Staged Python has syntax errors. Fix them before preview.');self.notice.show();return
            import subprocess
            env=dict(os.environ,DEEPSEEK_DESKTOP_DATA=str(client.directory()),DEEPSEEK_DESKTOP_SOURCE=str(client.SERVICE_ROOT))
            subprocess.Popen([sys.executable,'-m','desktop.app'],cwd=stage['folder'],env=env,start_new_session=True)
        self.request('validate_stage',{'id':stage['id']},checked)
    def restart_service(self):
        if QMessageBox.question(self,'Restart idle service','Load activated backend changes? Active or pending tasks and commands must finish first. The saved key and task history will be reloaded.')!=QMessageBox.StandardButton.Yes:return
        self.request('restart_service',{},lambda state:(self.notice.hide(),self.receive_state(state)))
    def stage_action(self,method):
        item=self.stages.currentItem()
        if not item:return
        stage=item.data(Qt.ItemDataRole.UserRole)
        if method in ('activate_stage','rollback_stage') and QMessageBox.question(self,'Switch app source','Apply this staged source change? The current service stays running; backend changes need an idle restart.')!=QMessageBox.StandardButton.Yes:return
        self.request(method,{'id':stage['id']},lambda result:(self.notice.setText(result.get('note',result.get('status','Saved'))),self.notice.show(),self.poll()))
    def effective_instructions(self):
        def display(result):
            dialog=QDialog(self);dialog.setWindowTitle('Saved effective instructions for the next turn');dialog.resize(800,650);layout=QVBoxLayout(dialog);layout.addWidget(label('Save ECU edits first to change these instructions.','Muted'));view=text_editor();view.setReadOnly(True);view.setPlainText(result['text']);layout.addWidget(view);layout.addWidget(button('Close',dialog.accept));dialog.exec()
        self.request('instructions',{},display)
    def key_dialog(self):
        dialog=QDialog(self);dialog.setWindowTitle('DeepSeek connection');dialog.resize(490,250);form=QFormLayout(dialog);form.addRow(label('Saved in the Linux credential store. Keys stay out of chats, source files and exports.','Muted'));key=QLineEdit();key.setEchoMode(QLineEdit.EchoMode.Password);key.setAccessibleName('New DeepSeek API key');form.addRow('API key',key);status=label(self.state.get('key_error',''));form.addRow(status)
        def saved(_):key.clear();dialog.accept();self.poll()
        def failed(message):status.setText(message);save.setEnabled(True)
        def validate():
            status.setText('Validating key and saving to the Linux credential store…');save.setEnabled(False)
            self.request('save_key',{'value':key.text()},saved,failed)
        save=button('Validate and save key',validate,'Primary');form.addRow(save);form.addRow(button('Remove saved key',lambda:self.request('remove_key',{},saved,failed),'Danger'));form.addRow(button('Cancel',dialog.reject));dialog.exec()
    def build_account_chat_dialog(self):
        dialog=QDialog(self);dialog.setWindowTitle('Normal chat · DeepSeek account');dialog.resize(510,350)
        layout=QVBoxLayout(dialog);layout.setSpacing(14)
        layout.addWidget(label('Chat with your DeepSeek account','Heading'))
        layout.addWidget(label('Open the official DeepSeek chat in your default browser and sign in there. Use Google sign-in if DeepSeek offers it for your account. No API key is needed for the official chat website.'))
        layout.addWidget(label('Your browser handles login and keeps the website session. This workspace does not receive Google tokens, passwords or DeepSeek website cookies.','Muted'))
        layout.addWidget(label('The native ECU workspace, local memory tools and laptop commands use the separate API connection. Website conversations stay with DeepSeek.','Muted'))
        status=label('','Muted');status.setAccessibleName('Normal chat launch status');layout.addWidget(status)
        def open_chat():
            opened=QDesktopServices.openUrl(QUrl(OFFICIAL_CHAT_URL))
            status.setText('Official chat opened in your browser. Complete sign-in there.' if opened else 'The browser could not be opened. Visit https://chat.deepseek.com/ manually.')
        dialog.open_chat_button=button('Open official DeepSeek chat ↗',open_chat,'Primary');layout.addWidget(dialog.open_chat_button)
        layout.addWidget(button('Close',dialog.reject));return dialog
    def normal_chat(self):
        self.mode.setCurrentIndex(self.mode.findData('chat'));self.switch_mode()
    def reload(self):
        def launch(_=None):
            import subprocess
            subprocess.Popen([sys.executable,'-m','desktop.app'],cwd=client.ROOT,start_new_session=True)
            self._closing_saved=True;self.close()
        if self.sid:self.request('draft',{'id':self.sid,'text':self.prompt.toPlainText()},launch)
        else:launch()
    def closeEvent(self,event):
        if hasattr(self,'website_chat'):
            self.website_chat.timer.stop();self.website_chat.draft_timer.stop();self.website_chat.save_draft()
        if self.sid and not getattr(self,'_closing_saved',False):
            event.ignore();self.draft_timer.stop()
            def saved(_):self._closing_saved=True;self.close()
            self.request('draft',{'id':self.sid,'text':self.prompt.toPlainText()},saved);return
        self.timer.stop();super().closeEvent(event)
