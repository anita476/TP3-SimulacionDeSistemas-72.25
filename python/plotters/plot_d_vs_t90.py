"""1.3: correlación entre D y <t90> de cada configuración.

    python python/plotters/plot_d_vs_t90.py --input corr.txt --output figura.png

    config D t90 t90_std
    vacia 0.12 15.2 1.1
    embudo 0.08 7.1 0.5
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from plot_style import MARKERS, SERIES, apply_sci_axis, load_table, new_figure, place_legend_below, save_figure, style_axes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    try:
        rows = load_table(args.input, ("config", "D", "t90", "t90_std"))
        configs = [row["config"] for row in rows]
        ds = [float(row["D"]) for row in rows]
        t90s = [float(row["t90"]) for row in rows]
        t90_stds = [float(row["t90_std"]) for row in rows]
    except (OSError, ValueError) as error:
        parser.error(str(error))

    fig, ax = new_figure()
    for i, (config, d, t90, t90_std) in enumerate(zip(configs, ds, t90s, t90_stds)):
        color = SERIES[i % len(SERIES)]
        marker = MARKERS[i % len(MARKERS)]
        ax.errorbar(
            t90,
            d,
            xerr=t90_std,
            color=color,
            marker=marker,
            markeredgecolor="black",
            markeredgewidth=0.6,
            linestyle="none",
            zorder=3,
            label=config,
        )
    style_axes(ax, r"tiempo $t_{90}$ (s)", r"coeficiente de difusión (m$^2$/s)")
    ax.set_xlim(left=0)
    ymax = max(ds) * 1.12 if ds else 1.0
    ax.set_ylim(0, ymax)
    apply_sci_axis(ax, "y")
    place_legend_below(ax, ncol=min(len(configs), 3))
    save_figure(fig, args.output or args.input.with_suffix(".png"))


if __name__ == "__main__":
    main()
