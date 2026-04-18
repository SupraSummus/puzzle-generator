# 3D puzzle generator (experiment)

Sketch of an idea we're exploring. Nothing here is settled.

## Core idea

Model 3D mechanical puzzles (interlocking / burr-style) as voxel pieces on an integer grid. Enumerate the puzzle's state graph. Generate many candidate puzzles and keep only those whose graph has the "right shape" — solvable, but with a *narrow passage* between the bulk of the state space and the solved region, so a casual solver is very unlikely to stumble through by chance.

## v0 scope

- **Puzzle family**: interlocking voxel pieces; ultimately inside a 6-sided cage.
- **Representation**: each piece is a set of unit voxels in its local frame; a state is a tuple of piece offsets; a world is a cage + piece shapes + solved state.
- **Moves**: single-piece unit slides along ±x, ±y, ±z. Rejected if they cause overlap with another piece or the cage, or push a piece beyond a displacement bound.
- **State graph**: BFS from the solved state.

## Open questions and known concerns

### 1. Unmodeled moves (rotational shortcuts)

A slide-only solver misses moves like twisting a piece. A physical puzzle might have enough slack to rotate, giving the user shortcuts we didn't score.

Options considered:
1. **Design it out**: require a 6-sided cage. Pieces in the solved state are confined on all faces, so no rotational slack exists until pieces have slid out. Slide-only becomes sound by construction.
2. **Expand the move set** with 90° rotations. Elegant but likely blows up the state space too much to be practical.
3. **Post-hoc verification**: generate under the slide-only model, then for each candidate check for rotational freedom.

Leaning toward (1), with (3) as a fallback if we later drop the cage.

### 2. Random generation wastes compute

Uniform-random piece shapes + placements will almost always produce bad puzzles (unsolvable, trivially solvable, or disconnected). We may never find a good one by chance.

Approaches considered:

- **Counterexample-guided refinement** (the plan): start with a loose random design, compute the graph, find the widest "shortcut" near the goal, fill one voxel to block it, repeat. Each iteration is cheap; narrowness improves monotonically-ish.
- **Superposition / lazy collapse** (deferred): hold the design undetermined and commit voxel assignments only when they become relevant during state exploration. Elegant in spirit, but:
  - connectivity of a piece is non-local — flipping one voxel can split a piece into two, and connectivity does not propagate by local rules;
  - retroactive invalidation — states explored earlier can become unreachable once new voxel commitments are made;
  - the objective (narrow cut) is global, so local commit heuristics don't obviously steer toward it;
  - branching still explodes, just more directed.

Counterexample-guided refinement keeps the "commit on demand" spirit without the bookkeeping.

### 3. What counts as a "good" graph?

We want a *narrow passage* between the solved region and the unsolved region. Concretely: the state graph admits a small edge cut (width 1 or 2) such that one side contains the solved state and is relatively small, and the other is large. A user exploring from the scrambled side is unlikely to cross by chance.

Three-region mental model:
- **unsolved** — large, connected, where random play stays;
- **transition** — the narrow cut (1–2 edges, few states);
- **solved** — where the goal lives.

Score sketch: something like `|unsolved| * |solved| / cut_width`, filtered by `cut_width ≤ k`. Possibly allow two narrow passages rather than one.

## Deferred

- Grid size and piece count defaults.
- Whether "piece fully removed" is a terminal state, or we require full disassembly, or we only care about a fixed subset of states.
- Generation algorithm details (perturbation strategy, acceptance criterion).
- Visualization.

## Layout

```
puzzle.py    core types + state graph BFS
example.py   two-piece toy demo
```
