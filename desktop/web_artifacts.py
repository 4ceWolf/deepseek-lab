"""Website chat visuals: validated fenced specs, native preview/export, never executable model markup."""
import hashlib,json,re,time
from . import artifacts,drawing
HINT='''For a useful chart, table or diagram, you may include a fenced block labelled deepseek-artifact containing JSON. Supported shapes: {"kind":"bar" or "line" or "donut","title":"...","source":"...","labels":["..."],"series":[{"name":"...","values":[1]}]}; {"kind":"table","title":"...","source":"...","columns":["..."],"rows":[["..."]]}; {"kind":"flowchart","title":"...","source":"...","nodes":[{"id":"a","label":"..."}],"edges":[{"from":"a","to":"a","label":"..."}]}. Use real data with sources, or label examples illustrative. No HTML or scripts. Ordinary answers need no artifact.'''
def capture(core,sid,messages):
    for m in messages:
        if m['role']!='assistant':continue
        content=m.get('content','');blocks=re.findall(r'```(deepseek-visual|deepseek-artifact|deepseek-draw|json)\s*\n(.*?)```',content,re.S)
        if not blocks and content.lstrip().startswith('{'):
            try:
                if json.loads(content).get('kind')=='interactive':blocks=[('deepseek-visual',content.strip())]
            except (ValueError,AttributeError):pass
        if not blocks and content.lstrip().startswith('canvas '):blocks=[('deepseek-draw',content.strip())]
        for language,text in blocks[:8]:
            if len(text.encode())>100000:continue
            if language=='json':
                try:
                    if json.loads(text).get('kind')!='interactive':continue
                except (ValueError,AttributeError):continue
            ident=hashlib.sha256((sid+'\0'+text).encode()).hexdigest()[:32]
            try:core.store.get('web_artifact',ident);continue
            except ValueError:pass
            try:spec=drawing.parse(core.redact(text)) if language=='deepseek-draw' else artifacts.validate(core.redact(json.loads(text)))
            except (ValueError,TypeError,KeyError):continue
            core.store.put('web_artifact',dict(session=sid,spec=spec,svg=artifacts.svg(spec),revision=1,created=time.time(),updated=time.time()),ident)
