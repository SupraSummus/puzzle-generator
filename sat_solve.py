"""SAT/SMT-based disassembly solver — bounded-horizon planning with Z3.

Alternative to BFS in `puzzle.shortest_disassembly_path`. The problem — is there a
sequence of T unit slides from the solved state to a bbox-disjoint state? — is
exactly PSPACE bounded-horizon reachability, the canonical home of SATPlan-style
encoding. Z3 handles the arithmetic natively so we avoid hand bit-blasting.

Encoding choices (all aimed at keeping the formula small enough for Z3 to make
real progress instead of drowning in clauses):

- Offsets are `BitVec` of fixed width. Bounded 2-complement arithmetic is cheap
  for Z3 and sidesteps unbounded-`Int` overhead. Width is chosen so every
  quantity in the formula — offsets, piece-voxel sums, pairwise differences —
  stays well clear of overflow.
- Non-overlap uses *deduplicated* Minkowski differences per piece pair. Two
  voxel pairs that produce the same displacement difference contribute the
  same forbidden triple; we emit it once.
- Transitions are factored via per-step move-selector Booleans `M[t][i][d]`,
  with exactly-one across (i, d). Frame axioms collapse to one implication
  per piece saying "if nobody moved me, my offset is unchanged"; unit-slide
  effects are one implication per (i, d). This avoids the 6N × 3N clause
  blowup of an `Or`-of-`And` enumeration per step.
- Horizon is extended incrementally: validity and transition clauses persist
  across iterations; only the goal assertion at step T is `push`/`pop`-scoped.
"""
from __future__ import annotations

import z3

from puzzle import DIRECTIONS, Bbox, State, World


def _piece_bbox_at_zero(piece) -> Bbox:
    xs = [x for (x, _, _) in piece]
    ys = [y for (_, y, _) in piece]
    zs = [z for (_, _, z) in piece]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _forbidden_diffs(piece_i, piece_j) -> list[tuple[int, int, int]]:
    """Unique offset differences that would make two pieces collide on some voxel.

    If any voxel of piece i at offset o_i coincides with any voxel of piece j at
    o_j, then o_i - o_j == v2 - v1 for some (v1 ∈ p_i, v2 ∈ p_j). Deduplicating
    shrinks the constraint count by a factor of ~2-5 on typical dense pieces.
    """
    return sorted({
        (v2x - v1x, v2y - v1y, v2z - v1z)
        for (v1x, v1y, v1z) in piece_i
        for (v2x, v2y, v2z) in piece_j
    })


