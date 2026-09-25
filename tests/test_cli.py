import json

import pytest

from herd import cli
from herd.registry import Registry


@pytest.fixture
def orch(fake, monkeypatch, tmp_path):
    """An orchestrator chat live in pane w1:p1 of workspace w1."""
    monkeypatch.setenv("HERDR_WORKSPACE_ID", "w1")
    monkeypatch.setenv("HERDR_PANE_ID", "w1:p1")
    fake.seed(workspaces={"w1": {"label": "old"}},
              tabs={"w1:t1": {"label": "1", "workspace_id": "w1", "pane_id": "w1:p1"}},
              agents=[{"agent": "claude", "pane_id": "w1:p1", "tab_id": "w1:t1", "agent_status": "working",
                       "agent_session": {"kind": "id", "value": "orch-sid"}}])
    assert cli.main(["init", "fc: postiz", "--name", "Herta and agent messaging"]) == 0
    brief = tmp_path / "brief.md"
    brief.write_text("Write the drip copy.")
    return brief


def reg():
    return Registry.load("fc-postiz")


def test_init_records_orchestrator_and_labels_workspace(fake, orch):
    r = reg()
    assert r.data["orchestrator"]["session_id"] == "orch-sid"
    assert r.data["orchestrator"]["name"] == "Herta and agent messaging"
    assert fake.world()["workspaces"]["w1"]["label"] == "◆ fc: postiz"


def test_init_refuses_second_orchestrator_in_same_workspace(fake, orch, capsys):
    assert cli.main(["init", "other", "--name", "x"]) == 1
    assert "already" in capsys.readouterr().err


def test_init_fails_loud_when_own_session_unknown(fake, monkeypatch, capsys):
    monkeypatch.setenv("HERDR_WORKSPACE_ID", "w9")
    monkeypatch.setenv("HERDR_PANE_ID", "w9:p9")
    assert cli.main(["init", "o", "--name", "x"]) == 1
    assert "session" in capsys.readouterr().err


def test_spawn_registers_before_tab_and_starts_claude(fake, orch):
    assert cli.main(["spawn", "Drip copy", "--model", "opus", "--why", "bounded copy", "--brief", str(orch)]) == 0
    w = reg().worker("drip copy")
    assert w["status"] == "live" and w["tab_id"] and w["model"] == "opus"
    calls = fake.calls()
    create = next(c for c in calls if c[:2] == ["tab", "create"])
    assert create[create.index("--label") + 1] == "opus · Drip copy"
    start = next(c for c in calls if c[:2] == ["agent", "start"])
    claude = start[start.index("--") + 1:]
    assert claude[:6] == ["--session-id", w["session_id"], "--name", "Drip copy", "--model", "claude-opus-5-5"]
    prompt = next(c for c in calls if c[:2] == ["agent", "prompt"])
    assert "herd-worker" in prompt[3] and "Herta and agent messaging" in prompt[3] and w["brief"] in prompt[3]
    assert open(w["brief"]).read() == "Write the drip copy."


def test_spawn_fable_uses_fable_model(fake, orch):
    cli.main(["spawn", "Pricing review", "--model", "fable", "--why", "tradeoffs", "--brief", str(orch)])
    start = next(c for c in fake.calls() if c[:2] == ["agent", "start"])
    assert "claude-fable-5-1" in start


def test_spawn_failure_marks_failed_and_exits_1(fake, orch, monkeypatch, capsys):
    monkeypatch.setenv("FAKE_HERDR_FAIL", "agent start")
    assert cli.main(["spawn", "Drip", "--model", "opus", "--why", "x", "--brief", str(orch)]) == 1
    w = reg().worker("drip")
    assert w["status"] == "failed" and "injected failure" in w["error"]
    assert "injected failure" in capsys.readouterr().err


def test_same_slug_labels_get_distinct_names(fake, orch):
    cli.main(["spawn", "Drip copy", "--model", "opus", "--why", "x", "--brief", str(orch)])
    cli.main(["spawn", "drip-copy", "--model", "opus", "--why", "x", "--brief", str(orch)])
    names = [c[2] for c in fake.calls() if c[:2] == ["agent", "start"]]
    assert names == ["drip-copy", "drip-copy-2"]


def spawn(orch, label="Drip"):
    assert cli.main(["spawn", label, "--model", "opus", "--why", "x", "--brief", str(orch)]) == 0
    return reg().worker(label)


def test_close_refuses_without_handoff(fake, orch, capsys):
    spawn(orch)
    assert cli.main(["close", "Drip"]) == 1
    assert "handoff" in capsys.readouterr().err
    assert reg().worker("drip")["status"] == "live"


