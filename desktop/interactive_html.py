"""Portable offline interactive exports with a fixed runtime and validated expression trees."""
import ast,base64,hashlib,json,math
from html import escape
from . import interactive

def static_svg(spec):
    v=interactive.defaults(spec);s=spec['scene'];xr,yr=s['x'],s['y'];colors=['#92baff','#62d4b1','#efbb70','#d2a4f5','#ef929e','#7ed5e8']
    def point(x,y):return (45+(x-xr[0])/(xr[1]-xr[0])*710,320-(y-yr[0])/(yr[1]-yr[0])*250)
    def ev(x):return interactive.evaluate(x,v)
    out=['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="390" viewBox="0 0 800 390"><rect width="800" height="390" fill="#14191f"/>','<title>'+escape(spec['title'])+'</title>',f'<text x="25" y="32" fill="#e8ebf2" font-size="20" font-family="sans-serif">{escape(spec["title"])}</text>','<defs><clipPath id="scene"><rect x="45" y="70" width="710" height="250"/></clipPath></defs><g clip-path="url(#scene)">']
    for l in s['layers']:
        try:
            if not ev(l['visible']):continue
            color=colors[int(l['color'][1:])] if l['color'].startswith('p') else l['color'];kind=l['type']
            if kind=='curve':
                points=[]
                for i in range(l['samples']):
                    v['u']=l['u'][0]+i*(l['u'][1]-l['u'][0])/(l['samples']-1)
                    try:
                        x,y=point(ev(l['x']),ev(l['y']))
                        if abs(x)<1e7 and abs(y)<1e7:points.append(f'{x},{y}')
                    except ValueError:pass
                out.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>')
            elif kind in ('line','arrow'):
                x,y=point(ev(l['x']),ev(l['y']));xx,yy=point(ev(l['x2']),ev(l['y2']));out.append(f'<line x1="{x}" y1="{y}" x2="{xx}" y2="{yy}" stroke="{color}" stroke-width="2"/>')
            elif kind=='text':
                x,y=point(ev(l['x']),ev(l['y']));out.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{l["size"]}">{escape(l["text"])}</text>')
            elif kind=='circle':
                x,y=point(ev(l['x']),ev(l['y']));r=ev(l['r']);out.append(f'<ellipse cx="{x}" cy="{y}" rx="{abs(r/(xr[1]-xr[0])*710)}" ry="{abs(r/(yr[1]-yr[0])*250)}" fill="none" stroke="{color}"/>')
            elif kind=='rect':
                x,y=point(ev(l['x']),ev(l['y'])+ev(l['h']));out.append(f'<rect x="{x}" y="{y}" width="{max(0,ev(l["w"])/(xr[1]-xr[0])*710)}" height="{max(0,ev(l["h"])/(yr[1]-yr[0])*250)}" fill="none" stroke="{color}"/>')
        except (ValueError,OverflowError):continue
    out.append('</g><text x="25" y="365" fill="#9eacbc" font-size="12">Interactive visual · controls are available in chat</text></svg>');return '\n'.join(out)

def trees(spec):
    names=tuple(sorted(interactive.defaults(spec)))
    def encode(n):
        if isinstance(n,ast.Constant):return ['num',n.value]
        if isinstance(n,ast.Name):return ['var',n.id]
        if isinstance(n,ast.BinOp):return ['bin',type(n.op).__name__,encode(n.left),encode(n.right)]
        if isinstance(n,ast.UnaryOp):return ['unary',type(n.op).__name__,encode(n.operand)]
        if isinstance(n,ast.Call):return ['call',n.func.id,[encode(a) for a in n.args]]
        if isinstance(n,ast.IfExp):return ['if',encode(n.test),encode(n.body),encode(n.orelse)]
        if isinstance(n,ast.Compare):return ['compare',encode(n.left),[type(o).__name__ for o in n.ops],[encode(a) for a in n.comparators]]
        if isinstance(n,ast.BoolOp):return ['bool',type(n.op).__name__,[encode(a) for a in n.values]]
        raise ValueError('Unknown expression')
    result={}
    def add(v):
        if isinstance(v,str):result[v]=encode(interactive.expression(v,names))
    add(spec['scene']['axes'])
    for l in spec['scene']['layers']:
        for key in ('x','y','x2','y2','r','w','h','visible'):
            if key in l:add(l[key])
    for r in spec['readouts']:add(r['expr'])
    return result

