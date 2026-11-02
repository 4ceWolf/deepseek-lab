"""Validated interactive scenes and a bounded expression interpreter. No eval or model code."""
import ast,copy,hashlib,json,keyword,math,operator,re
from functools import lru_cache
FUNCTIONS={'sin':math.sin,'cos':math.cos,'tan':math.tan,'sqrt':math.sqrt,'abs':abs,'exp':math.exp,'log':math.log,'log10':math.log10,'min':lambda *xs:min(xs),'max':lambda *xs:max(xs),'floor':math.floor,'ceil':math.ceil,'atan2':math.atan2}
BIN={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Mod:operator.mod,ast.Pow:operator.pow}
CMP={ast.Lt:operator.lt,ast.LtE:operator.le,ast.Gt:operator.gt,ast.GtE:operator.ge,ast.Eq:operator.eq,ast.NotEq:operator.ne}
HINT='''You can create LIVE interactive visuals inline in this chat. For sliders, calculators, graphs, simulations or draggable points, output a deepseek-visual fenced JSON block with kind:"interactive", title, source, description, controls, scene, readouts. controls: [{id:"a",label:"Amplitude",type:"slider",min:0,max:3,step:0.1,value:1}], or type:"toggle" with boolean value, type:"select" with options:[{label:"...",value:1}], or type:"point" with x,y. scene: {x:[-8,8],y:[-4,4],axes:true,layers:[{type:"curve",x:"u",y:"a*sin(u-t)",u:[-8,8],samples:240,color:"p0",label:"Wave"}]}. Other layers: circle {x,y,r}, rect {x,y,w,h}, line/arrow {x,y,x2,y2}, text {x,y,text,size}. Numeric fields can be math-expression strings using control IDs, point IDs as id_x/id_y, t, u, pi, tau, sin/cos/sqrt/abs/exp/log/min/max, arithmetic (power is **, not ^) and comparisons. Use visible:"toggle_id" to switch a layer. readouts:[{label:"Peak",expr:"a",unit:"m"}]. Optional animation:{duration:12,speed:1} adds Play/Pause and time scrubbing; animation starts paused. Point controls are draggable. Colors: #RRGGBB or p0..p5. Controls run locally without another model request. These are general scenes, not fixed demos. Use real sources or label illustrative assumptions. No HTML, JS or shell commands. Ordinary replies need no visual.'''

def number(v,lo=-1e12,hi=1e12):
    if type(v) not in (int,float) or not lo<=v<=hi or not math.isfinite(v):raise ValueError('Interactive number is outside its finite bounds')
    return float(v)
def text(v,limit=200):
    if not isinstance(v,str) or len(v)>limit or any(ord(c)<32 and c not in '\n\t' for c in v):raise ValueError('Invalid interactive text')
    return v
@lru_cache(maxsize=1024)
def expression(value,names):
    value=text(value,240)
    try:tree=ast.parse(value,mode='eval').body
    except (SyntaxError,RecursionError):raise ValueError('Invalid expression') from None
    if len(list(ast.walk(tree)))>80:raise ValueError('Expression too complex')
    def check(n):
        if isinstance(n,ast.Constant) and type(n.value) in (int,float,bool):number(n.value if type(n.value)!=bool else int(n.value));return
        if isinstance(n,ast.Name) and n.id in names:return
        if isinstance(n,ast.BinOp) and type(n.op) in BIN:check(n.left);check(n.right);return
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub,ast.Not)):check(n.operand);return
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in FUNCTIONS and not n.keywords and 1<=len(n.args)<=8:
            expected=(1,8) if n.func.id in ('min','max') else (1,2) if n.func.id=='log' else (2,2) if n.func.id=='atan2' else (1,1)
            if not expected[0]<=len(n.args)<=expected[1]:raise ValueError('Wrong function argument count')
            for a in n.args:check(a)
            return
        if isinstance(n,ast.Compare) and len(n.ops)<=3 and all(type(o) in CMP for o in n.ops):
            check(n.left)
            for a in n.comparators:check(a)
            return
        if isinstance(n,ast.IfExp):check(n.test);check(n.body);check(n.orelse);return
        if isinstance(n,ast.BoolOp) and isinstance(n.op,(ast.And,ast.Or)):
            for a in n.values:check(a)
            return
        raise ValueError('Unsupported expression operation or variable')
    check(tree);return tree

