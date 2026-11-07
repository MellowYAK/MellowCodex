import asyncio
from types import SimpleNamespace
import pytest
from hub.tools import ToolRunner
from hub.errors import ObservationError
from hub.visual_review import parse_review

def test_review_requires_explicit_boolean_evidence():
    assert parse_review({'text':'Everything is done'})['passed'] is None
    assert parse_review({'text':'```json\n{"visual_verification":{"passed":false,"reason":"Home page only","next_step":"Open account menu"}}\n```'})['passed'] is False
    assert parse_review({'text':'{"visual_verification":{"passed":"true"}}'})['passed'] is None

def test_accessibility_and_image_share_observation_id(monkeypatch,tmp_path):
    runner=ToolRunner()
    runner.desktop.user=SimpleNamespace(GetForegroundWindow=lambda:42)
    def capture(hwnd,folder):
        runner.desktop.observation={'id':'image-id','hwnd':42}
        return {'id':'image-id','hwnd':42,'path':str(tmp_path/'shot.png')}
    runner.desktop.capture_target=capture
    async def inspect(hwnd):return {'id':'control-id','hwnd':42,'elements':[]}
    runner.accessibility.inspect=inspect
    result=asyncio.run(runner.execute({'id':'visual-id','mode':'desktop'},'window_inspect',{'hwnd':42}))
    assert result['id']==result['after']['id']=='control-id'
    assert runner.desktop.observation['id']=='control-id'

def test_native_target_cannot_switch_to_coordinator():
    runner=ToolRunner();runner.application_targets['task']='Target'
    runner.application_executables['task']='C:/Target.exe'
    runner.desktop.windows=lambda:[{'hwnd':7,'executable':'C:/Coordinator.exe'}]
    with pytest.raises(ObservationError,match='not the requested application'):
        asyncio.run(runner.execute({'id':'task','mode':'desktop'},'focus_window',{'hwnd':7}))

def test_invalid_input_is_recoverable_and_not_executed():
    runner=ToolRunner();runner.desktop.observation=None
    with pytest.raises(ObservationError,match='no action was sent'):
        asyncio.run(runner.execute({'id':'task','mode':'desktop'},'desktop_action',{'action':'click','x':1,'y':2}))


def test_shared_screenshot_is_not_attached_twice(tmp_path):
    from hub.bridge_controller import additional_evidence_image
    original=tmp_path/'original.png';shared=tmp_path/'shared.png';other=tmp_path/'other.png'
    original.write_bytes(b'original screenshot');shared.write_bytes(original.read_bytes());other.write_bytes(b'different screenshot')
    assert additional_evidence_image(original,[shared]) is None
    assert additional_evidence_image(original,[other])==original
    assert additional_evidence_image(original,[])==original


def test_window_fallback_is_not_reported_as_full_desktop():
    runner=ToolRunner();runner.desktop.capture=lambda folder:{'backend':'foreground-window-printwindow'}
    with pytest.raises(ObservationError,match='No partial image'):
        asyncio.run(runner.execute({'id':'capture-test','mode':'desktop'},'capture_screenshot',{'scope':'desktop','share_with_chatgpt':True}))


def test_feedback_uses_current_attempt_not_obsolete_screenshots(tmp_path):
    from hub.bridge_controller import feedback_actions
    from hub.store import Store
    store=Store(tmp_path/'test.sqlite3');task=store.create('Capture screenshot',str(tmp_path),'desktop','capture')
    old=store.begin_action(task['id'],'capture_screenshot',{});store.end_action(old,{'id':'old','share_with_chatgpt':True})
    current=store.begin_action(task['id'],'capture_screenshot',{});store.end_action(current,{'id':'current','share_with_chatgpt':True})
    store.event(task['id'],'verification',{'attempt_action_ids':[current]})
    assert [a['id'] for a in feedback_actions(store,task['id'])]==[current]
    assert len(store.actions(task['id']))==2  # Durable audit evidence is retained.
