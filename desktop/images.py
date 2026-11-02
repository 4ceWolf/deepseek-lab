"""Explicit project image snapshots; bytes never enter the model context."""
import base64,time
from pathlib import Path

MAX_BYTES=8_000_000

def publish(core,session_id,path,title):
    session=core.store.get('session',session_id);project=session['project']
    if project!=core.workspace.settings()['project']:raise ValueError('Select this task’s project first')
    file=core.workspace.inside(project,path)
    if file.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):raise ValueError('Select a PNG, JPEG or WebP image')
    with file.open('rb') as stream:data=stream.read(MAX_BYTES+1)
    if not data or len(data)>MAX_BYTES:raise ValueError('Images must be nonempty and at most 8 MB')
    valid=data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff') or (data[:4]==b'RIFF' and data[8:12]==b'WEBP')
    if not valid:raise ValueError('File is not a supported image')
    if not isinstance(title,str) or not title.strip() or len(title)>160:raise ValueError('Image title must be 1–160 characters')
    record=core.store.put('image',dict(session=session_id,project=project,title=core.redact(title),name=file.name,content=base64.b64encode(data).decode('ascii'),created=time.time(),bytes=len(data)))
    result=summary(record);core.store.put('image_meta',result);return result

def summary(record):return {k:record[k] for k in ('id','session','project','title','name','created','bytes')}