def shortest_disassembly_path_sat(
    world: World,
    max_horizon: int = 60,
    strategy: str = "linear",
) -> list[State] | None:
    """Shortest move sequence from `world.solved` to a bbox-disjoint state, via SAT.

    Returns None if no such path exists at length ≤ max_horizon. The returned
    path, if any, starts at `world.solved` and ends at a state whose piece
    bboxes are pairwise disjoint (matching `puzzle.bboxes_disjoint`). Length
    is minimum across horizons up to `max_horizon`.

    `strategy`:
    - "linear" (default): iterate T=1..max_horizon, return on first SAT.
      Cheap when the answer is short; expensive when the puzzle is unsolvable
      (pays for a UNSAT proof at every T).
    - "max_first": build the full horizon with no-op moves allowed, prove
      feasibility once at T=max_horizon, then binary-search for the smallest
      T. Cheap when the puzzle is unsolvable (one UNSAT proof on the full
      formula); extra build overhead when the answer is short.
    """
    N = len(world.pieces)
    piece_bboxes = [_piece_bbox_at_zero(p) for p in world.pieces]
    cage = tuple(world.cage)

    # Width chosen so offset ± piece-voxel + pair-difference all stay in range.
    # Offsets live in [solved - k, solved + k]; voxel coords fit in the target
    # shape's extent. 16 bits signed gives ±32768 — orders of magnitude of head-
    # room for any puzzle size we care about.
    BV = 16

    def bv(val: int) -> z3.BitVecNumRef:
        return z3.BitVecVal(val, BV)

    solver = z3.Solver()
    X: list[list[z3.BitVecRef]] = []
    Y: list[list[z3.BitVecRef]] = []
    Z: list[list[z3.BitVecRef]] = []
    # Move selectors: M[t][i][d] true iff at step t→t+1 piece i slides in direction d.
    M: list[list[list[z3.BoolRef]]] = []

    forbidden = [
        [_forbidden_diffs(world.pieces[i], world.pieces[j]) if i < j else [] for j in range(N)]
        for i in range(N)
    ]

    def new_offset_vars(t: int) -> None:
        X.append([z3.BitVec(f"x_{t}_{i}", BV) for i in range(N)])
        Y.append([z3.BitVec(f"y_{t}_{i}", BV) for i in range(N)])
        Z.append([z3.BitVec(f"z_{t}_{i}", BV) for i in range(N)])

    def add_validity(t: int) -> None:
        k = world.max_displacement
        # Displacement bound, encoded as signed comparisons on BitVecs.
        for i, (sx, sy, sz) in enumerate(world.solved):
            solver.add(z3.And(
                X[t][i] - bv(sx) <= bv(k),
                X[t][i] - bv(sx) >= bv(-k),
                Y[t][i] - bv(sy) <= bv(k),
                Y[t][i] - bv(sy) >= bv(-k),
                Z[t][i] - bv(sz) <= bv(k),
                Z[t][i] - bv(sz) >= bv(-k),
            ))
        # Pairwise non-overlap via deduped Minkowski differences.
        for i in range(N):
            for j in range(i + 1, N):
                for (dx, dy, dz) in forbidden[i][j]:
                    solver.add(z3.Or(
                        X[t][i] - X[t][j] != bv(dx),
                        Y[t][i] - Y[t][j] != bv(dy),
                        Z[t][i] - Z[t][j] != bv(dz),
                    ))
        # Cage collision: for each piece voxel and each cage cell, block the equality.
        for i in range(N):
            for (vx, vy, vz) in world.pieces[i]:
                for (cx, cy, cz) in cage:
                    solver.add(z3.Or(
                        X[t][i] != bv(cx - vx),
                        Y[t][i] != bv(cy - vy),
                        Z[t][i] != bv(cz - vz),
                    ))

    def add_transition(t: int, allow_noop: bool = False) -> None:
        """Factored transition from step t to step t+1.

        Introduces 6N booleans M[t][i][d]; exactly one is true. Frame axiom:
        for each piece i, if no M[t][i][*] is set then piece i's offset is
        unchanged. Effect axiom: if M[t][i][d] is set then piece i's offset
        shifts by direction d and every other piece is unchanged.

        When `allow_noop` is true, a "do nothing" option joins the exactly-one,
        so a plan of length k ≤ T can be embedded in a T-step formula by
        padding with no-ops. That turns the goal assertion at T into the
        question "is there a plan of length ≤ T?" — useful for feasibility
        checks and binary search over horizons.
        """
        moves = [[z3.Bool(f"m_{t}_{i}_{d}") for d in range(len(DIRECTIONS))] for i in range(N)]
        M.append(moves)

        flat = [m for row in moves for m in row]
        if allow_noop:
            noop = z3.Bool(f"m_{t}_noop")
            flat = [noop] + flat
        solver.add(z3.PbEq([(m, 1) for m in flat], 1))

        for i in range(N):
            moved_i = z3.Or(*moves[i])
            # Frame: piece i stays put unless picked.
            solver.add(z3.Implies(z3.Not(moved_i), z3.And(
                X[t + 1][i] == X[t][i],
                Y[t + 1][i] == Y[t][i],
                Z[t + 1][i] == Z[t][i],
            )))
            # Effect: piece i shifts by d if M[t][i][d] is picked.
            for d, (dx, dy, dz) in enumerate(DIRECTIONS):
                solver.add(z3.Implies(moves[i][d], z3.And(
                    X[t + 1][i] == X[t][i] + bv(dx),
                    Y[t + 1][i] == Y[t][i] + bv(dy),
                    Z[t + 1][i] == Z[t][i] + bv(dz),
                )))

        # No immediate reversal: if piece i went in direction d at t-1, forbid
        # piece i going in -d at t. A plan that reverses itself one step later
        # with nothing changing in between has a strictly shorter equivalent,
        # so this preserves optimality while pruning a large chunk of the
        # search tree.
        if t >= 1:
            for i in range(N):
                for d, (dx, dy, dz) in enumerate(DIRECTIONS):
                    d_opp = DIRECTIONS.index((-dx, -dy, -dz))
                    solver.add(z3.Not(z3.And(M[t - 1][i][d], moves[i][d_opp])))

    def _pair_bbox_disjoint(t: int, i: int, j: int) -> z3.BoolRef:
        xmin_i, xmax_i, ymin_i, ymax_i, zmin_i, zmax_i = piece_bboxes[i]
        xmin_j, xmax_j, ymin_j, ymax_j, zmin_j, zmax_j = piece_bboxes[j]
        return z3.Or(
            X[t][i] + bv(xmax_i) < X[t][j] + bv(xmin_j),
            X[t][j] + bv(xmax_j) < X[t][i] + bv(xmin_i),
            Y[t][i] + bv(ymax_i) < Y[t][j] + bv(ymin_j),
            Y[t][j] + bv(ymax_j) < Y[t][i] + bv(ymin_i),
            Z[t][i] + bv(zmax_i) < Z[t][j] + bv(zmin_j),
            Z[t][j] + bv(zmax_j) < Z[t][i] + bv(zmin_i),
        )

    def bbox_disjoint_goal(t: int) -> z3.BoolRef:
        clauses = [_pair_bbox_disjoint(t, i, j) for i in range(N) for j in range(i + 1, N)]
        return z3.And(*clauses) if clauses else z3.BoolVal(True)

    def extract_path(model: z3.ModelRef, T: int) -> list[State]:
        path: list[State] = []
        for t in range(T + 1):
            state = tuple(
                (
                    model[X[t][i]].as_signed_long(),
                    model[Y[t][i]].as_signed_long(),
                    model[Z[t][i]].as_signed_long(),
                )
                for i in range(N)
            )
            path.append(state)
        return path

    new_offset_vars(0)
    for i, (sx, sy, sz) in enumerate(world.solved):
        solver.add(X[0][i] == bv(sx), Y[0][i] == bv(sy), Z[0][i] == bv(sz))
    add_validity(0)

    if strategy == "linear":
        for T in range(1, max_horizon + 1):
            new_offset_vars(T)
            add_transition(T - 1)
            add_validity(T)
            solver.push()
            solver.add(bbox_disjoint_goal(T))
            if solver.check() == z3.sat:
                model = solver.model()
                path = extract_path(model, T)
                solver.pop()
                return path
            solver.pop()
        return None

    if strategy == "max_first":
        # Build the full formula up to max_horizon with no-op transitions, so
        # that asserting goal at T actually means "plan of length ≤ T exists."
        for T in range(1, max_horizon + 1):
            new_offset_vars(T)
            add_transition(T - 1, allow_noop=True)
            add_validity(T)

        # Feasibility check at max_horizon. UNSAT ⇒ no plan of length ≤ max_horizon.
        solver.push()
        solver.add(bbox_disjoint_goal(max_horizon))
        if solver.check() != z3.sat:
            solver.pop()
            return None
        solver.pop()

        # Binary search for the smallest T where goal is satisfiable.
        # Invariant: no plan of length ≤ lo exists; a plan of length ≤ hi does.
        lo, hi = 0, max_horizon
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            solver.push()
            solver.add(bbox_disjoint_goal(mid))
            if solver.check() == z3.sat:
                hi = mid
            else:
                lo = mid
            solver.pop()

        # Rebuild the final model at hi.
        solver.push()
        solver.add(bbox_disjoint_goal(hi))
        solver.check()
        model = solver.model()
        solver.pop()

        # The raw path may contain no-op steps (consecutive identical states);
        # strip them so the returned path is a walk of genuine unit slides.
        raw = extract_path(model, hi)
        compressed = [raw[0]]
        for s in raw[1:]:
            if s != compressed[-1]:
                compressed.append(s)
        return compressed

    raise ValueError(f"unknown strategy: {strategy!r}")