SCRIPT=r'''
'use strict';
const data=JSON.parse(document.getElementById('data').textContent),spec=data.spec,trees=data.trees;
let values=Object.assign(Object.create(null),data.state),playing=false,last=0,drag=null;
const canvas=document.getElementById('scene'),ctx=canvas.getContext('2d'),status=document.getElementById('status'),bindings=[];if(!spec.scene.layers.length&&!spec.controls.some(c=>c.type==='point'))canvas.hidden=true;
const palette=['#92baff','#62d4b1','#efbb70','#d2a4f5','#ef929e','#7ed5e8'];
const funcs={sin:Math.sin,cos:Math.cos,tan:Math.tan,sqrt:Math.sqrt,abs:Math.abs,exp:Math.exp,log:(x,b)=>b===undefined?Math.log(x):Math.log(x)/Math.log(b),log10:Math.log10,min:Math.min,max:Math.max,floor:Math.floor,ceil:Math.ceil,atan2:Math.atan2};
function walk(n){let a,b;switch(n[0]){case 'num':return n[1];case 'var':return values[n[1]];case 'unary':a=walk(n[2]);return n[1]==='Not'?!a:n[1]==='USub'?-a:a;case 'bin':a=walk(n[2]);b=walk(n[3]);switch(n[1]){case 'Add':return a+b;case 'Sub':return a-b;case 'Mult':return a*b;case 'Div':return a/b;case 'Mod':return a-Math.floor(a/b)*b;case 'Pow':return Math.abs(b)>16||Math.abs(a)>1e6?NaN:a**b;}break;case 'call':return funcs[n[1]](...n[2].map(walk));case 'if':return walk(walk(n[1])?n[2]:n[3]);case 'bool':return n[1]==='And'?n[2].every(x=>!!walk(x)):n[2].some(x=>!!walk(x));case 'compare':a=walk(n[1]);for(let i=0;i<n[2].length;i++){b=walk(n[3][i]);let ok={Lt:a<b,LtE:a<=b,Gt:a>b,GtE:a>=b,Eq:a===b,NotEq:a!==b}[n[2][i]];if(!ok)return false;a=b;}return true;}return NaN;}
function ev(v){const n=typeof v==='string'?walk(trees[v]):Number(v);return Number.isFinite(Number(n))&&Math.abs(n)<=1e12?Number(n):NaN;}
function bounds(){return {w:canvas.clientWidth,h:canvas.clientHeight,x:spec.scene.x,y:spec.scene.y};}
function point(x,y){let b=bounds();return [45+(x-b.x[0])/(b.x[1]-b.x[0])*(b.w-65),b.h-35-(y-b.y[0])/(b.y[1]-b.y[0])*(b.h-55)];}
function draw(){const b=bounds(),ratio=Math.min(2,window.devicePixelRatio||1);if(canvas.width!==Math.round(b.w*ratio)||canvas.height!==Math.round(b.h*ratio)){canvas.width=Math.round(b.w*ratio);canvas.height=Math.round(b.h*ratio);}ctx.setTransform(ratio,0,0,ratio,0,0);ctx.fillStyle='#14191f';ctx.fillRect(0,0,b.w,b.h);ctx.font='11px system-ui';if(ev(spec.scene.axes)){for(let i=0;i<=5;i++){let x=b.x[0]+i*(b.x[1]-b.x[0])/5,y=b.y[0]+i*(b.y[1]-b.y[0])/5,[px,py]=point(x,y);ctx.strokeStyle='#2c3540';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(px,20);ctx.lineTo(px,b.h-35);ctx.moveTo(45,py);ctx.lineTo(b.w-20,py);ctx.stroke();ctx.fillStyle='#9eacbc';ctx.fillText(Number(x.toPrecision(3)),px-10,b.h-12);ctx.fillText(Number(y.toPrecision(3)),3,py+4);}}
ctx.save();ctx.beginPath();ctx.rect(45,20,b.w-65,b.h-55);ctx.clip();for(const l of spec.scene.layers){if(!ev(l.visible))continue;const color=l.color.startsWith('p')?palette[Number(l.color[1])]:l.color;ctx.strokeStyle=ctx.fillStyle=color;ctx.lineWidth=l.width;ctx.beginPath();let a,c;try{if(l.type==='curve'){let started=false,previous=null,old=values.u;for(let i=0;i<l.samples;i++){values.u=l.u[0]+i*(l.u[1]-l.u[0])/(l.samples-1);const p=point(ev(l.x),ev(l.y));if(!p.every(Number.isFinite)||p.some(v=>Math.abs(v)>1e7)){started=false;continue;}if(previous&&Math.abs(p[1]-previous[1])>b.h*3)started=false;if(started)ctx.lineTo(...p);else ctx.moveTo(...p);started=true;previous=p;}values.u=old;ctx.stroke();}else if(l.type==='text'){a=point(ev(l.x),ev(l.y));ctx.font=l.size+'px system-ui';ctx.fillText(l.text,...a);}else if(l.type==='circle'){a=point(ev(l.x),ev(l.y));let r=ev(l.r);if(r>=0){ctx.ellipse(...a,r/(b.x[1]-b.x[0])*(b.w-65),r/(b.y[1]-b.y[0])*(b.h-55),0,0,Math.PI*2);ctx.stroke();}}else if(l.type==='rect'){a=point(ev(l.x),ev(l.y)+ev(l.h));c=point(ev(l.x)+ev(l.w),ev(l.y));ctx.strokeRect(...a,c[0]-a[0],c[1]-a[1]);}else{a=point(ev(l.x),ev(l.y));c=point(ev(l.x2),ev(l.y2));ctx.moveTo(...a);ctx.lineTo(...c);if(l.type==='arrow'){let angle=Math.atan2(c[1]-a[1],c[0]-a[0]);for(let d of [-.5,.5]){ctx.moveTo(...c);ctx.lineTo(c[0]-10*Math.cos(angle+d),c[1]-10*Math.sin(angle+d));}}ctx.stroke();}}catch{}}
for(const c of spec.controls)if(c.type==='point'){const p=point(values[c.id+'_x'],values[c.id+'_y']);ctx.beginPath();ctx.arc(...p,7,0,Math.PI*2);ctx.fillStyle='#92baff';ctx.fill();ctx.fillStyle='#d8e8ff';ctx.font='12px system-ui';ctx.fillText(c.label,p[0]+12,p[1]-9);}ctx.restore();document.getElementById('readouts').textContent=spec.readouts.map(r=>{const v=ev(r.expr);return r.label+': '+(Number.isFinite(v)?Number(v.toPrecision(6)):'undefined')+(r.unit?' '+r.unit:'');}).join(' · ');for(const b of bindings)b();}
function input(type,label){const x=document.createElement('input');x.type=type;x.setAttribute('aria-label',label);return x;}
for(const c of spec.controls){let row=document.createElement('label');row.className='control';let name=document.createElement('span');name.textContent=c.label;row.append(name);if(c.type==='slider'){let slider=input('range',c.label),number=input('number',c.label+' value');for(const w of [slider,number]){w.min=c.min;w.max=c.max;w.step=c.step;w.addEventListener('input',()=>{const n=Number(w.value);if(Number.isFinite(n)){values[c.id]=Math.max(c.min,Math.min(c.max,n));draw();}});row.append(w);}bindings.push(()=>{slider.value=number.value=values[c.id];});}else if(c.type==='toggle'){let w=input('checkbox',c.label);w.addEventListener('change',()=>{values[c.id]=w.checked;draw();});row.append(w);bindings.push(()=>w.checked=values[c.id]);}else if(c.type==='select'){let w=document.createElement('select');w.setAttribute('aria-label',c.label);for(const o of c.options){let option=document.createElement('option');option.textContent=o.label;option.value=o.value;w.append(option);}w.addEventListener('change',()=>{values[c.id]=Number(w.value);draw();});row.append(w);bindings.push(()=>w.value=values[c.id]);}else{for(const axis of ['x','y']){let w=input('number',c.label+' '+axis),range=spec.scene[axis];w.min=range[0];w.max=range[1];w.step=(range[1]-range[0])/100;w.addEventListener('input',()=>{let n=Number(w.value);if(Number.isFinite(n)){values[c.id+'_'+axis]=Math.max(range[0],Math.min(range[1],n));draw();}});row.append(w);bindings.push(()=>w.value=Number(values[c.id+'_'+axis].toFixed(5)));}}document.getElementById('controls').append(row);}
const play=document.getElementById('play'),time=document.getElementById('time');if(!spec.animation){play.hidden=true;time.hidden=true;}else{time.addEventListener('input',()=>{values.t=Number(time.value)/1000*spec.animation.duration;draw();});bindings.push(()=>time.value=values.t/spec.animation.duration*1000);play.addEventListener('click',()=>{if(matchMedia('(prefers-reduced-motion: reduce)').matches){status.textContent='Reduced motion: use the time slider.';return;}playing=!playing;play.textContent=playing?'Pause':'Play';last=performance.now();});}
document.getElementById('reset').addEventListener('click',()=>{values=Object.assign(Object.create(null),data.defaults);playing=false;play.textContent='Play';draw();});
canvas.addEventListener('pointerdown',e=>{const r=canvas.getBoundingClientRect(),p=[e.clientX-r.left,e.clientY-r.top];for(const c of spec.controls)if(c.type==='point'){const q=point(values[c.id+'_x'],values[c.id+'_y']);if(Math.hypot(q[0]-p[0],q[1]-p[1])<20){drag=c.id;canvas.setPointerCapture(e.pointerId);break;}}});
canvas.addEventListener('pointermove',e=>{if(!drag)return;const r=canvas.getBoundingClientRect(),b=bounds();values[drag+'_x']=Math.max(b.x[0],Math.min(b.x[1],b.x[0]+(e.clientX-r.left-45)/(b.w-65)*(b.x[1]-b.x[0])));values[drag+'_y']=Math.max(b.y[0],Math.min(b.y[1],b.y[0]+(b.h-35-(e.clientY-r.top))/(b.h-55)*(b.y[1]-b.y[0])));draw();});canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);
function frame(now){if(playing&&spec.animation&&!document.hidden&&now-last>=50){values.t=(values.t+Math.min(.15,(now-last)/1000)*spec.animation.speed)%spec.animation.duration;last=now;draw();}requestAnimationFrame(frame);}new ResizeObserver(draw).observe(canvas);draw();requestAnimationFrame(frame);
window.visualTest={value:ev,state:()=>({...values})};
'''

