"""Sanity-check demo: two L-shaped pieces, explore their state graph."""
from puzzle import State, World, shortest_path_lengths, state_graph

piece_a: frozenset = frozenset({(0, 0, 0), (1, 0, 0), (0, 1, 0)})
piece_b: frozenset = frozenset({(0, 0, 0), (1, 0, 0), (1, 1, 0)})

solved: State = ((0, 0, 0), (2, 0, 0))

world = World(
    pieces=(piece_a, piece_b),
    cage=frozenset(),
    solved=solved,
    max_displacement=2,
)

edges = state_graph(world)
dist = shortest_path_lengths(edges, world.solved)

print(f"states:         {len(edges)}")
print(f"directed edges: {sum(len(v) for v in edges.values())}")
print(f"max BFS depth:  {max(dist.values())}")
