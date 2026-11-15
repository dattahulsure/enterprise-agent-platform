import os, tempfile, unittest
from pathlib import Path
from fastapi.testclient import TestClient

class PlatformTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();os.environ['AGENT_DB']=str(Path(cls.tmp.name)/'test.sqlite3')
  from app import core
  core.DB=Path(os.environ['AGENT_DB']);core.init_db()
  from app.main import app
  cls.client=TestClient(app)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def request(self,path,method='get',user='krishna',body=None):return getattr(self.client,method)(path,headers={'X-Demo-User':user},json=body) if method!='get' else self.client.get(path,headers={'X-Demo-User':user})
 def test_health(self):self.assertEqual(self.request('/health').status_code,200)
 def test_seed_agents(self):self.assertGreaterEqual(len(self.request('/api/agents').json()),5)
 def test_simple_agent(self):
  r=self.request('/api/chat','post',body={'query':'my leave balance'});self.assertEqual(r.status_code,200);self.assertIn('12 leave days',r.json()['answer'])
 def test_multi_agent(self):
  r=self.request('/api/chat','post',body={'query':'leave balance, reimbursements, meetings'});self.assertEqual(r.status_code,200);self.assertEqual(set(r.json()['results']),{'hr','finance','calendar'})
 def test_denied_customer(self):self.assertEqual(self.request('/api/chat','post',body={'query':'ACME renewal risk'}).status_code,403)
 def test_manager_customer(self):
  r=self.request('/api/chat','post',user='manager',body={'query':'ACME renewal risk'});self.assertEqual(r.status_code,200);self.assertIn('HIGH',r.json()['answer'])
 def test_agent_creation_and_publish(self):
  d=self.request('/api/generate','post',body={'description':'Check expense reimbursement'}).json();self.assertEqual(d['kind'],'finance')
  r=self.request('/api/agents','post',body={k:d[k] for k in ('name','kind','description','tools')});self.assertEqual(r.status_code,200)
  aid=r.json()['id'];self.assertEqual(self.request('/api/agents/'+aid+'/publish','post').status_code,200)
 def test_agent_tool_validation(self):
  r=self.request('/api/agents','post',body={'name':'Unauthorized','kind':'hr','description':'bad','tools':['support_read']});self.assertEqual(r.status_code,400)
 def test_role_tool_validation(self):
  r=self.request('/api/agents','post',body={'name':'Customer','kind':'renewal','description':'bad','tools':['crm_read','support_read']});self.assertEqual(r.status_code,403)
 def test_recovery(self):
  d=self.request('/api/recovery','post',body={'run_id':'unit-test-run','fail_at_five':True}).json();self.assertEqual(d['status'],'failed_recoverably')
  d=self.request('/api/recovery','post',body={'run_id':'unit-test-run','fail_at_five':False}).json();self.assertEqual(d['status'],'completed');self.assertEqual(len([x for x in d['steps'] if x['status']=='skipped_already_completed']),4)
 def test_document_acl(self):
  from app.core import search_docs
  self.assertEqual(search_docs('renewal','krishna'),[]);self.assertTrue(search_docs('renewal','manager'))
 def test_approval(self):
  d=self.request('/api/approvals','post',body={'action':'Change CRM record'}).json();aid=d['id']
  self.assertEqual(self.request('/api/approvals/'+aid+'/approve','post').status_code,403)
  self.assertEqual(self.request('/api/approvals/'+aid+'/approve','post',user='admin').status_code,200)
 def test_logs_visibility(self):
  self.request('/api/chat','post',body={'query':'leave balance'})
  self.assertTrue(all(x['username']=='krishna' for x in self.request('/api/executions').json()))
if __name__=='__main__':unittest.main()
