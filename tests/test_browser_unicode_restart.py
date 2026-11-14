import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from hub.navigation import normalized_url, require_observed_navigation
from hub.errors import ObservationError
from hub.browser import Browser
from hub.config import CDP_PORT

class UnicodeNavigationTests(unittest.TestCase):
    def test_multilingual_equivalence(self):
        for word in ['\u0434\u043e\u043c','\u05d1\u05d9\u05ea','caf\u00e9']:
            from urllib.parse import quote
            literal='https://example.test/wiki/'+word
            encoded='https://example.test/wiki/'+quote(word)
            self.assertEqual(normalized_url(literal),normalized_url(encoded))
            require_observed_navigation('Open '+encoded,literal,[])
    def test_reserved_escapes_still_distinct(self):
        for tail,other in [('a%2fb','a/b'),('a%3fb','a?b'),('a%252fb','a%2fb')]:
            with self.assertRaises(ObservationError):
                require_observed_navigation('Open https://example.test/'+tail,'https://example.test/'+other,[])
    def test_other_host_path_query_still_rejected(self):
        for target in ['https://other.test/a','https://example.test/b','https://example.test/a?q=2']:
            with self.assertRaises(ObservationError):
                require_observed_navigation('Open https://example.test/a?q=1',target,[])

class InstanceRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def check_instance(self,instance):
        b=Browser();b.instance='old';b.target_id='old-target';b.observation={'id':'old-input'};b.tab_refs={'old-target':object()};b.recoveries={'old-target':[1]}
        connection=SimpleNamespace(is_connected=lambda:True)
        b.connection=connection
        b.playwright=SimpleNamespace(stop=AsyncMock())
        replacement=SimpleNamespace(chromium=SimpleNamespace(connect_over_cdp=AsyncMock(return_value=connection)))
        manager=SimpleNamespace(start=AsyncMock(return_value=replacement))
        with tempfile.TemporaryDirectory() as directory:
            state=Path(directory)
            (state/'browser-endpoint.json').write_text(json.dumps({'url':f'http://127.0.0.1:{CDP_PORT}','pid':123,'instance':instance}))
            with patch('hub.browser.STATE',state),patch('hub.browser.psutil.pid_exists',return_value=True),patch('playwright.async_api.async_playwright',return_value=manager):
                await b.connect(ready=False)
        return b
    async def test_restarted_instance_discards_stale_identity(self):
        b=await self.check_instance('new')
        self.assertIsNone(b.target_id);self.assertIsNone(b.observation)
        self.assertEqual(b.tab_refs,{});self.assertEqual(b.recoveries,{})
    async def test_same_instance_keeps_explicit_selection(self):
        b=await self.check_instance('old')
        self.assertEqual(b.target_id,'old-target')
        self.assertEqual(b.observation,{'id':'old-input'})

if __name__=='__main__':unittest.main()
