"""Seed generation: partition a target shape into connected pieces."""
from __future__ import annotations

import random

from puzzle import DIRECTIONS, Shape, State, Voxel, World


def cube(n: int) -> Shape:
    """The n-side solid cube occupying [0, n) on each axis."""
    return frozenset((x, y, z) for x in range(n) for y in range(n) for z in range(n))


def cross_3d(arm: int) -> Shape:
    """A plus/3D-cross: a central unit cube with three orthogonal arms of length `arm`."""
    vs: set[Voxel] = {(0, 0, 0)}
    for k in range(1, arm + 1):
        for d in DIRECTIONS:
            vs.add((d[0] * k, d[1] * k, d[2] * k))
    return frozenset(vs)


def random_partition(
    target_shape: Shape,
    n_pieces: int,
    rng: random.Random,
) -> tuple[Shape, ...]:
    """Randomly partition `target_shape` into `n_pieces` connected pieces by simultaneous flood-fill.

    Returns piece shapes in the same (world) coordinates as `target_shape`; when used as
    `World.pieces`, pair them with all-zero solved offsets.
    """
    if n_pieces <= 0:
        raise ValueError("n_pieces must be positive")
    if n_pieces > len(target_shape):
        raise ValueError("more pieces than voxels in target shape")

    remaining = set(target_shape)
    # Sort before sampling so hash randomization cannot change the outcome.
    seed_list = rng.sample(sorted(remaining), n_pieces)
    pieces: list[set[Voxel]] = [{s} for s in seed_list]
    for s in seed_list:
        remaining.remove(s)

    while remaining:
        candidates: list[tuple[int, Voxel]] = []
        for i, piece in enumerate(pieces):
            for x, y, z in sorted(piece):
                for dx, dy, dz in DIRECTIONS:
                    n = (x + dx, y + dy, z + dz)
                    if n in remaining:
                        candidates.append((i, n))
        if not candidates:
            raise RuntimeError(
                "flood-fill stalled; target shape may be disconnected or seeds unreachable"
            )
        candidates.sort()
        i, v = rng.choice(candidates)
        pieces[i].add(v)
        remaining.discard(v)

    return tuple(frozenset(p) for p in pieces)


def world_from_partition(
    pieces: tuple[Shape, ...],
    max_displacement: int,
    cage: Shape = frozenset(),
) -> World:
    """Build a World whose solved state is the partition as-is (all zero offsets)."""
    solved: State = tuple((0, 0, 0) for _ in pieces)
    return World(
        pieces=pieces,
        cage=cage,
        solved=solved,
        max_displacement=max_displacement,
    )
