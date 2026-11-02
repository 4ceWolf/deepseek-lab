"""Native visual widgets anchored to inline objects in the actual chat document."""
import copy,hashlib,json,re
from PySide6.QtCore import QObject,QSizeF,QTimer,QUrl,Qt,Signal
from PySide6.QtGui import QTextFormat,QTextCharFormat,QTextCursor,QPyTextObject
from PySide6.QtWidgets import QFrame,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFileDialog,QWidget,QToolButton
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import QByteArray
from . import artifacts,drawing,interactive
from .interactive_view import InteractiveCard
from .ui import SafeBrowser

OBJECT=int(QTextFormat.ObjectTypes.UserObject)+37
KEY=int(QTextFormat.Property.UserProperty)+37

class TranscriptDisclosure(QWidget):
    """A native, keyboard-accessible disclosure rather than a document hyperlink."""
    def __init__(self,url,parent,activate):
        super().__init__(parent);self.setObjectName('TranscriptDisclosureRow')
        layout=QHBoxLayout(self);layout.setContentsMargins(0,2,0,2)
        self.button=QToolButton(self);self.button.setObjectName('TranscriptDisclosure')
        self.label='Activity' if url.startswith('app-activity:') else 'Thinking';self.detail='tool activity' if self.label=='Activity' else 'reasoning'
        self.button.setText(self.label);self.button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.button.setCheckable(True);self.button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.clicked.connect(lambda:activate(QUrl(url)))
        layout.addWidget(self.button);layout.addStretch(1)
    def update_expanded(self,expanded):
        self.button.setChecked(expanded)
        self.button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.button.setAccessibleName(self.label)
        self.button.setAccessibleDescription(('Expanded. Hide ' if expanded else 'Collapsed. Show ')+self.detail+'.')
        self.button.setToolTip(('Hide ' if expanded else 'Show ')+self.detail)
    def display_height(self,width):return 38

class StaticCard(QFrame):
    def __init__(self,spec,parent):
        super().__init__(parent);self.spec=spec;self.setObjectName('InlineVisual');layout=QVBoxLayout(self);layout.setContentsMargins(16,16,16,16)
        title=QLabel(spec['title']);title.setTextFormat(Qt.TextFormat.PlainText);title.setWordWrap(True);title.setObjectName('VisualTitle');layout.addWidget(title)
        self.visual=QSvgWidget();self.visual.load(QByteArray(artifacts.svg(spec).encode()));layout.addWidget(self.visual,1)
        source=QLabel('Source: '+spec['source']);source.setTextFormat(Qt.TextFormat.PlainText);source.setWordWrap(True);source.setObjectName('Muted');layout.addWidget(source)
        export=QPushButton('Export visual…');export.clicked.connect(self.export);layout.addWidget(export)
    def display_height(self,width):return min(620,max(360,int(width*.55)))
    def export(self):
        path,selected=QFileDialog.getSaveFileName(self,'Export visual','visual.html','HTML (*.html);;SVG (*.svg);;PNG (*.png);;CSV (*.csv);;JSON (*.json)')
        if path:
            from .artifact_export import export_spec
            try:export_spec(self.spec,path,selected.split()[0])
            except (OSError,ValueError) as exc:self.setToolTip(str(exc))

class VisualObject(QPyTextObject):
    def __init__(self,browser):super().__init__(browser);self.browser=browser
    def intrinsicSize(self,document,pos,fmt):
        card=self.browser.cards.get(str(fmt.property(KEY)));width=max(250,min(820,self.browser.viewport().width()-55))
        return QSizeF(width,card.display_height(width) if card else 100)
    def drawObject(self,painter,rect,document,pos,fmt):pass

