"""1.2: fracción de partículas usadas Fu(t) = Ng(t)/N, escalera exacta por realización.

python python/plotters/plot_fu.py --output fu.png \
        --series "mesa vacía" data/runs/empty \
        --series "x = 0.60 m" data/runs/t90/single_x/0.60
        
Cada serie es una carpeta con run_*.txt. Con una realización se dibuja la
escalera. Con varias, la media y la banda del desvío muestral. Los tiempos
son los de los cuadros de gol.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from metrics import mean_std, ng_series
from plot_style import SERIES, new_figure, place_legend_below, save_figure, style_axes
from runs import dump_paths
from traj import read_traj


def _fu_at(series: list[tuple[float, int]], times: list[float], n: int) -> list[float]:
    values = []
    index = 0
    ng = 0
    for t in times:
        while index < len(series) and series[index][0] <= t:
            ng = series[index][1]
            index += 1
        values.append(ng / n)
    return values


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
            loaded = []
            for path in paths:
                traj = read_traj(path)
                series = ng_series(traj)
                if not series:
                    parser.error(f"{path}: no hay cuadros")
                loaded.append((traj.n, series))
                t_end = max(t_end, series[-1][0])
            if len(loaded) == 1:
                n, series = loaded[0]
                ax.step(
                    [t for t, _ng in series],
                    [ng / n for _t, ng in series],
                    where="post",
                    color=color,
                    lw=1.2,
                    zorder=3,
                    label=label,
                )
                continue
            n0 = loaded[0][0]
            if any(n != n0 for n, _series in loaded):
                parser.error(f"{folder}: las realizaciones no tienen el mismo N")
            times = sorted({0.0, *(t for _n, series in loaded for t, _ng in series)})
            if args.t_max is not None:
                times = [t for t in times if t <= args.t_max]
                if not times or times[-1] < args.t_max:
                    times.append(args.t_max)
            columns = [_fu_at(series, times, n0) for _n, series in loaded]
            means, stds = [], []
            for column in zip(*columns):
                mean, std = mean_std(list(column))
                means.append(mean)
                stds.append(std)
            ax.fill_between(
                times,
                [mean - std for mean, std in zip(means, stds)],
                [mean + std for mean, std in zip(means, stds)],
                step="post",
                color=color,
                alpha=0.2,
                linewidth=0,
                zorder=2,
            )
            ax.step(times, means, where="post", color=color, lw=1.8, zorder=3, label=label)
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