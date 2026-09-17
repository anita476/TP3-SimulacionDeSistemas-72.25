"""1.3: DCM vs t y ajuste lineal (Teórica 0). En 2D, ⟨Δr²⟩ = 4 D t.

    python python/plotters/plot_msd.py --input msd.txt --t-min 2 --t-max 20 --output figura.png

    t msd
    0.0 0.0
    0.5 0.12
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from plot_style import BLUE, VERMILLION, apply_sci_axis, load_table, new_figure, place_legend_below, save_figure, style_axes
from metrics import diffusion, fit_line


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--t-min", type=float, default=None, help="inicio de la ventana de ajuste (s)")
    parser.add_argument("--t-max", type=float, default=None, help="fin de la ventana de ajuste (s)")
    args = parser.parse_args()

    try:
        rows = load_table(args.input, ("t", "msd"))
        pairs = sorted(((float(row["t"]), float(row["msd"])) for row in rows), key=lambda item: item[0])
        times = [t for t, _msd in pairs]
        msds = [msd for _t, msd in pairs]
        fit_t, fit_msd = [], []
        for t, msd in zip(times, msds):
            if args.t_min is not None and t < args.t_min:
                continue
            if args.t_max is not None and t > args.t_max:
                continue
            fit_t.append(t)
            fit_msd.append(msd)
        slope, intercept = fit_line(fit_t, fit_msd)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    d = diffusion(slope)
    print(f"D = {d:.6g} m^2/s  (pendiente / 4)")

    fig, ax = new_figure()
    ax.plot(times, msds, color=BLUE, marker="o", linestyle="none", markeredgecolor="black", markeredgewidth=0.6, zorder=3, label="DCM")
    t0, t1 = fit_t[0], fit_t[-1]
    ax.plot(
        [t0, t1],
        [intercept + slope * t0, intercept + slope * t1],
        color=VERMILLION,
        zorder=4,
        label=rf"$D={d:.3g}\,\mathrm{{m}}^2/\mathrm{{s}}$",
    )
    style_axes(ax, "tiempo (s)", r"desplazamiento cuadrático medio (m$^2$)")
    ax.set_ylim(bottom=0)
    apply_sci_axis(ax, "y")
    place_legend_below(ax, ncol=2)
    save_figure(fig, args.output or args.input.with_suffix(".png"))


if __name__ == "__main__":
    main()
