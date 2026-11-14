import tempfile
from pathlib import Path
from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch
from hub import desktop_runtime as d

@contextmanager
def admitted():
    yield True

class DesktopRuntimeTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        for name,value in [('STATE',Path(self.temp.name)),('_admission',admitted)]:
            p=patch.object(d,name,value);p.start();self.addCleanup(p.stop)
        p=patch('hub.power.transition_active',return_value=False);p.start();self.addCleanup(p.stop)

    def ready(self):
        return dict(ready=True,state='operational',process_count=1,pid=77,owned=True)

    def test_absent_status_does_not_launch(self):
        with patch.object(d.health,'inventory',return_value={}),patch.object(d,'_launch') as launch:
            self.assertEqual(d.status()['state'],'stopped');launch.assert_not_called()

    def test_foreign_process_not_trusted(self):
        with patch.object(d.health,'inventory',return_value={'desktop':[dict(pid=77,owned=False)]}),patch.object(d,'_ipc') as ipc:
            self.assertEqual(d.status()['state'],'blocked');ipc.assert_not_called()

    def test_wrong_ipc_pid_rejected(self):
        with patch.object(d.health,'inventory',return_value={'desktop':[dict(pid=77,owned=True)]}),patch.object(d,'_ipc',return_value=dict(pid=88,ready=True)):
            self.assertFalse(d.status()['ready'])

    def test_readiness_requires_cdp(self):
        with patch.object(d.health,'inventory',return_value={'desktop':[dict(pid=77,owned=True)]}),patch.object(d,'_ipc',return_value=dict(pid=77,ready=True)),patch.object(d,'_cdp',return_value=False):
            self.assertEqual(d.status()['state'],'unverified')

    def test_existing_reused_and_shown(self):
        with patch.object(d,'status',return_value=self.ready()),patch.object(d,'_ipc',return_value=dict(pid=77,ready=True,visible=True)),patch.object(d,'_launch') as launch:
            self.assertTrue(d.open_desktop('one')['ready']);launch.assert_not_called()

    def test_request_id_no_replay(self):
        with patch.object(d,'status',return_value=self.ready()),patch.object(d,'_ipc',return_value=dict(pid=77,ready=True,visible=True)) as ipc:
            d.open_desktop('same');d.open_desktop('same')
            self.assertEqual(ipc.call_count,1)
            with self.assertRaises(ValueError):d.open_desktop('same',False)

    def test_unresponsive_owned_process_not_duplicated(self):
        with patch.object(d,'status',return_value=dict(ready=False,process_count=1,reason='IPC timeout')),patch.object(d,'_launch') as launch:
            self.assertEqual(d.open_desktop('hung')['state'],'blocked');launch.assert_not_called()

    def test_session_zero_requires_user(self):
        with patch.object(d,'status',return_value=dict(ready=False,process_count=0)),patch.object(d,'_session',return_value=0),patch.object(d,'_launch') as launch:
            self.assertEqual(d.open_desktop('session')['state'],'requires_user_action');launch.assert_not_called()

    def test_power_transition_blocks(self):
        with patch('hub.power.transition_active',return_value=True),patch.object(d,'_launch') as launch:
            self.assertEqual(d.open_desktop('power')['state'],'blocked');launch.assert_not_called()

    def test_launch_then_verify(self):
        with patch.object(d,'status',side_effect=[dict(ready=False,process_count=0),self.ready()]),patch.object(d,'_session',return_value=1),patch.object(d,'_launch',return_value=77) as launch:
            result=d.open_desktop('new',False)
            self.assertTrue(result['ready']);self.assertEqual(result['launched_pid'],77);launch.assert_called_once()

    def test_launch_failure_not_success(self):
        with patch.object(d,'status',return_value=dict(ready=False,process_count=0)),patch.object(d,'_session',return_value=1),patch.object(d,'_launch',side_effect=OSError('missing')):
            self.assertEqual(d.open_desktop('failure')['state'],'failed')

    def test_grace_period_no_second_launch(self):
        d.health.write(d.STATE/'desktop-launch-last.json',dict(started_at=d.time.time()))
        with patch.object(d,'status',return_value=dict(ready=False,process_count=0)),patch.object(d,'_session',return_value=1),patch.object(d,'_launch') as launch:
            self.assertEqual(d.open_desktop('grace')['state'],'starting');launch.assert_not_called()

    def test_concurrent_admission_no_launch(self):
        @contextmanager
        def busy():yield False
        with patch.object(d,'_admission',busy),patch.object(d,'_launch') as launch:
            self.assertEqual(d.open_desktop('busy')['state'],'starting');launch.assert_not_called()
