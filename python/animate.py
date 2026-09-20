r"""Anima un dump del motor de billar-metegol.

El simulador escribe un archivo de texto; este script solo lo lee. Cada
cuadro es un evento (cada k eventos o un gol). La velocidad de
reproducción (--fps) es una elección de visualización, no un dt de la
simulación: entre cuadros pasan k eventos, no un tiempo fijo.

    python python/animate.py --traj data/sample_traj.txt --show
    python python/animate.py --traj run.txt --out run.gif --png run.png
    python python/animate.py --traj run.txt --mp4 run.mp4 --clean --fps 12
    python python/animate.py --traj demo.txt --arrows --png demo.png --frame 0

Por defecto se ve la mesa, los arcos, los obstáculos, las partículas
frescas (azul) y usadas (rojo), un anillo sobre la que acaba de hacer un
gol, y arriba Ng y Fu. No se muestra ningún tiempo.

--inset   agrega un inset con Fu(t) que crece con la animación.
--arrows  flechas de velocidad (exactas: vx, vy del cuadro). Útil con pocas
          partículas; con N = 100 tapan la mesa.
--clean   sin ejes ni ticks, con barra de escala: para el video.
--frame   índice del cuadro del PNG (0 = condición inicial).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

import matplotlib
from matplotlib.patches import Circle, Patch, Rectangle

from metrics import ng_series
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
ARROW_SCALE = 0.06  # metros de flecha por m/s
RING_FACTOR = 2.2  # radio del anillo de gol, en radios de partícula


def _stats_line(frame: Frame, n: int) -> str:
    ng_w = len(str(n))
    return f"Ng = {frame.ng:{ng_w}d}    Fu = {frame.ng / n:4.2f}"


def make_figure(traj: Traj, arrows: bool = False, clean: bool = False, inset: bool = False):
    apply_academic_style()
    import matplotlib.pyplot as plt

    L, W, r, n = traj.L, traj.W, traj.r, traj.n
    margin = max(0.04 * L, 0.04 * W, 2.0 * r)

    fig = plt.figure(figsize=(10.0, 7.6 if inset else 6.4))
    if inset:
        rect = [0.09, 0.36, 0.88, 0.55] if not clean else [0.02, 0.30, 0.96, 0.62]
    else:
        rect = [0.09, 0.22, 0.88, 0.68] if not clean else [0.02, 0.16, 0.96, 0.76]
    ax = fig.add_axes(rect)
    ax.set_xlim(-margin, L + margin)
    ax.set_ylim(-margin, W + margin)
    ax.set_aspect("equal")

    # Mesa: contorno negro. El arco se dibuja como una cajita detrás de cada
    # pared corta (la pared sigue reflejando; el arco solo marca la franja).
    ax.add_patch(Rectangle((0, 0), L, W, fill=False, edgecolor="black", lw=1.4, zorder=2))
    y0 = 0.5 * W - 0.5 * traj.d
    depth = 0.55 * margin
    goal_boxes = {
        "left": Rectangle((-depth, y0), depth, traj.d, fc=GOAL, ec=GOAL, lw=1.5, alpha=0.35, zorder=1),
        "right": Rectangle((L, y0), depth, traj.d, fc=GOAL, ec=GOAL, lw=1.5, alpha=0.35, zorder=1),
    }
    for box in goal_boxes.values():
        ax.add_patch(box)

    for x, y, radius in traj.obstacles:
        ax.add_patch(Circle((x, y), radius, fc=OBSTACLE, ec="black", lw=0.6, zorder=3))

    patches, rings = [], []
    for x, y, _vx, _vy, used in traj.frames[0].particles:
        patch = Circle((x, y), r, fc=USED if used else FRESH, ec="black", lw=0.4, zorder=4)
        ring = Circle((x, y), RING_FACTOR * r, fill=False, ec="black", lw=2.0, zorder=5, visible=False)
        ax.add_patch(patch)
        ax.add_patch(ring)
        patches.append(patch)
        rings.append(ring)

    quiver = None
    if arrows:
        xs = [p[0] for p in traj.frames[0].particles]
        ys = [p[1] for p in traj.frames[0].particles]
        us = [p[2] for p in traj.frames[0].particles]
        vs = [p[3] for p in traj.frames[0].particles]
        quiver = ax.quiver(xs, ys, us, vs, angles="xy", scale_units="xy", scale=1.0 / ARROW_SCALE,
                           color="black", width=0.003, zorder=5)

    if clean:
        ax.set_axis_off()
        bar = 0.2
        ax.plot([0, bar], [-0.55 * margin, -0.55 * margin], color="black", lw=2.0, zorder=6)
        ax.text(0.5 * bar, -0.62 * margin, f"{bar:g} m", ha="center", va="top", fontsize=12)
    else:
        style_axes(ax, r"posición $x$ (m)", r"posición $y$ (m)")

    # Leyenda adentro de la figura (abajo a la izquierda), no como caja aparte.
    handles = [
        ax.plot([], [], linestyle="none", marker="o", color=FRESH, markeredgecolor="black", label="fresca")[0],
        ax.plot([], [], linestyle="none", marker="o", color=USED, markeredgecolor="black", label="usada")[0],
        ax.plot([], [], linestyle="none", marker="o", color=OBSTACLE, markeredgecolor="black", label="obstáculo")[0],
        Patch(fc=GOAL, ec=GOAL, alpha=0.5, label="arco"),
    ]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.06, 0.04), ncol=2,
               frameon=True, fancybox=False, fontsize=14)

    # Inset Fu(t) opcional: escalera exacta de los cuadros de gol, hasta el cuadro actual.
    fu_line = fu_dot = None
    series = ng_series(traj)
    ts = [t for t, _ng in series]
    fus = [ng / n for _t, ng in series]
    if inset:
        ax_in = fig.add_axes([0.62, 0.07, 0.34, 0.15])
        ax_in.set_xlim(0, ts[-1] if ts[-1] > 0 else 1.0)
        ax_in.set_ylim(0, 1.0)
        ax_in.axhline(0.9, color="black", linestyle="--", lw=0.8)
        (fu_line,) = ax_in.plot([], [], color=USED, lw=1.6, drawstyle="steps-post")
        (fu_dot,) = ax_in.plot([], [], marker="o", color=USED, markeredgecolor="black", markersize=5, linestyle="none")
        ax_in.set_xlabel("t (s)", fontsize=12, labelpad=2)
        ax_in.set_ylabel(r"$F_u$", fontsize=12, labelpad=2)
        ax_in.tick_params(labelsize=10)
        ax_in.set_yticks([0, 0.5, 0.9])

    stats = fig.text(0.5, 0.965, _stats_line(traj.frames[0], n), ha="center", va="top",
                     fontsize=FONT_SIZE, fontfamily="DejaVu Sans Mono")

    def draw(index: int) -> None:
        frame = traj.frames[index]
        prev = traj.frames[index - 1] if index > 0 else None
        flash = {"left": False, "right": False}
        for i, (patch, ring, p) in enumerate(zip(patches, rings, frame.particles)):
            x, y, _vx, _vy, used = p
            patch.center = (x, y)
            patch.set_facecolor(USED if used else FRESH)
            scored = prev is not None and used == 1 and prev.particles[i][4] == 0
            ring.center = (x, y)
            ring.set_visible(scored)
            if scored:
                flash["left" if x < 0.5 * L else "right"] = True
        for side, box in goal_boxes.items():
            box.set_alpha(0.9 if flash[side] else 0.35)
        if quiver is not None:
            quiver.set_offsets([(p[0], p[1]) for p in frame.particles])
            quiver.set_UVC([p[2] for p in frame.particles], [p[3] for p in frame.particles])
        if fu_line is not None:
            fu_line.set_data(ts[: index + 1], fus[: index + 1])
            fu_dot.set_data([ts[index]], [fus[index]])
        stats.set_text(_stats_line(frame, n))

    draw(0)
    return fig, draw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--traj", required=True, help="dump escrito por el motor (--out)")
    parser.add_argument("--out", help="GIF de salida")
    parser.add_argument("--mp4", help="MP4 de salida (requiere ffmpeg; es lo que se sube a YouTube/Vimeo)")
    parser.add_argument("--png", help="PNG de un cuadro")
    parser.add_argument("--frame", type=int, default=None, help="cuadro del PNG (default: el del medio; 0 = inicial)")
    parser.add_argument("--show", action="store_true", help="abrir ventana")
    parser.add_argument("--fps", type=int, default=8, help="cuadros por segundo de reproducción")
    parser.add_argument("--inset", action="store_true", help="inset con Fu(t)")
    parser.add_argument("--arrows", action="store_true", help="flechas de velocidad")
    parser.add_argument("--clean", action="store_true", help="sin ejes, con barra de escala")
    args = parser.parse_args()

    if args.fps < 1:
        sys.exit("--fps debe ser >= 1")
    if not args.out and not args.mp4 and not args.png and not args.show:
        args.show = True
    if not args.show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FFMpegWriter, FuncAnimation, PillowWriter

    try:
        traj = read_traj(args.traj)
    except (OSError, ValueError) as error:
        sys.exit(str(error))
    fig, draw = make_figure(traj, arrows=args.arrows, clean=args.clean, inset=args.inset)
    n_frames = len(traj.frames)

    if args.png:
        index = n_frames // 2 if args.frame is None else args.frame
        if not 0 <= index < n_frames:
            sys.exit(f"--frame debe estar en [0, {n_frames - 1}]")
        draw(index)
        png_path = Path(args.png)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(png_path, dpi=SAVE_DPI, facecolor="white")
        print(f"se escribió {png_path} (cuadro {index})")

    if args.out:
        gif_path = Path(args.out)
        gif_path.parent.mkdir(parents=True, exist_ok=True)
        anim = FuncAnimation(fig, draw, frames=n_frames, blit=False, interval=1000 / args.fps)
        anim.save(gif_path, writer=PillowWriter(fps=args.fps), dpi=GIF_DPI, savefig_kwargs={"facecolor": "white"})
        print(f"se escribió {gif_path} ({n_frames} cuadros a {args.fps} fps)")

    if args.mp4:
        mp4_path = Path(args.mp4)
        mp4_path.parent.mkdir(parents=True, exist_ok=True)
        anim = FuncAnimation(fig, draw, frames=n_frames, blit=False, interval=1000 / args.fps)
        anim.save(mp4_path, writer=FFMpegWriter(fps=args.fps, bitrate=2400), dpi=GIF_DPI,
                  savefig_kwargs={"facecolor": "white"})
        print(f"se escribió {mp4_path} ({n_frames} cuadros a {args.fps} fps)")

    if args.show:
        FuncAnimation(fig, draw, frames=n_frames, blit=False, interval=1000 / args.fps, repeat=True)
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    main()
