"""Chat keyboard behavior, including IME-safe Enter-to-send."""
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import QPlainTextEdit
class MessageEdit(QPlainTextEdit):
    submitted=Signal()
    def __init__(self,*args):super().__init__(*args);self.composing=False
    def inputMethodEvent(self,event):
        self.composing=bool(event.preeditString());super().inputMethodEvent(event)
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and not self.composing and not event.modifiers() & (Qt.KeyboardModifier.ShiftModifier|Qt.KeyboardModifier.AltModifier):
            if not event.isAutoRepeat():self.submitted.emit()
            event.accept();return
        super().keyPressEvent(event)
