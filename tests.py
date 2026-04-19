"""Invariant tests for the puzzle model.

Run with `python3 tests.py`. Exits non-zero on failure.
"""
from __future__ import annotations

import sys
import traceback

import random

from generate import cube, random_partition, world_from_partition
from puzzle import (
    DIRECTIONS,
    State,
    World,
    bboxes_disjoint,
    is_connected,
    is_target_partition,
    pieces_out_along_path,
    shortest_disassembly_path,
    shortest_path,
    shortest_path_lengths,
    state_graph,
)


def test_overlap_detection() -> None:
    cube = frozenset({(0, 0, 0)})
    world = World(
        pieces=(cube, cube),
        cage=frozenset(),
        solved=((0, 0, 0), (1, 0, 0)),
        max_displacement=1,
    )
    assert world.valid(((0, 0, 0), (1, 0, 0)))
    assert not world.valid(((0, 0, 0), (0, 0, 0)))


def test_cage_collision() -> None:
    cube = frozenset({(0, 0, 0)})
    world = World(
        pieces=(cube,),
        cage=frozenset({(1, 0, 0)}),
        solved=((0, 0, 0),),
        max_displacement=2,
    )
    assert world.valid(((0, 0, 0),))
    assert not world.valid(((1, 0, 0),))


def test_displacement_bound() -> None:
    cube = frozenset({(0, 0, 0)})
    world = World(
        pieces=(cube,),
        cage=frozenset(),
        solved=((0, 0, 0),),
        max_displacement=2,
    )
    assert world.valid(((2, 0, 0),))
    assert not world.valid(((3, 0, 0),))
    assert not world.valid(((0, -3, 0),))


def test_moves_are_reversible() -> None:
    """Every slide must have a matching reverse slide. The graph should be symmetric."""
    piece_a = frozenset({(0, 0, 0), (1, 0, 0)})
    piece_b = frozenset({(0, 0, 0), (0, 1, 0)})
    world = World(
        pieces=(piece_a, piece_b),
        cage=frozenset(),
        solved=((0, 0, 0), (3, 0, 0)),
        max_displacement=2,
    )
    edges = state_graph(world)
    for s, nbrs in edges.items():
        for n in nbrs:
            assert s in edges[n], f"missing reverse edge {n} -> {s}"


def test_free_single_piece_state_count() -> None:
    """A lone unit cube with max_displacement=k must produce exactly (2k+1)^3 states."""
    cube = frozenset({(0, 0, 0)})
    for k in (0, 1, 2, 3):
        world = World(
            pieces=(cube,),
            cage=frozenset(),
            solved=((0, 0, 0),),
            max_displacement=k,
        )
        edges = state_graph(world)
        assert len(edges) == (2 * k + 1) ** 3, (k, len(edges))


def test_free_single_piece_interior_degree() -> None:
    """Every interior state must have exactly 6 neighbors."""
    cube = frozenset({(0, 0, 0)})
    k = 2
    world = World(
        pieces=(cube,),
        cage=frozenset(),
        solved=((0, 0, 0),),
        max_displacement=k,
    )
    edges = state_graph(world)
    for (off,), nbrs in edges.items():
        if all(abs(c) < k for c in off):
            assert len(nbrs) == 6, (off, nbrs)


def test_cage_tube_forces_line_graph() -> None:
    """A cube inside a tube along x can only slide along x; the graph is a path."""
    cube = frozenset({(0, 0, 0)})
    cage = frozenset(
        (x, y, z)
        for x in range(-5, 6)
        for y in range(-2, 3)
        for z in range(-2, 3)
        if (y, z) != (0, 0)
    )
    world = World(
        pieces=(cube,),
        cage=cage,
        solved=((0, 0, 0),),
        max_displacement=3,
    )
    edges = state_graph(world)
    assert len(edges) == 7  # offsets (-3,0,0) .. (3,0,0)
    degrees = sorted(len(n) for n in edges.values())
    assert degrees == [1, 1, 2, 2, 2, 2, 2]


def test_invalid_solved_raises() -> None:
    cube = frozenset({(0, 0, 0)})
    world = World(
        pieces=(cube, cube),
        cage=frozenset(),
        solved=((0, 0, 0), (0, 0, 0)),
        max_displacement=1,
    )
    try:
        state_graph(world)
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid solved state")


def test_shortest_path_is_walk_of_valid_moves() -> None:
    """The returned path must be a walk in the state graph ending at target."""
    piece_a = frozenset({(0, 0, 0), (1, 0, 0)})
    piece_b = frozenset({(0, 0, 0), (0, 1, 0)})
    world = World(
        pieces=(piece_a, piece_b),
        cage=frozenset(),
        solved=((0, 0, 0), (3, 0, 0)),
        max_displacement=2,
    )
    edges = state_graph(world)
    dist = shortest_path_lengths(edges, world.solved)
    farthest = max(dist, key=lambda s: dist[s])
    path = shortest_path(edges, farthest, world.solved)
    assert path is not None
    assert path[0] == farthest
    assert path[-1] == world.solved
    assert len(path) - 1 == dist[farthest]
    for a, b in zip(path, path[1:]):
        assert b in edges[a], f"non-edge step {a} -> {b}"


