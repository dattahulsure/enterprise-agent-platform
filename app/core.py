"""Configuration-driven demo agent platform. Uses LangGraph when installed."""
import json, os, sqlite3, uuid, time
from pathlib import Path
from typing import TypedDict, Any

ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get('AGENT_DB', str(ROOT/'agent_platform.sqlite3')))
USERS = {'krishna': 'employee', 'manager': 'manager', 'admin': 'admin'}
DATA = {
 'hr': {'krishna': {'leave_days': 12}, 'manager': {'leave_days': 19}, 'admin': {'leave_days': 21}},
 'finance': {'krishna': {'pending_reimbursements': 3400}, 'manager': {'pending_reimbursements': 900}, 'admin': {'pending_reimbursements': 0}},
 'calendar': {'krishna': {'meetings': ['Team sync, Monday 10 AM', 'Project review, Tuesday 3 PM']}, 'manager': {'meetings': ['Budget review, Wednesday 11 AM']}, 'admin': {'meetings': []}},
 'crm': {'ACME': {'customer_id': 'C-101', 'renewal_days': 45, 'annual_value': 125000}},
 'support': {'C-101': {'open_tickets': 3, 'critical': 1}},
}
AGENT_TEMPLATES = {
 'hr': ('HR Leave Agent', 'hr', ['hr_read'], 'Check leave balance for the current employee'),
 'finance': ('Finance Agent', 'finance', ['finance_read'], 'Check pending reimbursements'),
 'calendar': ('Calendar Agent', 'calendar', ['calendar_read'], 'List upcoming meetings'),
 'crm': ('Customer Research Agent', 'crm', ['crm_read'], 'Retrieve customer profile'),
 'renewal': ('Renewal Risk Agent', 'renewal', ['crm_read', 'support_read'], 'Summarize customer renewal risk'),
}
ROLE_TOOLS = {'employee': {'hr_read','finance_read','calendar_read'}, 'manager': {'hr_read','finance_read','calendar_read','crm_read','support_read'}, 'admin': {'hr_read','finance_read','calendar_read','crm_read','support_read'}}


def connection():
 DB.parent.mkdir(parents=True, exist_ok=True)
 c = sqlite3.connect(str(DB)); c.row_factory = sqlite3.Row
 return c


