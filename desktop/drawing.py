"""Small declarative drawing language, parsed as data and rendered to SVG."""
import json,math,re,shlex,textwrap
from html import escape

HINT='''This app interprets your visual output, so you CAN draw using text commands. Put a complete drawing in a fenced block labelled deepseek-draw. Commands (one per line; quote text with double quotes): canvas WIDTH HEIGHT; title "TITLE"; source "SOURCE"; rect X Y WIDTH HEIGHT FILL STROKE RADIUS; circle CX CY R FILL STROKE; line X1 Y1 X2 Y2 COLOR WIDTH; arrow X1 Y1 X2 Y2 COLOR WIDTH; text X Y SIZE COLOR "TEXT". Colors: #RRGGBB, none, background, surface, text, title, muted, grid, p0..p5 (palette). Example:\ncanvas 800 320\ntitle "Example workflow"\nsource "Illustrative diagram"\nrect 40 100 240 100 surface p0 12\ntext 70 155 22 p0 "Input"\narrow 290 150 500 150 p1 3\nrect 520 100 240 100 surface p1 12\ntext 550 155 22 p1 "Output"\nUse existing chart/table artifacts for numeric data. Draw only when useful.'''
FORMATS={'rect':7,'circle':5,'line':6,'arrow':6,'text':5}
COLORS={'none','background','surface','text','title','muted','grid',*[f'p{i}' for i in range(6)]}
def paint(value):
    if not isinstance(value,str) or (value not in COLORS and not re.fullmatch(r'#[0-9a-fA-F]{6}',value)):raise ValueError('Use #RRGGBB or a supported color token')
    return value

def finite(value,low,high):
    if type(value) not in (int,float) or not low<=value<=high or not math.isfinite(value):raise ValueError(f'Drawing number must be between {low} and {high}')
    return value

def validate(spec):
    width=finite(spec.get('width',800),200,2400);height=finite(spec.get('height',400),100,2400)
    commands=spec.get('commands')
    if not isinstance(commands,list) or not 1<=len(commands)<=80:raise ValueError('Drawings need 1–80 commands')
    out=[]
    for cmd in commands:
        if not isinstance(cmd,list) or not cmd or not isinstance(cmd[0],str) or cmd[0] not in FORMATS or len(cmd)!=FORMATS[cmd[0]]+1:raise ValueError('Invalid drawing command or argument count')
        kind=cmd[0];args=cmd[1:]
        if kind=='rect':
            x,y,w,h=finite(args[0],0,width),finite(args[1],0,height),finite(args[2],1,width),finite(args[3],1,height)
            if x+w>width or y+h>height:raise ValueError('Rectangle is outside the canvas')
            out.append([kind,x,y,w,h,paint(args[4]),paint(args[5]),finite(args[6],0,min(w,h)/2)])
        elif kind=='circle':
            x,y,r=finite(args[0],0,width),finite(args[1],0,height),finite(args[2],1,min(width,height)/2)
            if x-r<0 or y-r<0 or x+r>width or y+r>height:raise ValueError('Circle is outside the canvas')
            out.append([kind,x,y,r,paint(args[3]),paint(args[4])])
        elif kind in ('line','arrow'):
            x1,y1,x2,y2=finite(args[0],0,width),finite(args[1],0,height),finite(args[2],0,width),finite(args[3],0,height)
            if kind=='arrow' and x1==x2 and y1==y2:raise ValueError('An arrow needs two distinct points')
            out.append([kind,x1,y1,x2,y2,paint(args[4]),finite(args[5],1,20)])
        else:
            x,y,size=finite(args[0],0,width),finite(args[1],0,height),finite(args[2],8,72)
            text=args[4]
            if not isinstance(text,str) or not text or len(text)>500 or any(ord(c)<32 and c not in '\n\t' for c in text):raise ValueError('Drawing text must be 1–500 characters')
            out.append([kind,x,y,size,paint(args[3]),text])
    return dict(width=width,height=height,commands=out)