class InlineBrowser(SafeBrowser):
    visualStateChanged=Signal(str,dict,dict)
    def __init__(self,*args):
        super().__init__(*args);self.cards={};self.positions=[];self.context='';self.saved_states={};self.extra_specs=[];self.original_markdown='';self._position_pending=False;self.locally_changed=set();self.state_request=None;self.pending_states={}
        self.state_timer=QTimer(self);self.state_timer.setSingleShot(True);self.state_timer.setInterval(500);self.state_timer.timeout.connect(self.flush_visual_state)
        self.handler=VisualObject(self);self.document().documentLayout().registerHandler(OBJECT,self.handler)
        self.verticalScrollBar().valueChanged.connect(self.position_cards);self.document().documentLayout().update.connect(self.schedule_position);self.document().documentLayout().documentSizeChanged.connect(self.schedule_position)
    @property
    def visual_keys(self):return {key for key,card in self.cards.items() if not isinstance(card,TranscriptDisclosure)}
    def set_context(self,key,states=None):
        if key!=self.context:
            self.flush_visual_state();self.clear_cards();self.flush_visual_state();self.context=key;self.saved_states=states or {};self.locally_changed=set();self.extra_specs=[];self.original_markdown='';super().setPlainText('')
        elif states:
            for ident,value in states.items():
                if ident in self.locally_changed:continue
                self.saved_states[ident]=value
                for card in self.cards.values():
                    if isinstance(card,InteractiveCard) and interactive.identity(card.spec)==ident:
                        try:card.values.clear();card.values.update(interactive.state(card.spec,value));card.changed(False)
                        except ValueError:card.values.update(interactive.defaults(card.spec));card.changed(False)
    def clear_cards(self):
        for card in self.cards.values():card.hide();card.deleteLater()
        self.cards={};self.positions=[]
    def set_artifacts(self,specs):
        if specs!=self.extra_specs:self.extra_specs=copy.deepcopy(specs);self.setMarkdown(self.original_markdown)
    def setPlainText(self,text):self.clear_cards();self.original_markdown='';super().setPlainText(text)
    def setMarkdown(self,markdown):
        self.original_markdown=markdown;specs={};disclosures={};order=[];counts={}
        def marker(spec):
            base=interactive.identity(spec);count=counts.get(base,0);counts[base]=count+1;key=base if count==0 else base+'x'+str(count);order.append(key);specs[key]=spec
            return '\n\nINLINEVISUAL'+key+'ENDVISUAL\n\n'
        def replace(match):
            language,body=match.group(1),match.group(2)
            if language=='json':
                try:
                    if json.loads(body).get('kind')!='interactive':return match.group(0)
                except (ValueError,AttributeError):return match.group(0)
            try:spec=drawing.parse(body) if language=='deepseek-draw' else artifacts.validate(json.loads(body))
            except (ValueError,TypeError,KeyError) as exc:return match.group(0)+'\n\nVisual could not be rendered: '+str(exc)[:160]
            return marker(spec)
        def disclosure(match):
            key='disclosure:'+match.group(3);disclosures[key]=(match.group(3),match.group(1)=='▾');order.append(key)
            return '\n\nINLINEVISUAL'+key+'ENDVISUAL\n\n'
        text=re.sub(r'```(deepseek-visual|deepseek-artifact|deepseek-draw|json)\s*\n(.*?)```',replace,markdown,flags=re.S)
        text=re.sub(r'\[([▾▸]) (Thinking|Activity[^\]\n]*)\]\((app-(?:thinking|activity):\d+)\)',disclosure,text)
        for spec in self.extra_specs:
            try:spec=artifacts.validate(spec)
            except (ValueError,TypeError,KeyError):continue
            if interactive.identity(spec) not in {interactive.identity(s) for s in specs.values()}:text+=marker(spec)
        for key,card in list(self.cards.items()):
            if key not in specs and key not in disclosures:card.hide();card.deleteLater();del self.cards[key]
        for key,spec in specs.items():
            if key not in self.cards:
                if spec['kind']=='interactive':
                    card=InteractiveCard(spec,self.saved_states.get(interactive.identity(spec)),self.viewport());card.stateChanged.connect(lambda values,key=interactive.identity(spec),spec=spec:self.state_changed(key,spec,values))
                else:card=StaticCard(spec,self.viewport())
                self.cards[key]=card
        for key,(url,expanded) in disclosures.items():
            if key not in self.cards:self.cards[key]=TranscriptDisclosure(url,self.viewport(),self.anchorClicked.emit)
            self.cards[key].update_expanded(expanded)
        super().setMarkdown(text);self.positions=[]
        # Replace marker text with a sized document object. Native widgets occupy that exact slot.
        for key in sorted(order,key=lambda key:self.document().find('INLINEVISUAL'+key+'ENDVISUAL').selectionStart()):
            cursor=self.document().find('INLINEVISUAL'+key+'ENDVISUAL')
            if cursor.isNull():continue
            pos=cursor.selectionStart();fmt=QTextCharFormat();fmt.setObjectType(OBJECT);fmt.setProperty(KEY,key);cursor.insertText('\ufffc',fmt);self.positions.append((key,pos))
        self.schedule_position()
    def bind_state(self,request):self.state_request=request
    def flush_visual_state(self):
        if not self.state_request:return
        if self.context:
            for key,card in self.cards.items():
                if isinstance(card,InteractiveCard):
                    base=interactive.identity(card.spec)
                    if card.playing or base in self.locally_changed:self.pending_states[(self.context,base)]=dict(context=self.context,key=base,spec=card.spec,state=interactive.state(card.spec,card.values))
        rows=list(self.pending_states.values());self.pending_states.clear();self.state_timer.stop()
        for data in rows:self.state_request('save_visual_state',data,None,lambda error:self.setToolTip('Visual state was not saved: '+error))
    def state_changed(self,key,spec,values):
        for card in self.cards.values():
            if isinstance(card,InteractiveCard) and interactive.identity(card.spec)==key and card.values!=dict(card.values,**values):card.values.update(values);card.changed(False)
        self.locally_changed.add(key);self.saved_states[key]=values;self.visualStateChanged.emit(key,spec,values)
        if self.context and self.state_request:
            self.pending_states[(self.context,key)]=dict(context=self.context,key=key,spec=spec,state=values);self.state_timer.start()
    def schedule_position(self,*_):
        if self._position_pending:return
        self._position_pending=True;QTimer.singleShot(0,self.position_cards)
    def position_cards(self,*_):
        self._position_pending=False
        for key,pos in self.positions:
            card=self.cards.get(key)
            if not card:continue
            cursor=QTextCursor(self.document());cursor.setPosition(min(pos,self.document().characterCount()-1));rect=self.cursorRect(cursor);width=max(250,min(820,self.viewport().width()-55));height=card.display_height(width)
            card.setGeometry(rect.x(),rect.y(),width,height);card.setVisible(self.viewport().rect().intersects(card.geometry()) and self.isVisible());card.raise_()
    def scroll_to_visual(self,last=True):
        positions=[(key,pos) for key,pos in self.positions if not isinstance(self.cards.get(key),TranscriptDisclosure)]
        if not positions:return
        key,pos=positions[-1 if last else 0];cursor=QTextCursor(self.document());cursor.setPosition(pos);rect=self.cursorRect(cursor)
        if self.verticalScrollBar().maximum():self.verticalScrollBar().setValue(self.verticalScrollBar().value()+rect.y()-12)
        else:
            from PySide6.QtWidgets import QScrollArea
            from PySide6.QtCore import QPoint
            parent=self.parentWidget()
            while parent:
                if isinstance(parent,QScrollArea) and parent.widget():
                    origin=self.mapTo(parent.widget(),QPoint(0,0));parent.verticalScrollBar().setValue(origin.y()+rect.y()-12);break
                parent=parent.parentWidget()
        self.position_cards()
    def resizeEvent(self,event):
        super().resizeEvent(event);self.document().markContentsDirty(0,self.document().characterCount());self.schedule_position()
    def showEvent(self,event):super().showEvent(event);self.schedule_position()
    def hideEvent(self,event):
        for card in self.cards.values():card.hide()
        super().hideEvent(event)
