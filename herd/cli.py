"""herd: an orchestrator Claude chat spawns, tracks, closes and restores
labelled worker chats in Herdr tabs. See docs/specs/2026-09-25-herd-design.md."""

import argparse
import os
import shutil
import sys
from pathlib import Path

from herd.herdr import Herdr, HerdrError
from herd.registry import Registry, RegistryError, new_worker, now, slugify, state_dir

MODEL_IDS = {"opus": "claude-opus-5-5", "fable": "claude-fable-5-1"}
REVIEW = "👀 "
OPEN_STATES = ("live", "handed-off", "review", "detached")


class HerdError(Exception):
    pass


def tab_label(w: dict) -> str:
    label = f"{w['model']} · {w['label']}"
    return REVIEW + label if w["status"] == "review" else label


def claude_args(session_id: str, name: str, model: str, resume: bool) -> list:
    args = ["--resume" if resume else "--session-id", session_id]
    if name:
        args += ["--name", name]
    return args + ["--model", MODEL_IDS[model], "--dangerously-skip-permissions"]


def kickoff(w: dict, orch_name: str) -> str:
    return (f'You are a herd worker named "{w["label"]}". Load the herd-worker skill now. '
            f'Your orchestrator\'s SendMessage name is "{orch_name}". '
            f'Your brief is at {w["brief"]}. Read it and start.')


def current_registry(slug=None) -> Registry:
    if slug:
        return Registry.load(slug)
    ws = os.environ.get("HERDR_WORKSPACE_ID")
    r = Registry.find_by_workspace(ws) if ws else None
    if r is None:
        raise HerdError("this workspace has no orchestrator; pass --orch <slug> (see: herd ls) or run herd init")
    return r


def need_worker(r: Registry, name: str) -> dict:
    w = r.worker(name)
    if w is None:
        raise HerdError(f"no worker {name!r} in {r.slug}")
    return w


def set_status(w: dict, status: str) -> None:
    w["status"] = status
    w["updated_at"] = now()


# commands

def cmd_init(a) -> None:
    ws, pane = os.environ.get("HERDR_WORKSPACE_ID"), os.environ.get("HERDR_PANE_ID")
    if not ws or not pane:
        raise HerdError("HERDR_WORKSPACE_ID or HERDR_PANE_ID missing; run herd init from the orchestrator's own pane")
    h = Herdr()
    existing = Registry.find_by_workspace(ws)
    if existing:
        raise HerdError(f"workspace {ws} already belongs to orchestrator {existing.slug}")
    mine = next((x for x in h.agents() if x.get("pane_id") == pane), None)
    sid = ((mine or {}).get("agent_session") or {}).get("value")
    if not sid:
        raise HerdError(f"herdr reports no Claude session in pane {pane}; cannot record the orchestrator")
    r = Registry.create(a.label, workspace_id=ws, cwd=(mine.get("cwd") or os.getcwd()), orchestrator={
        "name": a.name, "session_id": sid, "model": a.model, "pane_id": pane, "tab_id": mine.get("tab_id")})
    r.save()
    h.workspace_rename(ws, f"◆ {a.label}")
    print(f"orchestrator {r.slug} in {ws} (session {sid})")


def cmd_spawn(a) -> None:
    r = current_registry(a.orch)
    h = Herdr()
    brief_src = Path(a.brief).expanduser()
    if not brief_src.is_file():
        raise HerdError(f"brief not found: {brief_src}")
    w = new_worker(r, a.label, model=a.model, why=a.why, cwd=str(Path(a.cwd or r.data["cwd"]).expanduser()), brief="")
    briefs = state_dir() / r.slug / "briefs"
    briefs.mkdir(parents=True, exist_ok=True)
    w["brief"] = str(briefs / f"{w['slug']}.md")
    shutil.copyfile(brief_src, w["brief"])
    r.data["workers"].append(w)
    r.save()
    try:
        w["tab_id"], w["pane_id"] = h.tab_create(r.data["workspace_id"], tab_label(w), w["cwd"])
        r.save()
        h.agent_start(w["slug"], w["pane_id"], claude_args(w["session_id"], w["label"], w["model"], resume=False))
        h.agent_prompt(w["slug"], kickoff(w, r.data["orchestrator"].get("name", "")))
    except HerdrError as e:
        set_status(w, "failed")
        w["error"] = str(e)
        r.save()
        raise
    set_status(w, "live")
    r.save()
    print(f"spawned {w['label']} as {w['slug']} on {w['model']} in {w['tab_id']} (session {w['session_id']})")


