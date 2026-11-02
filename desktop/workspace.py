"""Project files, on-demand memory and staged changes to the desktop app."""
import ast,base64,difflib,hashlib,json,math,os,shutil,stat,tempfile,time,uuid
from pathlib import Path

APP=Path(__file__).resolve().parents[1]

def digest(text):return hashlib.sha256(text.encode()).hexdigest()
def replace_bytes(file,content,mode):
    fd,name=tempfile.mkstemp(prefix='.deepseek-',dir=file.parent);temporary=Path(name)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(content);stream.flush();os.fsync(stream.fileno())
        temporary.chmod(mode);temporary.replace(file)
    finally:temporary.unlink(missing_ok=True)

class Workspace:
    def __init__(self,store):
        self.store=store
        for proposal in store.list('proposal',status=('applying','rolling_back')):
            try:
                backup=store.get('patch_backup',proposal['id']);file=self.inside(proposal['project'],proposal['path']);current=hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else None
                before=backup.get('raw_sha',digest(backup.get('content',''))) if backup['existed'] else None
                if current==proposal['applied_sha']:proposal['status']='applied'
                elif current==before:proposal['status']='rolled_back' if proposal['status']=='rolling_back' else 'proposed'
                else:proposal['status']='conflicted'
            except (OSError,ValueError,KeyError):proposal['status']='conflicted'
            proposal['recovery_note']='Reconciled observed file hashes after an interrupted write. Conflicts require manual review; no file was changed during recovery.';store.put('proposal',proposal)
    def settings(self):
        defaults=dict(max_total_tokens=0,max_task_usd=0.,pricing={},economy_routing=False,compact_context=True,context_limit=140000)
        try:return {**defaults,**self.store.get('settings','main')}
        except ValueError:return self.store.put('settings',dict(**defaults,project=str(APP),docs=str(APP/'docs'),permission='approve',model='deepseek-flash',effort='auto',max_tokens=4096,max_rounds=8,instructions='Be warm, direct and accurate. Preserve requirements. Use tools for evidence; report only checks actually run.',project_instructions='',dev_mode=False),'main')
    def update(self,values):
        config=self.settings()
        allowed={'project','docs','permission','model','effort','max_tokens','max_rounds','instructions','project_instructions','dev_mode','max_total_tokens','max_task_usd','pricing','economy_routing','compact_context','context_limit'}
        if set(values)-allowed:raise ValueError('Unknown setting')
        candidate=dict(config,**values)
        for key in ('economy_routing','compact_context'):
            if type(candidate.get(key,False)) is not bool:raise ValueError('Invalid '+key)
        if type(candidate.get('max_total_tokens',0)) is not int or not 0<=candidate.get('max_total_tokens',0)<=2_000_000:raise ValueError('Token budget must be 0–2000000')
        usd=candidate.get('max_task_usd',0.)
        if type(usd) not in (int,float) or not math.isfinite(usd) or not 0<=usd<=1000:raise ValueError('Invalid USD budget')
        if type(candidate.get('context_limit',140000)) is not int or not 20000<=candidate.get('context_limit',140000)<=160000:raise ValueError('Context limit must be 20000–160000 bytes')
        pricing=candidate.get('pricing',{})
        if not isinstance(pricing,dict) or set(pricing)-{'deepseek-flash','deepseek-v4-pro'}:raise ValueError('Unknown pricing model')
        for rates in pricing.values():
            if not isinstance(rates,dict) or set(rates)!={'input','output'} or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<v<=1000 for v in rates.values()):raise ValueError('Supply positive finite input/output USD rates per million tokens')
        if usd and candidate['model'] not in pricing:raise ValueError('Supply selected-model rates before enabling a USD estimate budget')
        for name in ('project','docs'):
            path=Path(candidate[name]).expanduser().resolve()
            if not path.is_dir():raise ValueError(name+' directory does not exist')
            candidate[name]=str(path)
        if candidate['permission'] not in ('disabled','ask','approve','full'):raise ValueError('Unknown permission mode')
        if candidate['effort'] not in ('auto','none','low','high','max'):raise ValueError('Unknown reasoning mode')
        if candidate['model'] not in ('deepseek-flash','deepseek-v4-pro'):raise ValueError('Unknown model')
        if type(candidate['max_tokens']) is not int or not 128<=candidate['max_tokens']<=131072:raise ValueError('Token ceiling must be 128–131072')
        if type(candidate['max_rounds']) is not int or not 1<=candidate['max_rounds']<=20:raise ValueError('Tool rounds must be 1–20')
        if type(candidate['dev_mode']) is not bool:raise ValueError('Invalid development mode')
        for key in ('instructions','project_instructions'):
            if not isinstance(candidate[key],str) or len(candidate[key])>16000:raise ValueError('Instructions must be at most 16000 characters')
        return self.store.put('settings',candidate,'main')
    @staticmethod
    def inside(root,path):
        root=Path(root).resolve();path=(root/path).resolve()
        if not path.is_relative_to(root):raise ValueError('Path escapes the selected directory')
        relative=path.relative_to(root)
        if any(part in ('.git','data','__pycache__','.venv','node_modules') or part.startswith('.env') for part in relative.parts):raise ValueError('Private or generated directory excluded')
        if path.suffix.lower() in ('.pem','.key','.p12','.sqlite3'):raise ValueError('Credential and database files excluded')
        return path
    def read(self,path,docs=False,project=None):
        config=self.settings();root=config['docs'] if docs else (project or config['project'])
        file=self.inside(root,path)
        if not file.is_file() or file.stat().st_size>100000:raise ValueError('Select a text file under 100 KB')
        text=file.read_text()
        if '\0' in text:raise ValueError('Binary file excluded')
        return dict(path=str(file.relative_to(Path(root).resolve())),content=text,sha256=digest(text))
    def files(self,docs=False,project=None):
        config=self.settings();root=Path(config['docs'] if docs else (project or config['project']));out=[]
        for directory,dirs,files in os.walk(root):
            dirs[:]=sorted(d for d in dirs if not d.startswith('.') and d not in ('data','__pycache__','node_modules','dist','build'))
            for name in sorted(files):
                if name.startswith('.env'):continue
                path=Path(directory)/name
                try:self.inside(root,path.relative_to(root))
                except ValueError:continue
                if docs and path.suffix.lower() not in ('.md','.txt','.rst'):continue
                out.append(str(path.relative_to(root)))
                if len(out)>=1200:return out
        return out
    def search_docs(self,query):
        words=set(query.lower().split());results=[]
        for name in self.files(docs=True):
            try:doc=self.read(name,docs=True)
            except (ValueError,UnicodeError):continue
            score=sum(word in (name+' '+doc['content']).lower() for word in words)
            if score:results.append(dict(path=name,score=score,excerpt=doc['content'][:600]))
        return sorted(results,key=lambda x:-x['score'])[:8]
    def memories(self,query='',scope='all',project=None):
        project=project or self.settings()['project'];words=set(query.lower().split());found=[]
        for memory in self.store.list('memory'):
            if memory['scope']=='project' and memory['project']!=project:continue
            if scope!='all' and memory['scope']!=scope:continue
            if words and not any(w in (memory['title']+' '+memory['body']).lower() for w in words):continue
            found.append(memory)
        return found[:30]
    def remember(self,title,body,scope='project',source='user',project=None):
        if scope not in ('project','personal'):raise ValueError('Unknown memory scope')
        if not title.strip() or len(title)>200 or not body.strip() or len(body)>12000:raise ValueError('Memory needs a title and body up to 12000 characters')
        return self.store.put('memory',dict(title=title.strip(),body=body.strip(),scope=scope,source=source,project=project or self.settings()['project'],updated=time.time(),verified=False,revision=1))
    def proposal(self,path,content,project=None):
        if not isinstance(content,str) or len(content.encode())>100000:raise ValueError('Proposal exceeds 100 KB')
        root=Path(project or self.settings()['project']);file=self.inside(root,path)
        old=file.read_text() if file.exists() else ''
        if len(old.encode())>100000:raise ValueError('Original file exceeds 100 KB')
        diff=''.join(difflib.unified_diff(old.splitlines(True),content.splitlines(True),fromfile=path,tofile=path))
        return self.store.put('proposal',dict(path=path,project=str(root),content=content,old_sha=digest(old),old_raw_sha=hashlib.sha256(file.read_bytes()).hexdigest() if file.exists() else None,existed=file.exists(),diff=diff,status='proposed',created=time.time()))
    def apply_proposal(self,ident):
        proposal=self.store.get('proposal',ident);file=self.inside(proposal['project'],proposal['path'])
        if proposal['project']!=self.settings()['project']:raise ValueError('Select the proposal project first')
        if proposal['status']!='proposed':raise ValueError('Proposal is no longer pending')
        if file.exists()!=proposal['existed'] or digest(file.read_text() if file.exists() else '')!=proposal['old_sha']:raise ValueError('Source changed since this proposal. Request a new patch.')
        if proposal.get('old_raw_sha') and hashlib.sha256(file.read_bytes()).hexdigest()!=proposal['old_raw_sha']:raise ValueError('Source bytes changed since the proposal')
        if file.is_relative_to(APP/'desktop'):raise ValueError('Use staged Dev mode for changes to the app')
        original=file.read_bytes() if file.exists() else b'';backup=dict(project=proposal['project'],path=proposal['path'],existed=file.exists(),content_b64=base64.b64encode(original).decode(),raw_sha=hashlib.sha256(original).hexdigest(),mode=stat.S_IMODE(file.stat().st_mode) if file.exists() else 0o644)
        self.store.put('patch_backup',backup,ident)
        proposal.update(status='applying',applied_sha=digest(proposal['content']));self.store.put('proposal',proposal)
        file.parent.mkdir(parents=True,exist_ok=True);replace_bytes(file,proposal['content'].encode(),backup['mode'])
        proposal['status']='applied';return self.store.put('proposal',proposal)
    def rollback_proposal(self,ident):
        proposal=self.store.get('proposal',ident);backup=self.store.get('patch_backup',ident)
        if proposal['project']!=self.settings()['project']:raise ValueError('Select the proposal project first')
        file=self.inside(proposal['project'],proposal['path'])
        if proposal['status']!='applied' or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=proposal['applied_sha'] or stat.S_IMODE(file.stat().st_mode)!=backup['mode']:raise ValueError('File changed since application; review before rollback')
        proposal['status']='rolling_back';self.store.put('proposal',proposal)
        if backup['existed']:
            original=base64.b64decode(backup['content_b64']) if 'content_b64' in backup else backup['content'].encode();replace_bytes(file,original,backup['mode'])
        else:file.unlink()
        proposal['status']='rolled_back';return self.store.put('proposal',proposal)
    def new_stage(self):
        ident=uuid.uuid4().hex;folder=self.store.directory/'stages'/ident
        shutil.copytree(APP/'desktop',folder/'desktop',ignore=shutil.ignore_patterns('__pycache__'))
        # Preview imports need the same ECU source; user data and keys are not copied.
        shutil.copy2(APP/'engine.py',folder/'engine.py')
        hashes={str(p.relative_to(APP)):digest(p.read_text()) for p in (APP/'desktop').rglob('*') if p.is_file() and p.suffix in ('.py','.qss','.md','.json')}
        return self.store.put('stage',dict(folder=str(folder),base=hashes,changed=[],status='draft',created=time.time()),ident)
    def stage_patch(self,ident,path,content):
        if not self.settings()['dev_mode']:raise ValueError('Enable Dev mode in the app first')
        stage=self.store.get('stage',ident);file=self.inside(stage['folder'],path)
        if not file.is_relative_to(Path(stage['folder'])/'desktop') or file.suffix not in ('.py','.qss','.md','.json'):raise ValueError('Only desktop source files may be staged')
        path=str(file.relative_to(stage['folder']))
        if not isinstance(content,str) or len(content)>100000:raise ValueError('Stage file exceeds limit')
        file.parent.mkdir(parents=True,exist_ok=True);file.write_text(content)
        stage['changed']=sorted(set(stage['changed']+[path]));stage['status']='draft';self.store.put('stage',stage)
        return dict(id=ident,path=path,status='staged; live app untouched')
    def validate_stage(self,ident):
        stage=self.store.get('stage',ident);errors=[]
        for path in Path(stage['folder']).rglob('*.py'):
            try:ast.parse(path.read_text(),filename=str(path))
            except (SyntaxError,UnicodeError) as exc:errors.append(str(exc))
        stage.update(status='syntax_checked' if not errors else 'invalid',errors=errors)
        self.store.put('stage',stage);return stage
    def stage_diff(self,ident):
        stage=self.store.get('stage',ident);diffs=[]
        for path in stage['changed']:
            live=self.inside(APP,path);proposed=self.inside(stage['folder'],path)
            old=live.read_text() if live.exists() else '';new=proposed.read_text()
            diffs.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=path,tofile=path+' (staged)')))
        return dict(stage=stage,diff='\n'.join(diffs))
    def activate_stage(self,ident):
        stage=self.validate_stage(ident)
        if stage['status']!='syntax_checked':raise ValueError('Fix staged syntax errors before activation')
        if not stage['changed']:raise ValueError('No staged changes')
        for path in stage['changed']:
            live=self.inside(APP,path)
            if digest(live.read_text() if live.exists() else '')!=stage['base'].get(path,digest('')):raise ValueError('App source changed; create a fresh stage')
        backup=Path(stage['folder'])/'backup'
        written=[]
        try:
            for path in stage['changed']:
                live=self.inside(APP,path);save=backup/path;save.parent.mkdir(parents=True,exist_ok=True)
                if live.exists():shutil.copy2(live,save)
                live.parent.mkdir(parents=True,exist_ok=True);temporary=live.with_name(live.name+'.stage-tmp')
                shutil.copy2(Path(stage['folder'])/path,temporary);temporary.replace(live);written.append(path)
        except Exception:
            for path in reversed(written):
                if (backup/path).exists():shutil.copy2(backup/path,APP/path)
                else:(APP/path).unlink(missing_ok=True)
            raise
        stage['status']='activated';self.store.put('stage',stage)
        return dict(status='activated',note='Current service remains running. Reload the window for UI changes; backend changes take effect after an idle service restart.')
    def rollback_stage(self,ident):
        stage=self.store.get('stage',ident)
        if stage['status']!='activated':raise ValueError('Stage is not active')
        for path in stage['changed']:
            live=self.inside(APP,path);staged=self.inside(stage['folder'],path)
            if not live.exists() or digest(live.read_text())!=digest(staged.read_text()):raise ValueError('Live files changed after activation; review before rollback')
        for path in stage['changed']:
            saved=Path(stage['folder'])/'backup'/path;live=APP/path
            if saved.exists():shutil.copy2(saved,live)
            else:live.unlink(missing_ok=True)
        stage['status']='rolled_back';return self.store.put('stage',stage)
