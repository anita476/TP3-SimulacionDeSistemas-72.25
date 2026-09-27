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

--fit-max-n X       todos los ajustes usan solo N <= X (régimen diluido); la recta se
                    dibuja llena en ese rango y punteada más allá, para ver cuánto se
                    apartan los N grandes de la ley de potencia.
--hollow-n N ...    esos N se dibujan con marcador vacío (p. ej. los que arrancan de la
                    red hexagonal) con leyenda --hollow-label; el resto lleva --label.
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


def _label_n_ticks(ax, ns: list[int], min_decades: float = 0.12) -> None:
    """Eje x log: se etiquetan N medidos "redondos" (25, 50 y múltiplos de 50) y
    siempre el mayor, salteando los que quedarían a menos de min_decades décadas
    del siguiente. Se recorre desde el N mayor para que el último siempre tenga
    etiqueta."""
    from matplotlib.ticker import NullLocator

    candidates = [n for n in ns[:-1] if n in (25, 50) or n % 50 == 0] or ns[:-1]
    ticks = [ns[-1]]
    for n in reversed(candidates):
        if log(ticks[-1]) - log(n) >= min_decades * log(10):
            ticks.append(n)
    ticks.reverse()
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(n) for n in ticks])
    ax.xaxis.set_minor_locator(NullLocator())


