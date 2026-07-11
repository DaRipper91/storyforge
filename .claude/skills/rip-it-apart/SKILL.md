---
description: Use when the user wants a full honest audit/teardown of a repository — real bugs, security/exposure risks, dead code, stale references — ending in a cited, task-by-task fix-plan file rather than a chat summary. Trigger on "run the audit", "audit this repo", "rip this apart", "tear this codebase apart", "full teardown of this project".
allowed-tools: Task, Read, Write, Bash, Grep, Glob
---

# rip-it-apart

A six-stage audit pipeline run as real subagent delegations, not one long pass in your own voice.
Each stage is a separate subagent defined in `.claude/agents/rip-it-apart-*.md`, invoked
explicitly in strict order via the Task tool, with a shared handoff file
(`.audit/SCRATCH.md`) carrying state between them so nothing depends on this session's own
context window holding everything.

**Install note:** subagent files are loaded at session start. If you just added or edited the
`rip-it-apart-*` agent files, restart the Claude Code session before running this skill, or the
invocations below will fail to find them.

Do not collapse this into a single pass yourself. The whole point is that each stage is a
distinct, narrow subagent — that's what keeps bug-hunting from crowding out "what's actually
good," and what lets the critic stage genuinely check earlier work instead of agreeing with
itself.

## Setup

1. Confirm you're at the target repo's root (check for `.git`, `README.md`, or similar).
2. Create `.audit/SCRATCH.md` (create `.audit/` if needed):
   ```markdown
   # Audit Scratch — <repo name> — started <date>

   ## 01 — Recon
   (pending)

   ## 02 — Core Verification
   (pending)

   ## 03 — Bug Hunt
   (pending)

   ## 04 — Strengths
   (pending)

   ## 05 — Critic Pass
   (pending)
   ```

## Stage execution

Invoke each subagent explicitly by name — do not rely on automatic delegation for this chain,
since the stages must run in strict order and automatic delegation doesn't guarantee that. After
each invocation returns, read `.audit/SCRATCH.md` yourself and confirm that stage's section is no
longer "(pending)" and contains cited, concrete content before invoking the next stage. If a
stage's output is empty or weak, invoke that same subagent again with a note about what's missing
before proceeding.

### Stage 1 — Recon
Invoke: "Use the rip-it-apart-recon-mapper subagent to map this repository and append findings to
`.audit/SCRATCH.md` under `## 01 — Recon`, replacing `(pending)`."

### Stage 2 — Core Verification
Invoke: "Use the rip-it-apart-core-verifier subagent. Read `.audit/SCRATCH.md`'s `## 01 — Recon`
section for the repo map and complexity hotspots, then verify the core logic with real
execution — tests, git history, scanners, dispatcher-gap scripts. Append findings under
`## 02 — Core Verification`, replacing `(pending)`."

### Stage 3 — Bug Hunt
Invoke: "Use the rip-it-apart-bug-hunter subagent. Read `.audit/SCRATCH.md`'s `## 01` and `## 02`
sections, then run the fixed bug-class checklist against this repository. Append findings under
`## 03 — Bug Hunt`, replacing `(pending)`."

### Stage 4 — Strengths
Invoke: "Use the rip-it-apart-strengths-scout subagent. Read `.audit/SCRATCH.md` in full so far
and find genuinely good, non-obvious engineering decisions. Run this regardless of how much
stage 3 found wrong. Append findings under `## 04 — Strengths`, replacing `(pending)`."

### Stage 5 — Critic Pass
Invoke: "Use the rip-it-apart-audit-critic subagent. Read `.audit/SCRATCH.md` in full and review
every finding in `## 02`, `## 03`, and `## 04` for missing citations, claims stated as fact that
weren't actually verified, and undisclosed coverage gaps. Append the review under
`## 05 — Critic Pass`, replacing `(pending)`, ending with an explicit `Clean pass? Yes` or
`Clean pass? No` line."

If stage 5 signals "Clean pass? No": invoke the relevant earlier stage's subagent again with the
specific gap called out, then re-run stage 5 once more to confirm before proceeding.

### Stage 6 — Fix Plan
Precondition: stage 5 must show "Clean pass? Yes" — do not invoke this stage otherwise.
Invoke: "Use the rip-it-apart-fixplan-writer subagent. Read the fully approved
`.audit/SCRATCH.md` and write the final fix plan to
`docs/plans/YYYY-MM-DD-<project>-fixes.md` (create `docs/plans/` if needed), using today's date
and the project name from the recon section."

## After the chain finishes

- Report the path to the final plan file.
- Move `.audit/SCRATCH.md` to `.audit/history/SCRATCH-<date>.md` rather than deleting it — it's a
  useful record of what was actually checked.
- Give a two-to-three sentence summary of the headline finding(s), not just "done, see the file."

## Constraints

- Every stage past stage 1 is read-only with respect to source code — only `.audit/SCRATCH.md`
  (and, for stage 6 only, the new plan file) gets written to. If any subagent reports having
  modified source code, treat that as a chain failure and flag it rather than proceeding.
- Never skip a stage to go faster, even if asked — stage N+1 depends on stage N's output being in
  the scratch file.
- For a targeted re-check of just one thing rather than a full pass, invoke only the relevant
  subagent and note in `.audit/SCRATCH.md` that it's a targeted re-check, not a full pass.
