"""Native structured visuals with inspectable data and explicit file exports."""
import json
from pathlib import Path
from PySide6.QtCore import QByteArray,Qt
from PySide6.QtGui import QImage,QPainter,QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QTabWidget,QScrollArea,QTableWidget,QTableWidgetItem,QPlainTextEdit,QFileDialog,QAbstractItemView,QFormLayout,QCheckBox,QColorDialog)
from . import artifacts,artifact_html

class ArtifactView(QWidget):
    def __init__(self,request,parent=None):
        super().__init__(parent);self.request=request;self.record=None
        layout=QVBoxLayout(self);layout.setContentsMargins(8,8,8,8)
        self.title=QLabel('Visuals for this task');self.title.setWordWrap(True);layout.addWidget(self.title)
        self.source=QLabel('Charts, diagrams and tables appear here when DeepSeek creates them.');self.source.setWordWrap(True);self.source.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.source)
        controls=QHBoxLayout();self.zoom=QComboBox();self.zoom.addItems(['Fit view','Fit width','75%','100%','150%']);self.zoom.setAccessibleName('Artifact zoom');self.zoom.currentIndexChanged.connect(self.resize_visual);controls.addWidget(self.zoom)
        self.format=QComboBox();self.format.addItems(['HTML','SVG','PNG','CSV','JSON']);self.format.setAccessibleName('Artifact export format');controls.addWidget(self.format)
        export=QPushButton('Export…');export.clicked.connect(self.export_dialog);controls.addWidget(export);controls.addStretch();layout.addLayout(controls)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        self.scroll=QScrollArea();self.visual=QSvgWidget();self.visual.setAccessibleName('Rendered artifact');self.scroll.setWidget(self.visual);self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter);self.tabs.addTab(self.scroll,'Visual')
        self.table=QTableWidget();self.table.setAccessibleName('Artifact data');self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.tabs.addTab(self.table,'Data')
        self.spec=QPlainTextEdit();self.spec.setAccessibleName('Editable artifact specification');self.tabs.addTab(self.spec,'Specification')
        appearance=QWidget();form=QFormLayout(appearance);form.setFormAlignment(Qt.AlignmentFlag.AlignTop);form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.match_labels=QCheckBox('Match legend and value text to chart colors');self.match_labels.toggled.connect(lambda checked:self.apply_style(match_labels=checked) if not self.loading_style else None);form.addRow(self.match_labels)
        self.color_by=QComboBox();self.color_by.addItems(['By series','Each bar']);self.color_by.setAccessibleName('Bar color grouping');self.color_by.currentIndexChanged.connect(lambda index:self.apply_style(color_by='category' if index else 'series') if not self.loading_style else None);form.addRow('Bar colors',self.color_by)
        self.color_buttons={}
        for key in ('background','text','title','muted','grid','surface'):
            picker=QPushButton();picker.setMaximumWidth(180);picker.setAccessibleName('Change '+key+' color');picker.clicked.connect(lambda checked=False,key=key:self.choose_color(key));self.color_buttons[key]=picker;form.addRow(key.capitalize(),picker)
        self.palette_index=QComboBox();self.palette_index.setAccessibleName('Palette color to edit');self.palette_index.currentIndexChanged.connect(self.update_palette_button);form.addRow('Chart color',self.palette_index)
        self.palette_button=QPushButton();self.palette_button.setMaximumWidth(180);self.palette_button.setAccessibleName('Change selected palette color');self.palette_button.clicked.connect(lambda:self.choose_color('palette'));form.addRow('Color',self.palette_button)
        presets=QHBoxLayout()
        for name in ('Dark','Light'):
            preset=QPushButton(name);preset.clicked.connect(lambda checked=False,name=name:self.preset(name));presets.addWidget(preset)
        form.addRow('Preset',presets);hint=QLabel('Changes preview immediately. Save appearance to keep them. Exports use the saved revision.');hint.setWordWrap(True);form.addRow(hint)
        style_scroll=QScrollArea();style_scroll.setWidgetResizable(True);style_scroll.setWidget(appearance);self.tabs.addTab(style_scroll,'Appearance');self.loading_style=False
        self.message=QLabel('');self.message.setTextFormat(Qt.TextFormat.PlainText);self.message.setWordWrap(True);layout.addWidget(self.message)
        self.save=QPushButton('Save changes');self.save.clicked.connect(self.save_spec);layout.addWidget(self.save);self.save.setEnabled(False);self.save.hide();self.tabs.currentChanged.connect(lambda index:self.save.setVisible(index in (2,3)))
    def clear(self):
        self.record=None;self.title.setText('Visuals for this task');self.source.setText('Charts, diagrams and tables appear here when DeepSeek creates them.');self.visual.load(QByteArray());self.table.setRowCount(0);self.spec.clear();self.save.setEnabled(False);self.message.clear()
    def is_dirty(self):
        if not self.record:return False
        try:return artifacts.validate(json.loads(self.spec.toPlainText()))!=artifacts.validate(self.record['spec'])
        except (ValueError,TypeError):return True
    def load(self,record):
        self.record=record;spec=artifacts.validate(record['spec']);self.title.setText(spec['title']+' · revision '+str(record['revision']));self.title.setTextFormat(Qt.TextFormat.PlainText)
        self.source.setText('Source: '+spec['source']+'\nSource labels do not independently verify the data.');self.visual.load(QByteArray(artifacts.svg(spec).encode()));self.resize_visual()
        columns,rows=artifacts.data_rows(spec);self.table.setColumnCount(len(columns));self.table.setHorizontalHeaderLabels(columns);self.table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for j,value in enumerate(row):self.table.setItem(i,j,QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents();self.spec.setPlainText(json.dumps(spec,indent=2,ensure_ascii=False));self.load_style(spec);self.save.setEnabled(True);self.message.setText('Adjust Appearance or edit Specification. Exports use the saved revision.')
    @staticmethod
    def swatch(button,value):
        rgb=QColor(value).getRgbF()[:3];linear=[c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb];light=sum(c*w for c,w in zip(linear,(.2126,.7152,.0722)))
        button.setText(value);button.setStyleSheet('background:'+value+'; color:'+('#000000' if light>.179 else '#ffffff')+';')
    def load_style(self,spec):
        self.loading_style=True
        try:
            style=spec['style']
            for key,picker in self.color_buttons.items():self.swatch(picker,style[key])
            index=max(0,self.palette_index.currentIndex());self.palette_index.clear()
            for i,value in enumerate(style['palette']):self.palette_index.addItem('Palette '+str(i+1)+' · '+value)
            self.palette_index.setCurrentIndex(min(index,len(style['palette'])-1));self.swatch(self.palette_button,style['palette'][self.palette_index.currentIndex()]);self.match_labels.setChecked(style['match_labels']);self.color_by.setCurrentIndex(style['color_by']=='category');self.color_by.setEnabled(spec['kind']=='bar' and len(spec.get('series',[]))==1)
        finally:self.loading_style=False
    def update_palette_button(self,*args):
        if not self.record or self.loading_style:return
        try:self.swatch(self.palette_button,json.loads(self.spec.toPlainText())['style']['palette'][self.palette_index.currentIndex()])
        except (ValueError,KeyError,IndexError,TypeError):pass
    def choose_color(self,key):
        if not self.record:return
        try:
            spec=artifacts.validate(json.loads(self.spec.toPlainText()));style=spec['style'];index=max(0,self.palette_index.currentIndex());value=style['palette'][index] if key=='palette' else style[key]
            chosen=QColorDialog.getColor(QColor(value),self,'Choose '+key+' color')
            if not chosen.isValid():return
            if key=='palette':palette=list(style['palette']);palette[index]=chosen.name();self.apply_style(palette=palette)
            else:self.apply_style(**{key:chosen.name()})
        except (ValueError,TypeError) as exc:self.message.setText(str(exc))
    def apply_style(self,**changes):
        if not self.record:return
        try:
            spec=artifacts.validate(json.loads(self.spec.toPlainText()));spec['style'].update(changes);spec=artifacts.validate(spec)
            self.spec.setPlainText(json.dumps(spec,indent=2,ensure_ascii=False));self.visual.load(QByteArray(artifacts.svg(spec).encode()));self.resize_visual();self.load_style(spec);self.message.setText('Unsaved appearance preview. Save changes to keep it; exports use the saved revision.')
        except (ValueError,TypeError) as exc:self.message.setText('Not changed: '+str(exc))
    def preset(self,name):
        style=artifacts.appearance({})
        if name=='Light':style.update(background='#fafbfe',text='#334155',title='#101827',muted='#526174',grid='#cbd5e1',surface='#e2e8f0',palette=['#2458a4','#13745d','#98600f','#7840a1','#ad3547','#14758b'])
        if self.record:
            try:
                current=artifacts.validate(json.loads(self.spec.toPlainText()))['style'];style.update({k:current[k] for k in ('match_labels','color_by')})
            except (ValueError,TypeError):pass
        self.apply_style(**style)
    def resizeEvent(self,event):super().resizeEvent(event);self.resize_visual()
    def resize_visual(self,*args):
        if not self.record:return
        size=self.visual.renderer().defaultSize();index=self.zoom.currentIndex()
        if index<2:
            scale=max(1,self.scroll.viewport().width()-12)/max(1,size.width())
            if index==0:scale=min(scale,max(1,self.scroll.viewport().height()-12)/max(1,size.height()))
        else:scale=[.75,1,1.5][index-2]
        self.visual.setFixedSize(max(1,int(size.width()*scale)),max(1,int(size.height()*scale)))
    def save_spec(self):
        if not self.record:return
        try:spec=artifacts.validate(json.loads(self.spec.toPlainText()))
        except (ValueError,TypeError) as exc:self.message.setText('Not saved: '+str(exc));return
        self.save.setEnabled(False);ident=self.record['id'];revision=self.record['revision'];submitted=self.spec.toPlainText()
        def current():return self.record and self.record['id']==ident and self.record['revision']==revision
        def failed(message):
            if current():self.save.setEnabled(True);self.message.setText('Not saved: '+message+' Your edits are still in Specification.')
        def saved(record):
            if not current():return
            if self.spec.toPlainText()!=submitted:
                self.record=record;self.save.setEnabled(True);self.message.setText('Saved the submitted revision. Newer local edits are preserved; save again to keep them.');return
            self.load(record)
        self.request('edit_artifact',{'id':ident,'revision':revision,'spec':spec},saved,error=failed)
    def export_to(self,path,kind):
        if not self.record:raise ValueError('Select an artifact first')
        from .artifact_export import export_spec
        export_spec(self.record['spec'],path,kind)
    def export_dialog(self):
        if not self.record:self.message.setText('Select an artifact first.');return
        kind=self.format.currentText();path,_=QFileDialog.getSaveFileName(self,'Export saved artifact','artifact.'+kind.lower(),kind+' (*.'+kind.lower()+')')
        if path:
            try:self.export_to(path,kind);self.message.setText('Exported saved revision to '+path)
            except (OSError,ValueError) as exc:self.message.setText(str(exc))