def _linear_n_ticks(ax, ns: list[int]) -> None:
    """Eje x lineal: con pocos N se etiquetan todos; con muchos, marcas cada 100
    (o cada 50 si N no pasa de 400) hasta cubrir el N mayor."""
    if len(ns) <= 8:
        ax.set_xticks(ns)
        return
    step = 100 if ns[-1] > 400 else 50
    ax.set_xticks(range(0, -(-ns[-1] // step) * step + 1, step))


def _hollow_proxy(ax, label: str) -> None:
    """Entrada de leyenda para los marcadores vacíos, después de las series."""
    ax.errorbar([float("nan")], [float("nan")], color="black", marker="o", markersize=4,
                markerfacecolor="white", linestyle="none", label=label)


def _power_fit(ns: list[int], ys: list[float], fit_max: float | None) -> tuple[float, float]:
    """Ajuste y = c N^a (recta en log-log) usando solo N <= fit_max. Devuelve (a, c)."""
    pts = [(n, y) for n, y in zip(ns, ys) if fit_max is None or n <= fit_max]
    a, logc = fit_line([log(n) for n, _ in pts], [log(y) for _, y in pts])
    return a, exp(logc)


def _fit_end(ns: list[int], fit_max: float | None) -> int:
    return max(n for n in ns if fit_max is None or n <= fit_max)


def _draw_fit(ax, ns: list[int], f, fit_max: float | None, color: str, label: str, start: float | None = None) -> None:
    """f(N) llena hasta el último N ajustado y punteada hasta el último N medido.
    Sirve para leyes de potencia en log-log y para rectas en escala lineal."""
    x0 = ns[0] if start is None else start
    end = _fit_end(ns, fit_max)
    ax.plot([x0, end], [f(x0), f(end)], color=color, zorder=2, label=label)
    if ns[-1] > end:
        ax.plot([end, ns[-1]], [f(end), f(ns[-1])], color=color, linestyle="--", zorder=2)


def _range_note(ns: list[int], fit_max: float | None) -> str:
    """' (N ≤ 300)' si el ajuste deja afuera algún N; vacío si usa todos."""
    end = _fit_end(ns, fit_max)
    return rf" ($N \leq {end}$)" if end < ns[-1] else ""


def _points(ax, ns, ys, yerr, hollow: set[int], color: str, marker: str, label, hollow_label) -> None:
    """Marcadores llenos para N fuera de hollow y vacíos para N en hollow."""
    for is_hollow, lab in ((False, label), (True, hollow_label)):
        idx = [i for i, n in enumerate(ns) if (n in hollow) == is_hollow]
        if not idx:
            continue
        ax.errorbar([ns[i] for i in idx], [ys[i] for i in idx],
                    yerr=None if yerr is None else [yerr[i] for i in idx],
                    color=color, marker=marker, markersize=4, markeredgecolor="black" if not is_hollow else color,
                    markeredgewidth=0.6 if not is_hollow else 1.0,
                    markerfacecolor="white" if is_hollow else color,
                    linestyle="none", capsize=3, zorder=3, label=lab)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--loglog-output", type=Path, default=None, help="misma curva en log-log con ajuste t = c N^a")
    parser.add_argument("--error-output", type=Path, default=None, help="E(a) vs a del ajuste t = c N^a (Teórica 0)")
    parser.add_argument("--events-output", type=Path, default=None, help="eventos en tf vs N (lineal)")
    parser.add_argument("--events-loglog-output", type=Path, default=None, help="eventos en tf vs N (log-log, con ajuste)")
    parser.add_argument("--per-event-output", type=Path, default=None, help="tiempo por evento vs N")
    parser.add_argument("--fit-max-n", type=float, default=None, help="ajustar solo con N <= este valor (default: todos)")
    parser.add_argument("--hollow-n", type=int, nargs="*", default=[], help="N dibujados con marcador vacío")
    parser.add_argument("--label", default=None, help="leyenda de los marcadores llenos (solo con --hollow-n)")
    parser.add_argument("--hollow-label", default=None, help="leyenda de los marcadores vacíos")
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

    fit_max = args.fit_max_n
    if fit_max is not None and sum(n <= fit_max for n in ns) < 2:
        parser.error(f"--fit-max-n {fit_max:g} deja menos de 2 puntos para ajustar")
    hollow = set(args.hollow_n)
    split = bool(hollow & set(ns))
    label = args.label if split else None
    hollow_label = args.hollow_label if split else None
    note = _range_note(ns, fit_max)
    # Con más de una década de N las etiquetas del eje log necesitan más aire.
    min_decades = 0.12 if log10(ns[-1] / ns[0]) <= 1.1 else 0.15

    fig, ax = new_figure()
    ax.plot(ns, means, color=BLUE, zorder=2)
    _points(ax, ns, means, stds, hollow, BLUE, "o", label, hollow_label)
    style_axes(ax, "cantidad de partículas", "tiempo de ejecución (s)")
    ax.set_ylim(0, max(m + s for m, s in zip(means, stds)) * 1.08)
    _linear_n_ticks(ax, ns)
    if split:
        place_legend_below(ax, ncol=2)
    save_figure(fig, args.output or args.input.with_suffix(".png"))

    if args.loglog_output:
        # Ajuste lineal en log-log: log t = a log N + log c  ->  t = c N^a
        a, c = _power_fit(ns, means, fit_max)
        print(f"ley de potencia (ajuste con N <= {_fit_end(ns, fit_max)}): t = {c:.3g} * N^{a:.2f}")
        fig, ax = new_figure()
        _points(ax, ns, means, stds, hollow, BLUE, "o", label if split else "medido", hollow_label)
        _draw_fit(ax, ns, lambda n: c * n ** a, fit_max, VERMILLION, rf"$t \propto N^{{{a:.2f}}}${note}")
        ax.set_xscale("log")
        ax.set_yscale("log")
        style_axes(ax, "cantidad de partículas", "tiempo de ejecución (s)")
        _label_n_ticks(ax, ns, min_decades)
        place_legend_below(ax, ncol=2)
        save_figure(fig, args.loglog_output)

        if args.error_output:
            # Teórica 0: E(a) = sum [y_i - f(x_i, a)]² con y = log t, x = log N,
            # f = log c(a) + a x y log c(a) el valor que minimiza E para ese a.
            fitted = [(n, m) for n, m in zip(ns, means) if fit_max is None or n <= fit_max]
            xs = [log(n) for n, _ in fitted]
            ys = [log(m) for _, m in fitted]
            grid = [a - 1.0 + 2.0 * i / 400 for i in range(401)]
            errors = []
            for a_try in grid:
                logc_try = sum(y - a_try * x for x, y in zip(xs, ys)) / len(xs)
                errors.append(sum((y - logc_try - a_try * x) ** 2 for x, y in zip(xs, ys)))
            a_best = grid[errors.index(min(errors))]
            print(f"E(a) mínimo en a = {a_best:.2f}")
            fig, ax = new_figure()
            ax.plot(grid, errors, color=BLUE, zorder=3)
            ax.axvline(a, color=VERMILLION, linestyle="--", zorder=2, label=rf"$a^* = {a:.2f}${note}")
            style_axes(ax, r"exponente $a$", r"error $E(a)$")
            ax.set_ylim(bottom=0)
            place_legend_below(ax, ncol=1)
            save_figure(fig, args.error_output)

    if args.events_output and events:
        fig, ax = new_figure()
        for name, vals in series.items():
            ax.plot(ns, vals, color=colors[name], zorder=2)
            _points(ax, ns, vals, None, hollow, colors[name], markers[name], name, None)
        if split:
            _hollow_proxy(ax, hollow_label)
        style_axes(ax, "cantidad de partículas", "número de eventos")
        ax.set_ylim(0, max(events) * 1.08)
        _linear_n_ticks(ax, ns)
        apply_sci_axis(ax, "y")
        if len(series) > 1 or split:
            place_legend_below(ax, ncol=3)
        save_figure(fig, args.events_output)

    if args.events_loglog_output and events:
        fig, ax = new_figure()
        for name, vals in series.items():
            a, c = _power_fit(ns, vals, fit_max)
            print(f"eventos en tf ({name}): {c:.3g} * N^{a:.2f}")
            _points(ax, ns, vals, None, hollow, colors[name], markers[name], None, None)
            _draw_fit(ax, ns, lambda n, a=a, c=c: c * n ** a, fit_max, colors[name],
                      rf"{name}: $\propto N^{{{a:.2f}}}$")
        if split:
            _hollow_proxy(ax, hollow_label)
        ax.set_xscale("log")
        ax.set_yscale("log")
        style_axes(ax, "cantidad de partículas", "número de eventos")
        _label_n_ticks(ax, ns, min_decades)
        place_legend_below(ax, ncol=1)
        save_figure(fig, args.events_loglog_output)

    if args.per_event_output and events:
        # Tiempo medio por evento: tiempo total / eventos procesados en tf (µs).
        # Modelo teórico: trabajo por evento proporcional a N (avanzar N partículas y
        # repredecir contra N-1), o sea tau = k N, un solo coeficiente k (Teórica 0).
        per_event = [1e6 * m / e for m, e in zip(means, events)]
        per_event_err = [1e6 * s / e for s, e in zip(stds, events)]
        fitted = [(n, tau) for n, tau in zip(ns, per_event) if fit_max is None or n <= fit_max]
        k = sum(n * tau for n, tau in fitted) / sum(n * n for n, _ in fitted)
        print(f"tiempo por evento: tau = {k:.4g} µs * N  ({1e3 * k:.3g} ns por partícula y evento)")
        fig, ax = new_figure()
        _points(ax, ns, per_event, per_event_err, hollow, BLUE, "o", label if split else "medido", hollow_label)
        _draw_fit(ax, ns, lambda n: k * n, fit_max, VERMILLION, rf"$\tau \propto N${note}", start=0)
        style_axes(ax, "cantidad de partículas", "tiempo medio por evento (µs)")
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        _linear_n_ticks(ax, ns)
        place_legend_below(ax, ncol=2)
        save_figure(fig, args.per_event_output)


if __name__ == "__main__":
    main()
