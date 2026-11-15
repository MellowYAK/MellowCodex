"""P05: existing editable Goal Board -> typed, safe V2 TaskPlan adapter."""
import pytest

from hub.agent_runtime_v2.contracts import TaskLifecycle, TaskPlan
from hub.agent_runtime_v2.goal_board_adapter import adapt_board
from hub.agent_runtime_v2.persistence import PlanRepository
from hub.browser_goal_board import BoardStore, seeded, progress


def test_walla_login_plan_has_exact_form_and_host_success_conditions():
    board=seeded("Open וואלה Walla and find the התחברות form")
    plan=adapt_board(board,"task-1")
    assert plan.status is TaskLifecycle.CREATED
    assert plan.goal==board["goal"]
    assert [s.id for s in plan.steps]==[x["id"] for x in board["steps"]]
    assert [s.dependencies for s in plan.steps]==[[],["entry"],["discover"],["act"]]
    final=plan.completion_criteria[0]
    assert final.required
    assert final.verifier_type=="dom"
    assert final.expected["login_form"] is True
    assert final.expected["required_host"]=="walla.co.il"
    assert final.expected["verified_assessment"] is True
    assert final.expected["final_goal_verified"] is True


@pytest.mark.parametrize("mode",["browser","code","desktop","inspect"])
def test_mode_specific_tool_and_final_evidence_contract(mode):
    board=seeded("Perform the requested objective",task_mode=mode)
    plan=adapt_board(board,"t")
    assert len(plan.steps)==4
    assert all(step.allowed_tool_classes for step in plan.steps)
    assert all(step.acceptance[0].required for step in plan.steps)
    assert plan.completion_criteria[0].expected["final_goal_verified"] is True
    if mode!="browser":
        assert plan.completion_criteria[0].expected["terminal_task_state"]=="done"
        assert "browser_act" not in plan.steps[-1].allowed_tool_classes


def test_user_edit_notes_alternatives_and_board_revision_survive(tmp_path):
    store=BoardStore(tmp_path/"boards.sqlite")
    original=store.ensure("task","Open Walla and find login",task_mode="browser")
    steps=[dict(s) for s in original["steps"]]
    steps[1]["expected"]="Find the exact כניסה entry"
    steps[1]["alternatives"]=["Use the footer", "Search in menu"]
    updated=store.update("task",1,steps=steps,notes="Try secondary menu",editor="user")
    p=adapt_board(updated,"task",plan_version=2)
    assert p.version==2 and p.created_from_revision==2
    assert p.steps[1].acceptance[0].description=="Find the exact כניסה entry"
    assert "Use the footer" in p.steps[1].objective
    assert "Try secondary menu" in p.constraints[-1]
    assert TaskPlan.model_validate_json(p.model_dump_json())==p


def test_preserve_original_language_without_credentials():
    board=seeded("Перейди в כניסה на וואלה и найди התחברות, password=secret123")
    plan=adapt_board(board,"t")
    assert "Перейди" in plan.goal and "כניסה" in plan.goal
    assert "secret123" not in plan.model_dump_json()
    board["notes"]="Do not enter password=123456"
    plan=adapt_board(board,"t")
    assert "123456" not in plan.model_dump_json()
    assert "REDACTED" in plan.model_dump_json()


def test_adapter_does_not_promote_old_generic_done_to_verified_plan():
    board=seeded("Modify code and test",task_mode="code")
    action={"tool":"context_search","state":"complete","result":{"items":[1]}}
    assert progress(board,[action],task_state="done")["done"]  # existing known gap
    plan=adapt_board(board,"t")
    assert plan.status is TaskLifecycle.CREATED
    assert plan.completion_criteria[0].expected["final_goal_verified"] is True


def test_adapter_does_not_assert_wrong_host_form_verification():
    board=seeded("Open Walla and find sign-in")
    plan=adapt_board(board,"t")
    assert plan.steps[-1].acceptance[0].expected["required_host"]=="walla.co.il"
    assert "attacker.example" not in plan.model_dump_json()
    assert plan.status is TaskLifecycle.CREATED


def test_plan_serializes_and_persists_with_existing_goal_board_untouched(tmp_path):
    board=seeded("Open Walla and reach login")
    p=adapt_board(board,"task-1")
    repo=PlanRepository(tmp_path/"v2.db")
    repo.ensure_schema()
    assert repo.write_plan(p,expected_revision=0)==1
    result,revision=repo.read_current("task-1")
    assert result==p and revision==1
    assert board["steps"][0]["role"]=="entry"
    assert all("status" not in item for item in board["steps"])


def test_bad_mode_goal_or_steps_fail_closed():
    b=seeded("Find login at Walla")
    with pytest.raises(ValueError):
        adapt_board({**b,"task_mode":"unknown"},"t")
    with pytest.raises(ValueError):
        adapt_board({**b,"goal":" "},"t")
    with pytest.raises(ValueError):
        adapt_board({**b,"steps":[b["steps"][0]]},"t")
    with pytest.raises(ValueError):
        adapt_board({**b,"target_host":"evil.example/login?token=bad"},"t")


def test_plan_version_validation_and_board_revision_explicit():
    b=seeded("Find login on Walla")
    b["revision"]=8
    p=adapt_board(b,"t",plan_version=3)
    assert p.version==3 and p.created_from_revision==8
    p=adapt_board(b,"t",created_from_revision=4)
    assert p.created_from_revision==4
    with pytest.raises(ValueError):
        adapt_board(b," ",plan_version=1)
