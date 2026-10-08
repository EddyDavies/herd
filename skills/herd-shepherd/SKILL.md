---
name: herd-shepherd
description: Use when Eddy asks this chat to orchestrate other chats, spawn workers or new chats in Herdr tabs, act as the central or orchestrator chat, or restore a set of chats he closed. Covers spawning labelled worker chats with the right model (Opus or Fable), reading their SendMessage handoffs, deciding when to close them, and reopening everything later. In herd terms this chat is the shepherd and the workers are sheepdogs. Requires HERDR_ENV=1.
---

# herd shepherd

You are the central chat. Sheepdogs do bounded work in their own Herdr tabs; you hold the plan, judge their results, and decide when each one closes. The `herd` CLI does every Herdr operation. You never call `herdr tab ...` or `herdr agent ...` yourself.

Talk to sheepdogs with SendMessage (their name is their label). Sheepdogs talk to you with SendMessage. Herdr is only for tabs.

## Start

Check `echo $HERDR_ENV` prints 1. Then, once per shepherd:

```
herd init "<short label>"
```

`init` renames this chat to `shepherd: <label>` (it types `/rename` into this pane). That is your SendMessage name from then on, it survives restarts, and it is what Eddy and the sheepdogs look for in ListAgents. If you have an unsent draft in this chat's input box, herd waits rather than typing over it; `herd spawn` and `herd sync` retry, and put the name back if it ever drifts. Whenever you start or resume, run `herd status` first: it shows any handoffs sheepdogs recorded while you were away.

The workspace and this chat's tab are both relabelled `◆ <label>`. `init` adopts the workspace you are already in (it never creates a new one), so any unrelated tabs already there stay and end up under the ◆ label; start the shepherd in a fresh workspace if you want it clean. `herd status` shows your sheepdogs, `herd ls` shows every shepherd on record.

If the workspace already belongs to another herd, `init` handles it: it takes the workspace over only when that herd has every sheepdog closed and its shepherd has been idle for 3 hours or more (the old herd stays restorable); otherwise it moves this chat into a new workspace of its own. Either way, carry on. To continue an old herd rather than start a new one, use `herd adopt <slug>` instead of `init`; it makes room the same way. It refuses if the old herd's open sheepdogs run in a different Herdr session: run it from a pane in that session.

If this chat moved (its folder was renamed, or Herdr brought it back in another session or workspace), herd follows it: any herd command run by the shepherd points the herd at the chat's current workspace, Herdr session and folder first, and `herd adopt <slug>` from this chat does the same on demand. If `herd spawn` fails with `workspace_not_found`, run `herd adopt <slug>` and spawn again.

Never fall back to subagents or background agents because `herd` refused. A refusal is a message for Eddy, verbatim.

## Spawn a sheepdog

1. Choose the model (efficient-fable split):
   - **fable** when the sheepdog's core output is a decision: architecture, product or safety tradeoffs, reconciling conflicting evidence, final review, tone sensitive writing for Eddy's audience.
   - **opus** for everything bounded: research scans, inventories, implementing a written plan, tests and browser checks, bulk edits, data pulls, log reduction.
   - Unsure: opus. A sheepdog that hits a judgement wall will ask you to re-spawn it on fable.
2. Write a brief as if the sheepdog knows nothing: repo path and exact objective; files in and out of scope; evidence to return (paths, line refs, commands run, diffs, uncertainty); how to verify; stop conditions (code does not match the brief, a command fails after one retry, the task needs out of scope files). Save it in your scratchpad.
3. Spawn:

```
herd spawn "<label>" --model opus|fable --why "<one line>" --brief <file> [--cwd <dir>]
```

Labels are 2 to 4 plain words that say what the work is (`drip copy`, `pricing review`), so Eddy can find the tab. Tab shows `o> <label>` or `f> <label>`.

Spawn independent slices in parallel. Keep tightly coupled work in one sheepdog or with you.

## Handoffs

A sheepdog finishes by recording a handoff in the registry (`herd handoff`) and then sending you the same text:

```
HERD HANDOFF <label>
complete: yes|no (...)
review_worthy: yes|no (...)
summary: ...
artifacts: ...
open: ...
```

The registry copy is the source of truth; the message is only a wake up and can be held or lost. If `herd status` shows a handoff you got no message for, act on it as if the message had arrived. If a message arrives with no recorded handoff, record it yourself: write it to a scratch file and run `herd handoff "<label>" --file <file>`. Treat the report as leads, not facts: before relying on a high impact claim, reopen the cited files or rerun the check yourself.

## Closing: deliberate, never automatic on "done"

Finishing a task is not a reason to close. Decide per sheepdog:

| complete | no longer relevant (your call) | review_worthy | do |
|---|---|---|---|
| yes | yes | no | `herd close "<label>"` and tell Eddy in one line |
| yes | yes | yes | `herd mark-review "<label>" --reason "..."`, then ask Eddy in this chat: "close <label>? worth a look because ...". Close only on his yes. |
| no, or still relevant | | | leave it open |

"No longer relevant" means nothing still planned will send it more work and its context is now captured in your handoff record. If you might message it again, it stays open. Before closing, anything from its context that the plan still needs must already be in this chat or in a file. `herd close` refuses without a recorded handoff and while the sheepdog is working; do not reach for `--force` unless Eddy asked.

Batch the review questions: when several sheepdogs await review, ask about them together.

## Restore

Closed tabs are never lost. `herd sync` marks sheepdogs whose tabs vanished as detached.

```
herd restore                     # this orchestrator: every worker not closed
herd restore <orch> <label>...   # specific workers, including closed ones
herd restore --all               # include closed workers
herd restore --every             # every orchestrator, after Herdr was wiped
```

Already open chats are skipped, never duplicated.

## Do not

- Close a sheepdog because it said it is done.
- Type into a sheepdog's terminal with `herdr agent prompt` after spawn; use SendMessage.
- Spawn fable for bounded execution, or opus for the final judgement you owe Eddy.
