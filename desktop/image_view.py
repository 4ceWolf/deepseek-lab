"""Bounded native image decoding and a local save/copy fallback."""
import base64
from pathlib import Path
from PySide6.QtCore import QByteArray,QBuffer,QIODevice,Qt
from PySide6.QtGui import QImage,QImageReader,QPixmap
from PySide6.QtWidgets import QApplication,QDialog,QVBoxLayout,QHBoxLayout,QLabel,QScrollArea,QPushButton,QFileDialog

def decode(record):
    data=base64.b64decode(record['content'],validate=True)
    if len(data)>8_000_000:raise ValueError('Image exceeds 8 MB')
    buffer=QBuffer();buffer.setData(QByteArray(data));buffer.open(QIODevice.OpenModeFlag.ReadOnly);reader=QImageReader(buffer);size=reader.size()
    if size.width()<=0 or size.height()<=0 or size.width()*size.height()>16_000_000:raise ValueError('Preview unavailable: image is invalid or exceeds 16 million pixels. Save the original instead.')
    image=reader.read()
    if image.isNull():raise ValueError('Preview unavailable: '+reader.errorString())
    return image

class ImageDialog(QDialog):
    def __init__(self,record,parent=None):
        super().__init__(parent);self.record=record;self.setWindowTitle(record['title']);self.resize(920,650);layout=QVBoxLayout(self)
        title=QLabel(record['title']);title.setTextFormat(Qt.TextFormat.PlainText);title.setWordWrap(True);layout.addWidget(title)
        self.status=QLabel('Local saved image · '+str(record['bytes'])+' bytes');self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
        scroll=QScrollArea();scroll.setWidgetResizable(True);preview=QLabel();preview.setAlignment(Qt.AlignmentFlag.AlignCenter);preview.setAccessibleName('Image preview');scroll.setWidget(preview);layout.addWidget(scroll,1);self.image=QImage()
        try:self.image=decode(record);preview.setPixmap(QPixmap.fromImage(self.image).scaled(850,490,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        except (ValueError,TypeError) as exc:preview.setText(str(exc));preview.setWordWrap(True)
        actions=QHBoxLayout();save=QPushButton('Save original…');save.clicked.connect(self.save_dialog);actions.addWidget(save);copy=QPushButton('Copy image');copy.setEnabled(not self.image.isNull());copy.clicked.connect(lambda:QApplication.clipboard().setImage(self.image));actions.addWidget(copy);close=QPushButton('Close');close.clicked.connect(self.accept);actions.addWidget(close);layout.addLayout(actions)
    def save_to(self,path):Path(path).write_bytes(base64.b64decode(self.record['content'],validate=True))
    def save_dialog(self):
        path,_=QFileDialog.getSaveFileName(self,'Save original image',Path(self.record['name']).name)
        if path:
            try:self.save_to(path);self.status.setText('Saved to '+path)
            except (OSError,ValueError) as exc:self.status.setText('Could not save: '+str(exc))
