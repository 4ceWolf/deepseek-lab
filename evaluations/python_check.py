"""Constrained pure-Python evaluator. Never accepts imports, arbitrary attributes or I/O."""
import ast,json,sys,resource
resource.setrlimit(resource.RLIMIT_CPU,(2,2))
resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
resource.setrlimit(resource.RLIMIT_FSIZE,(0,0))
req=json.load(sys.stdin);code=req['code'].strip()
if code.startswith('```') and code.endswith('```'):code='\n'.join(code.splitlines()[1:-1])
try:
 tree=ast.parse(code)
 forbidden=(ast.Import,ast.ImportFrom,ast.ClassDef,ast.Global,ast.Nonlocal,ast.With,ast.AsyncWith,ast.AsyncFunctionDef,ast.Await)
 attrs={'append','extend','get','items','keys','values','strip','lstrip','rstrip','split','splitlines','startswith','endswith','lower','upper','join','copy','sort','pop','add'}
 for node in ast.walk(tree):
  if isinstance(node,forbidden):raise ValueError('Disallowed syntax in pure-function evaluator')
  if isinstance(node,ast.Attribute) and node.attr not in attrs:raise ValueError('Disallowed attribute')
  if isinstance(node,ast.Name) and node.id.startswith('__'):raise ValueError('Disallowed identifier')
  if isinstance(node,(ast.FunctionDef,ast.arg)) and getattr(node,'name',getattr(node,'arg','')).startswith('__'):raise ValueError('Disallowed identifier')
 allowed={k:__builtins__[k] for k in []} if isinstance(__builtins__,dict) else {}
 import builtins
 for name in ['len','range','enumerate','zip','sorted','reversed','list','tuple','dict','set','str','int','float','bool','min','max','sum','abs','all','any','isinstance','iter','next','StopIteration','ValueError','TypeError']:
  allowed[name]=getattr(builtins,name)
 env={'__builtins__':allowed}
 exec(compile(tree,'<candidate>','exec'),env,env)
 fn=env[req['function']];fail=[]
 for n,case in enumerate(req['cases']):
  args=json.loads(json.dumps(case['args']));before=json.loads(json.dumps(args))
  try:
   result=fn(*args)
   if 'raises'in case:fail.append({'case':n,'reason':'Expected exception'})
   elif (json.loads(json.dumps(result)) if case.get('json_equivalent') else result)!=case['expected']:fail.append({'case':n,'reason':'Wrong result','actual':result})
  except Exception as e:
   if type(e).__name__!=case.get('raises'):fail.append({'case':n,'reason':type(e).__name__})
  if case.get('immutable') and args!=before:fail.append({'case':n,'reason':'Input mutated'})
 print(json.dumps({'pass':not fail,'cases':len(req['cases']),'failures':fail}))
except Exception as e:print(json.dumps({'pass':False,'error':str(e)}))
