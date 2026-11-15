"""Execute the actual Engine.run browser completion conditional in isolation."""
import ast
import copy
import time
from pathlib import Path

import hub.browser_goal_board as goal_board

ENGINE=Path(__file__).resolve().parents[1]/"hub"/"engine.py"


def _gate(monkeypatch, board, actions, *, strict):
    source=ENGINE.read_text(encoding="utf-8")
    tree=ast.parse(source)
    found=[
        node for node in ast.walk(tree)
        if isinstance(node,ast.If)
        and "task['mode']" in ast.unparse(node.test)
        and "'browser'" in ast.unparse(node.test)
        and any(isinstance(child,ast.ImportFrom) and child.module=="browser_goal_board"
                for child in node.body)
        and any(isinstance(child,ast.If) and any(
            isinstance(grand,ast.ImportFrom) and grand.module=="agent_runtime_v2.engine_gate"
            for grand in child.body) for child in node.body)
    ]
    assert len(found)==1, "Real Engine.run browser gate must have exactly one callsite"
    class FakeBoardStore:
        def read(self,task_id):
            assert task_id=="test-task"
            return board
    monkeypatch.setattr(goal_board,"BoardStore",FakeBoardStore)
    if strict:
        monkeypatch.setenv("AGENT_RUNTIME_V2_GOAL_GATE","1")
    else:
        monkeypatch.delenv("AGENT_RUNTIME_V2_GOAL_GATE",raising=False)
    module=ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(found[0])],type_ignores=[]))
    env={"task":{"mode":"browser"},"task_id":"test-task","actions":actions,
         "verified_goal":True,"__package__":"hub","__name__":"hub.engine.test"}
    exec(compile(module,str(ENGINE),"exec"),env)
    return env["verified_goal"]


def page(url):
    return {"tool":"browser_observe","state":"complete",
            "result":{"coherent":True,"url":url,"title":"Walla","elements":[]}}


def assessment(goal):
    return {"tool":"browser_assess","state":"complete","result":{
        "status":"success","verified":True,"goal_verified":True,
        "original_goal":goal,"checked_at":time.time()}}


def test_real_engine_flag_off_preserves_legacy_search_policy(monkeypatch):
    board=goal_board.seeded("Find the exact result on Walla")
    assert _gate(monkeypatch,board,[page("https://www.walla.co.il/")],strict=False)


def test_real_engine_flag_on_blocks_search_homepage_as_false_completion(monkeypatch):
    board=goal_board.seeded("Find the exact result on Walla")
    assert not _gate(monkeypatch,board,[page("https://www.walla.co.il/")],strict=True)


def test_real_engine_flag_on_accepts_goal_bound_search_assessment(monkeypatch):
    board=goal_board.seeded("Find the exact result on Walla")
    assert _gate(monkeypatch,board,[page("https://www.walla.co.il/search"),
                                   assessment(board["goal"])],strict=True)


def test_real_engine_flag_on_homepage_and_host_safety(monkeypatch):
    board=goal_board.seeded("Open Walla homepage")
    assert _gate(monkeypatch,board,[page("https://www.walla.co.il/")],strict=True)
    assert not _gate(monkeypatch,board,[page("https://walla.co.il.evil.invalid/")],strict=True)


def test_real_engine_login_guard_remains_when_flag_off(monkeypatch):
    board=goal_board.seeded("Open Walla and show login form")
    assert not _gate(monkeypatch,board,[page("https://www.walla.co.il/")],strict=False)


def test_real_engine_strict_fails_closed_when_board_missing(monkeypatch):
    assert not _gate(monkeypatch,None,[page("https://www.walla.co.il/")],strict=True)


def test_other_completion_protections_remain_present():
    source=ENGINE.read_text(encoding="utf-8")
    assert "if completion_check(actions) is False or not verified_goal:" in source
    assert "verified_tab_close" in source
    assert "missing_document_outputs" in source
