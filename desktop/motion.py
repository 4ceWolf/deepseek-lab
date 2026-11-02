"""Short native transitions; no animation is required for completing an action."""
import os
from PySide6.QtCore import QPropertyAnimation,QEasingCurve,QSettings
from PySide6.QtWidgets import QApplication,QGraphicsOpacityEffect

def reduced():
    app=QApplication.instance()
    value=app.property('reduceMotion') if app else None
    return bool(value) if value is not None else os.environ.get('DEEPSEEK_REDUCED_MOTION')=='1' or QSettings('DeepSeekLocal','deepseek-lab').value('reduceMotion',False,type=bool)
def set_reduced(value):
    QApplication.instance().setProperty('reduceMotion',bool(value));QSettings('DeepSeekLocal','deepseek-lab').setValue('reduceMotion',bool(value))
def reveal(widget,duration=160):
    prior=getattr(widget,'_entrance',None)
    if prior:
        prior.stop();widget._entrance=None
        widget.setGraphicsEffect(None);prior.deleteLater()
    if reduced() or not widget.isVisible():return
    effect=QGraphicsOpacityEffect(widget);widget.setGraphicsEffect(effect)
    animation=QPropertyAnimation(effect,b'opacity',widget);animation.setDuration(duration);animation.setStartValue(.35);animation.setEndValue(1.);animation.setEasingCurve(QEasingCurve.Type.OutCubic);widget._entrance=animation
    def finish():
        if getattr(widget,'_entrance',None) is animation:
            widget._entrance=None;widget.setGraphicsEffect(None)
        animation.deleteLater()
    animation.finished.connect(finish);animation.start()
