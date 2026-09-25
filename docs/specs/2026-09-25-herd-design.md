# herd: orchestrator and worker chats on Herdr

Date: 2026-09-25. Status: draft for review.

## Purpose

One orchestrator chat spawns worker chats, each in its own labelled Herdr tab, running the model the work needs. Workers report back over SendMessage. A worker is closed only on a deliberate decision, never because its task finished. Everything that was ever spawned can be reopened with its conversation intact.

## Agreed rules

- Orchestrator runs Fable. Workers default to Opus; a worker runs Fable only when its own work is mostly judgement (efficient-fable split).
- Chats talk over SendMessage. Only the `herd` CLI touches Herdr (tabs, workspaces, agent start).
- One Herdr workspace per orchestrator (option A): orchestrator is tab 1, one tab per worker.
- Personal tooling: code in `~/code/tools/herd`, skills in `~/.claude/skills/`, state in `~/.local/state/herd/`. Nothing in campaign-central.
- Close rule (section 3).

## Section 1: parts

1. **`herd` CLI**, `herd.py`, stdlib only, run through `uv run --script`, symlinked to `~/.local/bin/herd`. All Herdr calls go through it.
2. **Registry**, one JSON file per orchestrator: `~/.local/state/herd/<orch-slug>.json`. Written atomically (temp file + rename) before any tab opens.
3. **Skills**: `herd-orchestrator` (spawn, model choice, handoffs, close table, asking Eddy) and `herd-worker` (who to report to, handoff format, never close yourself). Both live in the repo and are symlinked into `~/.claude/skills/`.

## Section 2: starting an orchestrator and spawning workers

### `herd init "<label>" --name "<orchestrator SendMessage name>"`

Run by the orchestrator chat inside its own pane. Reads `HERDR_WORKSPACE_ID` and `HERDR_PANE_ID`, looks up its own Claude session id from `herdr agent list` (`agent_session.value`), renames the workspace to `◆ <label>`, and writes the registry with the orchestrator's session id, cwd, name and model. Refuses if that workspace already belongs to another registry.

### `herd spawn "<label>" --model opus|fable --brief <file> [--cwd <dir>]`

1. Generate a uuid; write the worker to the registry with status `starting`.
2. `herdr tab create` in the orchestrator's workspace, label `<model> · <label>`, cwd defaulting to the orchestrator's.
3. `herdr agent start <slug> --kind claude --pane <pane> -- --session-id <uuid> --name "<label>" --model <model id> --dangerously-skip-permissions`. `<slug>` is the label lowercased to `[a-z0-9-]`, max 32, deduplicated.
4. `herdr agent prompt <slug> "<kickoff>"`, where the kickoff says: load the `herd-worker` skill, your orchestrator is `<name>`, your brief is at `<file>` (copied into `~/.local/state/herd/<orch-slug>/briefs/`).
5. Status `live`. Print the tab id and slug.

Any failed step marks the worker `failed` with the error, prints it, and exits non zero. No silent retries.

### Labels

- Workspace: `◆ <orchestrator label>`, e.g. `◆ fc: postiz rollout`.
- Tab: `<model> · <label>`, e.g. `opus · drip copy`, `fable · pricing review`. When a worker is awaiting your review, `herd` renames its tab to `👀 <model> · <label>`.
- Claude session name (what ListAgents and SendMessage show, and what `claude -r` lists): `<label>`.

### Model choice (in `herd-orchestrator`)

Fable when the worker's core output is a decision: architecture, product or safety tradeoffs, reconciling conflicting evidence, final review, anything user facing where tone and judgement matter. Opus for everything bounded: research scans, inventories, implementing a written plan, test runs, bulk edits, data pulls. When unsure, Opus, and the worker may ask the orchestrator to re-spawn on Fable if it hits a judgement wall. The orchestrator states the choice and one-line reason in the registry (`--why`).

## Section 3: handoff and closing

### Handoff

When a worker believes it has finished (or is stuck), it sends the orchestrator one SendMessage:

