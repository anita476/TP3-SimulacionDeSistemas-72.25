"""1.2: <t90> vs la variable explorada, con mesa vacía de referencia.

    python python/plotters/plot_t90.py --input sweep.txt --xlabel "posición $x$ (m)" \\
        --empty 12.4 0.8 --output figura.png

    x t90_mean t90_std
    0.2 9.1 0.7
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from plot_style import BLUE, VERMILLION, load_table, new_figure, place_legend_below, save_figure, style_axes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--xlabel", required=True, help="variable explorada, en palabras")
    parser.add_argument(
        "--empty",
        nargs=2,
        type=float,
        metavar=("MEAN", "STD"),
        help="<t90> ± desvío de la mesa vacía",
    )
    args = parser.parse_args()

    try:
        rows = load_table(args.input, ("x", "t90_mean", "t90_std"))
        xs = [float(row["x"]) for row in rows]
        means = [float(row["t90_mean"]) for row in rows]
        stds = [float(row["t90_std"]) for row in rows]
    except (OSError, ValueError) as error:
        parser.error(str(error))

    order = sorted(range(len(xs)), key=lambda i: xs[i])
    xs = [xs[i] for i in order]
    means = [means[i] for i in order]
    stds = [stds[i] for i in order]

    fig, ax = new_figure()
    ax.errorbar(
        xs,
        means,
        yerr=stds,
        color=BLUE,
        marker="o",
        markeredgecolor="black",
        markeredgewidth=0.6,
        linestyle="-",
        zorder=3,
        label="con obstáculos" if args.empty is not None else None,
    )
    ymax = max(mean + std for mean, std in zip(means, stds))
    if args.empty is not None:
        empty_mean, empty_std = args.empty
        ax.axhline(empty_mean, color=VERMILLION, linestyle="--", zorder=2, label="mesa vacía")
        ax.axhspan(empty_mean - empty_std, empty_mean + empty_std, color=VERMILLION, alpha=0.15, zorder=1)
        ymax = max(ymax, empty_mean + empty_std)
    style_axes(ax, args.xlabel, r"tiempo $t_{90}$ (s)")
    ax.set_ylim(0, ymax * 1.08)
    if args.empty is not None:
        place_legend_below(ax, ncol=2)
    save_figure(fig, args.output or args.input.with_suffix(".png"))


if __name__ == "__main__":
    main()
