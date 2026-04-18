# SPEC

This file is the source of truth for *what* the project should do. Implementation details live in code. You (the human) own this file. Agents read it and propose plans against it.

## How to use this file

- Add requirements as you think of them. Rough is fine.
- Each requirement gets a stable ID (`R-001`, `R-002`, …) so plans and commits can reference it.
- "Done" means the acceptance criteria pass, not that code was written.
- When a requirement changes, edit it in place and bump a note in the changelog at the bottom.

---

## Vision

One-line goal: *Generate 3D interlocking voxel puzzles whose state graph has a narrow passage between scrambled and solved — hard for a human to solve by chance, but solvable.*

See `README.md` for the longer framing.

---

## Requirements

### R-001: Puzzles tile a target shape
- **What**: In the solved state, pieces must partition a given target shape (e.g. 3×3×3 cube) into disjoint connected pieces covering every voxel.
- **Acceptance**: `is_target_partition(pieces, solved, target)` returns True.
- **Status**: implemented (`puzzle.py`, `generate.py`).

### R-002: Slide-only move model is sound
- **What**: The physical puzzle must not admit moves the model doesn't know about (no rotational shortcuts in the solved region).
- **Acceptance**: enforced by 6-sided cage; documented; covered by a test that a cage-confined solved state has no rotational freedom.
- **Status**: design chosen (cage), enforcement not yet tested.

### R-003: State graph terminates
- **What**: BFS from solved must stop; "fully disassembled" = all piece bounding boxes disjoint.
- **Acceptance**: `bboxes_disjoint` leaf cutoff; `tests.py` covers free-piece state count.
- **Status**: implemented.

### R-004: Score a puzzle's graph shape
- **What**: Given a state graph, compute a score reflecting "narrow passage" quality.
- **Acceptance**: function `score_graph(g, solved) -> float` + a handful of hand-built graphs whose scores match intuition (wide cut → low, narrow cut + big unsolved region → high).
- **Status**: not started. Score formula still a sketch (`|unsolved| * |solved| / cut_width`).

### R-005: Counterexample-guided refinement loop
- **What**: Given a seed puzzle, iteratively find the widest shortcut near the goal and block it with a voxel edit, keeping the partition invariant.
- **Acceptance**: a generator that takes a seed and N iterations, returns a puzzle with monotonically-improving (non-worsening) score.
- **Status**: not started.

### R-006: Reproducible renders
- **What**: Demo scripts produce the same PNGs on every run for pinned deps.
- **Acceptance**: CI job reruns them and diffs committed frames.
- **Status**: implemented (`.github/workflows/reproducibility.yml`).

---

## Open questions (not yet requirements)

Promote these to R-### once the decision is made.

- Grid size and piece count defaults.
- Is "one piece fully removed" terminal, or do we require full disassembly?
- Two narrow passages allowed, or only one?
- UI / interactive viewer beyond static frames?

---

## Non-goals (for now)

- Rotational moves in the solver.
- Physical tolerancing / 3D-print-ready output.
- Puzzles outside the voxel/cage family.

---

## Changelog

- 2026-04-18: initial SPEC extracted from README.