```
HERD HANDOFF <label>
complete: yes|no (what remains, if no)
review_worthy: yes|no (why Eddy might want to look)
summary: <3 to 6 lines>
artifacts: <paths, urls, commits>
open: <loose ends, or none>
```

The orchestrator records it verbatim: `herd handoff <label> --file <tmp>` (status `handed-off`). The worker then stays idle in its tab; it never closes itself.

### Close decision (orchestrator)

The orchestrator judges relevance itself (it holds the bigger picture); the worker supplies complete and review_worthy.

| complete | no longer relevant | review worthy | action |
|---|---|---|---|
| yes | yes | no | `herd close <label>`; one line in the orchestrator chat |
| yes | yes | yes | `herd mark-review <label>`; tab gets 👀; orchestrator asks Eddy "close X? (worth a look because ...)" and closes only on yes |
| no, or still relevant | | | stays open |

### `herd close <label>`

Refuses unless a handoff is recorded, or `--force` is given. Refuses if the agent is `working`. Closes the tab with `herdr tab close`, status `closed`, keeps everything else. A closed worker is still restorable.

## Section 4: seeing and restoring

- `herd ls` lists orchestrators; `herd status [<orch>]` lists workers with model, status, tab, age, last handoff line. Default orchestrator is the one owning `HERDR_WORKSPACE_ID`.
- `herd sync` compares the registry with `herdr agent list`: a worker whose tab disappeared without `herd close` becomes `detached` (restorable, flagged).
- `herd restore <orch> [--all | <label>...]`:
  - no workspace for it: `herdr workspace create` with the saved label and cwd; orchestrator tab resumes with `claude --resume <orch id>`.
  - default restores every worker that is not `closed` (live, handed-off, review, detached); `--all` includes closed; labels restore just those.
  - each worker: new tab with its saved label, `herdr agent start ... -- --resume <uuid> --name "<label>" --model <model>`.
  - already open workers are skipped, never duplicated (checked by session id against `herdr agent list`).
- `herd restore --every` restores every orchestrator in the registry, for "I deleted the whole thing".

## Compared with what Herdr already gives

| Need | Herdr CLI and skill today | herd adds |
|---|---|---|
| Open a labelled tab or workspace | `tab create --label`, `workspace create --label` | naming convention, model in label, 👀 review marker |
| Start a Claude in a pane | `agent start --kind claude -- <args>`, waits until ready | pre-assigned `--session-id`, `--name`, `--model`, kickoff prompt |
| Talk to an agent | `agent prompt` types into its terminal, `agent read` scrapes output | SendMessage both ways, structured handoff, no screen scraping |
| Know which conversation a pane holds | `agent list` reports `agent_session` while it is live | durable registry that survives tab, workspace and server loss |
| Reopen closed things | undo-close plugin (our fork f1a06fd) reopens a recently closed tab; Claude resume is off (`relaunch_agents: false`) | restore any worker or whole orchestrator by label, any time later |
| Decide when to close | nothing | handoff plus close table, review prompt to Eddy |
| Pick a model | nothing | Fable vs Opus rule, recorded with a reason |

herd uses Herdr's `agent prompt` exactly once per spawn (the kickoff), because a fresh worker has no SendMessage peer yet. After that, all traffic is SendMessage.

## Named Herdr sessions (separate windows)

Not part of herd v1. `herdr --session <name>` gives a separate persistent server that any new terminal window can attach to (`herdr session attach <name>`). herd could later take `--session` to put an orchestrator in its own window; option A keeps everything in `default` for now.

## Testing

- Unit (pytest via uv): registry read/write and atomic save, slug rules, label formats, argv built for `herdr` and `claude`, close refusals, restore skip logic, using a fake `herdr` on PATH that records calls and returns canned JSON.
- Live smoke (one run, Opus, tiny brief, well under $0.50 of tokens): init in a scratch workspace, spawn one worker that replies with a handoff, close it, restore it, confirm the same session id resumed, clean up the workspace.

## Out of scope for v1

Named Herdr sessions per orchestrator, non-Claude workers (Codex), cross-machine, automatic re-spawn on Fable, a dashboard.
