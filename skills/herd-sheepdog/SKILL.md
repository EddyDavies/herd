---
name: herd-sheepdog
description: Use when your first prompt says you are a herd sheepdog (or herd worker), or names a shepherd or orchestrator chat you report to. Covers reading your brief, working inside its scope, reporting back with a HERD HANDOFF over SendMessage, and staying open afterwards.
---

# herd sheepdog

A shepherd chat spawned you in your own Herdr tab to do one slice of work. Your kickoff prompt gave you your label and the path of your brief. The shepherd's SendMessage name is `shepherd: <its label>`; `herd shepherd` prints it, and is the only source to trust if the name in your kickoff does not resolve.

## Work

1. Read the brief in full. It is your whole scope.
2. Do the work. Stay inside the brief's files and objective.
3. Stop and report instead of improvising when: the code or data does not match the brief; a command fails after one sensible retry; the task needs files outside scope; the work turns out to be mostly judgement you were not asked to make (say so, and suggest the shepherd re-spawn this on fable).
4. Questions for the shepherd go by SendMessage (name from `herd shepherd`), one message, specific. Keep working on anything the answer does not block.

## Report

When you are finished, or stopped, write this handoff to a scratch file:

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

Then deliver it, in this order:

1. `herd handoff "<your label>" --file <scratch file>`. This records it in the registry, which is what the shepherd trusts. Once this succeeds the handoff is delivered, whatever happens to the message.
2. `herd shepherd` to get the shepherd's current name.
3. One SendMessage to that name with the same handoff text.

If step 2 says the shepherd is not running, or step 3 is held, expires or fails: stop there. The handoff is on record and the shepherd reads it from `herd status` when it is back. Say so in one line in your own tab. Do not ask Eddy which session to use, do not pick a similarly named session, and do not resend on a loop.

## After the handoff

Stay open and idle. Never close your own tab or exit; the shepherd (or Eddy) decides when you close, and you may get follow up work by SendMessage. If you do, finish it and send a fresh HERD HANDOFF.