def cmd_handoff(a) -> None:
    r = current_registry(a.orch)
    w = need_worker(r, a.label)
    text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text()
    if not text.strip():
        raise HerdError("handoff text is empty")
    w["handoff"] = {"text": text.strip(), "at": now()}
    set_status(w, "handed-off")
    r.save()
    print(f"handoff recorded for {w['label']}")


def cmd_mark_review(a) -> None:
    r = current_registry(a.orch)
    w = need_worker(r, a.label)
    set_status(w, "review")
    w["review_reason"] = a.reason
    r.save()
    if w.get("tab_id"):
        Herdr().tab_rename(w["tab_id"], tab_label(w))
    print(f"{w['label']} awaits review")


def cmd_close(a) -> None:
    r = current_registry(a.orch)
    w = need_worker(r, a.label)
    if w["status"] == "closed":
        print(f"{w['label']} is already closed")
        return
    if not w.get("handoff") and not a.force:
        raise HerdError(f"{w['label']} has no handoff on record; record one first or pass --force")
    h = Herdr()
    agent = h.live_sessions().get(w["session_id"])
    if agent and agent.get("agent_status") == "working":
        raise HerdError(f"{w['label']} is still working; not closing")
    if w.get("tab_id") and any(t["tab_id"] == w["tab_id"] for t in h.tabs()):
        h.tab_close(w["tab_id"])
    set_status(w, "closed")
    w["closed_at"] = now()
    r.save()
    print(f"closed {w['label']} (restore with: herd restore {r.slug} {w['slug']})")


def sync(r: Registry, h: Herdr) -> list:
    live = h.live_sessions()
    changed = []
    for w in r.data["workers"]:
        if w["status"] in ("live", "handed-off", "review") and w["session_id"] not in live:
            set_status(w, "detached")
            changed.append(w["label"])
        elif w["session_id"] in live:
            w["tab_id"] = live[w["session_id"]].get("tab_id") or w.get("tab_id")
            w["pane_id"] = live[w["session_id"]].get("pane_id") or w.get("pane_id")
    r.save()
    return changed


def cmd_sync(a) -> None:
    r = current_registry(a.orch)
    changed = sync(r, Herdr())
    print(f"detached: {', '.join(changed)}" if changed else "in sync")


def cmd_status(a) -> None:
    r = current_registry(a.orch)
    o = r.data["orchestrator"]
    print(f"◆ {r.data['label']}  [{r.slug}]  workspace {r.data['workspace_id']}  orchestrator {o.get('name')} ({o.get('model')})")
    for w in r.data["workers"]:
        last = (w.get("handoff") or {}).get("text", "").splitlines()
        tail = last[1] if len(last) > 1 else (last[0] if last else "")
        print(f"  {w['status']:<10} {w['model']:<5} {w['label']:<28} {w.get('tab_id') or '':<8} {tail[:60]}")


def cmd_ls(a) -> None:
    for r in Registry.all():
        counts = {}
        for w in r.data["workers"]:
            counts[w["status"]] = counts.get(w["status"], 0) + 1
        summary = ", ".join(f"{n} {s}" for s, n in sorted(counts.items())) or "no workers"
        print(f"{r.slug:<28} {r.data['label']:<32} {r.data['workspace_id']:<6} {summary}")


