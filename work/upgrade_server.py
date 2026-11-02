from pathlib import Path
p=Path('server.py');s=p.read_text().replace('import json, os, sqlite3, threading, time, uuid, urllib.request, urllib.error','import json, os, sqlite3, threading, time, uuid, urllib.request, urllib.error, runpy')
s=s.replace("DEFAULT = 'Be clear", "DEFAULT = 'Be clear")
s=s.replace('def connect_db():',"def engine():\n    return runpy.run_path(str(ROOT/'engine.py'))\n\ndef connect_db():")
start=s.index("        effort = data.get('effort','low')")
end=s.index("        payload = {'model':model",start)
s=s[:start]+'''        demo = bool(data.get('demo',False))
        if sid.startswith('recovered_'): raise ValueError('Recovered records are historical and incomplete; start a new conversation.')
        if any(m.get('demo') != demo for m in session['messages'] if m['role'] == 'assistant'):
            raise ValueError('Start a new conversation when switching between Demo and live mode')
        if not demo and not KEY: raise ValueError('Connect your API key first, or select Demo')
        module = engine()
        prepared = module['prepare'](data,session['messages'])
        decision = prepared['decision']
        effort,cap = decision['effort'],decision['max_tokens']
        messages = prepared['messages']
''' + s[end:]
s=s.replace("event(sid,'request',{'run_id':rid,'demo':demo,'request':payload})", "event(sid,'route',{'run_id':rid,'decision':decision})\n        event(sid,'request',{'run_id':rid,'demo':demo,'request':payload})")
s=s.replace("event(sid,'response',{'run_id':rid,'demo':demo,'elapsed_seconds':elapsed,'response':response})", "event(sid,'response',{'run_id':rid,'demo':demo,'elapsed_seconds':elapsed,'response':response})\n            validation = module['validate'](message['content'],data.get('output_check','none'))\n            event(sid,'validation',{'run_id':rid,'result':validation})")
s=s.replace("'usage':response.get('usage',{}),'finish_reason':choice.get('finish_reason')", "'usage':response.get('usage',{}),'finish_reason':choice.get('finish_reason'),'decision':decision,'validation':validation")
s=s.replace("'defaults':DEFAULT", "'defaults':engine()['INSTRUCTIONS'],'version':engine()['VERSION'],'knowledge_count':len(engine()['cards']()),'data_directory':str(DATA)")
s=s.replace("if path == '/api/export':", "if path == '/api/knowledge': return self.reply(200,{'cards':engine()['cards'](),'manifest':json.loads((ROOT/'knowledge/manifest.json').read_text())})\n            if path == '/api/export':")
s=s.replace("if self.path == '/api/run':", "if self.path == '/api/preview':\n                history=get_session(data['session_id'])['messages'] if data.get('session_id') else []\n                return self.reply(200,engine()['prepare'](data,history))\n            if self.path == '/api/run':")
s=s.replace("with LOCK: KEY = key", "with LOCK:\n                    if BUSY: raise ValueError('Wait for active runs before changing the key')\n                    KEY = key")
s=s.replace("if size > 2_000_000:","if size < 0 or size > 2_000_000:")
p.write_text(s)
