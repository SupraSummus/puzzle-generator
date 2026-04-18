# Working protocol for agents

The human driving this project knows the **requirements and the effects**, not the implementation. Work with that.

## Before you write code

1. **Read `SPEC.md` first.** It's the source of truth for what the project should do. Figure out which requirement ID(s) the current task touches. If none fit, stop and ask the user whether to add one.
2. **Propose before implementing.** For any task beyond a trivial edit (≤10 lines, obvious fix), reply with a short plan *before* touching files:
   - Which requirement this serves (e.g. "R-004").
   - What you'll change (files, functions, data flow) — concrete, not abstract.
   - How the user will verify it worked (what they'll see, run, or click).
   - Anything you're unsure about and want the user to decide.
3. **Wait for a go.** The user reviews the plan against their requirements and intuition. They may redirect. Don't start coding until they say go.

## While coding

- Reference the requirement ID in commit messages (`R-004: add score_graph skeleton`).
- Keep the scope to the approved plan. If you discover the plan won't work, stop and report — don't silently expand.

## After coding

- Tell the user *how to observe the effect*: exact command to run, what output to expect, which file to open. They verify behavior; you don't get to declare it done.
- If the change revealed a missing or wrong requirement, call it out so they can edit `SPEC.md`.

## When the user gives feedback on effects

The user's feedback will be about *what they saw*, not *what's wrong in the code*. Treat their observation as ground truth and do the diagnosis yourself. Don't ask them to debug.

## Branching

Feature work goes on the branch named in the session instructions. Don't push to other branches without explicit permission.

## Committing generated artifacts

Rule of thumb: **committing effects to the repo makes them easy to demonstrate and inspect, but must be guarded by a reproducibility check.** If you commit rendered output (PNGs, dumps, fixtures), wire the producing script into `.github/workflows/reproducibility.yml` so CI regenerates the artifact and fails on drift. No committed artifact without a guard.
