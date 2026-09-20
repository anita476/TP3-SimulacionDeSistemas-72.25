"""1.2: fracción de partículas usadas Fu(t) = Ng(t)/N, escalera exacta por realización.

python python/plotters/plot_fu.py --output fu.png \
        --series "mesa vacía" data/runs/empty \
        --series "x = 0.60 m" data/runs/t90/single_x/0.60
        
Cada serie es una carpeta con run_*.txt; cada realización es una escalera
fina del mismo color. Los tiempos son los de los cuadros de gol.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from metrics import ng_series
from plot_style import SERIES, new_figure, place_legend_below, save_figure, style_axes
from runs import dump_paths
from traj import read_traj


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--series", nargs=2, action="append", metavar=("LABEL", "FOLDER"), required=True)
    parser.add_argument("--t-max", type=float, default=None, help="recorta el eje x (s)")
    args = parser.parse_args()

    fig, ax = new_figure()
    t_end = 0.0
    try:
        for i, (label, folder) in enumerate(args.series):
            color = SERIES[i % len(SERIES)]
            paths = dump_paths(Path(folder))
            if not paths:
                parser.error(f"{folder}: no hay run_*.txt")
            for j, path in enumerate(paths):
                traj = read_traj(path)
                ts = [t for t, _ng in ng_series(traj)]
                fus = [ng / traj.n for _t, ng in ng_series(traj)]
                t_end = max(t_end, ts[-1])
                ax.step(ts, fus, where="post", color=color, lw=1.2, alpha=0.85, zorder=3,
                        label=label if j == 0 else None)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    ax.axhline(0.9, color="black", linestyle="--", lw=0.9, zorder=2, label=r"$F_u = 0.9$")
    style_axes(ax, "tiempo (s)", r"fracción de partículas usadas $F_u$")
    ax.set_xlim(0, args.t_max if args.t_max is not None else t_end)
    ax.set_ylim(0, 1.02)
    place_legend_below(ax, ncol=min(len(args.series) + 1, 3))
    save_figure(fig, args.output)


if __name__ == "__main__":
    main()