def evaluate(value,values):
    if type(value) in (int,float,bool):return float(value)
    tree=expression(value,tuple(sorted(values)))
    def walk(n):
        if isinstance(n,ast.Constant):return n.value
        if isinstance(n,ast.Name):return values[n.id]
        if isinstance(n,ast.BinOp):
            a,b=walk(n.left),walk(n.right)
            if isinstance(n.op,ast.Pow) and (abs(b)>16 or abs(a)>1e6):raise ValueError('Power exceeds the evaluation limit')
            return BIN[type(n.op)](a,b)
        if isinstance(n,ast.UnaryOp):
            a=walk(n.operand);return not a if isinstance(n.op,ast.Not) else -a if isinstance(n.op,ast.USub) else a
        if isinstance(n,ast.Call):return FUNCTIONS[n.func.id](*[walk(a) for a in n.args])
        if isinstance(n,ast.IfExp):return walk(n.body if walk(n.test) else n.orelse)
        if isinstance(n,ast.BoolOp):return all(walk(a) for a in n.values) if isinstance(n.op,ast.And) else any(walk(a) for a in n.values)
        if isinstance(n,ast.Compare):
            a=walk(n.left)
            for op,bn in zip(n.ops,n.comparators):
                b=walk(bn)
                if not CMP[type(op)](a,b):return False
                a=b
            return True
        raise ValueError('Invalid expression')
    try:
        result=walk(tree)
        if isinstance(result,complex) or not math.isfinite(result) or abs(result)>1e12:raise ValueError('Undefined or out-of-range value')
        return float(result)
    except (ArithmeticError,TypeError,ValueError) as exc:raise ValueError('Expression is undefined for these controls') from None

