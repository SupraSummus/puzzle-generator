"""Render puzzle states to PNG frames so a human can eyeball them."""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from puzzle import State, World


def _state_bbox(world: World, states: list[State]) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    vs = set(world.cage)
    for state in states:
        for i, off in enumerate(state):
            vs.update(world.voxels_at(i, off))
    xs = [v[0] for v in vs]
    ys = [v[1] for v in vs]
    zs = [v[2] for v in vs]
    return (min(xs), min(ys), min(zs)), (max(xs) + 1, max(ys) + 1, max(zs) + 1)


def render_path(world: World, path: list[State], out_dir: str) -> None:
    """Write one PNG per state in `path` to `out_dir`, all on a shared global bbox."""
    os.makedirs(out_dir, exist_ok=True)
    (x0, y0, z0), (x1, y1, z1) = _state_bbox(world, path)
    shape = (x1 - x0, y1 - y0, z1 - z0)
    cmap = plt.get_cmap("tab10")

    for idx, state in enumerate(path):
        fig = plt.figure(figsize=(6, 6))
        ax = fig.add_subplot(111, projection="3d")

        if world.cage:
            cage_arr = np.zeros(shape, dtype=bool)
            for (x, y, z) in world.cage:
                cage_arr[x - x0, y - y0, z - z0] = True
            ax.voxels(cage_arr, facecolors=(0.5, 0.5, 0.5, 0.2), edgecolor=(0.3, 0.3, 0.3, 0.4))

        for i, off in enumerate(state):
            arr = np.zeros(shape, dtype=bool)
            for (x, y, z) in world.voxels_at(i, off):
                arr[x - x0, y - y0, z - z0] = True
            ax.voxels(arr, facecolors=cmap(i % 10), edgecolor="black")

        ax.set_xlim(0, shape[0])
        ax.set_ylim(0, shape[1])
        ax.set_zlim(0, shape[2])
        ax.set_box_aspect(shape)
        ax.set_title(f"step {idx}/{len(path) - 1}")
        plt.tight_layout()
        fig.savefig(
            os.path.join(out_dir, f"frame_{idx:03d}.png"),
            dpi=80,
            metadata={"Software": None},
        )
        plt.close(fig)
