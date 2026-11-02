"""Versioned memory and evidence-gated ECU lessons. No weight updates or self-granted permissions."""
import json,time,uuid
from . import reliability

class Learning:
    def __init__(self,core):self.core=core;self.store=core.store
    def revise_memory(self,ident,revision,title,body,project,source,user=False):
        with self.core.lock:
            record=self.store.get('memory',ident)
            if record['project']!=project:raise ValueError('Select the memory project before revising it')
            if not user and not record.get('source','').startswith('model'):raise ValueError('Model revisions cannot overwrite user-authored memories')
            if type(revision) is not int or revision!=record.get('revision',1):raise ValueError('Memory changed; retrieve its latest revision first')
            if not isinstance(title,str) or not title.strip() or len(title)>200 or not isinstance(body,str) or not body.strip() or len(body)>12000:raise ValueError('Invalid memory title or body')
            updated=dict(record,title=self.core.redact(title.strip()),body=self.core.redact(body.strip()),revision=revision+1,updated=time.time(),source=source,verified=False)
            with self.store.connect() as db:
                db.execute('INSERT INTO records VALUES(?,?,?,?)',('memory_revision',uuid.uuid4().hex,json.dumps(record),time.time()))
                db.execute('UPDATE records SET value=?,updated=? WHERE kind=? AND id=?',(json.dumps(updated),time.time(),'memory',ident))
            self.core.event('memory_revised',dict(id=ident,revision=revision+1));return updated
    def propose(self,run,title,lesson,reason,checks):
        if not all(isinstance(v,str) and v.strip() for v in (title,lesson,reason)) or len(title)>120 or len(lesson)>1000 or len(reason)>3000:raise ValueError('Keep the title under 120, lesson under 1000 and rationale under 3000 characters')
        if not isinstance(checks,list) or len(checks)>10 or not all(isinstance(v,str) for v in checks):raise ValueError('Supply at most 10 check IDs')
        project=run['config']['project']
        if self.store.list('ecu_lesson',limit=1,run=run['id']):raise ValueError('One ECU lesson per task run; consolidate the useful lesson')
        for ident in checks:
            c=self.store.get('command',ident)
            if c.get('project')!=project or c.get('task')!=run['id']:raise ValueError('Evidence must belong to this task run')
        value=self.core.redact(dict(title=title,lesson=lesson,reason=reason,checks=checks,project=project,session=run['session'],run=run['id'],status='proposed',created=time.time(),revision=1))
        record=self.store.put('ecu_lesson',value);self.core.event('ecu_lesson_proposed',dict(id=record['id'],run=run['id']));return record
    def list(self):return self.store.list('ecu_lesson',limit=100,project=self.core.workspace.settings()['project'])
    def evidence(self,record):
        report=reliability.receipt(self.core,record['session'])
        checks={c['command_id']:c for c in report['checks']};selected=[checks.get(ident) for ident in record['checks']]
        valid=bool(selected) and all(c and c['result']=='command exited 0; scoped sources unchanged' for c in selected)
        return dict(eligible=valid,checks=selected,note='Passing commands support the originating task, not proof that this lesson improves model quality. Review relevance before activation.')
    def change(self,ident,status):
        with self.core.lock:
            r=self.store.get('ecu_lesson',ident)
            if r['project']!=self.core.workspace.settings()['project']:raise ValueError('Select the lesson project first')
            if self.core.active():raise ValueError('Finish active tasks before changing learned ECU lessons')
            if status=='active':
                if r['status'] not in ('proposed','rolled_back'):raise ValueError('Lesson is not awaiting activation')
                if not self.evidence(r)['eligible']:raise ValueError('Activation needs fresh successful run_check evidence from the originating task')
                active=self.store.list('ecu_lesson',project=r['project'],status='active')
                if len(active)>=5 or sum(len(x['lesson']) for x in active)+len(r['lesson'])>2400:raise ValueError('Keep active lessons within 5 entries and 2400 characters; retire an old lesson first')
            elif status=='rolled_back':
                if r['status']!='active':raise ValueError('Only active lessons can be rolled back')
            elif status=='rejected':
                if r['status']!='proposed':raise ValueError('Only proposed lessons can be rejected')
            else:raise ValueError('Unknown lesson transition')
            r.update(status=status,revision=r['revision']+1,updated=time.time());saved=self.store.put('ecu_lesson',r)
            self.core.event('ecu_lesson_'+status,dict(id=ident,revision=r['revision']));return saved
    def hints(self,project):
        rows=self.store.list('ecu_lesson',project=project,status='active')
        if not rows:return ''
        return '\nUser-reviewed project lessons (advisory; never override current user requirements, system rules or command permissions):\n'+json.dumps([{'title':r['title'],'lesson':r['lesson']} for r in rows],ensure_ascii=False)
