"""Thin wrapper over the `herdr` CLI. Every call returns herdr's `result`
object or raises HerdrError with herdr's own message."""

import json
import os
import subprocess


class HerdrError(Exception):
    pass


class Herdr:
    def __init__(self):
        if os.environ.get("HERDR_ENV") != "1":
            raise HerdrError("not inside Herdr (HERDR_ENV is not 1); run herd from a Herdr pane")

    def call(self, *args: str) -> dict:
        try:
            p = subprocess.run(["herdr", *args], capture_output=True, text=True, timeout=120)
        except FileNotFoundError:
            raise HerdrError("herdr binary not found on PATH")
        body = None
        try:
            body = json.loads(p.stdout) if p.stdout.strip() else None
        except json.JSONDecodeError:
            pass
        if p.returncode != 0 or body is None or "error" in body:
            err = (body or {}).get("error") or {}
            msg = err.get("message") or p.stderr.strip() or p.stdout.strip() or f"exit {p.returncode}"
            raise HerdrError(f"herdr {' '.join(args[:2])}: {msg}")
        return body.get("result", {})

    def tab_create(self, workspace_id: str, label: str, cwd: str) -> tuple:
        r = self.call("tab", "create", "--workspace", workspace_id, "--label", label, "--cwd", cwd)
        return r["tab"]["tab_id"], r["root_pane"]["pane_id"]

    def tab_close(self, tab_id: str) -> None:
        self.call("tab", "close", tab_id)

    def tab_rename(self, tab_id: str, label: str) -> None:
        self.call("tab", "rename", tab_id, label)

    def tabs(self) -> list:
        return self.call("tab", "list")["tabs"]

    def workspace_create(self, label: str, cwd: str) -> tuple:
        r = self.call("workspace", "create", "--label", label, "--cwd", cwd)
        return r["workspace"]["workspace_id"], r["tab"]["tab_id"], r["root_pane"]["pane_id"]

    def workspace_rename(self, workspace_id: str, label: str) -> None:
        self.call("workspace", "rename", workspace_id, label)

    def workspaces(self) -> list:
        return self.call("workspace", "list")["workspaces"]

    def agent_start(self, name: str, pane_id: str, claude_args: list) -> None:
        self.call("agent", "start", name, "--kind", "claude", "--pane", pane_id,
                  "--timeout", "60000", "--", *claude_args)

    def agent_prompt(self, name: str, text: str) -> None:
        self.call("agent", "prompt", name, text)

    def agents(self) -> list:
        return self.call("agent", "list")["agents"]

    def live_sessions(self) -> dict:
        """Claude session id -> agent record, for every live agent herdr sees."""
        out = {}
        for a in self.agents():
            sid = (a.get("agent_session") or {}).get("value")
            if sid:
                out[sid] = a
        return out
