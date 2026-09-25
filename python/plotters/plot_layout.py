"""Mesa con los obstáculos de un archivo, sin partículas.

Cada línea es xk yk Rk, en metros. L, W y d son los del enunciado.

    python python/plotters/plot_layout.py --obstacles configs/disco_grande.txt --output disco.png
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import matplotlib
from matplotlib.patches import Circle, Rectangle

from plot_style import GREEN, apply_academic_style, legend_corner, save_figure, style_axes

L = 1.20
W = 0.68
D_GOAL = 0.20
OBSTACLE = "#4d4d4d"


def read_obstacles(path: Path) -> list[tuple[float, float, float]]:
    discs = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"{path}:{lineno}: se esperaban xk yk Rk, hay {len(parts)} campos")
        discs.append((float(parts[0]), float(parts[1]), float(parts[2])))
    if not discs:
        raise ValueError(f"{path}: no hay obstáculos")
    return discs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--obstacles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        discs = read_obstacles(args.obstacles)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    apply_academic_style()
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(10.0, 7.6))
    ax = fig.add_axes([0.11, 0.30, 0.86, 0.64])
    margin = 0.06
    ax.set_xlim(-margin, L + margin)
    ax.set_ylim(-margin, W + margin)
    ax.set_aspect("equal")
    style_axes(ax, r"largo $x$ (m)", r"ancho $y$ (m)")

    ax.add_patch(Rectangle((0, 0), L, W, fill=False, edgecolor="black", lw=1.4, zorder=3))
    y0, y1 = 0.5 * W - 0.5 * D_GOAL, 0.5 * W + 0.5 * D_GOAL
    ax.plot([0, 0], [y0, y1], color=GREEN, lw=4.0, solid_capstyle="butt", zorder=4, label="arco")
    ax.plot([L, L], [y0, y1], color=GREEN, lw=4.0, solid_capstyle="butt", zorder=4)
    for x, y, radius in discs:
        ax.add_patch(Circle((x, y), radius, fc=OBSTACLE, ec="black", lw=0.8, zorder=2))
    ax.plot([], [], linestyle="none", marker="o", color=OBSTACLE, markeredgecolor="black", label="obstáculo")
    handles, labels = ax.get_legend_handles_labels()
    corner = legend_corner(ax)
    if corner is not None:
        ax.legend(handles, labels, loc=corner, frameon=True, fancybox=False, framealpha=0.92)
    else:
        ax.legend(
            handles,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, -0.16),
            ncol=2,
            frameon=True,
            fancybox=False,
        )
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()
