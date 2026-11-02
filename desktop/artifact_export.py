"""Explicit exports of validated visual specs shared by inline and inspector views."""
import json
from pathlib import Path
from . import artifacts,artifact_html

def export_spec(spec,path,kind):
    spec=artifacts.validate(spec);path=Path(path);kind=kind.upper()
    if kind=='HTML':path.write_text(artifact_html.document(spec),encoding='utf-8')
    elif kind=='SVG':path.write_text(artifacts.svg(spec),encoding='utf-8')
    elif kind=='JSON':path.write_text(json.dumps(spec,indent=2,ensure_ascii=False),encoding='utf-8')
    elif kind=='CSV':path.write_text(artifacts.csv_text(spec),encoding='utf-8')
    elif kind=='PNG':
        from PySide6.QtCore import QByteArray,Qt
        from PySide6.QtGui import QImage,QPainter
        from PySide6.QtSvg import QSvgRenderer
        renderer=QSvgRenderer(QByteArray(artifacts.svg(spec).encode()));image=QImage(renderer.defaultSize(),QImage.Format.Format_ARGB32);image.fill(Qt.GlobalColor.transparent);painter=QPainter(image)
        try:painter.setRenderHints(QPainter.RenderHint.Antialiasing|QPainter.RenderHint.TextAntialiasing|QPainter.RenderHint.SmoothPixmapTransform);renderer.render(painter)
        finally:painter.end()
        if not image.save(str(path),'PNG'):raise ValueError('Could not write PNG')
    else:raise ValueError('Unsupported export format')