def validate(spec):
    if not isinstance(spec,dict) or len(json.dumps(spec,allow_nan=False).encode())>60000:raise ValueError('Interactive spec must be under 60 KB')
    controls=spec.get('controls',[])
    if not isinstance(controls,list) or len(controls)>8:raise ValueError('Use at most 8 controls')
    out=[];names={'t','u','pi','e','tau'};ids=set()
    for c in controls:
        if not isinstance(c,dict):raise ValueError('Invalid control')
        ident=c.get('id');kind=c.get('type','slider')
        if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,30}',ident) or keyword.iskeyword(ident) or ident in names or ident in ids or ident in FUNCTIONS:raise ValueError('Controls need unique simple IDs')
        new_names={ident+'_x',ident+'_y'} if kind=='point' else {ident}
        if new_names & names:raise ValueError('Control names overlap')
        names|=new_names;ids.add(ident)
        r=dict(id=ident,label=text(c.get('label',ident),80),type=kind)
        if kind=='slider':
            lo,hi=number(c.get('min',0)),number(c.get('max',1));step=number(c.get('step',(hi-lo)/100),1e-9,1e12)
            if hi<=lo:raise ValueError('Slider max must exceed min')
            if (hi-lo)/step>10000:raise ValueError('Use at most 10000 slider steps')
            r.update(min=lo,max=hi,step=step,value=number(c.get('value',lo),lo,hi),unit=text(c.get('unit',''),30))
        elif kind=='toggle':
            if type(c.get('value',False)) is not bool:raise ValueError('Toggle value must be boolean')
            r['value']=c.get('value',False)
        elif kind=='select':
            opts=c.get('options',[])
            if not isinstance(opts,list) or not 1<=len(opts)<=12:raise ValueError('Select needs 1–12 options')
            r['options']=[dict(label=text(o['label'],80),value=number(o['value'])) for o in opts if isinstance(o,dict)]
            if len(r['options'])!=len(opts):raise ValueError('Invalid option')
            r['value']=number(c.get('value',r['options'][0]['value']))
            if r['value'] not in [o['value'] for o in r['options']]:raise ValueError('Select value must match an option')
        elif kind=='point':r.update(x=number(c.get('x',0)),y=number(c.get('y',0)))
        else:raise ValueError('Unknown control type')
        out.append(r)
    scene=spec.get('scene',{});xr=scene.get('x',[-10,10]);yr=scene.get('y',[-5,5])
    def extent(r):
        if not isinstance(r,list) or len(r)!=2:raise ValueError('Scene bounds need two numbers')
        a,b=number(r[0],-1e6,1e6),number(r[1],-1e6,1e6)
        if b-a<1e-6:raise ValueError('Scene bounds must increase')
        return [a,b]
    xr,yr=extent(xr),extent(yr)
    for c in out:
        if c['type']=='point':number(c['x'],*xr);number(c['y'],*yr)
    def formula(v):
        if isinstance(v,str):expression(v,tuple(sorted(names)));return v
        if type(v) is bool:return v
        return number(v)
    layers=scene.get('layers',[])
    if not isinstance(layers,list) or len(layers)>12:raise ValueError('Use at most 12 layers')
    normalized=[];samples=0
    fields={'curve':('x','y'),'circle':('x','y','r'),'rect':('x','y','w','h'),'line':('x','y','x2','y2'),'arrow':('x','y','x2','y2'),'text':('x','y')}
    for layer in layers:
        if not isinstance(layer,dict) or layer.get('type') not in fields:raise ValueError('Unknown scene layer')
        kind=layer['type'];color=layer.get('color','p0')
        if not isinstance(color,str) or not re.fullmatch(r'(#[0-9a-fA-F]{6}|p[0-5])',color):raise ValueError('Layer color must be #RRGGBB or p0..p5')
        r=dict(type=kind,color=color,label=text(layer.get('label',''),100),visible=formula(layer.get('visible',True)),width=number(layer.get('width',2),1,8))
        for key in fields[kind]:r[key]=formula(layer.get(key,'u' if key=='x' and kind=='curve' else 0))
        if kind=='curve':
            r['u']=extent(layer.get('u',xr));n=layer.get('samples',180)
            if type(n) is not int or not 16<=n<=500:raise ValueError('Use 16–500 curve samples')
            r['samples']=n;samples+=n
        if kind=='text':r.update(text=text(layer.get('text',''),200),size=number(layer.get('size',14),10,32))
        normalized.append(r)
    if samples>1600:raise ValueError('Scene sample budget exceeded')
    readouts=spec.get('readouts',[])
    if not isinstance(readouts,list) or len(readouts)>8:raise ValueError('Use at most 8 readouts')
    ro=[dict(label=text(r['label'],80),expr=formula(r['expr']),unit=text(r.get('unit',''),30)) for r in readouts if isinstance(r,dict)]
    if len(ro)!=len(readouts):raise ValueError('Invalid readout')
    if not normalized and not ro:raise ValueError('Add a visual layer or a calculator readout')
    animation=spec.get('animation')
    if animation is not None:
        if not isinstance(animation,dict):raise ValueError('Invalid animation')
        animation=dict(duration=number(animation.get('duration',10),.1,120),speed=number(animation.get('speed',1),.1,4))
    return dict(controls=out,scene=dict(x=xr,y=yr,axes=formula(scene.get('axes',True)),layers=normalized),readouts=ro,animation=animation,description=text(spec.get('description',''),600))

def identity(spec):return hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()[:24]
def defaults(spec):
    values=dict(t=0.,u=0.,pi=math.pi,e=math.e,tau=math.tau)
    for c in spec['controls']:
        if c['type']=='point':values.update({c['id']+'_x':c['x'],c['id']+'_y':c['y']})
        else:values[c['id']]=c['value']
    return values

def state(spec,value):
    if not isinstance(value,dict):raise ValueError('Invalid visual state')
    result=defaults(spec)
    for c in spec['controls']:
        key=c['id'];kind=c['type']
        if kind=='slider':result[key]=number(value.get(key,result[key]),c['min'],c['max'])
        elif kind=='toggle':
            v=value.get(key,result[key])
            if type(v) is not bool:raise ValueError('Invalid toggle state')
            result[key]=v
        elif kind=='select':
            v=number(value.get(key,result[key]))
            if v not in [o['value'] for o in c['options']]:raise ValueError('Invalid select state')
            result[key]=v
        else:
            result[key+'_x']=number(value.get(key+'_x',result[key+'_x']),*spec['scene']['x']);result[key+'_y']=number(value.get(key+'_y',result[key+'_y']),*spec['scene']['y'])
    if spec['animation']:result['t']=number(value.get('t',0),0,spec['animation']['duration'])
    return result
