"""Render the shortest disassembly path for a random 2-piece partition of a 3x3x3 cube.

Starts from solved and writes one PNG per step of the shortest walk to a
fully-disassembled (bbox-disjoint) state. Pieces that have become 'out' are
hidden from the frame so the view stays focused on what's still assembled.
Deterministic given the seed.
"""
from __future__ import annotations

import random
import sys

from generate import cube, random_partition, world_from_partition
from puzzle import pieces_out_along_path, shortest_disassembly_path
from render import render_path

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 13

rng = random.Random(seed)
target = cube(3)
pieces = random_partition(target, 2, rng)
world = world_from_partition(pieces, max_displacement=3)

path = shortest_disassembly_path(world)
if path is None:
    raise SystemExit("no disassembled state reachable from solved")

hidden = pieces_out_along_path(world, path)

print(f"seed={seed}")
print(f"piece sizes:        {sorted(len(p) for p in pieces)}")
print(f"disassembly steps:  {len(path) - 1}")

render_path(world, path, "disassembly_frames", hidden_per_frame=hidden)
print(f"wrote {len(path)} frames to disassembly_frames/")