def document(spec,values=None):
    from . import artifacts
    spec=artifacts.validate(spec);payload=json.dumps(dict(spec=spec,state=interactive.state(spec,values or {}),defaults=interactive.defaults(spec),trees=trees(spec)),ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    digest=base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'sha256-'+digest+'\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>'+escape(spec['title'])+'</title><style>'+'''*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;background:#101113;color:#e8e9ec;font:15px/1.6 system-ui,sans-serif;padding:24px}main{max-width:860px;margin:auto;background:#1b1d20;border:1px solid #343b47;border-radius:14px;padding:24px}h1{font-size:24px;line-height:1.3}p{color:#a9b2c1;white-space:pre-wrap}canvas{display:block;width:100%;height:320px;border-radius:10px;touch-action:none}.control{display:flex;gap:14px;align-items:center;margin:14px 0;flex-wrap:wrap}.control>span{min-width:130px}.control input[type=range]{flex:1;min-width:120px}input[type=number]{width:110px}input,select,button{font:inherit;background:#25272b;border:1px solid #526078;color:#e8ebf2;padding:7px;border-radius:6px}input[type=range]{accent-color:#92baff}input[type=checkbox]{width:22px;height:22px}button{cursor:pointer;padding:8px 16px}:focus-visible{outline:3px solid #92baff;outline-offset:3px}.actions{display:flex;gap:14px;align-items:center;flex-wrap:wrap}#readouts{color:#c2dcff;font-variant-numeric:tabular-nums;margin:16px 0}#status{font-size:12px}'''+ '</style><main><h1>'+escape(spec['title'])+'</h1><p>'+escape(spec.get('description',''))+'</p><canvas id="scene" role="img" aria-label="'+escape(spec['title'],quote=True)+'"></canvas><div id="readouts"></div><div id="controls"></div><div class="actions"><button id="play">Play</button><input id="time" type="range" min="0" max="1000" value="0" aria-label="Animation time"><button id="reset">Reset</button></div><p>Source: '+escape(spec['source'])+'</p><p id="status">Controls run locally · no model request</p><noscript>This interactive export needs JavaScript. Open the original native chat for controls.</noscript><script type="application/json" id="data">'+payload+'</script><script>'+SCRIPT+'</script></main></html>'
