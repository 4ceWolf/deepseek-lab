"""Trusted worker inside a disposable OS sandbox. No expected answers supplied."""
import ast,builtins,json,resource,sys

resource.setrlimit(resource.RLIMIT_CPU,(2,2))
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
resource.setrlimit(resource.RLIMIT_FSIZE,(1024*1024,1024*1024))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))

def main():
 req=json.load(sys.stdin)
 code=open('/work/module.py').read()
 tree=ast.parse(code)
 forbidden=(ast.Import,ast.ImportFrom,ast.ClassDef,ast.Global,ast.Nonlocal,ast.With,ast.AsyncWith,ast.AsyncFunctionDef,ast.Await)
 attrs={'append','extend','get','items','keys','values','strip','lstrip','rstrip','split','splitlines','startswith','endswith','lower','upper','join','copy','sort','pop','add'}
 for node in ast.walk(tree):
  if isinstance(node,forbidden):raise ValueError('Unsupported syntax in pure-function executor')
  if isinstance(node,ast.Attribute) and node.attr not in attrs:raise ValueError('Unsupported attribute')
  if isinstance(node,ast.Name) and node.id.startswith('__'):raise ValueError('Reserved name')
  if isinstance(node,(ast.FunctionDef,ast.arg)) and getattr(node,'name',getattr(node,'arg','')).startswith('__'):raise ValueError('Reserved name')
 names=['len','range','enumerate','zip','sorted','reversed','list','tuple','dict','set','str','int','float','bool','min','max','sum','abs','all','any','isinstance','iter','next','StopIteration','ValueError','TypeError']
 env={'__builtins__':{name:getattr(builtins,name) for name in names}}
 exec(compile(tree,'module.py','exec'),env,env)
 fn=env[req['function']];results=[]
 for supplied in req['inputs']:
  args=json.loads(json.dumps(supplied));before=json.loads(json.dumps(args))
  try:
   value=fn(*args)
   # JSON normalizes tuples deliberately; the public contract is JSON-compatible values.
   results.append({'value':value,'mutated':args!=before})
  except Exception as exc:results.append({'exception':type(exc).__name__,'mutated':args!=before})
 print(json.dumps({'results':results},allow_nan=False))

try:main()
except Exception as exc:
 print(json.dumps({'error':type(exc).__name__+': '+str(exc)[:500]}))
 sys.exit(1)