def parse(program):
    if not isinstance(program,str) or len(program.encode())>30000:raise ValueError('Drawing program must be at most 30 KB')
    spec=dict(kind='drawing',title='Drawing',source='Model-provided drawing; not independently verified',width=800,height=400,commands=[])
    for line_no,line in enumerate(program.splitlines(),1):
        if not line.strip() or line.lstrip().startswith('//'):continue
        try:
            words=shlex.split(line,comments=False)
            op=words[0];a=words[1:]
            if op=='canvas' and len(a)==2:spec.update(width=float(a[0]),height=float(a[1]))
            elif op in ('title','source') and len(a)==1:spec[op]=a[0]
            elif op in FORMATS:
                if len(a)!=FORMATS[op]:raise ValueError('Wrong number of arguments')
                counts={'rect':4,'circle':3,'line':4,'arrow':4,'text':3};n=counts[op]
                args=[float(v) for v in a[:n]]+a[n:]
                if op in ('rect','line','arrow'):args[-1]=float(args[-1])
                spec['commands'].append([op]+args)
            else:raise ValueError('Unsupported command')
        except (ValueError,IndexError) as exc:raise ValueError(f'Drawing line {line_no}: {exc}') from None
    from . import artifacts
    return artifacts.validate(spec)

def svg(spec):
    w,h=spec['width'],spec['height'];style=spec['style'];titles=textwrap.wrap(spec['title'],max(12,int(w/15)));top=40+len(titles)*28;bottom=80
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h+top+bottom}" viewBox="0 0 {w} {h+top+bottom}">',f'<rect width="{w}" height="{h+top+bottom}" fill="{style["background"]}" data-role="background"/>','<title>'+escape(spec['title'])+'</title><desc>'+escape(spec['source'])+'</desc>']
    def color(value,attribute='fill'):
        if value in style and isinstance(style[value],str):return f'{attribute}="{style[value]}" '+(f'data-role="{value}"' if attribute=='fill' else f'data-stroke-role="{value}"')
        if value.startswith('p') and value[1:].isdigit():
            i=int(value[1:]);return f'{attribute}="{style["palette"][i%len(style["palette"])]}" '+(f'data-stroke-index="{i}"' if attribute=='stroke' else f'data-color-index="{i}"')
        return f'{attribute}="{value}"'
    for i,title in enumerate(titles):out.append(f'<text x="24" y="{35+i*28}" {color("title")} font-size="23" font-family="sans-serif">{escape(title)}</text>')
    out.append(f'<defs><clipPath id="canvas"><rect width="{w}" height="{h}"/></clipPath></defs><g transform="translate(0 {top})" clip-path="url(#canvas)">')
    for cmd in spec['commands']:
        op,*a=cmd
        if op=='rect':
            x,y,width,height,fill,stroke,r=a;out.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{r}" {color(fill)} {color(stroke,"stroke")} stroke-width="2"/>')
        elif op=='circle':
            x,y,r,fill,stroke=a;out.append(f'<circle cx="{x}" cy="{y}" r="{r}" {color(fill)} {color(stroke,"stroke")} stroke-width="2"/>')
        elif op in ('line','arrow'):
            x1,y1,x2,y2,stroke,width=a;out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {color(stroke,"stroke")} stroke-width="{width}"/>')
            if op=='arrow':
                angle=math.atan2(y2-y1,x2-x1);length=min(15,max(6,math.hypot(x2-x1,y2-y1)/3));points=[(x2,y2),(x2-length*math.cos(angle-.5),y2-length*math.sin(angle-.5)),(x2-length*math.cos(angle+.5),y2-length*math.sin(angle+.5))]
                out.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in points)+'" '+color(stroke)+'/>')
        else:
            x,y,size,fill,text=a
            out.append(f'<text x="{x}" y="{y}" font-size="{size}" font-family="sans-serif" {color(fill)}>')
            for i,row in enumerate(text.splitlines()):out.append(f'<tspan x="{x}" dy="{0 if i==0 else size*1.3}">{escape(row)}</tspan>')
            out.append('</text>')
    out.append('</g>')
    for i,row in enumerate(textwrap.wrap('Source: '+spec['source'],max(10,int(w/8)))[:3]):out.append(f'<text x="24" y="{h+top+25+i*16}" {color("muted")} font-size="11" font-family="sans-serif">{escape(row)}</text>')
    out.append('</svg>');return '\n'.join(out)
