"""Safe Mode status and explicit promotion guardrails; all runtime state isolated."""
import os
from pathlib import Path
import unittest
from fastapi.testclient import TestClient
from hub.app import app,TOKEN

class SafeModeAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client=TestClient(app)
    @classmethod
    def tearDownClass(cls):
        cls.client.close()
    def test_status_requires_authenticated_owner(self):
        response=self.client.get('/api/safe-mode/status')
        self.assertEqual(response.status_code,401)
    def test_status_reports_pinned_version_and_runtime(self):
        response=self.client.get('/api/safe-mode/status',headers={'x-hub-key':TOKEN})
        self.assertEqual(response.status_code,200,response.text[:300])
        data=response.json()
        self.assertEqual(data['safe']['version'],'0.26.0')
        self.assertTrue(data['safe']['verified'])
        self.assertEqual(data['production_version'],'0.26.0')
        self.assertIn('runtime',data)
    def test_promotion_requires_correct_explicit_confirmation(self):
        req={'request_id':'f'*32,'confirmation':'IMPLICIT'}
        response=self.client.post('/api/safe-mode/promote',json=req,headers={'x-hub-key':TOKEN})
        self.assertEqual(response.status_code,422)
    def test_promotion_rejects_unauthenticated_request(self):
        req={'request_id':'e'*32,'confirmation':'PROMOTE_CURRENT_TO_SAFE'}
        response=self.client.post('/api/safe-mode/promote',json=req)
        self.assertEqual(response.status_code,401)
    def test_missing_job_does_not_fabricate_success(self):
        response=self.client.get('/api/safe-mode/promotions/'+'a'*32,headers={'x-hub-key':TOKEN})
        self.assertEqual(response.status_code,404)
    def test_mcp_registration_is_explicit(self):
        from hub.mcp_gateway import mcp
        import asyncio
        tools=asyncio.run(mcp.list_tools())
        names={tool.name for tool in tools}
        self.assertTrue({'safe_mode_status','safe_mode_promote',
                         'safe_mode_promotion_status'}<=names,names)
if __name__=='__main__':
    unittest.main()