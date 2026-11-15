import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from . import core

app=FastAPI(title='Enterprise Agent Platform Demo',version='0.1.0')
core.init_db()
class Description(BaseModel): description:str=Field(min_length=3,max_length=1000)
class AgentInput(BaseModel): name:str;kind:str;description:str;tools:list[str]
class ChatInput(BaseModel): query:str=Field(min_length=2,max_length=1000)
class RecoveryInput(BaseModel):run_id:str|None=None;fail_at_five:bool=True
class ApprovalInput(BaseModel):action:str

def actor(x_demo_user:str='krishna'):
 if x_demo_user not in core.USERS: raise HTTPException(401,'Unknown demo user')
 return x_demo_user

def err(e):
 if isinstance(e,PermissionError):raise HTTPException(403,str(e))
 raise HTTPException(400,str(e))

@app.get('/')
def index():return FileResponse(Path(__file__).resolve().parent.parent/'static'/'index.html')
@app.get('/health')
def health():return {'status':'ok','langgraph_installed':__import__('importlib').util.find_spec('langgraph') is not None}
@app.get('/api/users')
def users():return core.USERS
@app.get('/api/agents')
def agents():return core.agents()
@app.post('/api/generate')
def generate(payload:Description,x_demo_user:str=Header('krishna')):
 u=actor(x_demo_user);return core.generate_draft(payload.description,u)
@app.post('/api/agents')
def create(payload:AgentInput,x_demo_user:str=Header('krishna')):
 try:return core.save_agent(payload.model_dump(),actor(x_demo_user))
 except (ValueError,PermissionError) as e:err(e)
@app.post('/api/agents/{aid}/publish')
def publish(aid:str,x_demo_user:str=Header('krishna')):
 try:return core.publish(aid,actor(x_demo_user))
 except (ValueError,PermissionError) as e:err(e)
@app.post('/api/chat')
def chat(payload:ChatInput,x_demo_user:str=Header('krishna')):
 u=actor(x_demo_user)
 try:
  out=core.execute(payload.query,u);out['execution_id']=core.record_execution(u,payload.query,out);return out
 except (ValueError,PermissionError) as e:err(e)
@app.get('/api/executions')
def executions(x_demo_user:str=Header('krishna')):
 u=actor(x_demo_user);rows=core.list_executions()
 return rows if u=='admin' else [r for r in rows if r['username']==u]
@app.post('/api/recovery')
def recovery(payload:RecoveryInput,x_demo_user:str=Header('krishna')):
 actor(x_demo_user);return core.recovery(payload.run_id or str(uuid.uuid4()),payload.fail_at_five)
@app.get('/api/search')
def search(q:str,x_demo_user:str=Header('krishna')):
 return {'documents':core.search_docs(q,actor(x_demo_user)),'mode':'keyword_acl_demo_not_vector_rag'}
@app.post('/api/approvals')
def request_approval(payload:ApprovalInput,x_demo_user:str=Header('krishna')):
 u=actor(x_demo_user);aid=str(uuid.uuid4())
 with core.connection() as c:c.execute('INSERT INTO approvals VALUES (?,?,?,?)',(aid,u,payload.action,'pending'))
 return {'id':aid,'status':'pending'}
@app.get('/api/approvals')
def approvals(x_demo_user:str=Header('krishna')):
 u=actor(x_demo_user)
 with core.connection() as c:
  return [dict(x) for x in c.execute('SELECT * FROM approvals')] if u=='admin' else [dict(x) for x in c.execute('SELECT * FROM approvals WHERE username=?',(u,))]
@app.post('/api/approvals/{aid}/approve')
def approve(aid:str,x_demo_user:str=Header('krishna')):
 if actor(x_demo_user)!='admin':raise HTTPException(403,'Admin approval required')
 with core.connection() as c:
  if not c.execute('SELECT 1 FROM approvals WHERE id=?',(aid,)).fetchone():raise HTTPException(404,'Not found')
  c.execute('UPDATE approvals SET status="approved" WHERE id=?',(aid,))
 return {'id':aid,'status':'approved'}
