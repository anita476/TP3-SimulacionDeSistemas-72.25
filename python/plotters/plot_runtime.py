"""1.1: tiempo de ejecución promedio vs N (mesa vacía, >= 10 realizaciones).

    python python/plotters/plot_runtime.py --input times.txt --output figura.png \\
        --loglog-output figura_loglog.png

Escala lineal y, si se pide, la misma curva en log-log con el ajuste de
ley de potencia t = c N^a (recta en log-log); el exponente a se imprime y
se muestra en la leyenda.

    N t_mean t_std events_mean wall_mean pair_mean
    50 1.2 0.1 4200 1100 3100

--error-output      curva de error E(a) del ajuste t = c N^a (método de la Teórica 0):
                    E(a) = sum_i [log t_i - (log c(a) + a log N_i)]², con log c(a) el
                    mejor valor para cada a; el exponente informado es el mínimo de E.
--events-output     eventos procesados en tf vs N (escala lineal): total y, si están
                    las columnas, entre partículas y contra paredes
--events-loglog-output  las mismas series en log-log, cada una con su exponente ajustado
                    (esperado: pares ~ N^2, paredes ~ N^1)
--per-event-output  tiempo por evento vs N: el costo O(N) de avanzar y repredecir
Ambas se omiten si la tabla no tiene events_mean (wall.txt viejo, "N time").
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from math import exp, floor, log, log10

from metrics import fit_line
from plot_style import BLUE, GREEN, VERMILLION, apply_sci_axis, load_table, new_figure, place_legend_below, save_figure, style_axes


def _sci(value: float, digits: int = 2) -> str:
    """Notación científica con la potencia como supraíndice (guía 1.9): 5.9×10^-8."""
    if value == 0:
        return "0"
    exponent = floor(log10(abs(value)))
    mantissa = value / 10 ** exponent
    return rf"{mantissa:.{digits - 1}f}\times10^{{{exponent}}}"


def _label_n_ticks(ax, ns: list[int]) -> None:
    """Eje x log con menos de una década: se etiquetan los N medidos, salteando
    los que quedarían a menos de 0.12 décadas del anterior."""
    from matplotlib.ticker import NullLocator

    ticks = [ns[0]]
    for n in ns[1:]:
        if log(n) - log(ticks[-1]) >= 0.12 * log(10):
            ticks.append(n)
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(n) for n in ticks])
    ax.xaxis.set_minor_locator(NullLocator())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--loglog-output", type=Path, default=None, help="misma curva en log-log con ajuste t = c N^a")
    parser.add_argument("--error-output", type=Path, default=None, help="E(a) vs a del ajuste t = c N^a (Teórica 0)")
    parser.add_argument("--events-output", type=Path, default=None, help="eventos en tf vs N (lineal)")
    parser.add_argument("--events-loglog-output", type=Path, default=None, help="eventos en tf vs N (log-log, con ajuste)")
    parser.add_argument("--per-event-output", type=Path, default=None, help="tiempo por evento vs N")
    args = parser.parse_args()

    try:
        rows = load_table(args.input, ("N", "t_mean", "t_std"))
        ns = [int(row["N"]) for row in rows]
        means = [float(row["t_mean"]) for row in rows]
        stds = [float(row["t_std"]) for row in rows]
        series: dict[str, list[float]] = {}
        for column, name in (("events_mean", "total"), ("pair_mean", "entre partículas"), ("wall_mean", "contra paredes")):
            try:
                ev_rows = load_table(args.input, ("N", column))
                values = [row[column] for row in ev_rows]
                if all(v != "None" for v in values):
                    series[name] = [float(v) for v in values]
            except ValueError:
                pass
        events = series.get("total", [])
    except (OSError, ValueError) as error:
        parser.error(str(error))

    order = sorted(range(len(ns)), key=lambda i: ns[i])
    ns = [ns[i] for i in order]
    means = [means[i] for i in order]
    stds = [stds[i] for i in order]
    events = [events[i] for i in order] if events else []
    series = {name: [vals[i] for i in order] for name, vals in series.items()}
    colors = {"total": BLUE, "entre partículas": VERMILLION, "contra paredes": GREEN}
    markers = {"total": "o", "entre partículas": "s", "contra paredes": "^"}

    fig, ax = new_figure()
    ax.errorbar(
        ns,
        means,
        yerr=stds,
        color=BLUE,
        marker="o",
        markersize=4,
        markeredgecolor="black",
        markeredgewidth=0.6,
        linestyle="-",
        capsize=3,
        zorder=3,
    )
    style_axes(ax, "cantidad de partículas", "tiempo de ejecución (s)")
    ax.set_ylim(0, max(m + s for m, s in zip(means, stds)) * 1.08)
    if len(ns) <= 8:
        ax.set_xticks(ns)
    save_figure(fig, args.output or args.input.with_suffix(".png"))

    if args.loglog_output:
        # Ajuste lineal en log-log: log t = a log N + log c  ->  t = c N^a
        a, logc = fit_line([log(n) for n in ns], [log(m) for m in means])
        c = exp(logc)
        print(f"ley de potencia: t = {c:.3g} * N^{a:.2f}")
        fig, ax = new_figure()
        ax.errorbar(ns, means, yerr=stds, color=BLUE, marker="o", markersize=4, markeredgecolor="black",
                    markeredgewidth=0.6, linestyle="none", capsize=3, zorder=3, label="medido")
        ax.plot([ns[0], ns[-1]], [c * ns[0] ** a, c * ns[-1] ** a], color=VERMILLION, zorder=2,
                label=rf"$t \propto N^{{{a:.2f}}}$")
        ax.set_xscale("log")
        ax.set_yscale("log")
        style_axes(ax, "cantidad de partículas", "tiempo de ejecución (s)")
        _label_n_ticks(ax, ns)
        place_legend_below(ax, ncol=2)
        save_figure(fig, args.loglog_output)

        if args.error_output:
            # Teórica 0: E(a) = sum [y_i - f(x_i, a)]² con y = log t, x = log N,
            # f = log c(a) + a x y log c(a) el valor que minimiza E para ese a.
            xs = [log(n) for n in ns]
            ys = [log(m) for m in means]
            grid = [a - 1.0 + 2.0 * i / 400 for i in range(401)]
            errors = []
            for a_try in grid:
                logc_try = sum(y - a_try * x for x, y in zip(xs, ys)) / len(xs)
                errors.append(sum((y - logc_try - a_try * x) ** 2 for x, y in zip(xs, ys)))
            a_best = grid[errors.index(min(errors))]
            print(f"E(a) mínimo en a = {a_best:.2f}")
            fig, ax = new_figure()
            ax.plot(grid, errors, color=BLUE, zorder=3)
            ax.axvline(a, color=VERMILLION, linestyle="--", zorder=2, label=rf"$a^* = {a:.2f}$")
            style_axes(ax, r"exponente $a$", r"error $E(a)$")
            ax.set_ylim(bottom=0)
            place_legend_below(ax, ncol=1)
            save_figure(fig, args.error_output)

    if args.events_output and events:
        fig, ax = new_figure()
        for name, vals in series.items():
            ax.plot(ns, vals, color=colors[name], marker=markers[name], markersize=4, markeredgecolor="black",
                    markeredgewidth=0.6, linestyle="-", zorder=3, label=name)
        style_axes(ax, "cantidad de partículas", "número de eventos")
        ax.set_ylim(0, max(events) * 1.08)
        if len(ns) <= 8:
            ax.set_xticks(ns)
        apply_sci_axis(ax, "y")
        if len(series) > 1:
            place_legend_below(ax, ncol=3)
        save_figure(fig, args.events_output)

    if args.events_loglog_output and events:
        fig, ax = new_figure()
        for name, vals in series.items():
            a, logc = fit_line([log(n) for n in ns], [log(v) for v in vals])
            c = exp(logc)
            print(f"eventos en tf ({name}): {c:.3g} * N^{a:.2f}")
            ax.plot(ns, vals, color=colors[name], marker=markers[name], markersize=4, markeredgecolor="black",
                    markeredgewidth=0.6, linestyle="none", zorder=3)
            ax.plot([ns[0], ns[-1]], [c * ns[0] ** a, c * ns[-1] ** a], color=colors[name], zorder=2,
                    label=rf"{name}: $\propto N^{{{a:.2f}}}$")
        ax.set_xscale("log")
        ax.set_yscale("log")
        style_axes(ax, "cantidad de partículas", "número de eventos")
        _label_n_ticks(ax, ns)
        place_legend_below(ax, ncol=1)
        save_figure(fig, args.events_loglog_output)

    if args.per_event_output and events:
        # Tiempo medio por evento: tiempo total / eventos procesados en tf (µs).
        # Modelo teórico: trabajo por evento proporcional a N (avanzar N partículas y
        # repredecir contra N-1), o sea tau = k N, un solo coeficiente k (Teórica 0).
        per_event = [1e6 * m / e for m, e in zip(means, events)]
        per_event_err = [1e6 * s / e for s, e in zip(stds, events)]
        k = sum(n * tau for n, tau in zip(ns, per_event)) / sum(n * n for n in ns)
        print(f"tiempo por evento: tau = {k:.4g} µs * N  ({1e3 * k:.3g} ns por partícula y evento)")
        fig, ax = new_figure()
        ax.errorbar(ns, per_event, yerr=per_event_err, color=BLUE, marker="o", markersize=4, markeredgecolor="black",
                    markeredgewidth=0.6, linestyle="none", capsize=3, zorder=3, label="medido")
        ax.plot([0, ns[-1]], [0, k * ns[-1]], color=VERMILLION, zorder=2,
                label=r"$\tau \propto N$")
        style_axes(ax, "cantidad de partículas", "tiempo medio por evento (µs)")
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        if len(ns) <= 8:
            ax.set_xticks(ns)
        place_legend_below(ax, ncol=2)
        save_figure(fig, args.per_event_output)


if __name__ == "__main__":
    main()
