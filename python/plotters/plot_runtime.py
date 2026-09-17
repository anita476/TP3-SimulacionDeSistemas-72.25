"""1.1: tiempo de ejecución promedio vs N (mesa vacía, >= 10 realizaciones).

    python python/plotters/plot_runtime.py --input times.txt --output figura.png

    N t_mean t_std
    50 1.2 0.1
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from plot_style import BLUE, load_table, new_figure, save_figure, style_axes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    try:
        rows = load_table(args.input, ("N", "t_mean", "t_std"))
        ns = [int(row["N"]) for row in rows]
        means = [float(row["t_mean"]) for row in rows]
        stds = [float(row["t_std"]) for row in rows]
    except (OSError, ValueError) as error:
        parser.error(str(error))

    order = sorted(range(len(ns)), key=lambda i: ns[i])
    ns = [ns[i] for i in order]
    means = [means[i] for i in order]
    stds = [stds[i] for i in order]

    fig, ax = new_figure()
    ax.errorbar(
        ns,
        means,
        yerr=stds,
        color=BLUE,
        marker="o",
        markeredgecolor="black",
        markeredgewidth=0.6,
        linestyle="-",
        zorder=3,
    )
    style_axes(ax, "cantidad de partículas", "tiempo de ejecución (s)")
    ax.set_ylim(0, max(m + s for m, s in zip(means, stds)) * 1.08)
    if len(ns) <= 8:
        ax.set_xticks(ns)
    save_figure(fig, args.output or args.input.with_suffix(".png"))


if __name__ == "__main__":
    main()
