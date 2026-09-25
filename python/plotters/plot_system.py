"""Genera un esquema conceptual del sistema de billar-metegol.

La figura usa posiciones ilustrativas: no lee trayectorias ni configuraciones
de obstáculos, y por eso sirve para explicar el modelo sin mostrar datos de
una simulación concreta.

    python python/plotters/plot_system.py --output docs/system_scheme.png
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import matplotlib
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

from plot_style import BLUE, GREEN, VERMILLION, apply_academic_style, save_figure

L = 1.20
M = 0.68
GOAL_WIDTH = 0.20
PARTICLE_RADIUS = 0.028
OBSTACLE_COLOR = "#4d4d4d"


def dimension_arrow(ax, start, end, label, text_offset):
    """Dibuja una cota con flechas y su etiqueta."""
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="<->",
            mutation_scale=14,
            linewidth=1.4,
            color="black",
            clip_on=False,
        )
    )
    midpoint = ((start[0] + end[0]) / 2 + text_offset[0], (start[1] + end[1]) / 2 + text_offset[1])
    ax.text(midpoint[0], midpoint[1], label, ha="center", va="center", color="black")


def draw_system(ax):
    """Dibuja una configuración genérica, sin valores de una realización."""
    ax.set_xlim(-0.16, L + 0.16)
    ax.set_ylim(-0.20, M + 0.16)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.add_patch(Rectangle((0, 0), L, M, facecolor="#f7f7f5", edgecolor="black", lw=2.0, zorder=1))

    goal_y0 = 0.5 * M - 0.5 * GOAL_WIDTH
    goal_y1 = 0.5 * M + 0.5 * GOAL_WIDTH
    for x in (0, L):
        ax.plot([x, x], [goal_y0, goal_y1], color=GREEN, lw=8, solid_capstyle="butt", zorder=4)

    obstacles = ((0.43, 0.22, 0.075), (0.72, 0.47, 0.065), (0.91, 0.22, 0.055))
    for x, y, radius in obstacles:
        ax.add_patch(Circle((x, y), radius, facecolor=OBSTACLE_COLOR, edgecolor="black", lw=1.0, zorder=3))

    particles = (
        (0.13, 0.16, BLUE), (0.18, 0.36, BLUE), (0.24, 0.55, VERMILLION),
        (0.31, 0.14, BLUE), (0.34, 0.45, BLUE), (0.52, 0.12, VERMILLION),
        (0.55, 0.56, BLUE), (0.65, 0.30, VERMILLION), (0.80, 0.16, BLUE),
        (0.82, 0.57, BLUE), (0.96, 0.40, VERMILLION), (1.04, 0.55, BLUE),
        (1.08, 0.15, BLUE), (1.12, 0.31, VERMILLION),
    )
    for x, y, color in particles:
        ax.add_patch(Circle((x, y), PARTICLE_RADIUS, facecolor=color, edgecolor="black", lw=0.8, zorder=5))

    dimension_arrow(ax, (0, -0.09), (L, -0.09), r"$L$", (0, -0.035))
    dimension_arrow(ax, (-0.09, 0), (-0.09, M), r"$M$", (-0.035, 0))
    dimension_arrow(ax, (L + 0.055, goal_y0), (L + 0.055, goal_y1), r"$d$", (0.035, 0))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=Path("docs/system_scheme.png"),
                        help="archivo de imagen de salida (por defecto: docs/system_scheme.png)")
    args = parser.parse_args()

    apply_academic_style()
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(10.0, 6.2))
    ax = fig.add_axes([0.08, 0.12, 0.84, 0.76])
    draw_system(ax)
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()