def restore_one(r: Registry, h: Herdr, include_closed: bool, labels: list) -> None:
    live = h.live_sessions()
    names = {a.get("name") for a in h.agents() if a.get("name")}
    ws_ids = {x["workspace_id"] for x in h.workspaces()}
    o = r.data["orchestrator"]
    if r.data["workspace_id"] not in ws_ids:
        ws, tab, pane = h.workspace_create(f"◆ {r.data['label']}", r.data["cwd"])
        r.data["workspace_id"] = ws
        r.save()
        if o.get("session_id") not in live:
            h.agent_start(slugify("orch-" + r.slug, names), pane, claude_args(o["session_id"], "", o.get("model", "fable"), resume=True))
            o.update(tab_id=tab, pane_id=pane)
            r.save()
        print(f"rebuilt workspace {ws} for {r.slug}")
    elif o.get("session_id") and o["session_id"] not in live:
        tab, pane = h.tab_create(r.data["workspace_id"], f"◆ {r.data['label']}", r.data["cwd"])
        h.agent_start(slugify("orch-" + r.slug, names), pane, claude_args(o["session_id"], "", o.get("model", "fable"), resume=True))
        o.update(tab_id=tab, pane_id=pane)
        r.save()
    wanted = [need_worker(r, l) for l in labels] if labels else [
        w for w in r.data["workers"] if w["status"] in OPEN_STATES or (include_closed and w["status"] == "closed")]
    for w in wanted:
        if w["session_id"] in live:
            print(f"  {w['label']}: already open")
            continue
        if w["status"] in ("detached", "closed", "failed"):
            set_status(w, "handed-off" if w.get("handoff") else "live")
        name = slugify(w["slug"], names)
        names.add(name)
        w["tab_id"], w["pane_id"] = h.tab_create(r.data["workspace_id"], tab_label(w), w["cwd"])
        r.save()
        h.agent_start(name, w["pane_id"], claude_args(w["session_id"], w["label"], w["model"], resume=True))
        w["slug"] = name
        r.save()
        print(f"  {w['label']}: resumed in {w['tab_id']}")


def cmd_restore(a) -> None:
    h = Herdr()
    if a.every:
        regs = Registry.all()
    else:
        regs = [current_registry(a.orch)]
    for r in regs:
        restore_one(r, h, include_closed=a.all, labels=a.labels if not a.every else [])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="herd", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        s = sub.add_parser(name, help=help_)
        s.set_defaults(fn=fn)
        return s

    s = add("init", cmd_init, "adopt this Herdr workspace for the orchestrator chat in this pane")
    s.add_argument("label")
    s.add_argument("--name", required=True, help="this chat's SendMessage name (as ListAgents shows it)")
    s.add_argument("--model", choices=MODEL_IDS, default="fable")

    s = add("spawn", cmd_spawn, "open a labelled tab and start a worker chat")
    s.add_argument("label")
    s.add_argument("--model", choices=MODEL_IDS, required=True)
    s.add_argument("--why", required=True, help="one line: why this model")
    s.add_argument("--brief", required=True, help="markdown brief file")
    s.add_argument("--cwd")

    s = add("handoff", cmd_handoff, "record a worker's HERD HANDOFF message")
    s.add_argument("label")
    s.add_argument("--file", required=True, help="file with the handoff text, or - for stdin")

    s = add("mark-review", cmd_mark_review, "flag a worker as awaiting Eddy's review")
    s.add_argument("label")
    s.add_argument("--reason", default="")

    s = add("close", cmd_close, "close a worker's tab after its handoff")
    s.add_argument("label")
    s.add_argument("--force", action="store_true", help="close without a recorded handoff")

    add("status", cmd_status, "workers of this orchestrator")
    add("ls", cmd_ls, "every orchestrator on record")
    add("sync", cmd_sync, "mark workers whose tabs vanished as detached")

    s = add("restore", cmd_restore, "reopen an orchestrator and its workers")
    s.add_argument("labels", nargs="*", help="only these workers")
    s.add_argument("--all", action="store_true", help="include closed workers")
    s.add_argument("--every", action="store_true", help="every orchestrator on record")

    for sp in sub.choices.values():
        sp.add_argument("--orch", help="orchestrator slug (default: the one owning this workspace)")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "restore" and args.labels and not args.orch:
        # `herd restore <orch> [labels]`: first positional names the orchestrator when it is one
        if (state_dir() / f"{args.labels[0]}.json").exists():
            args.orch, args.labels = args.labels[0], args.labels[1:]
    try:
        args.fn(args)
    except (HerdError, HerdrError, RegistryError) as e:
        print(f"herd: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
