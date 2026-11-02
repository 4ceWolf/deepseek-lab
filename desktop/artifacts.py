"""Validated visual specifications rendered as standalone SVG; no executable markup."""
import csv,io,json,math,textwrap,re
from html import escape

KINDS=('bar','line','donut','flowchart','table','drawing','interactive')
PALETTE=['#92baff','#62d4b1','#efbb70','#d2a4f5','#ef929e','#7ed5e8']

DEFAULT_STYLE=dict(background='#111820',text='#b4c4d8',title='#eff5ff',muted='#91a5bf',grid='#314052',surface='#1b2b3e',palette=PALETTE,match_labels=True,color_by='series')
STYLE_SCHEMA={'type':'object','properties':{**{k:{'type':'string','pattern':'^#[0-9a-fA-F]{6}$'} for k in ('background','text','title','muted','grid','surface')},'palette':{'type':'array','minItems':1,'maxItems':24,'items':{'type':'string','pattern':'^#[0-9a-fA-F]{6}$'}},'match_labels':{'type':'boolean'},'color_by':{'type':'string','enum':['series','category']}},'additionalProperties':False}

def color(value):
    if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value):raise ValueError('Colors must use #RRGGBB notation')
    return value.lower()
def appearance(value):
    if not isinstance(value,dict) or set(value)-set(DEFAULT_STYLE):raise ValueError('Unknown appearance setting')
    result={**DEFAULT_STYLE,**value}
    for key in ('background','text','title','muted','grid','surface'):result[key]=color(result[key])
    if not isinstance(result['palette'],list) or not 1<=len(result['palette'])<=24:raise ValueError('Choose 1–24 palette colors')
    result['palette']=[color(v) for v in result['palette']]
    if type(result['match_labels']) is not bool or result['color_by'] not in ('series','category'):raise ValueError('Invalid label matching or color grouping')
    return result

def text(value,maximum,name):
    if not isinstance(value,str) or len(value)>maximum:raise ValueError(name+' must be text up to '+str(maximum)+' characters')
    if any(ord(c)<32 and c not in '\n\t' for c in value):raise ValueError('Unsupported control character')
    return value
def number(value):
    if type(value) not in (int,float) or abs(value)>1e12 or not math.isfinite(value):raise ValueError('Chart values must be finite numbers between -1e12 and 1e12')
    return value
