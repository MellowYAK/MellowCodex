import ctypes
from unittest.mock import Mock
import pytest
from hub import desktop as m
@pytest.fixture
def d():
 d=m.Desktop.__new__(m.Desktop)
 d.user=Mock();d._validate_target_point=Mock();d._send=Mock();d.guard=Mock(return_value={"left":0,"top":0,"width":100,"height":100});d.stopped=False
 d.user.SetCursorPos.return_value=1
 def pos(ptr):
  ptr._obj.x=30;ptr._obj.y=40;return 1
 d.user.GetCursorPos.side_effect=pos
 return d
def click(d):
 return d.act({"observation_id":"mock","action":"click","x":30,"y":40})
def test_rejected_move_never_clicks(d):
 d.user.SetCursorPos.return_value=0
 with pytest.raises(m.ObservationError,match="rejected cursor movement"):click(d)
 d._send.assert_not_called()
def test_position_mismatch_never_clicks(d):
 def pos(ptr):ptr._obj.x=31;ptr._obj.y=40;return 1
 d.user.GetCursorPos.side_effect=pos
 with pytest.raises(m.ObservationError,match="did not reach"):click(d)
 d._send.assert_not_called()
def test_query_failure_never_scrolls(d):
 d.user.GetCursorPos.side_effect=lambda p:0
 with pytest.raises(m.ObservationError,match="position query"):d.act({"observation_id":"mock","action":"scroll","amount":1})
 d._send.assert_not_called()
def test_valid_click_sends_two_events(d):
 click(d);assert d._send.call_count==2
def test_cursor_changed_between_move_and_click(d):
 calls=iter([(30,40),(31,40)])
 def pos(ptr):ptr._obj.x,ptr._obj.y=next(calls);return 1
 d.user.GetCursorPos.side_effect=pos
 with pytest.raises(m.ObservationError,match="changed before click"):click(d)
 d._send.assert_not_called()
def test_drag_releases_on_movement_failure(d):
 d.user.SetCursorPos.side_effect=[1,0]
 with pytest.raises(m.ObservationError,match="rejected cursor movement"):
  d.act({"observation_id":"mock","action":"drag","x":30,"y":40,"end_x":50,"end_y":60})
 assert [c.kwargs["flags"] for c in d._send.call_args_list]==[2,4]
