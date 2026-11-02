"""Native, locally evaluated interactive cards for the conversation viewport."""
import copy,json,math,time
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QPointF,QRectF,Signal
from PySide6.QtGui import QColor,QPainter,QPen,QPainterPath,QFont
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QSlider,QDoubleSpinBox,QCheckBox,QComboBox,QPushButton,QFileDialog,QPlainTextEdit,QFrame
from . import interactive,motion

PALETTE=['#92baff','#62d4b1','#efbb70','#d2a4f5','#ef929e','#7ed5e8']
class Scene(QWidget):
    changed=Signal()
    def __init__(self,spec,values,parent=None):
        super().__init__(parent);self.spec=spec;self.values=values;self.dragging=None;self.errors=[];self.setMinimumHeight(260);self.setMouseTracking(True);self.setAccessibleName('Interactive scene. Point coordinates can also be changed with the controls below.');self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    def plot_rect(self):return QRectF(45,20,max(40,self.width()-65),max(40,self.height()-55))
    def point(self,x,y):
        r=self.plot_rect();xr=self.spec['scene']['x'];yr=self.spec['scene']['y'];return QPointF(r.left()+(x-xr[0])/(xr[1]-xr[0])*r.width(),r.bottom()-(y-yr[0])/(yr[1]-yr[0])*r.height())
    def coordinate(self,p):
        r=self.plot_rect();xr=self.spec['scene']['x'];yr=self.spec['scene']['y'];return (min(xr[1],max(xr[0],xr[0]+(p.x()-r.left())/r.width()*(xr[1]-xr[0]))),min(yr[1],max(yr[0],yr[0]+(r.bottom()-p.y())/r.height()*(yr[1]-yr[0]))))
    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHints(QPainter.RenderHint.Antialiasing|QPainter.RenderHint.TextAntialiasing);self.paint_scene(painter)
    def paint_scene(self,p):
        p.fillRect(self.rect(),QColor('#14191f'));r=self.plot_rect();xr=self.spec['scene']['x'];yr=self.spec['scene']['y'];self.errors=[]
        def ev(expr):return interactive.evaluate(expr,self.values)
        try:axes=ev(self.spec['scene']['axes'])
        except ValueError:axes=False
        p.setFont(QFont('sans-serif',9))
        if axes:
            for i in range(6):
                x=xr[0]+i*(xr[1]-xr[0])/5;y=yr[0]+i*(yr[1]-yr[0])/5;xp=self.point(x,yr[0]).x();yp=self.point(xr[0],y).y();p.setPen(QPen(QColor('#2c3540'),1));p.drawLine(QPointF(xp,r.top()),QPointF(xp,r.bottom()));p.drawLine(QPointF(r.left(),yp),QPointF(r.right(),yp));p.setPen(QColor('#9eacbc'));p.drawText(QRectF(xp-26,r.bottom()+7,52,20),Qt.AlignmentFlag.AlignCenter,f'{x:.3g}');p.drawText(QRectF(0,yp-10,38,20),Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,f'{y:.3g}')
        p.save();p.setClipRect(r)
        for index,l in enumerate(self.spec['scene']['layers']):
            try:
                if not ev(l['visible']):continue
                color=QColor(PALETTE[int(l['color'][1:])] if l['color'].startswith('p') else l['color']);p.setPen(QPen(color,l['width']));p.setBrush(Qt.BrushStyle.NoBrush);kind=l['type']
                if kind=='curve':
                    path=QPainterPath();started=False;previous=None;lo,hi=l['u'];previous_u=self.values['u']
                    for i in range(l['samples']):
                        self.values['u']=lo+i*(hi-lo)/(l['samples']-1)
                        try:pt=self.point(ev(l['x']),ev(l['y']))
                        except ValueError:started=False;continue
                        if abs(pt.x())>1e7 or abs(pt.y())>1e7:started=False;continue
                        if previous is not None and abs(pt.y()-previous.y())>self.height()*3:started=False
                        previous=pt
                        if started:path.lineTo(pt)
                        else:path.moveTo(pt);started=True
                    self.values['u']=previous_u;p.drawPath(path)
                elif kind=='circle':
                    x,y,rad=ev(l['x']),ev(l['y']),ev(l['r'])
                    if not 0<=rad<=1e6:raise ValueError('Circle radius is outside bounds')
                    a=self.point(x-rad,y+rad);b=self.point(x+rad,y-rad);p.drawEllipse(QRectF(a,b))
                elif kind=='rect':
                    x,y,w,h=ev(l['x']),ev(l['y']),ev(l['w']),ev(l['h'])
                    if w<0 or h<0:raise ValueError('Negative rectangle size')
                    p.drawRoundedRect(QRectF(self.point(x,y+h),self.point(x+w,y)),6,6)
                elif kind in ('line','arrow'):
                    a,b=self.point(ev(l['x']),ev(l['y'])),self.point(ev(l['x2']),ev(l['y2']));p.drawLine(a,b)
                    if kind=='arrow':
                        angle=math.atan2(b.y()-a.y(),b.x()-a.x());p.drawLine(b,QPointF(b.x()-10*math.cos(angle-.5),b.y()-10*math.sin(angle-.5)));p.drawLine(b,QPointF(b.x()-10*math.cos(angle+.5),b.y()-10*math.sin(angle+.5)))
                else:p.setFont(QFont('sans-serif',int(l['size'])));p.drawText(self.point(ev(l['x']),ev(l['y'])),l['text'])
            except (ValueError,OverflowError):self.errors.append(l['label'] or f'Layer {index+1}')
        for c in self.spec['controls']:
            if c['type']=='point':
                pt=self.point(self.values[c['id']+'_x'],self.values[c['id']+'_y']);p.setPen(QPen(QColor('#d8e8ff'),2));p.setBrush(QColor('#92baff'));p.drawEllipse(pt,7,7);p.setFont(QFont('sans-serif',10));p.drawText(pt+QPointF(11,-9),c['label'])
        p.restore()
    def mousePressEvent(self,e):
        if e.button()!=Qt.MouseButton.LeftButton:return
        for c in self.spec['controls']:
            if c['type']=='point' and (self.point(self.values[c['id']+'_x'],self.values[c['id']+'_y'])-e.position()).manhattanLength()<24:self.dragging=c['id'];self.setCursor(Qt.CursorShape.ClosedHandCursor);e.accept();return
    def mouseMoveEvent(self,e):
        if self.dragging:
            x,y=self.coordinate(e.position());self.values[self.dragging+'_x']=x;self.values[self.dragging+'_y']=y;self.changed.emit();self.update()
    def mouseReleaseEvent(self,e):self.dragging=None;self.unsetCursor()