def validate(spec):
    if not isinstance(spec,dict) or len(json.dumps(spec,allow_nan=False).encode())>100000:raise ValueError('Artifact must be an object under 100 KB')
    kind=spec.get('kind')
    if kind not in KINDS:raise ValueError('Choose bar, line, donut, flowchart, table or drawing')
    result=dict(kind=kind,title=text(spec.get('title',''),120,'Title'),subtitle=text(spec.get('subtitle',''),240,'Subtitle'),source=text(spec.get('source','Model-provided data; not independently verified.'),600,'Source'))
    if not result['title'].strip():raise ValueError('Give the artifact a title')
    result['style']=appearance(spec.get('style',{}))
    if kind in ('bar','line','donut'):
        labels=spec.get('labels');series=spec.get('series')
        if not isinstance(labels,list) or not 1<=len(labels)<=24:raise ValueError('Charts need 1–24 labels')
        result['labels']=[text(v,100,'Label') for v in labels]
        if not isinstance(series,list) or not 1<=len(series)<=6:raise ValueError('Charts need 1–6 series')
        result['series']=[]
        for item in series:
            if not isinstance(item,dict) or not isinstance(item.get('values'),list) or len(item['values'])!=len(labels):raise ValueError('Each series must match the label count')
            result['series'].append(dict(name=text(item.get('name','Values'),100,'Series name'),values=[number(v) for v in item['values']]))
        result['unit']=text(spec.get('unit',''),50,'Unit')
        if kind=='donut':
            if len(series)!=1 or any(v<0 for v in result['series'][0]['values']) or sum(result['series'][0]['values'])<=0:raise ValueError('Donuts need one nonnegative series with a positive total')
    elif kind=='interactive':
        from . import interactive
        result.update(interactive.validate(spec))
    elif kind=='drawing':
        from . import drawing
        result.update(drawing.validate(spec))
    elif kind=='flowchart':
        nodes=spec.get('nodes');edges=spec.get('edges',[])
        if not isinstance(nodes,list) or not 1<=len(nodes)<=24 or not isinstance(edges,list) or len(edges)>60:raise ValueError('Flowcharts support 1–24 nodes and up to 60 edges')
        result['nodes']=[];ids=set()
        for node in nodes:
            if not isinstance(node,dict):raise ValueError('Nodes must be objects')
            ident=text(node.get('id',''),60,'Node ID')
            if not ident or ident in ids:raise ValueError('Node IDs must be unique and nonempty')
            ids.add(ident);result['nodes'].append(dict(id=ident,label=text(node.get('label',''),120,'Node label')))
        result['edges']=[]
        for edge in edges:
            if not isinstance(edge,dict) or not isinstance(edge.get('from'),str) or not isinstance(edge.get('to'),str):raise ValueError('Edges must name their source and target nodes')
            if edge.get('from') not in ids or edge.get('to') not in ids:raise ValueError('Edges must refer to existing nodes')
            result['edges'].append({'from':edge['from'],'to':edge['to'],'label':text(edge.get('label',''),80,'Edge label')})
    else:
        columns=spec.get('columns');rows=spec.get('rows')
        if not isinstance(columns,list) or not 1<=len(columns)<=10 or not isinstance(rows,list) or len(rows)>100:raise ValueError('Tables support 1–10 columns and up to 100 rows')
        result['columns']=[text(v,100,'Column') for v in columns];result['rows']=[]
        for row in rows:
            if not isinstance(row,list) or len(row)!=len(columns):raise ValueError('Table row length must match the columns')
            normalized=[]
            for cell in row:
                if cell is None:normalized.append('')
                elif isinstance(cell,str):normalized.append(text(cell,500,'Cell'))
                elif type(cell) in (int,float):normalized.append(str(number(cell)))
                elif type(cell) is bool:normalized.append(str(cell))
                else:raise ValueError('Table cells must be text, numbers, booleans or null')
            result['rows'].append(normalized)
    if result['style']['color_by']=='category' and (kind!='bar' or len(result['series'])!=1):raise ValueError('Category coloring requires a bar chart with one series')
    return result

def data_rows(spec):
    spec=validate(spec)
    if spec['kind'] in ('bar','line','donut'):
        return ['Label']+[s['name'] for s in spec['series']],[[label]+[s['values'][i] for s in spec['series']] for i,label in enumerate(spec['labels'])]
    if spec['kind']=='table':return spec['columns'],spec['rows']
    if spec['kind']=='interactive':return ['Control','Default'],[[c['label'],json.dumps({k:v for k,v in c.items() if k in ('value','x','y')})] for c in spec['controls']]
    if spec['kind']=='drawing':return ['Command','Arguments'],[[c[0],json.dumps(c[1:],ensure_ascii=False)] for c in spec['commands']]
    return ['Node ID','Label'],[[n['id'],n['label']] for n in spec['nodes']]

def csv_text(spec):
    columns,rows=data_rows(spec);stream=io.StringIO();writer=csv.writer(stream)
    # Spreadsheet exports must not treat model-supplied text as formulas.
    def safe(value):return "'"+value if isinstance(value,str) and value.startswith(('=','+','-','@','\t','\r')) else value
    writer.writerow([safe(v) for v in columns]);writer.writerows([[safe(v) for v in row] for row in rows]);return stream.getvalue()

