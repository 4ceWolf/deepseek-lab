"""User review of model-proposed learning; activating is never a model tool."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QListWidget,QListWidgetItem,QTextBrowser,QPushButton

class LearningView(QWidget):
    def __init__(self,request):
        super().__init__();self.request=request;self.selected=None
        layout=QVBoxLayout(self)
        from .ui import label,button
        layout.addWidget(label('Lessons that improve with experience','Heading'))
        layout.addWidget(label('DeepSeek can revise its own memories and propose ECU lessons. Review the lesson and its checks before enabling it. Passing checks do not prove a quality improvement.','Muted'))
        layout.addWidget(button('Refresh lessons',self.refresh))
        self.items=QListWidget();self.items.setAccessibleName('ECU learning proposals');self.items.itemClicked.connect(self.select);layout.addWidget(self.items)
        self.detail=QTextBrowser();self.detail.setOpenExternalLinks(False);self.detail.setAccessibleName('Lesson, rationale and evidence');layout.addWidget(self.detail)
        row=QHBoxLayout();self.enable=button('Activate reviewed lesson',lambda:self.change('active'),'Primary');self.rollback=button('Roll back',lambda:self.change('rolled_back'));self.reject=button('Reject',lambda:self.change('rejected'))
        for b in (self.enable,self.rollback,self.reject):b.setEnabled(False);row.addWidget(b)
        layout.addLayout(row);self.feedback=label('No lesson selected.','Muted');layout.addWidget(self.feedback)
    def refresh(self):
        def got(rows):
            self.items.clear()
            for row in rows:
                item=QListWidgetItem(row['title']+' · '+row['status'].replace('_',' '));item.setData(Qt.ItemDataRole.UserRole,row);self.items.addItem(item)
                if self.selected and self.selected['id']==row['id']:self.items.setCurrentItem(item);self.select(item)
            if not rows:self.detail.setPlainText('No lessons yet. After useful verified work, DeepSeek can propose a reusable lesson here. Nothing is invented just to fill this list.')
        self.request('learning_list',{},got,self.failed)
    def failed(self,error):self.feedback.setText(error)
    def select(self,item):
        r=item.data(Qt.ItemDataRole.UserRole);self.selected=r;self.enable.setEnabled(False);self.rollback.setEnabled(r['status']=='active');self.reject.setEnabled(r['status']=='proposed')
        self.detail.setPlainText(r['title']+'\n\n'+r['lesson']+'\n\nWhy this lesson\n'+r['reason']+'\n\nStatus: '+r['status'])
        def evidence(result):
            if not self.selected or self.selected['id']!=r['id']:return
            self.enable.setEnabled(result['eligible'] and r['status'] in ('proposed','rolled_back'))
            text=self.detail.toPlainText()+'\n\nCheck evidence (not a model quality score):'
            for c in result['checks']:text+='\n'+((c['command']+' — '+c['result']) if c else 'Missing check')
            self.detail.setPlainText(text)
            self.feedback.setText(result['note'])
        self.request('learning_evidence',{'id':r['id']},evidence,self.failed)
    def change(self,status):
        if self.selected:self.request('learning_change',{'id':self.selected['id'],'status':status},lambda _:(self.feedback.setText('Lesson updated. Future API turns use the active lessons.'),self.refresh()),self.failed)