def test_shortest_path_move_is_single_piece_unit_slide() -> None:
    """Each step must differ from the previous by one piece's offset changing by ±1 on one axis."""
    piece_a = frozenset({(0, 0, 0), (1, 0, 0)})
    piece_b = frozenset({(0, 0, 0), (0, 1, 0)})
    world = World(
        pieces=(piece_a, piece_b),
        cage=frozenset(),
        solved=((0, 0, 0), (3, 0, 0)),
        max_displacement=2,
    )
    edges = state_graph(world)
    dist = shortest_path_lengths(edges, world.solved)
    farthest = max(dist, key=lambda s: dist[s])
    path = shortest_path(edges, farthest, world.solved)
    assert path is not None
    for a, b in zip(path, path[1:]):
        diffs = [tuple(bi - ai for ai, bi in zip(ao, bo)) for ao, bo in zip(a, b)]
        nonzero = [d for d in diffs if d != (0, 0, 0)]
        assert len(nonzero) == 1, (a, b)
        assert nonzero[0] in DIRECTIONS, (a, b, nonzero[0])


def test_is_connected() -> None:
    assert is_connected(frozenset())
    assert is_connected(frozenset({(0, 0, 0)}))
    assert is_connected(frozenset({(0, 0, 0), (1, 0, 0), (2, 0, 0)}))
    assert is_connected(frozenset({(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1)}))
    # Two disjoint cubes.
    assert not is_connected(frozenset({(0, 0, 0), (2, 0, 0)}))
    # Diagonal is not connected under 6-neighborhood.
    assert not is_connected(frozenset({(0, 0, 0), (1, 1, 0)}))


def test_is_target_partition_accepts_valid() -> None:
    target = cube(2)
    pieces = (
        frozenset({(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)}),
        frozenset({(0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)}),
    )
    solved: State = ((0, 0, 0), (0, 0, 0))
    assert is_target_partition(pieces, solved, target)


def test_is_target_partition_rejects_overlap() -> None:
    target = cube(2)
    pieces = (
        frozenset({(0, 0, 0), (1, 0, 0)}),
        frozenset({(0, 0, 0), (1, 0, 0)}),  # same voxels
    )
    solved: State = ((0, 0, 0), (0, 0, 0))
    assert not is_target_partition(pieces, solved, target)


def test_is_target_partition_rejects_missing_voxels() -> None:
    target = cube(2)
    pieces = (frozenset({(0, 0, 0), (1, 0, 0)}),)
    solved: State = ((0, 0, 0),)
    assert not is_target_partition(pieces, solved, target)


def test_is_target_partition_rejects_disconnected_piece() -> None:
    target = frozenset({(0, 0, 0), (1, 0, 0), (3, 0, 0), (4, 0, 0)})
    pieces = (frozenset({(0, 0, 0), (1, 0, 0), (3, 0, 0), (4, 0, 0)}),)
    solved: State = ((0, 0, 0),)
    assert not is_target_partition(pieces, solved, target)


def test_random_partition_covers_target_and_each_piece_connected() -> None:
    rng = random.Random(42)
    target = cube(3)
    for n in (2, 3, 4, 5):
        for _ in range(10):
            pieces = random_partition(target, n, rng)
            assert len(pieces) == n
            assert all(len(p) >= 1 for p in pieces)
            assert all(is_connected(p) for p in pieces)
            solved: State = tuple((0, 0, 0) for _ in pieces)
            assert is_target_partition(pieces, solved, target)


def test_random_partition_into_every_voxel_gives_singletons() -> None:
    rng = random.Random(0)
    target = cube(2)  # 8 voxels
    pieces = random_partition(target, 8, rng)
    assert sorted(len(p) for p in pieces) == [1] * 8


def test_world_from_partition_yields_valid_solved_state() -> None:
    rng = random.Random(7)
    target = cube(3)
    pieces = random_partition(target, 4, rng)
    world = world_from_partition(pieces, max_displacement=1)
    assert world.valid(world.solved)


def test_bboxes_disjoint_solved_cube_is_false() -> None:
    """Pieces in a freshly assembled cube necessarily share bounding boxes."""
    rng = random.Random(0)
    target = cube(3)
    for n in (2, 3, 4):
        pieces = random_partition(target, n, rng)
        world = world_from_partition(pieces, max_displacement=2)
        assert not bboxes_disjoint(world, world.solved)


def test_bboxes_disjoint_separated_pieces_is_true() -> None:
    a = frozenset({(0, 0, 0), (1, 0, 0)})
    b = frozenset({(0, 0, 0), (1, 0, 0)})
    world = World(
        pieces=(a, b),
        cage=frozenset(),
        solved=((0, 0, 0), (10, 0, 0)),
        max_displacement=0,
    )
    assert bboxes_disjoint(world, world.solved)