def svg(spec):
    spec=validate(spec);kind=spec['kind']
    if kind=='interactive':
        from .interactive_html import static_svg
        return static_svg(spec)
    if kind=='drawing':
        from . import drawing
        return drawing.svg(spec)
    width=960;style=spec['style'];palette=style["palette"]
    def swatch(index):return palette[index%len(palette)]
    height=620 if kind not in ('table','flowchart') else max(430,190+len(spec.get('rows',[]))*42) if kind=='table' else 190+math.ceil(len(spec['nodes'])/3)*130
    titles=textwrap.wrap(spec['title'],62);offset=28*(len(titles)-1);height+=offset
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',f'<rect width="{width}" height="{height}" rx="18" fill="{style["background"]}" data-role="background"/>']
    def t(x,y,value,size=13,color=None,anchor='start',role='text',index=None):
        paint=style[role] if color is None else color
        if index is not None:paint=swatch(index) if style["match_labels"] else style["text"]
        attrs=f' data-color-index="{index}"' if index is not None else ''
        out.append(f'<text x="{x:.2f}" y="{y:.2f}" fill="{paint}" data-role="{role}"{attrs} font-family="sans-serif" font-size="{size}" text-anchor="{anchor}">{escape(str(value))}</text>')
    def line(x1,y1,x2,y2,color=None,extra=''):
        color=color or style["grid"]
        out.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" data-role="grid" data-paint="stroke" {extra}/>')
    out.append('<title>'+escape(spec['title'])+'</title><desc>'+escape(spec['source'])+'</desc>')
    for i,row in enumerate(titles):t(36,42+i*28,row,23,role='title')
    for i,row in enumerate(textwrap.wrap(spec['subtitle'],115)[:2]):t(36,67+offset+i*17,row)
    out.append(f'<g transform="translate(0 {offset})">')
    if kind in ('bar','line'):
        series=spec['series'];labels=spec['labels'];values=[v for s in series for v in s['values']]
        low=min(0,min(values));high=max(0,max(values))
        if high==low:high=low+1
        padding=(high-low)*.08
        if low<0:low-=padding
        if high>0:high+=padding
        x0,y0,w,h=90,135,820,330
        def yy(value):return y0+h-(value-low)/(high-low)*h
        for i in range(6):
            value=low+(high-low)*i/5;y=yy(value);line(x0,y,x0+w,y);t(x0-14,y+4,f'{value:,.3g}',12,anchor='end')
        line(x0,yy(0),x0+w,yy(0));t(x0,112,spec['unit'],12)
        step=w/len(labels)
        for i,name in enumerate(labels):
            short=name if len(name)<=16 else name[:15]+'…';t(x0+step*(i+.5),y0+h+26,short,11,anchor='middle',index=i if style['color_by']=='category' else None)
        for j,s in enumerate(series):
            color=swatch(j)
            if kind=='bar':
                bw=step*.72/len(series)
                for i,value in enumerate(s['values']):
                    index=i if style["color_by"]=='category' else j;color=swatch(index)
                    x=x0+step*i+step*.14+bw*j;y=min(yy(value),yy(0));bar_h=abs(yy(value)-yy(0))
                    out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(.5,bw-2):.2f}" height="{bar_h:.2f}" rx="2" fill="{color}" data-color-index="{index}"><title>{escape(labels[i])}: {value} {escape(spec["unit"])}</title></rect>')
                    if len(labels)*len(series)<=14:t(x+bw/2,yy(value)-8 if value>=0 else yy(value)+17,f'{value:,.4g}',12,anchor='middle',index=index)
            else:
                points=[(x0+step*(i+.5),yy(v)) for i,v in enumerate(s['values'])]
                out.append('<polyline points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="3" data-color-index="{j}" data-paint="stroke"/>')
                for x,y in points:out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}" data-color-index="{j}"/>')
            if style['color_by']=='series':
                col=j%3;row=j//3;x=90+col*280;y=535+row*23
                out.append(f'<rect x="{x}" y="{y-10}" width="12" height="12" rx="3" fill="{swatch(j)}" data-color-index="{j}"/>');t(x+21,y,s['name'][:33],12,index=j)
    elif kind=='donut':
        values=spec['series'][0]['values'];total=sum(values);angle=-math.pi/2;cx,cy,r=275,310,145
        for i,value in enumerate(values):
            sweep=value/total*2*math.pi;color=swatch(i)
            if value:
                # Split full circles into two arcs so a one-category donut renders.
                for part in range(2):
                    start=angle+sweep*part/2;end=start+sweep/2
                    x1,y1=cx+r*math.cos(start),cy+r*math.sin(start);x2,y2=cx+r*math.cos(end),cy+r*math.sin(end)
                    out.append(f'<path d="M {cx} {cy} L {x1:.3f} {y1:.3f} A {r} {r} 0 0 1 {x2:.3f} {y2:.3f} Z" fill="{color}" data-color-index="{i}"/>')
            angle+=sweep
        out.append(f'<circle cx="{cx}" cy="{cy}" r="100" fill="{style["background"]}" data-role="background"/>');t(cx,cy-6,f'{total:,.5g}',32,anchor='middle',role='title');t(cx,cy+24,spec['unit'] or 'Total',13,anchor='middle')
        for i,(name,value) in enumerate(zip(spec['labels'],values)):
            y=140+i*17
            out.append(f'<rect x="510" y="{y-9}" width="10" height="10" rx="2" fill="{swatch(i)}" data-color-index="{i}"/>');t(532,y,name[:32],12,index=i);t(905,y,f'{value/total:.1%}',12,anchor='end',index=i)
    elif kind=='table':
        columns=spec['columns'];cw=888/len(columns)
        out.append(f'<rect x="36" y="102" width="888" height="40" rx="6" fill="{style["surface"]}" data-role="surface"/>')
        for i,col in enumerate(columns):t(46+i*cw,127,col[:max(6,int(cw/7))],12,role='title')
        for j,row in enumerate(spec['rows']):
            y=148+j*42
            if j%2==0:out.append(f'<rect x="36" y="{y-4}" width="888" height="40" fill="{style["surface"]}" data-role="surface"/>')
            for i,value in enumerate(row):
                limit=max(6,int(cw/7));short=value if len(value)<=limit else value[:limit-1]+'…';t(46+i*cw,y+20,short,12)
    else:
        nodes=spec['nodes'];positions={n['id']:(45+(i%3)*305,105+(i//3)*130) for i,n in enumerate(nodes)}
        out.append(f'<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="{style["grid"]}" data-role="grid"/></marker></defs>')
        for edge in spec['edges']:
            x,y=positions[edge['from']];xx,yy_=positions[edge['to']]
            if y==yy_:
                a,b=(x+260,y+40) if xx>x else (x,y+40);c,d=(xx,yy_+40) if xx>x else (xx+260,yy_+40)
            else:a,b=x+130,y+80;c,d=xx+130,yy_
            if edge['from']==edge['to']:
                out.append(f'<path d="M{x+210} {y} C{x+210} {y-35} {x+280} {y-35} {x+260} {y+20}" fill="none" stroke="{style["grid"]}" data-role="grid" data-paint="stroke" marker-end="url(#arrow)"/>')
            else:line(a,b,c,d,style["grid"],'stroke-width="2" marker-end="url(#arrow)"')
            if edge['label']:t((a+c)/2,(b+d)/2-7,edge['label'][:30],11,anchor='middle')
        for i,node in enumerate(nodes):
            x,y=positions[node['id']];out.append(f'<rect x="{x}" y="{y}" width="260" height="80" rx="12" fill="{style["surface"]}" data-role="surface" stroke="{swatch(i)}" data-stroke-index="{i}"/>')
            for j,row in enumerate(textwrap.wrap(node['label'],29)[:3]):t(x+130,y+25+j*18,row,13,anchor='middle',index=i)
    out.append('</g>')
    source_lines=textwrap.wrap('Source: '+spec['source'],125)
    for i,row in enumerate(source_lines[:2]):t(36,height-32+i*16,row+('…' if i==1 and len(source_lines)>2 else ''),11,role='muted')
    out.append('</svg>');return '\n'.join(out)
