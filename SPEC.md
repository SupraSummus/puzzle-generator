# SPEC

This file is the source of truth for *what* the project should do. It's written in **effects** — what the user wants to observe — not in implementation. The implementer (human or agent) translates effects into code.

The user owns this file. Agents propose plans against it before writing code.

## How to use this file

- Requirements have stable IDs (`R-001`, `R-002`, …). Plans and commits reference them.
- Each requirement says **what effect** the user wants and **how they'll know it holds**. Implementation is not specified here.
- When a requirement changes, edit in place and note it in the changelog.

---

## Vision

Generate 3D interlocking voxel puzzles that are **hard to solve by mental inspection, but are solvable**. See `README.md` for the longer framing.

---

## What makes a puzzle bad

The user-visible criteria for rejection. The numbered requirements below formalize these.

1. **Unsolvable.** No move sequence from solved reaches a fully-disassembled state. → R-007.
2. **Trivially obvious.** Looking at the pieces, a human can simulate the solution in their head without trying moves. → R-004.
3. **Not physically realizable.** A "piece" is two blobs held together by abstract constraint rather than a connected solid. → R-008.
4. **Ugly assembled shape.** The solved shape is irregular or random-looking. → R-001 (via user-chosen `target_shape`).
5. **Falls apart on its own.** When assembled, the puzzle doesn't hold together — gentle handling displaces pieces. → R-009.
6. **Already a known puzzle.** A human could look up the solution online. → *non-goal*, see below.

---

## Requirements

### R-001 — Pieces partition the target shape
- **Effect**: in the solved state, the pieces tile a user-chosen target shape — no gaps, no overlaps.
- **How to tell**: `is_target_partition(pieces, solved, target)` returns True.
- **Notes**: the user supplies `target_shape` per run. The set of allowed shapes is open — any shape the user picks is valid. The generator never invents target shapes.
- **Status**: implemented (`puzzle.py`, `generate.py`).

### R-002 — Slide-only move model is sound
- **Effect**: the physical puzzle never admits a move the simulator missed (no rotational shortcuts in the solved region).
- **How to tell**: a 6-sided cage confines pieces when solved; a test confirms no rotational freedom until a piece has slid partway out.
- **Status**: design chosen (cage), enforcement test not written.

### R-003 — State graph terminates
- **Effect**: BFS from solved stops at "fully disassembled" rather than drifting forever.
- **How to tell**: `bboxes_disjoint` cutoff; `tests.py` covers free-piece state counts.
- **Status**: implemented.

### R-004 — Puzzle is not mentally solvable by inspection
- **Effect**: a human looking at the piece shapes **cannot** predict the correct move sequence in their head. To solve, they must actually try moves and observe.
- **How to tell**: the implementer designs a measure and shows it agrees with the user's snap judgment on a small test set. The 2-piece cube is a **negative** example (bad puzzle — obviously solvable at a glance). Positive examples are a deliverable of R-005.
- **Notes**: this is the keystone requirement. "Mentally solvable" is a cognitive property, not a graph property; the implementer's job is to find a graph-shape proxy that correlates.
- **Status**: measure not chosen. Open problem for the implementer.

### R-005 — Counterexample-guided refinement loop
- **Effect**: given a seed puzzle, the system edits it to improve R-004's measure while keeping R-001, R-007, R-008, and the `target_shape` from R-001 intact.
- **How to tell**: a function that takes a seed and N iterations, returns a puzzle whose R-004 measure is monotonically non-worse across iterations, and still passes the invariants.
- **Status**: not started.

### R-006 — Reproducible renders
- **Effect**: demo scripts produce the same PNGs on every run under pinned deps; CI catches drift.
- **How to tell**: `.github/workflows/reproducibility.yml` passes.
- **Status**: implemented.

### R-007 — Puzzle is solvable
- **Effect**: from the solved state, some move sequence reaches a fully-disassembled state.
- **How to tell**: BFS from solved reaches at least one disassembly leaf. Used as a rejection filter in the generator.
- **Status**: BFS exists; rejection filter not wired up.

### R-008 — Each piece is a connected solid
- **Effect**: every piece is one 3D-printable object, not two chunks bridged by fiction.
- **How to tell**: each piece's voxels are face-connected (6-neighbor adjacency). `is_connected` over each piece.
- **Status**: checked inside `is_target_partition`. Call out as its own requirement.

### R-009 — Assembled puzzle interlocks
- **Effect**: once assembled, the pieces **interlock** (in the burr-puzzle sense) — the puzzle doesn't fall apart on its own. Pick it up, tip it, shake it gently; pieces stay in place. Disassembly requires deliberate moves, not a bump.
- **How to tell**: TBD. "Interlock" is the user's word; the implementer turns it into a formal check. Under the 6-sided cage design in R-002 it's automatically satisfied (pieces are confined on every face). Without a cage, the implementer needs a graph-based stability check (e.g. "no single piece can slide out along any axis from the solved state"), vetted against user intuition on examples.
- **Status**: satisfied-by-construction under the current cage design (R-002). Revisit if the cage is dropped.

### R-010 — Shortest-path disassembly visualization
- **Effect**: for any candidate puzzle, render a minimal frame-by-frame sequence from solved to fully disassembled along the shortest possible path. No wandering, no clutter. Pieces that are already "out" are hidden from the frame so the view focuses on what's still assembled.
- **How to tell**: run on the 2-piece cube → 2–3 frames, the two pieces visibly part. Run on a harder candidate → more frames, still no clutter. The user can form an opinion about the puzzle from the PNG sequence alone, without 3D-printing.
- **Open sub-question**: what counts as "out" for rendering — outside the cage, bbox-disjoint from the rest, or moved > k units? Implementer picks a first pass; user reviews on examples and requests refinement.
- **Status**: not started. `solve_demo.py` renders a related but different path (farthest-reachable back to solved, with no hiding).

---

## Open questions

Promote to R-### once decided.

- Grid size and piece count defaults.
- Is "one piece fully removed" a terminal state, or must full disassembly happen?
- Does a "good" puzzle need exactly one narrow path, or are several acceptable?
- Interactive viewer beyond static frames?

---

## Non-goals

- Rotational moves in the solver.
- 3D-print overhangs, tolerances, clearances (beyond "pieces are connected").
- Novelty check against known puzzles (bad-puzzle #5). Random generation gives probabilistic novelty; we don't verify.
- Inventing target shapes. The user supplies them.

---

## Changelog

- 2026-04-18: initial SPEC extracted from README.
- 2026-04-18: rewrote in effects-language after bad-puzzle interview. Reframed R-004 (was "score_graph formula") as the cognitive "not mentally solvable" property with deferred measure. Added R-007 (solvable), R-008 (pieces connected), R-009 (interlocks). Clarified R-001 allows any user-chosen target shape.
- 2026-04-18: added R-010 (shortest-path disassembly visualization) so candidates can be judged from frames alone.