def test_close_refuses_while_working(fake, orch, tmp_path, capsys):
    w = spawn(orch)
    world = fake.world()
    for a in world["agents"]:
        if a.get("tab_id") == w["tab_id"]:
            a["agent_status"] = "working"
    fake.seed(agents=world["agents"])
    (tmp_path / "h.txt").write_text("HERD HANDOFF Drip\ncomplete: yes")
    cli.main(["handoff", "Drip", "--file", str(tmp_path / "h.txt")])
    assert cli.main(["close", "Drip"]) == 1
    assert "working" in capsys.readouterr().err
    assert w["tab_id"] in fake.world()["tabs"]


def test_handoff_then_close(fake, orch, tmp_path):
    w = spawn(orch)
    (tmp_path / "h.txt").write_text("HERD HANDOFF Drip\ncomplete: yes")
    assert cli.main(["handoff", "Drip", "--file", str(tmp_path / "h.txt")]) == 0
    assert reg().worker("drip")["status"] == "handed-off"
    assert cli.main(["close", "Drip"]) == 0
    assert reg().worker("drip")["status"] == "closed"
    assert w["tab_id"] not in fake.world()["tabs"]


def test_mark_review_adds_eyes_to_tab(fake, orch):
    w = spawn(orch)
    assert cli.main(["mark-review", "Drip", "--reason", "new layout"]) == 0
    assert fake.world()["tabs"][w["tab_id"]]["label"] == "👀 opus · Drip"
    assert reg().worker("drip")["status"] == "review"


def test_sync_marks_vanished_tabs_detached(fake, orch):
    w = spawn(orch)
    world = fake.world()
    del world["tabs"][w["tab_id"]]
    world["agents"] = [a for a in world["agents"] if a.get("tab_id") != w["tab_id"]]
    fake.seed(tabs=world["tabs"], agents=world["agents"])
    assert cli.main(["sync"]) == 0
    assert reg().worker("drip")["status"] == "detached"


def test_restore_skips_live_and_resumes_the_rest(fake, orch):
    a = spawn(orch, "Alpha")
    b = spawn(orch, "Beta")
    world = fake.world()
    del world["tabs"][b["tab_id"]]
    world["agents"] = [x for x in world["agents"] if x.get("tab_id") != b["tab_id"]]
    fake.seed(tabs=world["tabs"], agents=world["agents"])
    before = len(fake.calls())
    assert cli.main(["restore"]) == 0
    starts = [c for c in fake.calls()[before:] if c[:2] == ["agent", "start"]]
    assert len(starts) == 1
    claude = starts[0][starts[0].index("--") + 1:]
    assert claude[:2] == ["--resume", b["session_id"]]
    assert reg().worker("beta")["status"] == "live"


def test_restore_skips_closed_unless_all(fake, orch, tmp_path):
    spawn(orch)
    (tmp_path / "h.txt").write_text("done")
    cli.main(["handoff", "Drip", "--file", str(tmp_path / "h.txt")])
    cli.main(["close", "Drip"])
    before = len(fake.calls())
    cli.main(["restore"])
    assert not [c for c in fake.calls()[before:] if c[:2] == ["agent", "start"]]
    cli.main(["restore", "--all"])
    assert [c for c in fake.calls()[before:] if c[:2] == ["agent", "start"]]


def test_restore_rebuilds_missing_workspace_with_orchestrator(fake, orch, monkeypatch):
    spawn(orch)
    fake.seed(workspaces={}, tabs={}, agents=[])
    monkeypatch.setenv("HERDR_WORKSPACE_ID", "w-elsewhere")
    assert cli.main(["restore", "fc-postiz"]) == 0
    calls = fake.calls()
    assert any(c[:2] == ["workspace", "create"] and "◆ fc: postiz" in c for c in calls)
    resumed = [c[c.index("--") + 2] for c in calls if c[:2] == ["agent", "start"] and "--resume" in c]
    assert "orch-sid" in resumed and reg().worker("drip")["session_id"] in resumed
    assert reg().data["workspace_id"] != "w1"


def test_restore_every(fake, orch):
    spawn(orch)
    fake.seed(workspaces={}, tabs={}, agents=[])
    assert cli.main(["restore", "--every"]) == 0
    assert any(c[:2] == ["workspace", "create"] for c in fake.calls())


def test_status_prints_workers(fake, orch, capsys):
    spawn(orch)
    capsys.readouterr()
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "Drip" in out and "opus" in out and "live" in out
