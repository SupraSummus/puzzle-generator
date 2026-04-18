"""Core data types and state-graph exploration for 3D voxel puzzles."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Iterable

Voxel = tuple[int, int, int]
Shape = frozenset[Voxel]
Offset = tuple[int, int, int]
State = tuple[Offset, ...]
Bbox = tuple[int, int, int, int, int, int]  # (xmin, xmax, ymin, ymax, zmin, zmax)

DIRECTIONS: tuple[Offset, ...] = (
    (1, 0, 0), (-1, 0, 0),
    (0, 1, 0), (0, -1, 0),
    (0, 0, 1), (0, 0, -1),
)


def is_connected(shape: Shape) -> bool:
    """True iff `shape` is 6-connected (empty shape is trivially connected)."""
    if not shape:
        return True
    remaining = set(shape)
    start = next(iter(remaining))
    remaining.discard(start)
    q: deque[Voxel] = deque([start])
    while q:
        x, y, z = q.popleft()
        for dx, dy, dz in DIRECTIONS:
            n = (x + dx, y + dy, z + dz)
            if n in remaining:
                remaining.discard(n)
                q.append(n)
    return not remaining


def is_target_partition(
    pieces: tuple[Shape, ...],
    solved: State,
    target_shape: Shape,
) -> bool:
    """True iff the pieces at their solved offsets disjointly tile `target_shape` and each piece is connected."""
    if len(pieces) != len(solved):
        return False
    if not all(is_connected(p) for p in pieces):
        return False
    occupied: set[Voxel] = set()
    total = 0
    for shape, (ox, oy, oz) in zip(pieces, solved):
        for x, y, z in shape:
            v = (x + ox, y + oy, z + oz)
            if v in occupied:
                return False
            occupied.add(v)
            total += 1
    return total == len(target_shape) and occupied == set(target_shape)


@dataclass(frozen=True)
class World:
    pieces: tuple[Shape, ...]
    cage: Shape
    solved: State
    max_displacement: int  # L∞ bound on each piece offset relative to its solved offset

    def voxels_at(self, i: int, offset: Offset) -> Iterable[Voxel]:
        ox, oy, oz = offset
        for x, y, z in self.pieces[i]:
            yield (x + ox, y + oy, z + oz)

    def _in_range(self, i: int, offset: Offset) -> bool:
        sx, sy, sz = self.solved[i]
        ox, oy, oz = offset
        k = self.max_displacement
        return abs(ox - sx) <= k and abs(oy - sy) <= k and abs(oz - sz) <= k

    def valid(self, state: State) -> bool:
        occupied: set[Voxel] = set()
        for i, off in enumerate(state):
            if not self._in_range(i, off):
                return False
            for v in self.voxels_at(i, off):
                if v in self.cage or v in occupied:
                    return False
                occupied.add(v)
        return True

    def neighbors(self, state: State) -> Iterable[State]:
        for i in range(len(state)):
            ox, oy, oz = state[i]
            for dx, dy, dz in DIRECTIONS:
                new_off = (ox + dx, oy + dy, oz + dz)
                new_state = state[:i] + (new_off,) + state[i + 1:]
                if self.valid(new_state):
                    yield new_state


def _piece_bbox(world: World, state: State, i: int) -> Bbox | None:
    shape = world.pieces[i]
    if not shape:
        return None
    ox, oy, oz = state[i]
    xs = [x + ox for (x, _, _) in shape]
    ys = [y + oy for (_, y, _) in shape]
    zs = [z + oz for (_, _, z) in shape]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def _bboxes_overlap(a: Bbox, b: Bbox) -> bool:
    ax0, ax1, ay0, ay1, az0, az1 = a
    bx0, bx1, by0, by1, bz0, bz1 = b
    return (ax0 <= bx1 and bx0 <= ax1
            and ay0 <= by1 and by0 <= ay1
            and az0 <= bz1 and bz0 <= az1)


def bboxes_disjoint(world: World, state: State) -> bool:
    """True iff every pair of pieces' axis-aligned bounding boxes is disjoint.

    If this holds, no future slide can bring the pieces into contact — the
    puzzle is effectively disassembled, and further exploration would only
    shuffle pieces through empty space.
    """
    bboxes = [b for b in (_piece_bbox(world, state, i) for i in range(len(world.pieces)))
              if b is not None]
    for i in range(len(bboxes)):
        for j in range(i + 1, len(bboxes)):
            if _bboxes_overlap(bboxes[i], bboxes[j]):
                return False
    return True


def state_graph(
    world: World,
    start: State | None = None,
    stop_at: Callable[[State], bool] | None = None,
    max_states: int = 200_000,
) -> dict[State, list[State]]:
    """BFS reachability from `start` (defaults to the solved state).

    If `stop_at(state)` is true, the state is kept as a leaf (no outgoing
    edges recorded) — useful for terminating expansion once pieces have
    effectively disassembled.
    """
    if start is None:
        start = world.solved
    if not world.valid(start):
        raise ValueError("start state is invalid")
    edges: dict[State, list[State]] = {start: []}
    q: deque[State] = deque([start])
    while q:
        if len(edges) > max_states:
            raise RuntimeError(f"exceeded max_states={max_states}")
        s = q.popleft()
        if stop_at is not None and s != start and stop_at(s):
            continue
        for ns in world.neighbors(s):
            edges[s].append(ns)
            if ns not in edges:
                edges[ns] = []
                q.append(ns)
    return edges


def shortest_path_lengths(
    edges: dict[State, list[State]],
    source: State,
) -> dict[State, int]:
    dist = {source: 0}
    q: deque[State] = deque([source])
    while q:
        s = q.popleft()
        for ns in edges[s]:
            if ns not in dist:
                dist[ns] = dist[s] + 1
                q.append(ns)
    return dist


def shortest_disassembly_path(world: World) -> list[State] | None:
    """Shortest move sequence from `world.solved` to a fully-disassembled state.

    Returns None if no disassembly leaf is reachable. 'Fully disassembled'
    means every pair of piece bounding boxes is disjoint — no future slide
    can bring pieces back into contact. BFS leaves are exactly the
    bboxes-disjoint states (by construction of `stop_at`), so we filter on
    empty neighbor lists rather than re-running the predicate.
    """
    edges = state_graph(world, stop_at=lambda s: bboxes_disjoint(world, s))
    terminals = [s for s, nbrs in edges.items() if not nbrs and s != world.solved]
    if not terminals:
        return None
    dist = shortest_path_lengths(edges, world.solved)
    nearest = min(terminals, key=lambda s: dist[s])
    return shortest_path(edges, world.solved, nearest)


def pieces_out_along_path(world: World, path: list[State]) -> list[frozenset[int]]:
    """For each frame in `path`, return the set of piece indices to hide.

    A piece becomes 'out' on the first frame where its bounding box is
    disjoint from every other piece's bounding box. It is shown at that
    frame (so the disassembly event is visible) and hidden on every
    subsequent frame. Sticky: once hidden, stays hidden.
    """
    result: list[frozenset[int]] = []
    hidden: set[int] = set()
    n = len(world.pieces)
    for state in path:
        result.append(frozenset(hidden))
        bboxes = [_piece_bbox(world, state, i) for i in range(n)]
        for i in range(n):
            if i in hidden or bboxes[i] is None:
                continue
            if all(
                bboxes[j] is None or not _bboxes_overlap(bboxes[i], bboxes[j])
                for j in range(n) if j != i
            ):
                hidden.add(i)
    return result


def shortest_path(
    edges: dict[State, list[State]],
    source: State,
    target: State,
) -> list[State] | None:
    if source == target:
        return [source]
    prev: dict[State, State] = {}
    q: deque[State] = deque([source])
    seen = {source}
    while q:
        s = q.popleft()
        for ns in edges[s]:
            if ns in seen:
                continue
            seen.add(ns)
            prev[ns] = s
            if ns == target:
                path = [ns]
                while path[-1] != source:
                    path.append(prev[path[-1]])
                return list(reversed(path))
            q.append(ns)
    return None
