# Working protocol for agents

The human driving this project knows the **requirements and the effects**, not the implementation. Work with that.

## Before you write code

1. **Read `SPEC.md` first.** It's the source of truth for what the project should do. Figure out which requirement ID(s) the current task touches. If none fit, add one yourself and flag it in the commit.
2. **Act, don't ask.** PR review is the safety net, not pre-approval. Pick a reasonable path, implement it, and let the diff be the proposal. Reserve questions for genuine forks where the user's intuition is the only tiebreaker — not for choices they can judge faster by reading the change. Prefer a one-line update ("doing X, will push") over a menu of options.
3. **No harm floor.** Branch work is cheap and reversible. Force-push nothing to `main`, respect the session's feature branch, and otherwise move.

## While coding

- Reference the requirement ID in commit messages (`R-004: add score_graph skeleton`).
- Efficiency and elegance are requirements (see R-011). A solution that blows the state-space budget or sprawls across files is not done.
- If the approach you picked turns out to be wrong, fix it in a follow-up commit — don't hide the detour.

## After coding

- Tell the user *how to observe the effect*: exact command to run, what output to expect, which file to open. They verify behavior; you don't get to declare it done.
- If the change revealed a missing or wrong requirement, call it out so they can edit `SPEC.md`.

## When the user gives feedback on effects

The user's feedback will be about *what they saw*, not *what's wrong in the code*. Treat their observation as ground truth and do the diagnosis yourself. Don't ask them to debug.

## Branching

Feature work goes on the branch named in the session instructions. Don't push to other branches without explicit permission.

## Committing generated artifacts

Rule of thumb: **committing effects to the repo makes them easy to demonstrate and inspect, but must be guarded by a reproducibility check.** If you commit rendered output (PNGs, dumps, fixtures), wire the producing script into `.github/workflows/reproducibility.yml` so CI regenerates the artifact and fails on drift. No committed artifact without a guard.
