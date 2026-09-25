"""Barrido de la pared: <t90> contra el centro, una curva por cantidad de columnas.

    python python/plotters/plot_pared.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from plot_style import MARKERS, SERIES, VERMILLION, new_figure, place_legend_below, save_figure, style_axes
from tables import load_table

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "docs" / "results" / "1.2" / "pared_t90.txt"
OUTPUT = ROOT / "docs" / "results" / "1.2" / "pared_t90.png"
# 1 es la pared fina, 9 el mínimo y 10 el ancho en el que vuelve a subir.
SHOWN = (1, 9, 10)


def main() -> None:
    rows = load_table(TABLE, ("columnas", "ancho", "x", "K", "t90_mean", "t90_std"))
    by: dict[int, list] = {}
    for row in rows:
        cols = int(row["columnas"])
        if cols in SHOWN:
            by.setdefault(cols, []).append(row)
    fig, ax = new_figure()
    for i, cols in enumerate(sorted(by)):
        pts = sorted(by[cols], key=lambda row: float(row["x"]))
        ax.errorbar(
            [float(row["x"]) for row in pts],
            [float(row["t90_mean"]) for row in pts],
            yerr=[float(row["t90_std"]) for row in pts],
            color=SERIES[i % len(SERIES)],
            marker=MARKERS[i % len(MARKERS)],
            markeredgecolor="black",
            markeredgewidth=0.6,
            linestyle="-",
            label=f"{cols} col.",
        )
    ax.axhline(23.7617, color=VERMILLION, linestyle="--", label="mesa vacía")
    ax.axhline(15.6094, color="0.25", linestyle=":", label="elegida")
    style_axes(ax, r"centro de la pared $x$ (m)", r"tiempo $t_{90}$ (s)")
    ax.set_ylim(0, 42)
    place_legend_below(ax, ncol=3)
    save_figure(fig, OUTPUT)


if __name__ == "__main__":
    main()
