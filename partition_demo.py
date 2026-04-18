"""Generate a random partition of a 3x3x3 cube and render the solved state.

Visual validation: the rendered cube should be fully filled, with each piece
a single connected blob in its own color. No gaps, no overlaps.
"""
from __future__ import annotations

import random
import sys

from generate import cube, random_partition, world_from_partition
from puzzle import is_target_partition
from render import render_path

seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
n_pieces = int(sys.argv[2]) if len(sys.argv) > 2 else 4

rng = random.Random(seed)
target = cube(3)
pieces = random_partition(target, n_pieces, rng)

print(f"seed={seed}, pieces={n_pieces}")
print(f"piece sizes: {sorted(len(p) for p in pieces)}")

world = world_from_partition(pieces, max_displacement=1)
assert is_target_partition(world.pieces, world.solved, target)

render_path(world, [world.solved], "partition_frames")
print("wrote partition_frames/frame_000.png")
