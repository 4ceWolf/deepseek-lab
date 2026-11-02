"""Review observed evidence before recovery; budgets require explicit configuration."""
import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QPlainTextEdit,QLabel,QDialog,QCheckBox,QFormLayout,QSpinBox,QDoubleSpinBox,QInputDialog,QFileDialog)

class ReviewPanel(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.report=None;self.loading=False;layout=QVBoxLayout(self)
        hint=QLabel('Command evidence and source freshness are separate from the model’s completion claims.');hint.setWordWrap(True);layout.addWidget(hint)
        actions=QHBoxLayout()
        for text,callback in [('Refresh receipt',self.refresh),('Review recovery…',self.recover),('Export receipt…',self.export)]:
            button=QPushButton(text);button.clicked.connect(callback);actions.addWidget(button)
        layout.addLayout(actions);self.view=QPlainTextEdit();self.view.setReadOnly(True);self.view.setAccessibleName('Task verification receipt');layout.addWidget(self.view,1)
        git=QHBoxLayout()
        for text,callback in [('Create coding worktree',self.create_worktree),('Open worktree…',self.open_worktree),('Inspect Git diff',self.git_diff)]:
            button=QPushButton(text);button.clicked.connect(callback);git.addWidget(button)
        layout.addLayout(git);self.status=QLabel('Worktrees start at committed HEAD. Your uncommitted files remain in the original checkout. Git commands use normal approvals.');self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
    def refresh(self):
        sid=self.window.sid
        if not sid:self.view.setPlainText('Select a task to inspect its evidence.');return
        if self.loading:return
        self.loading=True
        def loaded(report):
            self.loading=False
            if sid!=self.window.sid:return
            self.report=report;run=report['run'];lines=['TASK RECEIPT','Model claims are unverified. A completed reply does not establish task correctness.']
            if run:
                account=run.get('accounting',{});lines+=['','Run: '+run['id']+' · '+run['status'],'Model: '+run['config']['model'],'Token accounting (includes carried uncertainty): '+str(account.get('tokens',0)),'Estimated USD (supplied rates): '+(str(account.get('usd',0)) if account.get('priced') else 'unavailable'),'Next-request admission estimate: '+json.dumps(run.get('next_request_estimate')),'Unsettled request reservation: '+json.dumps(run.get('reservation')),'Carried uncertain requests: '+json.dumps(account.get('uncertain_requests',[])),'','Saved completed claims:']+run['completed']+['','Remaining work:']+run['remaining']+['','Requirements:']+run.get('requirements',[])+['','Context: '+json.dumps(run.get('context',{}))]
            lines+=['','CHECKS']
            for check in report['checks']:lines += [check['result']+' · '+check['command'], 'Sources unchanged: '+str(check['sources_unchanged'])+' · exit '+str(check['exit_code']),check['output_tail']]
            if not report['checks']:lines+=['No scoped executable checks recorded.']
            lines+=['','PATCHES']+[str(p['path'])+' · '+str(p['status']) for p in report['patches']]+['','COMMANDS']+[c['status']+' · '+c['command']+' · '+c['id'] for c in report['commands']]+['',report['limits']];self.view.setPlainText('\n'.join(lines))
        def failed(message):self.loading=False;self.status.setText(message)
        self.window.request('task_receipt',{'session':sid},loaded,error=failed)
    def build_recovery_dialog(self,report):
        dialog=QDialog(self);dialog.setWindowTitle('Review saved task before continuing');dialog.resize(820,650);layout=QVBoxLayout(dialog);hint=QLabel(report['note']);hint.setWordWrap(True);layout.addWidget(hint);view=QPlainTextEdit();view.setReadOnly(True);view.setPlainText(json.dumps(report,indent=2));layout.addWidget(view,1)
        dialog.ack=QCheckBox('I reviewed uncertain command/provider state before continuing');dialog.ack.setVisible(bool(report['uncertainties']));layout.addWidget(dialog.ack);dialog.resume=QPushButton('Continue from saved state');dialog.resume.setEnabled(not report['uncertainties']);dialog.ack.toggled.connect(dialog.resume.setEnabled);layout.addWidget(dialog.resume)
        def submit():
            dialog.resume.setEnabled(False)
            def failed(message):hint.setText(message);dialog.resume.setEnabled(not report['uncertainties'] or dialog.ack.isChecked())
            self.window.request('recover_session',{'session':report['session'],'expected_run':report['expected_run'],'acknowledge_uncertain':dialog.ack.isChecked()},lambda _:(dialog.accept(),self.window.poll(),self.refresh()),error=failed)
        dialog.resume.clicked.connect(submit);cancel=QPushButton('Cancel');cancel.clicked.connect(dialog.reject);layout.addWidget(cancel);return dialog
    def recover(self):
        if self.window.sid:self.window.request('recovery_report',{'session':self.window.sid},lambda report:self.build_recovery_dialog(report).exec(),error=self.status.setText)
    def export(self):
        if not self.report:return
        path,_=QFileDialog.getSaveFileName(self,'Export current receipt','task-receipt.json','JSON (*.json)')
        if path:
            try:Path(path).write_text(json.dumps(self.report,indent=2));self.status.setText('Exported the displayed receipt. Refresh before exporting newer evidence.')
            except OSError as exc:self.status.setText(str(exc))
    def create_worktree(self):
        def created(record):self.window.request('command_record',{'id':record['command']},self.window.command_created);self.status.setText(record['note'])
        self.window.request('create_worktree',{},created,error=self.status.setText)
    def open_worktree(self):
        records=self.window.state.get('worktrees',[])
        if not records:self.status.setText('Create a worktree and finish its command first.');return
        choices=[r['path'] for r in records];chosen,ok=QInputDialog.getItem(self,'Open coding worktree','Managed worktree',choices,0,False)
        if ok:
            def opened(config):self.window.sid=None;self.window.last_session_ids=None;self.window.saved_settings(config);self.window.refresh_files(False);self.window.refresh_memory();self.window.new_task()
            self.window.request('open_worktree',{'id':records[choices.index(chosen)]['id']},opened,error=self.status.setText)
    def git_diff(self):self.window.request('command',{'command':'git -c core.hooksPath=/dev/null diff --no-ext-diff --no-textconv','cwd':'.','timeout':120},self.window.command_created,error=self.status.setText)

def budget_dialog(window):
    cfg=window.state['settings'];dialog=QDialog(window);dialog.setWindowTitle('Budgets, routing and context');dialog.resize(570,680);form=QFormLayout(dialog)
    hint=QLabel('Task accounting carries across messages. Saved controls apply to new runs; recovery retains its original budget/prices. Admission estimates are conservative estimates, not a guaranteed provider billing cap. Zero disables a budget.');hint.setWordWrap(True);form.addRow(hint)
    tokens=QSpinBox();tokens.setRange(0,2_000_000);tokens.setSingleStep(1000);tokens.setValue(cfg.get('max_total_tokens',0));form.addRow('Task token budget',tokens)
    usd=QDoubleSpinBox();usd.setRange(0,1000);usd.setDecimals(4);usd.setValue(cfg.get('max_task_usd',0));form.addRow('Task USD estimate cap',usd)
    priced=QCheckBox('Use my supplied USD prices per million tokens');priced.setChecked(bool(cfg.get('pricing')));form.addRow(priced);rates={}
    for model in ('deepseek-flash','deepseek-v4-pro'):
        rates[model]={}
        for kind in ('input','output'):
            field=QDoubleSpinBox();field.setRange(0,1000);field.setDecimals(6);field.setValue(cfg.get('pricing',{}).get(model,{}).get(kind,0));field.setEnabled(priced.isChecked());priced.toggled.connect(field.setEnabled);rates[model][kind]=field;form.addRow(model+' '+kind,field)
    economy=QCheckBox('Use cheaper configured model for low-effort tasks');economy.setChecked(cfg.get('economy_routing',False));form.addRow(economy)
    compact=QCheckBox('Compact older assistant/tool exchanges; keep user messages');compact.setChecked(cfg.get('compact_context',True));form.addRow(compact);context=QSpinBox();context.setRange(20000,160000);context.setSingleStep(10000);context.setValue(cfg.get('context_limit',140000));form.addRow('Context input byte ceiling',context)
    status=QLabel('Rates are not fetched or verified. Use current cache-miss input and output rates; update after provider price changes.');status.setWordWrap(True);form.addRow(status)
    save=QPushButton('Save budget controls')
    def submit():
        values=dict(max_total_tokens=tokens.value(),max_task_usd=usd.value(),pricing={m:{k:f.value() for k,f in fields.items()} for m,fields in rates.items()} if priced.isChecked() else {},economy_routing=economy.isChecked(),compact_context=compact.isChecked(),context_limit=context.value());save.setEnabled(False)
        def failed(message):status.setText(message);save.setEnabled(True)
        window.request('settings',values,lambda config:(window.saved_settings(config),dialog.accept()),error=failed)
    save.clicked.connect(submit);form.addRow(save);cancel=QPushButton('Cancel');cancel.clicked.connect(dialog.reject);form.addRow(cancel);dialog.controls=dict(tokens=tokens,usd=usd,priced=priced,rates=rates,economy=economy,compact=compact,context=context,save=save);return dialog
