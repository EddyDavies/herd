# herd

A shepherd Claude chat spawns labelled sheepdog chats in Herdr tabs, reads their SendMessage handoffs, closes them only on a deliberate decision, and can reopen any of them later with the conversation intact.

- Design: `docs/specs/2026-09-25-herd-design.md`
- Skills: `skills/herd-shepherd`, `skills/herd-sheepdog`
- State: `~/.local/state/herd/<orchestrator>.json` (override with `HERD_STATE_DIR`)

## Install

```
./install.sh        # uv tool install --editable, links both skills into ~/.claude/skills
```

## Use (from the shepherd chat, inside a Herdr pane)

```
herd init "fc: postiz rollout"   # moves to a new workspace if this one belongs to a herd still in use
herd adopt fc-postiz-rollout      # or: become an existing herd's orchestrator
herd spawn "drip copy" --model opus --why "bounded copy" --brief brief.md
herd status
herd handoff "drip copy" --file handoff.txt
herd close "drip copy"          # refuses without a handoff or while working
herd restore [--all | --every]
```

## Test

```
uv run --group dev pytest
```
