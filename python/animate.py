"""Anima un dump del motor de billar-metegol.

El simulador escribe un archivo de texto; este script solo lo lee.
El formato del dump está en lib/traj.py.

    python python/animate.py --traj data/sample_traj.txt --show
    python python/animate.py --traj data/sample_traj.txt --out data/sample.gif --png data/sample.png
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

import matplotlib
from matplotlib.patches import Circle, Rectangle

from plot_style import (
    BLUE,
    FONT_SIZE,
    GREEN,
    SAVE_DPI,
    VERMILLION,
    apply_academic_style,
    style_axes,
)
from traj import Frame, Traj, read_traj

FRESH = BLUE
USED = VERMILLION
GOAL = GREEN
OBSTACLE = "#4d4d4d"
GIF_DPI = 100


def _stats_line(frame: Frame, n: int) -> str:
    ng_w = len(str(n))
    return f"t = {frame.t:7.3f} s    Ng = {frame.ng:{ng_w}d}    Fu = {frame.ng / n:4.2f}"


def make_figure(traj: Traj):
    apply_academic_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10.0, 7.0))
    L, W, r = traj.L, traj.W, traj.r
    margin = max(0.04 * L, 0.04 * W, 2.0 * r)
    ax.set_xlim(-margin, L + margin)
    ax.set_ylim(-margin, W + margin)
    ax.set_aspect("equal")
    style_axes(ax, r"posición $x$ (m)", r"posición $y$ (m)")
    ax.add_patch(Rectangle((0, 0), L, W, fill=False, edgecolor="black", lw=1.4, zorder=5))

    y0 = 0.5 * W - 0.5 * traj.d
    y1 = 0.5 * W + 0.5 * traj.d
    ax.plot([0, 0], [y0, y1], color=GOAL, lw=4.0, solid_capstyle="butt", zorder=6)
    ax.plot([L, L], [y0, y1], color=GOAL, lw=4.0, solid_capstyle="butt", zorder=6)

    for x, y, radius in traj.obstacles:
        ax.add_patch(Circle((x, y), radius, fc=OBSTACLE, ec="black", lw=0.6, zorder=2))

    patches = []
    for x, y, _vx, _vy, used in traj.frames[0].particles:
        patch = Circle((x, y), r, fc=USED if used else FRESH, ec="black", lw=0.4, zorder=4)
        ax.add_patch(patch)
        patches.append(patch)

    ax.plot([], [], linestyle="none", marker="o", color=FRESH, markeredgecolor="black", label="fresca")
    ax.plot([], [], linestyle="none", marker="o", color=USED, markeredgecolor="black", label="usada")
    ax.plot([], [], linestyle="none", marker="o", color=OBSTACLE, markeredgecolor="black", label="obstáculo")
    ax.plot([], [], color=GOAL, lw=4.0, label="arco")
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=4,
        frameon=True,
        fancybox=False,
    )

    fig.subplots_adjust(left=0.14, right=0.98, bottom=0.22, top=0.88)
    stats = fig.text(
        0.5,
        0.96,
        _stats_line(traj.frames[0], traj.n),
        ha="center",
        va="top",
        fontsize=FONT_SIZE,
        fontfamily="DejaVu Sans Mono",
    )
    fig.canvas.draw()
    fig.set_layout_engine("none")

    def draw(index: int) -> None:
        frame = traj.frames[index]
        for patch, (x, y, _vx, _vy, used) in zip(patches, frame.particles):
            patch.center = (x, y)
            patch.set_facecolor(USED if used else FRESH)
        stats.set_text(_stats_line(frame, traj.n))

    return fig, draw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--traj", required=True, help="dump escrito por el motor (--out)")
    parser.add_argument("--out", help="GIF de salida")
    parser.add_argument("--png", help="PNG del cuadro del medio")
    parser.add_argument("--show", action="store_true", help="abrir ventana")
    parser.add_argument("--fps", type=int, default=8)
    args = parser.parse_args()

    if args.fps < 1:
        sys.exit("--fps debe ser >= 1")
    if not args.out and not args.png and not args.show:
        args.show = True
    if not args.show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter

    try:
        traj = read_traj(args.traj)
    except (OSError, ValueError) as error:
        sys.exit(str(error))
    fig, draw = make_figure(traj)
    n_frames = len(traj.frames)

    if args.png:
        draw(n_frames // 2)
        png_path = Path(args.png)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(png_path, dpi=SAVE_DPI, facecolor="white")
        print(f"se escribió {png_path}")

    if args.out:
        gif_path = Path(args.out)
        gif_path.parent.mkdir(parents=True, exist_ok=True)
        anim = FuncAnimation(fig, draw, frames=n_frames, blit=False, interval=1000 / args.fps)
        anim.save(
            gif_path,
            writer=PillowWriter(fps=args.fps),
            dpi=GIF_DPI,
            savefig_kwargs={"facecolor": "white"},
        )
        print(f"se escribió {gif_path} ({n_frames} cuadros)")

    if args.show:
        FuncAnimation(fig, draw, frames=n_frames, blit=False, interval=1000 / args.fps, repeat=True)
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    main()
