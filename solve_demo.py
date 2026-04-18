"""Render the shortest solve path for a random 2-piece partition of a 3x3x3 cube.

Picks the reachable state farthest from solved and writes one PNG per step of
the shortest walk back to solved. Deterministic given the seed.
"""
from __future__ import annotations

import random
import sys

from generate import cube, random_partition, world_from_partition
from puzzle import (
    bboxes_disjoint,
    is_target_partition,
    shortest_path,
    shortest_path_lengths,
    state_graph,
)
from render import render_path

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 13

rng = random.Random(seed)
target = cube(3)
pieces = random_partition(target, 2, rng)
world = world_from_partition(pieces, max_displacement=3)
assert is_target_partition(world.pieces, world.solved, target)

edges = state_graph(world, stop_at=lambda s: bboxes_disjoint(world, s))
dist = shortest_path_lengths(edges, world.solved)

terminals = [s for s in edges if s != world.solved and bboxes_disjoint(world, s)]
if not terminals:
    raise SystemExit(
        "no disassembled (bbox-disjoint) state reachable — puzzle is stuck"
    )
disassembled = max(terminals, key=lambda s: dist[s])

print(f"seed={seed}")
print(f"piece sizes:        {sorted(len(p) for p in pieces)}")
print(f"reachable states:   {len(edges)}")
print(f"terminal states:    {len(terminals)}")
print(f"disassembly depth:  {dist[disassembled]}")

forward = shortest_path(edges, world.solved, disassembled)
assert forward is not None
path = list(reversed(forward))

render_path(world, path, "frames")
print(f"wrote {len(path)} frames to frames/")
