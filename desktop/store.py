"""Small durable record store shared by the service's worker threads."""
import json,os,sqlite3,time,uuid
from pathlib import Path
from contextlib import contextmanager

class Store:
    def __init__(self, directory):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        os.chmod(self.directory,0o700);self.path=self.directory/'workspace.sqlite3'
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS records(kind TEXT,id TEXT,value TEXT,updated REAL,PRIMARY KEY(kind,id))')
            db.execute('CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,time REAL,kind TEXT,value TEXT)')
        os.chmod(self.path,0o600)
    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=15)
        try:
            with db:yield db
        finally:db.close()
    def put(self,kind,value,ident=None):
        ident=ident or value.get('id') or uuid.uuid4().hex
        value=dict(value,id=ident)
        with self.connect() as db:db.execute('INSERT OR REPLACE INTO records VALUES(?,?,?,?)',(kind,ident,json.dumps(value),time.time()))
        return value
    def get(self,kind,ident):
        with self.connect() as db:row=db.execute('SELECT value FROM records WHERE kind=? AND id=?',(kind,ident)).fetchone()
        if not row:raise ValueError('Record not found')
        return json.loads(row[0])
    def list(self,kind,limit=None,**filters):
        query='SELECT value FROM records WHERE kind=?';params=[kind]
        for key,value in filters.items():
            if not key.replace('_','').isalnum():raise ValueError('Invalid record filter')
            values=value if isinstance(value,(tuple,list)) else [value]
            if not values:return []
            query+=' AND json_extract(value,?) IN ('+','.join('?' for _ in values)+')';params+=['$.'+key]+list(values)
        query+=' ORDER BY updated DESC'
        if limit is not None:query+=' LIMIT ?';params.append(max(0,int(limit)))
        with self.connect() as db:rows=db.execute(query,params).fetchall()
        return [json.loads(row[0]) for row in rows]
    def delete(self,kind,ident):
        with self.connect() as db:db.execute('DELETE FROM records WHERE kind=? AND id=?',(kind,ident))
    def event(self,kind,value):
        with self.connect() as db:db.execute('INSERT INTO events(time,kind,value) VALUES(?,?,?)',(time.time(),kind,json.dumps(value)))
    def events(self,limit=100):
        with self.connect() as db:rows=db.execute('SELECT seq,time,kind,value FROM events ORDER BY seq DESC LIMIT ?',(min(limit,1000),)).fetchall()
        return [dict(seq=r[0],time=r[1],kind=r[2],value=json.loads(r[3])) for r in rows]
