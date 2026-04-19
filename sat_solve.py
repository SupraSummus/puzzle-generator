"""SAT/SMT-based disassembly solver — bounded-horizon planning with Z3.

Alternative to BFS in `puzzle.shortest_disassembly_path`. The problem — is there a
sequence of T unit slides from the solved state to a bbox-disjoint state? — is
exactly PSPACE bounded-horizon reachability, the canonical home of SATPlan-style
encoding. Z3 handles the integer arithmetic natively so we avoid hand bit-blasting.

Shape of the encoding at horizon T:
- Per timestep t ∈ [0, T], per piece i: three integer variables (x_i^t, y_i^t, z_i^t).
- Initial: t=0 fixed to world.solved.
- Validity at every t: displacement bound, piece/piece non-overlap, cage collision.
- Transition between t and t+1: exactly one of the 6N unit slides fires.
- Goal at t=T: every pair of piece bboxes is strictly separated on at least one axis.

The solver is built incrementally: we extend horizon by one step each outer
iteration and re-check under a `push`/`pop` of the goal assertion, so assertions
about validity and transitions persist across horizons.
"""
from __future__ import annotations

import z3

from puzzle import DIRECTIONS, Bbox, State, World


def _piece_bbox_at_zero(piece) -> Bbox:
    xs = [x for (x, _, _) in piece]
    ys = [y for (_, y, _) in piece]
    zs = [z for (_, _, z) in piece]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def shortest_disassembly_path_sat(
    world: World,
    max_horizon: int = 60,
) -> list[State] | None:
    """Shortest move sequence from `world.solved` to a bbox-disjoint state, via SAT.

    Returns None if no such path exists at length ≤ max_horizon. The returned
    path, if any, starts at `world.solved` and ends at a state whose piece
    bboxes are pairwise disjoint (matching `puzzle.bboxes_disjoint`). Length
    is minimum across horizons up to `max_horizon`.
    """
    N = len(world.pieces)
    piece_bboxes = [_piece_bbox_at_zero(p) for p in world.pieces]
    cage = tuple(world.cage)

    solver = z3.Solver()
    X: list[list[z3.ArithRef]] = []
    Y: list[list[z3.ArithRef]] = []
    Z: list[list[z3.ArithRef]] = []

    def add_step(t: int) -> None:
        X.append([z3.Int(f"x_{t}_{i}") for i in range(N)])
        Y.append([z3.Int(f"y_{t}_{i}") for i in range(N)])
        Z.append([z3.Int(f"z_{t}_{i}") for i in range(N)])

    def add_validity(t: int) -> None:
        k = world.max_displacement
        for i, (sx, sy, sz) in enumerate(world.solved):
            solver.add(X[t][i] - sx <= k, X[t][i] - sx >= -k)
            solver.add(Y[t][i] - sy <= k, Y[t][i] - sy >= -k)
            solver.add(Z[t][i] - sz <= k, Z[t][i] - sz >= -k)
        for i in range(N):
            for j in range(i + 1, N):
                for (v1x, v1y, v1z) in world.pieces[i]:
                    for (v2x, v2y, v2z) in world.pieces[j]:
                        solver.add(z3.Or(
                            X[t][i] + v1x != X[t][j] + v2x,
                            Y[t][i] + v1y != Y[t][j] + v2y,
                            Z[t][i] + v1z != Z[t][j] + v2z,
                        ))
        for i in range(N):
            for (vx, vy, vz) in world.pieces[i]:
                for (cx, cy, cz) in cage:
                    solver.add(z3.Or(
                        X[t][i] + vx != cx,
                        Y[t][i] + vy != cy,
                        Z[t][i] + vz != cz,
                    ))

    def add_transition(t_prev: int, t_next: int) -> None:
        options = []
        for i in range(N):
            for dx, dy, dz in DIRECTIONS:
                clauses = [
                    X[t_next][i] == X[t_prev][i] + dx,
                    Y[t_next][i] == Y[t_prev][i] + dy,
                    Z[t_next][i] == Z[t_prev][i] + dz,
                ]
                for j in range(N):
                    if j == i:
                        continue
                    clauses.extend([
                        X[t_next][j] == X[t_prev][j],
                        Y[t_next][j] == Y[t_prev][j],
                        Z[t_next][j] == Z[t_prev][j],
                    ])
                options.append(z3.And(*clauses))
        solver.add(z3.Or(*options))

    def bbox_disjoint_goal(t: int) -> z3.BoolRef:
        clauses = []
        for i in range(N):
            xmin_i, xmax_i, ymin_i, ymax_i, zmin_i, zmax_i = piece_bboxes[i]
            for j in range(i + 1, N):
                xmin_j, xmax_j, ymin_j, ymax_j, zmin_j, zmax_j = piece_bboxes[j]
                clauses.append(z3.Or(
                    X[t][i] + xmax_i < X[t][j] + xmin_j,
                    X[t][j] + xmax_j < X[t][i] + xmin_i,
                    Y[t][i] + ymax_i < Y[t][j] + ymin_j,
                    Y[t][j] + ymax_j < Y[t][i] + ymin_i,
                    Z[t][i] + zmax_i < Z[t][j] + zmin_j,
                    Z[t][j] + zmax_j < Z[t][i] + zmin_i,
                ))
        return z3.And(*clauses) if clauses else z3.BoolVal(True)

    def extract_path(model: z3.ModelRef, T: int) -> list[State]:
        path: list[State] = []
        for t in range(T + 1):
            state = tuple(
                (model[X[t][i]].as_long(), model[Y[t][i]].as_long(), model[Z[t][i]].as_long())
                for i in range(N)
            )
            path.append(state)
        return path

    add_step(0)
    for i, (sx, sy, sz) in enumerate(world.solved):
        solver.add(X[0][i] == sx, Y[0][i] == sy, Z[0][i] == sz)
    add_validity(0)

    for T in range(1, max_horizon + 1):
        add_step(T)
        add_transition(T - 1, T)
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
