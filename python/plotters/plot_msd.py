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
    parser.add_argument("--error-output", type=Path, default=None, help="curva E(D) del ajuste (Teórica 0)")
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
    if len(times) > 40:
        ax.plot(times, msds, color=BLUE, linestyle="-", zorder=3, label="DCM")
    else:
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

    if args.error_output:
        # Teórica 0: E(D) = sum [msd_i - f(t_i, D)]², con f = b(D) + 4 D t
        # y b(D) el intercepto que minimiza E para ese D. El mínimo es la pendiente / 4.
        n = len(fit_t)
        d_hi = max(d * 2.5, 1e-6)
        grid = [d_hi * i / 400 for i in range(401)]
        errors = []
        for d_try in grid:
            slope_try = 4.0 * d_try
            intercept_try = sum(y - slope_try * x for x, y in zip(fit_t, fit_msd)) / n
            errors.append(sum((y - intercept_try - slope_try * x) ** 2 for x, y in zip(fit_t, fit_msd)))
        d_best = grid[errors.index(min(errors))]
        print(f"E(D) mínimo en D = {d_best:.6g} m^2/s")
        fig, ax = new_figure()
        ax.plot(grid, errors, color=BLUE, zorder=3)
        ax.axvline(d, color=VERMILLION, linestyle="--", zorder=2, label=rf"$D^* = {d:.3g}$")
        style_axes(ax, r"coeficiente de difusión $D$ (m$^2$/s)", r"error $E(D)$")
        ax.set_ylim(bottom=0)
        apply_sci_axis(ax, "x")
        place_legend_below(ax, ncol=1)
        save_figure(fig, args.error_output)


if __name__ == "__main__":
    main()