class InteractiveCard(QFrame):
    stateChanged=Signal(dict)
    def __init__(self,spec,saved=None,parent=None):
        super().__init__(parent);self.spec=copy.deepcopy(spec);self.values=interactive.state(spec,saved or {});self.setObjectName('InlineVisual');self.bindings={};self.playing=False
        layout=QVBoxLayout(self);layout.setContentsMargins(18,16,18,16);layout.setSpacing(12)
        self.title=QLabel(spec['title']);self.title.setTextFormat(Qt.TextFormat.PlainText);self.title.setWordWrap(True);self.title.setObjectName('VisualTitle');layout.addWidget(self.title)
        if spec.get('description'):
            d=QLabel(spec['description']);d.setTextFormat(Qt.TextFormat.PlainText);d.setWordWrap(True);d.setObjectName('Muted');layout.addWidget(d)
        self.scene=Scene(spec,self.values);self.scene.changed.connect(self.changed);layout.addWidget(self.scene);self.has_scene=bool(spec['scene']['layers']) or any(c['type']=='point' for c in spec['controls']);self.scene.setVisible(self.has_scene)
        self.readout=QLabel();self.readout.setTextFormat(Qt.TextFormat.PlainText);self.readout.setWordWrap(True);self.readout.setObjectName('VisualReadout');layout.addWidget(self.readout)
        for c in spec['controls']:
            row=QHBoxLayout();name=QLabel(c['label']);name.setTextFormat(Qt.TextFormat.PlainText);name.setMinimumWidth(100);name.setWordWrap(True);row.addWidget(name)
            ident=c['id'];kind=c['type']
            if kind=='slider':
                slider=QSlider(Qt.Orientation.Horizontal);slider.setRange(0,math.ceil((c['max']-c['min'])/c['step']));slider.setAccessibleName(c['label']);spin=self.spin(c['min'],c['max'],c['step']);spin.setAccessibleName(c['label']+' value');row.addWidget(slider,1);row.addWidget(spin);self.bindings[ident]=(slider,spin,c)
                slider.valueChanged.connect(lambda n,c=c:self.set_value(c['id'],min(c['max'],c['min']+n*c['step'])));spin.valueChanged.connect(lambda v,key=ident:self.set_value(key,v))
                if c.get('unit'):
                    unit=QLabel(c['unit']);unit.setTextFormat(Qt.TextFormat.PlainText);row.addWidget(unit)
                name.setBuddy(spin)
            elif kind=='toggle':
                check=QCheckBox('Enabled');check.setAccessibleName(c['label']);row.addWidget(check);row.addStretch();self.bindings[ident]=(check,);check.toggled.connect(lambda v,key=ident:self.set_value(key,v));name.setBuddy(check)
            elif kind=='select':
                select=QComboBox();select.setAccessibleName(c['label'])
                for opt in c['options']:select.addItem(opt['label'],opt['value'])
                row.addWidget(select,1);self.bindings[ident]=(select,);select.currentIndexChanged.connect(lambda _,w=select,key=ident:self.set_value(key,w.currentData()));name.setBuddy(select)
            else:
                coordinate_box=QWidget();coordinate_layout=QVBoxLayout(coordinate_box);coordinate_layout.setContentsMargins(0,0,0,0);coordinate_layout.setSpacing(4)
                for axis,bounds in [('x',spec['scene']['x']),('y',spec['scene']['y'])]:
                    coordinate_row=QHBoxLayout();spin=self.spin(*bounds,(bounds[1]-bounds[0])/100);spin.setAccessibleName(c['label']+' '+axis);coordinate_row.addWidget(QLabel(axis));coordinate_row.addWidget(spin,1);coordinate_layout.addLayout(coordinate_row);self.bindings[ident+'_'+axis]=(spin,);spin.valueChanged.connect(lambda v,key=ident+'_'+axis:self.set_value(key,v))
                row.addWidget(coordinate_box,1)
            layout.addLayout(row)
        self.clock=QTimer(self);self.clock.setInterval(50);self.clock.timeout.connect(self.tick)
        toolbar=QHBoxLayout()
        if spec['animation']:
            self.play=QPushButton('Play');self.play.setAccessibleName('Play or pause animation');self.play.clicked.connect(self.toggle_play);toolbar.addWidget(self.play)
            self.time_slider=QSlider(Qt.Orientation.Horizontal);self.time_slider.setRange(0,1000);self.time_slider.setAccessibleName('Animation time');self.time_slider.valueChanged.connect(lambda n:self.set_value('t',n*spec['animation']['duration']/1000));toolbar.addWidget(self.time_slider,1)
        reset=QPushButton('Reset');reset.clicked.connect(self.reset);toolbar.addWidget(reset);export=QPushButton('Export…');export.clicked.connect(self.export);toolbar.addWidget(export);layout.addLayout(toolbar)
        self.source=QLabel('Source: '+spec['source']);self.source.setTextFormat(Qt.TextFormat.PlainText);self.source.setWordWrap(True);self.source.setObjectName('Muted');layout.addWidget(self.source)
        self.status=QLabel('Controls run locally · no model request');self.status.setTextFormat(Qt.TextFormat.PlainText);self.status.setWordWrap(True);self.status.setObjectName('Muted');layout.addWidget(self.status);self.changed(False)
    @staticmethod
    def spin(lo,hi,step):
        w=QDoubleSpinBox();w.setDecimals(5);w.setRange(lo,hi);w.setSingleStep(step);w.setMinimumWidth(96);return w
    def display_height(self,width):
        columns=max(25,int((width-40)/7));description=max(36,math.ceil(len(self.spec.get('description',''))/columns)*19) if self.spec.get('description') else 0
        labels=sum(max(80 if c['type']=='point' else 49,math.ceil(len(c['label'])/14)*18+12) for c in self.spec['controls']);readout=max(30,math.ceil(sum(len(r['label'])+len(r['unit'])+20 for r in self.spec['readouts'])/columns)*19) if self.spec['readouts'] else 0
        return (450 if self.has_scene else 190)+labels+description+readout+max(0,math.ceil(len(self.spec['title'])/max(15,int((width-40)/11)))-1)*26+max(0,math.ceil(len(self.spec['source'])/columns)-2)*16
    def set_value(self,key,value):self.values[key]=value;self.changed()
    def changed(self,emit=True):
        for key,b in self.bindings.items():
            if len(b)==3:
                slider,spin,c=b
                for w in (slider,spin):w.blockSignals(True)
                slider.setValue(round((self.values[key]-c['min'])/c['step']));spin.setValue(self.values[key])
                for w in (slider,spin):w.blockSignals(False)
            else:
                w=b[0];w.blockSignals(True)
                if isinstance(w,QCheckBox):w.setChecked(self.values[key])
                elif isinstance(w,QComboBox):w.setCurrentIndex(w.findData(self.values[key]))
                else:w.setValue(self.values[key])
                w.blockSignals(False)
        if self.spec['animation']:
            self.time_slider.blockSignals(True);self.time_slider.setValue(round(self.values['t']/self.spec['animation']['duration']*1000));self.time_slider.blockSignals(False)
        output=[];errors=False
        for r in self.spec['readouts']:
            try:value=f"{interactive.evaluate(r['expr'],self.values):.6g}"
            except ValueError:value='undefined';errors=True
            output.append(r['label']+': '+value+(' '+r['unit'] if r['unit'] else ''))
        self.readout.setText('   ·   '.join(output));self.scene.update();self.status.setText('Some values are undefined at these settings. Adjust the controls.' if errors else 'Controls run locally · no model request')
        if emit:self.stateChanged.emit(interactive.state(self.spec,self.values))
    def toggle_play(self):
        if motion.reduced():self.status.setText('Reduced motion is enabled. Use the time slider to explore.');return
        self.playing=not self.playing;self.play.setText('Pause' if self.playing else 'Play')
        if self.playing:self.last_tick=time.monotonic();self.clock.start()
        else:self.clock.stop();self.stateChanged.emit(interactive.state(self.spec,self.values))
    def tick(self):
        if not self.isVisible() or self.visibleRegion().isEmpty() or motion.reduced():self.last_tick=time.monotonic();return
        now=time.monotonic();animation=self.spec['animation'];self.values['t']=(self.values['t']+min(.15,now-self.last_tick)*animation['speed'])%animation['duration'];self.last_tick=now;self.changed(False)
    def reset(self):
        self.playing=False;self.clock.stop()
        if self.spec['animation']:self.play.setText('Play')
        self.values.clear();self.values.update(interactive.defaults(self.spec));self.changed()
    def hideEvent(self,event):
        if self.playing:self.playing=False;self.clock.stop();self.play.setText('Play');self.stateChanged.emit(interactive.state(self.spec,self.values))
        super().hideEvent(event)
    def export(self):
        path,selected=QFileDialog.getSaveFileName(self,'Export interactive visual','visual.html','Interactive HTML (*.html);;PNG snapshot (*.png);;JSON specification (*.json)')
        if not path:return
        try:
            if selected.startswith('Interactive'):
                from .interactive_html import document
                Path(path).write_text(document(self.spec,self.values),encoding='utf-8')
            elif selected.startswith('PNG'):
                if not self.grab().save(path,'PNG'):raise ValueError('Could not write PNG')
            else:Path(path).write_text(json.dumps(dict(spec=self.spec,state=interactive.state(self.spec,self.values)),indent=2),encoding='utf-8')
            self.status.setText('Exported visual.')
        except (OSError,ValueError) as exc:self.status.setText('Export failed: '+str(exc))
