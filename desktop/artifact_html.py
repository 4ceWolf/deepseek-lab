"""Self-contained interactive HTML from validated data and a fixed local template."""
import base64,hashlib,json
from html import escape
from . import artifacts

SCRIPT=r'''
'use strict';
const original=JSON.parse(document.getElementById('spec').textContent);
let style=structuredClone(original.style);
const graphic=document.querySelector('svg');
function paint(){
 graphic.querySelectorAll('[data-role]').forEach(e=>e.setAttribute(e.dataset.paint||'fill',style[e.dataset.role]));
 graphic.querySelectorAll('[data-stroke-role]').forEach(e=>e.setAttribute('stroke',style[e.dataset.strokeRole]));
 graphic.querySelectorAll('[data-color-index]').forEach(e=>{const isText=e.tagName.toLowerCase()==='text';const color=isText&&!style.match_labels?style.text:style.palette[Number(e.dataset.colorIndex)%style.palette.length];e.setAttribute(e.dataset.paint||'fill',color);});
 graphic.querySelectorAll('[data-stroke-index]').forEach(e=>e.setAttribute('stroke',style.palette[Number(e.dataset.strokeIndex)%style.palette.length]));
 document.getElementById('status').textContent='Appearance updated locally. Your saved app revision is unchanged.';
}
function controls(){
 const area=document.getElementById('colors');area.replaceChildren();
 function picker(name,value,change){const label=document.createElement('label');label.append(document.createTextNode(name));const input=document.createElement('input');input.type='color';input.value=value;input.setAttribute('aria-label',name);input.addEventListener('input',()=>{change(input.value);paint();});label.append(input);area.append(label);}
 ['background','text','title','muted','grid','surface'].forEach(key=>picker(key[0].toUpperCase()+key.slice(1),style[key],value=>style[key]=value));
 style.palette.forEach((color,i)=>picker('Palette '+(i+1),color,value=>style.palette[i]=value));
 document.getElementById('match').checked=style.match_labels;
}
document.getElementById('match').addEventListener('change',event=>{style.match_labels=event.target.checked;paint();});
document.getElementById('reset').addEventListener('click',()=>{style=structuredClone(original.style);controls();paint();});
function download(name,data,type){const url=URL.createObjectURL(new Blob([data],{type}));const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
document.getElementById('svg-save').addEventListener('click',()=>download('artifact.svg',new XMLSerializer().serializeToString(graphic),'image/svg+xml'));
document.getElementById('json-save').addEventListener('click',()=>download('artifact.json',JSON.stringify({...original,style},null,2),'application/json'));
controls();
'''

def document(spec):
    spec=artifacts.validate(spec)
    if spec['kind']=='interactive':
        from .interactive_html import document as interactive_document
        return interactive_document(spec)
    columns,rows=artifacts.data_rows(spec)
    payload=json.dumps(spec,ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    digest=base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    head=''.join('<th scope="col">'+escape(str(v))+'</th>' for v in columns)
    body=''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'sha256-'''+digest+''''; style-src 'unsafe-inline'; img-src blob: data:; base-uri 'none'; form-action 'none'">
<title>'''+escape(spec['title'])+'''</title>
<style>
:root{color-scheme:dark;font:15px/1.55 system-ui,sans-serif;background:#101216;color:#e8ebf2}*{box-sizing:border-box}body{margin:0;padding:clamp(16px,3vw,40px)}main{max-width:1440px;margin:auto}h1{font-size:clamp(24px,3vw,36px);line-height:1.2;overflow-wrap:anywhere}p{max-width:85ch;color:#b6c1d1}.workspace{display:grid;grid-template-columns:minmax(0,1fr) 270px;gap:20px;align-items:start}.card{background:#1a1d23;border:1px solid #343b47;border-radius:16px;padding:18px;min-width:0}svg{display:block;width:100%;height:auto}h2{font-size:18px;margin:0 0 14px}#colors{display:grid;gap:10px}label{display:flex;align-items:center;justify-content:space-between;gap:12px}input[type=color]{width:52px;height:34px;padding:2px;background:#242932;border:1px solid #738297;border-radius:7px}input[type=checkbox]{width:20px;height:20px}button{font:inherit;color:#e8ebf2;background:#29364a;border:1px solid #738297;border-radius:8px;padding:8px 12px;margin-top:10px;cursor:pointer}:focus-visible{outline:3px solid #accbfa;outline-offset:3px}.actions{display:flex;gap:8px;flex-wrap:wrap}.source{white-space:pre-wrap;overflow-wrap:anywhere}details{margin-top:20px}summary{cursor:pointer;padding:10px}.data{overflow:auto}table{border-collapse:collapse;width:100%;margin-top:12px}th,td{text-align:left;border-bottom:1px solid #39414e;padding:10px;overflow-wrap:anywhere}th{color:#accbfa}#status{font-size:13px;min-height:3em}noscript{display:block;padding:12px;background:#29364a}@media(max-width:800px){.workspace{grid-template-columns:1fr}#colors{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}}
</style><main><h1>'''+escape(spec['title'])+'''</h1><p class="source">Source: '''+escape(spec['source'])+'''</p><p>Source labels do not independently verify the data. Changes below are local to this file.</p>
<noscript>The chart and data remain readable. Enable JavaScript for local appearance controls and downloads.</noscript>
<div class="workspace"><section class="card" aria-label="Visual artifact">'''+artifacts.svg(spec)+'''</section>
<aside class="card" aria-label="Appearance"><h2>Appearance</h2><div id="colors"></div><p><label>Match labels to chart colors<input id="match" type="checkbox"></label></p><div class="actions"><button id="reset">Reset colors</button><button id="svg-save">Save SVG</button><button id="json-save">Save specification</button></div><p id="status" role="status">Color changes need no connection or API key.</p></aside></div>
<details class="card"><summary>Inspect full data</summary><div class="data"><table><thead><tr>'''+head+'''</tr></thead><tbody>'''+body+'''</tbody></table></div></details>
<script type="application/json" id="spec">'''+payload+'''</script><script>'''+SCRIPT+'''</script></main></html>'''
