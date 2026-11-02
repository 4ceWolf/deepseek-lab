"""Display-only disclosures. Expanding never changes inference effort or executes tools."""
import json,re
from . import artifacts,drawing

def render(messages,thinking=(),activity=(),show_all=False,visuals=False,records=None):
    parts=[];results={m.get('tool_call_id'):m for m in messages if m['role']=='tool'}
    for index,m in enumerate(messages):
        if m['role']=='tool':continue
        content=m.get('content') or ''
        if m['role']=='assistant' and content.lstrip().startswith('{'):
            try:
                if json.loads(content).get('kind')=='interactive':content='```deepseek-visual\n'+content+'\n```'
            except (ValueError,AttributeError):pass
        if visuals and m['role']=='assistant':
            if content.lstrip().startswith('canvas '):
                try:drawing.parse(content);content='[Open visual artifact](app-artifacts:'+str(index)+')'
                except ValueError:pass
            def visual(match):
                try:drawing.parse(match.group(2)) if match.group(1)=='deepseek-draw' else artifacts.validate(json.loads(match.group(2)))
                except (ValueError,TypeError,KeyError) as exc:return match.group(0)+'\n\nDrawing/visual could not be rendered: '+str(exc)[:180]
                return '[Open visual artifact](app-artifacts:'+str(index)+')'
            content=re.sub(r'```(deepseek-artifact|deepseek-draw)\s*\n(.*?)```',visual,content,flags=re.S)
        parts += ['### '+('You' if m['role']=='user' else 'DeepSeek'),content]
        thought=m.get('reasoning_content') or m.get('reasoning') or ''
        if thought:
            expanded=index in thinking
            parts += [f'[{"▾" if expanded else "▸"} Thinking](app-thinking:{index})']
            if expanded:parts += ['```text\n'+thought[:60000].replace('```','｀｀｀')+'\n```']
        calls=m.get('tool_calls',[])
        if records:
            for call in calls:
                try:
                    ident=json.loads(results[call['id']]['content']).get('id');record=records.get(ident)
                    if record:parts+=['```deepseek-visual\n'+json.dumps(record['spec'],ensure_ascii=False)+'\n```']
                except (ValueError,TypeError,KeyError):pass
        if calls:
            expanded=show_all or index in activity
            names=', '.join(c['function']['name'] for c in calls)
            parts += [f'[{"▾" if expanded else "▸"} Activity · Work · {names}](app-activity:{index})']
            if expanded:
                for c in calls:
                    parts += ['**'+c['function']['name']+'**','```json\n'+c['function']['arguments'][:16000].replace('```','｀｀｀')+'\n```']
                    r=results.get(c['id'])
                    if r:
                        try:text=json.dumps(json.loads(r['content']),indent=2,ensure_ascii=False)
                        except ValueError:text=r['content']
                        parts += ['```text\n'+text[:16000].replace('```','｀｀｀')+'\n```']
    return '\n\n'.join(parts)
