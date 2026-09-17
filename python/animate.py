"""Anima un dump del motor de billar-metegol.

El simulador escribe un archivo de texto; este script solo lo lee.

    python python/animate.py --traj data/sample_traj.txt --show
    python python/animate.py --traj data/sample_traj.txt --out data/sample.gif --png data/sample.png

Formato (el motor debe escribir exactamente esto):

    L <m>
    W <m>
    d <m>
    r <m>
    N <int>
    O <xk> <yk> <Rk>          cero o más obstáculos
    t <s> Ng <int>
    <x> <y> <vx> <vy> <used>  N líneas; used es 0 (fresca) o 1 (usada)
    t ...                     siguiente cuadro

Líneas vacías y comentarios (#) se ignoran. Ng tiene que coincidir con
cuántas partículas tienen used=1 en ese cuadro.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

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

FRESH = BLUE
USED = VERMILLION
GOAL = GREEN
OBSTACLE = "#4d4d4d"
GIF_DPI = 100


@dataclass
class Frame:
    t: float
    ng: int
    particles: list[tuple[float, float, float, float, int]]  # x, y, vx, vy, used


@dataclass
class Traj:
    L: float
    W: float
    d: float
    r: float
    n: int
    obstacles: list[tuple[float, float, float]]
    frames: list[Frame]


def _fail(path: str, lineno: int, msg: str) -> None:
    sys.exit(f"{path}:{lineno}: {msg}")


def _tokens(path: str, lineno: int, line: str, expected: int) -> list[str]:
    parts = line.split()
    if len(parts) != expected:
        _fail(path, lineno, f"se esperaban {expected} campos, hay {len(parts)}: {line!r}")
    return parts


def read_traj(path: str) -> Traj:
    rows: list[tuple[int, str]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.split("#", 1)[0].strip()
            if line:
                rows.append((lineno, line))
    if not rows:
        sys.exit(f"{path}: archivo vacío")

    header: dict[str, float] = {}
    n: int | None = None
    obstacles: list[tuple[float, float, float]] = []
    i = 0
    while i < len(rows) and rows[i][1].split()[0] != "t":
        lineno, line = rows[i]
        tag = line.split()[0]
        if tag in ("L", "W", "d", "r"):
            header[tag] = float(_tokens(path, lineno, line, 2)[1])
        elif tag == "N":
            n = int(_tokens(path, lineno, line, 2)[1])
        elif tag == "O":
            _, x, y, radius = _tokens(path, lineno, line, 4)
            obstacles.append((float(x), float(y), float(radius)))
        else:
            _fail(path, lineno, f"etiqueta de encabezado desconocida {tag!r}")
        i += 1

    missing = [key for key in ("L", "W", "d", "r") if key not in header]
    if n is None:
        missing.append("N")
    if missing:
        sys.exit(f"{path}: faltan en el encabezado: {', '.join(missing)}")
    assert n is not None
    for key in ("L", "W", "d", "r"):
        if header[key] <= 0:
            sys.exit(f"{path}: {key} debe ser > 0, es {header[key]}")
    if n < 1:
        sys.exit(f"{path}: N debe ser >= 1, es {n}")

    frames: list[Frame] = []
    while i < len(rows):
        lineno, line = rows[i]
        parts = _tokens(path, lineno, line, 4)
        if parts[0] != "t" or parts[2] != "Ng":
            _fail(path, lineno, f"se esperaba 't <s> Ng <int>', se obtuvo {line!r}")
        t, ng = float(parts[1]), int(parts[3])
        i += 1
        if i + n > len(rows):
            sys.exit(f"{path}: cuadro truncado en t={t}")
        particles: list[tuple[float, float, float, float, int]] = []
        for _ in range(n):
            lineno, line = rows[i]
            x, y, vx, vy, used_s = _tokens(path, lineno, line, 5)
            used = int(used_s)
            if used not in (0, 1):
                _fail(path, lineno, f"used debe ser 0 o 1, no {used_s!r}")
            particles.append((float(x), float(y), float(vx), float(vy), used))
            i += 1
        used_count = sum(p[4] for p in particles)
        if used_count != ng:
            _fail(path, lineno, f"Ng={ng} pero {used_count} partículas usadas")
        frames.append(Frame(t, ng, particles))

    if not frames:
        sys.exit(f"{path}: no hay cuadros")

    return Traj(header["L"], header["W"], header["d"], header["r"], n, obstacles, frames)


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

    traj = read_traj(args.traj)
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
