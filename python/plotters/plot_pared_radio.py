"""Pared de radio mínimo: <t90> contra la cantidad de columnas.

    python python/plotters/plot_pared_radio.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from plot_style import MARKERS, SERIES, VERMILLION, new_figure, place_legend_below, save_figure, style_axes
from tables import load_table

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "docs" / "results" / "1.2" / "pared_columnas.txt"
OUTPUT = ROOT / "docs" / "results" / "1.2" / "pared_columnas.png"


def main() -> None:
    rows = load_table(TABLE, ("radio", "columnas", "ancho", "x", "K", "t90_mean", "t90_std"))
    pts = sorted(rows, key=lambda row: int(row["columnas"]))
    fig, ax = new_figure()
    ax.errorbar(
        [int(row["columnas"]) for row in pts],
        [float(row["t90_mean"]) for row in pts],
        yerr=[float(row["t90_std"]) for row in pts],
        color=SERIES[0],
        marker=MARKERS[0],
        markeredgecolor="black",
        markeredgewidth=0.6,
        linestyle="-",
        label=r"$R$ = 0.0175 m",
    )
    ax.axhline(23.7617, color=VERMILLION, linestyle="--", label="mesa vacía")
    ax.axhline(15.6094, color="0.25", linestyle=":", label="elegida")
    style_axes(ax, "columnas", r"tiempo $t_{90}$ (s)")
    ax.set_ylim(8, 28)
    place_legend_below(ax, ncol=3)
    save_figure(fig, OUTPUT)


if __name__ == "__main__":
    main()
