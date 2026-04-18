"""Core data types and state-graph exploration for 3D voxel puzzles."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

Voxel = tuple[int, int, int]
Shape = frozenset[Voxel]
Offset = tuple[int, int, int]
State = tuple[Offset, ...]

DIRECTIONS: tuple[Offset, ...] = (
    (1, 0, 0), (-1, 0, 0),
    (0, 1, 0), (0, -1, 0),
    (0, 0, 1), (0, 0, -1),
)


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


def state_graph(
    world: World,
    start: State | None = None,
    max_states: int = 200_000,
) -> dict[State, list[State]]:
    """BFS reachability from `start` (defaults to the solved state)."""
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
