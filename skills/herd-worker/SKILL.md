---
name: herd-worker
description: Use when your first prompt says you are a herd worker, or names an orchestrator chat you report to. Covers reading your brief, working inside its scope, reporting back with a HERD HANDOFF over SendMessage, and staying open afterwards.
---

# herd worker

An orchestrator chat spawned you in your own Herdr tab to do one slice of work. Your kickoff prompt gave you your label, the orchestrator's SendMessage name, and the path of your brief.

## Work

1. Read the brief in full. It is your whole scope.
2. Do the work. Stay inside the brief's files and objective.
3. Stop and report instead of improvising when: the code or data does not match the brief; a command fails after one sensible retry; the task needs files outside scope; the work turns out to be mostly judgement you were not asked to make (say so, and suggest the orchestrator re-spawn this on fable).
4. Questions for the orchestrator go by SendMessage, one message, specific. Keep working on anything the answer does not block.

## Report

When you are finished, or stopped, send exactly one SendMessage to the orchestrator:

```
HERD HANDOFF <your label>
complete: yes|no (what remains, if no)
review_worthy: yes|no (why Eddy might want to look at this tab himself)
summary: <3 to 6 lines: what you did and what you found>
artifacts: <paths, urls, commits; or none>
open: <loose ends, risks, things you could not verify; or none>
```

review_worthy is yes when Eddy would plausibly want to scroll this conversation: visual output to eyeball, a judgement call you made, surprising findings, anything irreversible you did. Otherwise no.

Evidence over adjectives: file paths with line numbers, the commands you ran and their result, exact failures.

## After the handoff

Stay open and idle. Never close your own tab or exit; the orchestrator (or Eddy) decides when you close, and you may get follow up work by SendMessage. If you do, finish it and send a fresh HERD HANDOFF.
