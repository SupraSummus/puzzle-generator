"""Render the shortest disassembly path for a non-trivial 3-piece partition of a 3x3x3 cube.

Searches seeds in order for the first partition whose shortest disassembly is
at least `MIN_MOVES` moves, so the committed frames are never a 1- or 2-move
giveaway (R-004 proxy: longer forced paths are less mentally inspectable).
Keeps the state space tiny by capping per-piece displacement at 1 (R-011).

Usage:
    python3 disassembly_demo.py           # searches for a seed meeting MIN_MOVES
    python3 disassembly_demo.py 7         # forces a specific seed
"""
from __future__ import annotations

import random
import sys

from generate import cube, random_partition, world_from_partition
from puzzle import pieces_out_along_path, shortest_disassembly_path

from render import render_path

N_PIECES = 3
CUBE_SIDE = 3
MAX_DISPLACEMENT = 1
MIN_MOVES = 5


def build(seed: int):
    rng = random.Random(seed)
    pieces = random_partition(cube(CUBE_SIDE), N_PIECES, rng)
    return pieces, world_from_partition(pieces, max_displacement=MAX_DISPLACEMENT)


def pick_seed() -> tuple[int, list, tuple]:
    for seed in range(10_000):
        pieces, world = build(seed)
        path = shortest_disassembly_path(world)
        if path is not None and len(path) - 1 >= MIN_MOVES:
            return seed, path, pieces
    raise SystemExit(f"no seed under 10_000 yielded a {MIN_MOVES}-move disassembly")


if len(sys.argv) > 1:
    seed = int(sys.argv[1])
    pieces, world = build(seed)
    path = shortest_disassembly_path(world)
    if path is None:
        raise SystemExit("no disassembled state reachable from solved")
else:
    seed, path, pieces = pick_seed()
    _, world = build(seed)

hidden = pieces_out_along_path(world, path)

print(f"seed={seed}")
print(f"piece sizes:        {sorted(len(p) for p in pieces)}")
print(f"disassembly steps:  {len(path) - 1}")

render_path(world, path, "disassembly_frames", hidden_per_frame=hidden)
print(f"wrote {len(path)} frames to disassembly_frames/")