def init_db():
 with connection() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, description TEXT NOT NULL, tools TEXT NOT NULL, owner TEXT NOT NULL, version INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS executions(id TEXT PRIMARY KEY, username TEXT, query TEXT, status TEXT, result TEXT, trace TEXT, created_at TEXT);
  CREATE TABLE IF NOT EXISTS workflow_steps(run_id TEXT, step INTEGER, status TEXT, PRIMARY KEY(run_id,step));
  CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, username TEXT, action TEXT, status TEXT);
  CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, title TEXT, content TEXT, access_role TEXT);''')
  if not c.execute('SELECT COUNT(*) FROM agents').fetchone()[0]:
   for kind,(name,_,tools,desc) in AGENT_TEMPLATES.items():
    c.execute('INSERT INTO agents VALUES (?,?,?,?,?,?,?,?,datetime("now"))', (str(uuid.uuid4()),name,kind,desc,json.dumps(tools),'admin',1,'published'))
  if not c.execute('SELECT COUNT(*) FROM documents').fetchone()[0]:
   c.executemany('INSERT INTO documents VALUES (?,?,?,?)', [('1','Employee Leave Policy','Annual leave is subject to manager approval.','employee'),('2','Customer Renewal Playbook','Escalate accounts with critical support tickets before renewal.','manager'),('3','Security Operations','Access to confidential records requires explicit authorization.','admin')])


def agents():
 with connection() as c: return [dict(x) | {'tools':json.loads(x['tools'])} for x in c.execute('SELECT * FROM agents ORDER BY name,version DESC')]


def generate_draft(description, username):
 d=description.lower()
 if any(x in d for x in ['renewal','customer','salesforce','crm']): kind='renewal'
 elif any(x in d for x in ['reimbursement','expense','finance']): kind='finance'
 elif any(x in d for x in ['meeting','calendar']): kind='calendar'
 else: kind='hr'
 name,_,tools,_=AGENT_TEMPLATES[kind]
 return {'name':name,'kind':kind,'description':description,'tools':tools,'owner':username,'generation_mode':'deterministic_demo'}


def save_agent(payload, username):
 kind=payload.get('kind')
 if kind not in AGENT_TEMPLATES: raise ValueError('Unsupported agent kind')
 allowed=set(AGENT_TEMPLATES[kind][2]); selected=set(payload.get('tools',[]))
 if not selected or not selected.issubset(allowed): raise ValueError('Tools do not match approved capability catalog')
 if not selected.issubset(ROLE_TOOLS[USERS[username]]): raise PermissionError('Your role cannot create an agent with these tools')
 name=str(payload.get('name','')).strip()
 if not 1<=len(name)<=100: raise ValueError('Agent name must be 1–100 characters')
 with connection() as c:
  prior=c.execute('SELECT MAX(version) FROM agents WHERE name=?',(name,)).fetchone()[0]
  version=(prior or 0)+1; aid=str(uuid.uuid4())
  c.execute('INSERT INTO agents VALUES (?,?,?,?,?,?,?,?,datetime("now"))',(aid,name,kind,str(payload.get('description',''))[:1000],json.dumps(sorted(selected)),username,version,'draft'))
 return {'id':aid,'version':version,'status':'draft'}


def publish(aid, username):
 with connection() as c:
  a=c.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
  if not a: raise ValueError('Agent not found')
  if a['owner']!=username and username!='admin': raise PermissionError('Only owner or admin can publish')
  if not set(json.loads(a['tools'])).issubset(ROLE_TOOLS[USERS[username]]): raise PermissionError('Tools not authorized')
  c.execute('UPDATE agents SET status="published" WHERE id=?',(aid,))
 return {'id':aid,'status':'published'}


def tool(kind, username, trace, customer='ACME'):
 required={'hr':'hr_read','finance':'finance_read','calendar':'calendar_read','crm':'crm_read','support':'support_read'}[kind]
 if required not in ROLE_TOOLS[USERS[username]]: raise PermissionError(f'Access denied: {required}')
 trace.append({'event':'tool_call','tool':required,'actor':username})
 if kind in ('hr','finance','calendar'): return DATA[kind][username]
 if kind=='crm': return DATA['crm'].get(customer, {})
 return DATA['support'].get(customer, {})


def route(query, username):
 q=query.lower(); selected=[]
 if any(x in q for x in ['leave','holiday','vacation']): selected.append('hr')
 if any(x in q for x in ['reimbursement','expense','finance']): selected.append('finance')
 if any(x in q for x in ['meeting','calendar','schedule']): selected.append('calendar')
 if any(x in q for x in ['customer','renewal','acme','support','ticket']): selected.append('renewal')
 if not selected: return []
 with connection() as c:
  published={r['kind'] for r in c.execute('SELECT kind FROM agents WHERE status="published"')}
 selected=[x for x in selected if x in published]
 return selected


class GraphState(TypedDict, total=False):
 username: str
 query: str
 trace: list
 results: dict
 customer: dict
 support: dict


def _run_graph(username, query, kinds, trace):
 """Compile a genuine LangGraph StateGraph when dependency is available."""
 from langgraph.graph import StateGraph, START, END
 from typing import Annotated
 import operator
 class State(TypedDict, total=False):
  username:str
  query:str
  results: Annotated[dict, lambda a,b:{**a,**b}]
  trace: Annotated[list,operator.add]
  customer:dict
  support:dict
 def simple_node(kind):
  def node(s):
   local=[]; result=tool(kind,username,local)
   return {'results':{kind:result},'trace':[{'event':'agent_executed','agent':kind}]+local}
  return node
 def customer_node(s):
  local=[]; c=tool('crm',username,local)
  return {'customer':c,'trace':[{'event':'agent_executed','agent':'customer_research'}]+local}
 def support_node(s):
  local=[]; customer_id=s['customer'].get('customer_id','')
  support=tool('support',username,local,customer_id)
  return {'support':support,'trace':[{'event':'agent_executed','agent':'support_check'}]+local}
 def renewal_node(s):
  c=s['customer']; t=s['support']; risk='HIGH' if t.get('critical',0)>0 or t.get('open_tickets',0)>=3 else 'LOW'
  return {'results':{'renewal':{'customer':c,'support':t,'risk':risk}},'trace':[{'event':'agent_executed','agent':'renewal_risk'}]}
 g=StateGraph(State)
 for kind in kinds:
  if kind=='renewal':
   g.add_node('customer_research',customer_node);g.add_node('support_check',support_node);g.add_node('renewal_risk',renewal_node)
   g.add_edge(START,'customer_research');g.add_edge('customer_research','support_check');g.add_edge('support_check','renewal_risk');g.add_edge('renewal_risk',END)
  else:
   g.add_node(kind,simple_node(kind));g.add_edge(START,kind);g.add_edge(kind,END)
 output=g.compile().invoke({'username':username,'query':query,'results':{},'trace':[]})
 trace.extend(output.get('trace',[]))
 return output.get('results',{})


def execute(query, username):
 kinds=route(query,username)
 trace=[{'event':'route','agents':kinds}]
 if not kinds: return {'answer':'I could not identify a suitable published agent. Please mention leave, expenses, meetings, or customer renewal.','results':{},'trace':trace,'engine':'router'}
 required=set()
 for k in kinds: required.update(AGENT_TEMPLATES[k][2])
 if not required.issubset(ROLE_TOOLS[USERS[username]]): raise PermissionError('Your account is not authorized to execute this agent')
 try:
  results=_run_graph(username,query,kinds,trace); engine='LangGraph'
 except ImportError:
  # Honest fallback so local demo can still run without installing optional orchestration package.
  engine='sequential_fallback_no_langgraph';results={}
  for k in kinds:
   if k=='renewal':
    c=tool('crm',username,trace); s=tool('support',username,trace,c.get('customer_id',''))
    results[k]={'customer':c,'support':s,'risk':'HIGH' if s.get('critical',0)>0 or s.get('open_tickets',0)>=3 else 'LOW'}
   else: results[k]=tool(k,username,trace)
   trace.append({'event':'agent_executed','agent':k})
 lines=[]
 for k,v in results.items():
  if k=='hr': lines.append(f"You have {v['leave_days']} leave days remaining.")
  if k=='finance': lines.append(f"Pending reimbursements: ₹{v['pending_reimbursements']:,}.")
  if k=='calendar': lines.append('Upcoming meetings: '+('; '.join(v['meetings']) if v['meetings'] else 'none')+'.')
  if k=='renewal': lines.append(f"ACME renewal risk: {v['risk']}; {v['support']['open_tickets']} open support tickets, {v['support']['critical']} critical; renewal in {v['customer']['renewal_days']} days.")
 return {'answer':' '.join(lines),'results':results,'trace':trace,'engine':engine}


def record_execution(username,query,output):
 eid=str(uuid.uuid4())
 with connection() as c:
  c.execute('INSERT INTO executions VALUES (?,?,?,?,?,?,datetime("now"))',(eid,username,query,'completed',output['answer'],json.dumps(output['trace'])))
 return eid


def list_executions():
 with connection() as c: return [dict(x)|{'trace':json.loads(x['trace'])} for x in c.execute('SELECT * FROM executions ORDER BY created_at DESC LIMIT 30')]


def recovery(run_id, fail=False):
 """Persistent, deterministic 10-step recovery demonstration; not LangGraph checkpointing."""
 with connection() as c:
  completed={r['step'] for r in c.execute('SELECT step FROM workflow_steps WHERE run_id=? AND status="completed"',(run_id,))}
  events=[]
  for step in range(1,11):
   if step in completed:
    events.append({'step':step,'status':'skipped_already_completed'});continue
   if step==5 and fail:
    events.append({'step':step,'status':'simulated_failure'});break
   c.execute('INSERT OR REPLACE INTO workflow_steps VALUES (?, ?, "completed")',(run_id,step))
   events.append({'step':step,'status':'completed'})
  return {'run_id':run_id,'status':'failed_recoverably' if events[-1]['status']=='simulated_failure' else 'completed','steps':events}


def search_docs(query,username):
 role=USERS[username]; allowed={'employee':['employee'],'manager':['employee','manager'],'admin':['employee','manager','admin']}[role]
 with connection() as c:
  docs=[dict(x) for x in c.execute('SELECT * FROM documents') if x['access_role'] in allowed]
 words=[w for w in query.lower().split() if len(w)>3]
 return [d for d in docs if any(w in (d['title']+' '+d['content']).lower() for w in words)]