def test_bboxes_disjoint_adjacent_unit_cubes_is_true() -> None:
    """Adjacent unit cubes have disjoint integer bboxes; we treat them as separated."""
    a = frozenset({(0, 0, 0)})
    b = frozenset({(0, 0, 0)})
    world = World(
        pieces=(a, b),
        cage=frozenset(),
        solved=((0, 0, 0), (1, 0, 0)),
        max_displacement=0,
    )
    assert bboxes_disjoint(world, world.solved)


def test_bboxes_disjoint_interleaved_ls_is_false() -> None:
    """Two L-pieces placed so voxels don't overlap but bboxes do."""
    l = frozenset({(0, 0, 0), (1, 0, 0), (0, 1, 0)})
    world = World(
        pieces=(l, l),
        cage=frozenset(),
        solved=((0, 0, 0), (1, 1, 0)),
        max_displacement=0,
    )
    assert world.valid(world.solved)
    assert not bboxes_disjoint(world, world.solved)


def test_state_graph_stop_at_trims_expansion() -> None:
    """With stop_at=bboxes_disjoint the graph is bounded by the disassembly frontier."""
    rng = random.Random(13)
    target = cube(3)
    pieces = random_partition(target, 2, rng)
    world = world_from_partition(pieces, max_displacement=3)
    full = state_graph(world)
    trimmed = state_graph(world, stop_at=lambda s: bboxes_disjoint(world, s))
    assert len(trimmed) < len(full)
    # Every leaf in the trimmed graph either is the root or has disjoint bboxes.
    for s, nbrs in trimmed.items():
        if not nbrs and s != world.solved:
            assert bboxes_disjoint(world, s), s


def test_shortest_disassembly_path_ends_bbox_disjoint() -> None:
    """The returned path starts at solved and ends at a bbox-disjoint state."""
    rng = random.Random(13)
    target = cube(3)
    pieces = random_partition(target, 2, rng)
    world = world_from_partition(pieces, max_displacement=3)
    path = shortest_disassembly_path(world)
    assert path is not None
    assert path[0] == world.solved
    assert bboxes_disjoint(world, path[-1])
    for a, b in zip(path, path[1:]):
        assert b in set(world.neighbors(a)), (a, b)


def test_pieces_out_along_path_is_sticky_and_lagged() -> None:
    """Once hidden, a piece stays hidden; a piece becomes hidden the frame
    after its bbox is first disjoint from every other piece."""
    rng = random.Random(13)
    target = cube(3)
    pieces = random_partition(target, 2, rng)
    world = world_from_partition(pieces, max_displacement=3)
    path = shortest_disassembly_path(world)
    assert path is not None
    hidden = pieces_out_along_path(world, path)
    assert len(hidden) == len(path)
    assert hidden[0] == frozenset()
    for a, b in zip(hidden, hidden[1:]):
        assert a <= b, (a, b)


def test_sat_solver_matches_bfs_on_small_partitions() -> None:
    """On 3x3x3 / 2-piece partitions, the SAT solver returns a shortest path
    of the same length as BFS, starting at solved, ending bbox-disjoint, and
    every step a single-piece unit slide."""
    from sat_solve import shortest_disassembly_path_sat

    target = cube(3)
    for seed in range(5):
        rng = random.Random(seed)
        pieces = random_partition(target, 2, rng)
        world = world_from_partition(pieces, max_displacement=3)
        bfs = shortest_disassembly_path(world)
        sat = shortest_disassembly_path_sat(world, max_horizon=20)
        if bfs is None:
            assert sat is None, (seed, sat)
            continue
        assert sat is not None, seed
        assert len(sat) == len(bfs), (seed, len(sat), len(bfs))
        assert sat[0] == world.solved, seed
        assert bboxes_disjoint(world, sat[-1]), seed
        for a, b in zip(sat, sat[1:]):
            diffs = [tuple(bi - ai for ai, bi in zip(ao, bo)) for ao, bo in zip(a, b)]
            nonzero = [d for d in diffs if d != (0, 0, 0)]
            assert len(nonzero) == 1, (seed, a, b)
            assert nonzero[0] in DIRECTIONS, (seed, a, b, nonzero[0])


def test_sat_solver_returns_none_when_no_disassembly() -> None:
    """A trivially-caged single piece has no path to bbox-disjoint (only one piece)."""
    from sat_solve import shortest_disassembly_path_sat

    # Single piece: no pair, so bbox-disjoint goal is vacuously true at t=0.
    # We require T >= 1, so there must be some move. Here a caged unit cube that
    # cannot move returns None within the horizon.
    piece = frozenset({(0, 0, 0)})
    cage = frozenset({(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)})
    world = World(
        pieces=(piece,),
        cage=cage,
        solved=((0, 0, 0),),
        max_displacement=1,
    )
    # One piece => only the T=0 state is bbox-disjoint (vacuously). No move
    # possible at all. SAT with horizon >= 1 returns None.
    assert shortest_disassembly_path_sat(world, max_horizon=3) is None


def _run() -> int:
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
        except Exception:
            failed += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
        else:
            print(f"ok    {name}")
    print()
    print(f"{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())
