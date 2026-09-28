"""1.3: DCM, coeficiente de difusión aparente y relación con <t90>. Un solo comando:

    python python/dcm_report.py

Qué calcula:
- DCM(t) = promedio sobre las N = 100 partículas (frescas y usadas: los arcos no
  retiran partículas, solo las marcan) de |r_i(t) - r_i(0)|^2, con un solo origen
  temporal (el cuadro inicial). Cada punto es un cuadro guardado por el motor (cada
  10 eventos y en cada gol), en su tiempo físico; no se interpola.
- En cada realización se ajusta DCM = 4 D t + b por cuadrados mínimos (D y b libres)
  en [0, t_e], con t_e = inicio de la meseta estimado visualmente (cortes.txt).
  D = pendiente / 4 (en 2D, <Δr²> = 4Dt).
- El DCM no tiene un tramo con pendiente 1 sostenida en log-log (ver
  dcm_pendiente_local.txt): D es un coeficiente aparente, que depende del intervalo.
  Por eso también se reporta su sensibilidad a los límites.
- Cada DCM es de UNA realización (promedio sobre sus partículas, como pide la consigna);
  no se promedian curvas entre realizaciones (habría que interpolar a tiempos comunes).
  Lo que se promedia es D, un escalar por corrida como t90: se ajusta cada una de las
  10 realizaciones (semillas 401-410) y se informa <D> ± desvío estándar entre ellas.
  La semilla 401 queda como realización de ejemplo para las figuras del ajuste.

Para cambiar un t_e: editar docs/results/1.3/cortes.txt y volver a correr, o pasarlo por
parámetro sin tocar el archivo (pisa cortes.txt solo en esa corrida):
    python python/dcm_report.py --te disco_022=12 vacia=5

Lee (salidas de run.py, N = 100, k = 10, tf = 30 s):
    data/1.3/t30/<config>/run_401.txt         realización de ejemplo
    data/1.3/t30/seeds/<config>/run_4xx.txt   semillas 401..410
Escribe:
    docs/results/1.3/dcm_resultados.txt       tabla completa
    docs/results/1.3/dcm_pendiente_local.txt  pendiente local en log-log (promedio de 10 semillas)
    docs/results/1.3/*.png, docs/results/1.3/t30/dcm30_<config>.png
    docs/presentation/dcm_valores.tex, docs/presentation/dcm_tabla.tex
y copia las figuras usadas por la presentación a docs/presentation/images/.
"""

import argparse
import math
import shutil
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "lib"))

from plot_style import (BLUE, GREEN, MARKERS, ORANGE, PURPLE, VERMILLION, apply_sci_axis, new_figure,
                        save_figure, style_axes)
from traj import read_traj

DATA = ROOT / "data" / "1.3" / "t30"
OUT = ROOT / "docs" / "results" / "1.3"
PRES = ROOT / "docs" / "presentation"
CUTS_FILE = OUT / "cortes.txt"
SEEDS = range(401, 411)
EXAMPLE_SEED = 401
L, W, R = 1.20, 0.68, 0.0175
N_T90 = 12  # realizaciones de <t90> (punto 1.2, semillas 601-612; no se recalcula acá)

# carpeta, etiqueta, macro LaTeX, ¿divide la mesa? (verificado: ninguna partícula cruza), color, <t90>, desvío
CONFIGS = [
    ("vacia", "mesa vacía", "vacia", "no", BLUE, 23.76, 3.22),
    ("disco_022", r"disco $R = 0.22$ m", "discochico", "no", ORANGE, 19.72, 3.19),
    ("disco", r"disco $R = 0.34$ m", "discogrande", "sí", VERMILLION, 16.96, 1.99),
    ("pared_9", "pared de 9 columnas", "paredA", "sí", GREEN, 14.21, 1.41),
    ("pared_18", "pared de 18 columnas", "paredB", "sí", PURPLE, 13.67, 1.31),
    ("pared_23", "pared de 23 columnas", "paredC", "sí", "#56B4E9", 17.0065, 1.66604),
]
SHORT = {"vacia": "vacía", "disco_022": r"disco $0.22$ m", "disco": r"disco $0.34$ m",
         "pared_9": "pared 9 col.", "pared_18": "pared 18 col.", "pared_23": "pared 23 col."}
TABLE_NAMES = {"vacia": "mesa vacía", "disco_022": r"disco, $R = 0.22\,\mathrm{m}$",
               "disco": r"disco, $R = 0.34\,\mathrm{m}$", "pared_9": "pared, 9 columnas",
               "pared_18": "pared, 18 columnas", "pared_23": "pared, 23 columnas"}


def read_cuts() -> dict[str, float]:
    cuts = {}
    for line in CUTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, value = line.split()
            cuts[name] = float(value)
    missing = [c for c, *_ in CONFIGS if c not in cuts]
    if missing:
        raise SystemExit(f"{CUTS_FILE}: falta t_e de {', '.join(missing)}")
    return cuts


def msd(path: Path) -> list[tuple[float, float]]:
    """DCM respecto del cuadro inicial, promedio sobre todas las partículas."""
    tr = read_traj(str(path))
    origin = tr.frames[0].particles
    return [(f.t, sum((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 for p, q in zip(f.particles, origin)) / tr.n)
            for f in tr.frames]


def covered(config: str) -> float:
    """Porcentaje del área de la mesa ocupado por obstáculos (todos quedan enteros dentro de la mesa)."""
    path = DATA / "seeds" / config / "obstacles.txt"
    if not path.exists():
        return 0.0
    discs = [tuple(map(float, line.split())) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return 100.0 * sum(math.pi * rk * rk for _, _, rk in discs) / (L * W)


def fit(series, a, b):
    """DCM = b + 4 D t por cuadrados mínimos en [a, b]. Devuelve (D, b, error del ajuste en D, puntos)."""
    pts = [(t, m) for t, m in series if a <= t <= b]
    n = len(pts)
    mt = st.mean(t for t, _ in pts)
    mm = st.mean(m for _, m in pts)
    sxx = sum((t - mt) ** 2 for t, _ in pts)
    slope = sum((t - mt) * (m - mm) for t, m in pts) / sxx
    b0 = mm - slope * mt
    s2 = sum((m - b0 - slope * t) ** 2 for t, m in pts) / (n - 2)
    return slope / 4.0, b0, math.sqrt(s2 / sxx) / 4.0, n


def local_slope(series, a, b):
    pts = [(math.log(t), math.log(m)) for t, m in series if a <= t <= b and t > 0 and m > 0]
    if len(pts) < 3:
        return None
    mx = st.mean(x for x, _ in pts)
    my = st.mean(y for _, y in pts)
    return sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts)


def rounded(value: float, error: float) -> tuple[str, str]:
    """Valor y error con las cifras que permite el error (Teórica 0): 1 cifra, 2 si empieza con 1."""
    exp = math.floor(math.log10(error))
    decimals = max(0, -exp + (1 if error / 10 ** exp < 2 else 0))
    return f"{value:.{decimals}f}", f"{error:.{decimals}f}"


def parse_te(items: list[str], names) -> dict[str, float]:
    """'config=t_e' -> {config: t_e}, verificando que la configuración exista."""
    out = {}
    for item in items:
        name, sep, value = item.partition("=")
        if not sep or name not in names:
            raise SystemExit(f"--te {item}: se espera config=segundos con config en {', '.join(map(str, names))}")
        out[name] = float(value)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="1.3: DCM y D a partir de cortes.txt")
    ap.add_argument("--te", nargs="+", default=[], metavar="config=t_e",
                    help="pisa el t_e de cortes.txt para esta corrida, p. ej. --te disco_022=12 vacia=5")
    cli = ap.parse_args()
    cuts = read_cuts()
    cuts.update(parse_te(cli.te, [c for c, *_ in CONFIGS]))
    if cli.te:
        print("t_e por parámetro:", ", ".join(cli.te), "(cortes.txt no se modifica)")
    example = {c: msd(DATA / c / f"run_{EXAMPLE_SEED}.txt") for c, *_ in CONFIGS}
    seeds = {c: [msd(DATA / "seeds" / c / f"run_{s}.txt") for s in SEEDS] for c, *_ in CONFIGS}

    rows = []
    for c, label, macro, divides, color, t90, t90_sd in CONFIGS:
        tm = cuts[c]
        d_ex, b_ex, se_ex, n_ex = fit(example[c], 0.0, tm)
        ds = [fit(s, 0.0, tm)[0] for s in seeds[c]]
        sens = [fit(example[c], a, f * tm)[0] for a in (0.0, 0.3) for f in (0.75, 1.0, 1.25)]
        plateaus = [st.mean(m for t, m in s if t >= tm) for s in seeds[c]]
        pl_ex = st.mean(m for t, m in example[c] if t >= tm)
        rows.append(dict(c=c, label=label, macro=macro, divides=divides, color=color, tm=tm,
                         d_ex=d_ex, b_ex=b_ex, se_ex=se_ex, n_ex=n_ex,
                         d=st.mean(ds), sd=st.stdev(ds), sem=st.stdev(ds) / math.sqrt(len(ds)),
                         sens_lo=min(sens), sens_hi=max(sens),
                         pl=st.mean(plateaus), pl_sd=st.stdev(plateaus), pl_ex=pl_ex,
                         t90=t90, t90_sd=t90_sd, t90_sem=t90_sd / math.sqrt(N_T90)))

    with (OUT / "dcm_resultados.txt").open("w", encoding="utf-8") as fh:
        fh.write("# 1.3 — DCM y coeficiente de difusión aparente. N = 100, tf = 30 s, cuadros cada 10 eventos.\n")
        fh.write("# t_e: inicio de la meseta, estimado visualmente sobre la realización de ejemplo (cortes.txt).\n")
        fh.write("# D: ajuste DCM = 4Dt + b en [0, t_e], D = pendiente/4.\n")
        fh.write("# VALOR INFORMADO: D_media ± D_sd = promedio y desvío estándar de D entre las 10 realizaciones\n")
        fh.write("#   (semillas 401-410), un ajuste por realización. D_sem = error estándar de la media.\n")
        fh.write("# D_ej: realización de ejemplo (semilla 401); D_ej_err_ajuste: error del ajuste (subestima).\n")
        fh.write("# D_sens_min/max: D de la realización 401 con inicio 0 o 0.3 s y final 0.75, 1 o 1.25 t_e.\n")
        fh.write("# meseta_ej: DCM medio entre t_e y 30 s en la realización 401; meseta_sd: desvío entre las 10.\n")
        fh.write(f"# t90: del 1.2 ({N_T90} realizaciones, semillas 601-612), no recalculado acá; t90_sem = t90_sd/sqrt({N_T90}).\n")
        fh.write("config divide_mesa t_e D_media D_sd D_sem D_ej D_ej_err_ajuste puntos_ej D_sens_min D_sens_max "
                 "meseta_ej meseta_media meseta_sd t90 t90_sd t90_sem\n")
        for r in rows:
            fh.write(f"{r['c']} {r['divides']} {r['tm']:g} {r['d']:.5f} {r['sd']:.5f} {r['sem']:.5f} "
                     f"{r['d_ex']:.5f} {r['se_ex']:.5f} {r['n_ex']} {r['sens_lo']:.5f} {r['sens_hi']:.5f} "
                     f"{r['pl_ex']:.4f} {r['pl']:.4f} {r['pl_sd']:.4f} {r['t90']} {r['t90_sd']} {r['t90_sem']:.2f}\n")
            print(f"{r['c']:9s} t_e {r['tm']:4g} s  <D> = {r['d']:.5f} ± {r['sd']:.5f}  (semilla 401: {r['d_ex']:.5f})  "
                  f"sens [{r['sens_lo']:.5f}, {r['sens_hi']:.5f}]  meseta(401) {r['pl_ex']:.3f} ± {r['pl_sd']:.3f} m²")

    # Pendiente local en log-log, promedio de las 10 semillas, ventanas [t, 1.5 t]
    starts = [0.05 * 1.5 ** i for i in range(13)]
    slope_table = {}
    with (OUT / "dcm_pendiente_local.txt").open("w", encoding="utf-8") as fh:
        fh.write("# Pendiente de log DCM vs log t en ventanas [t, 1.5t], promedio de las 10 semillas.\n")
        fh.write("# 2 = balístico, 1 = lineal (difusivo), 0 = meseta. '-' = menos de 5 semillas con 3 puntos.\n")
        fh.write("config " + " ".join(f"{t:.2f}" for t in starts) + "\n")
        for r in rows:
            vals = []
            for t in starts:
                v = [a for a in (local_slope(s, t, 1.5 * t) for s in seeds[r["c"]]) if a is not None]
                vals.append(f"{st.mean(v):.2f}" if len(v) >= 5 else "-")
            slope_table[r["c"]] = vals
            fh.write(r["c"] + " " + " ".join(vals) + "\n")

    # Números para la presentación
    macros = ["% Generado por python/dcm_report.py (docs/results/1.3/cortes.txt). No editar a mano."]
    for r in rows:
        v, e = rounded(r["d"], r["sd"])
        lo, hi = rounded(r["sens_lo"], r["sd"])[0], rounded(r["sens_hi"], r["sd"])[0]
        macros += [rf"\newcommand{{\DcmD{r['macro']}}}{{{v} \pm {e}}}",
                   rf"\newcommand{{\DcmCorte{r['macro']}}}{{{r['tm']:g}}}",
                   rf"\newcommand{{\DcmRango{r['macro']}}}{{{lo}\text{{--}}{hi}}}"]
    vac = next(r for r in rows if r["c"] == "vacia")
    macros.append(rf"\newcommand{{\DcmDejemplo}}{{{vac['d_ex']:.4f}}}")
    pv, pe = rounded(vac["pl_ex"], vac["pl_sd"])
    macros.append(rf"\newcommand{{\DcmMesetavacia}}{{{pv} \pm {pe}}}")
    (PRES / "dcm_valores.tex").write_text("\n".join(macros) + "\n", encoding="utf-8")

    table = [macros[0],
             r"\begin{tabular}{lcccc}",
             r"  \hline",
             r"  configuración & área ocupada & $t_e$ (s) & $D$ (m$^{2}$/s) & $\langle t_{90}\rangle$ (s) \\",
             r"  \hline"]
    for r in sorted(rows, key=lambda r: r["d"], reverse=True):
        v, e = rounded(r["d"], r["sd"])
        pv, pe = rounded(r["pl_ex"], r["pl_sd"])
        tv, te = rounded(r["t90"], r["t90_sd"])
        table.append(rf"  {TABLE_NAMES[r['c']]} & {covered(r['c']):.0f}\,\% & ${r['tm']:g}$ & ${v} \pm {e}$ & ${tv} \pm {te}$ \\")
    table += [r"  \hline", r"\end{tabular}"]
    (PRES / "dcm_tabla.tex").write_text("\n".join(table) + "\n", encoding="utf-8")

    # Pendiente local para el apéndice: algunas ventanas representativas
    cols = [1, 3, 5, 7, 9, 11]
    ptab = [macros[0], r"\begin{tabular}{l" + "c" * len(cols) + "}", r"  \hline",
            "  $t$ (s) & " + " & ".join(f"${starts[i]:.2f}$" for i in cols) + r" \\", r"  \hline"]
    for r in rows:
        ptab.append(f"  {TABLE_NAMES[r['c']]} & " + " & ".join(f"${slope_table[r['c']][i]}$" for i in cols) + r" \\")
    ptab += [r"  \hline", r"\end{tabular}"]
    (PRES / "dcm_pendiente.tex").write_text("\n".join(ptab) + "\n", encoding="utf-8")

    # Figura por configuración: realización de ejemplo, recta del ajuste y t_e
    (OUT / "t30").mkdir(parents=True, exist_ok=True)
    for r in rows:
        s = example[r["c"]]
        fig, ax = new_figure()
        ax.plot([t for t, _ in s], [m for _, m in s], color=BLUE, lw=1.2, zorder=3, label="simulación")
        ax.plot([0, r["tm"]], [r["b_ex"], r["b_ex"] + 4 * r["d_ex"] * r["tm"]], color=VERMILLION, lw=2.5,
                zorder=4, label=r"ajuste en $[0, t_e]$")
        ax.axvline(r["tm"], color="gray", ls="--", lw=1.5, zorder=2)
        style_axes(ax, "tiempo (s)", r"DCM (m$^2$)")
        ax.set_xlim(0, 30)
        ax.set_ylim(0, max(m for _, m in s) * 1.4)
        ax.legend(loc="upper left", frameon=True)
        save_figure(fig, OUT / "t30" / f"dcm30_{r['c']}.png")
    shutil.copyfile(OUT / "t30" / "dcm30_vacia.png", OUT / "dcm_vacia.png")

    # E(D) del ejemplo de la mesa vacía: b se optimiza para cada D (Teórica 0)
    pts = [(t, m) for t, m in example["vacia"] if 0.0 <= t <= vac["tm"]]
    grid = [2 * vac["d_ex"] * i / 400 for i in range(1, 401)]
    errs = []
    for dt in grid:
        bb = st.mean(m - 4 * dt * t for t, m in pts)
        errs.append(sum((m - bb - 4 * dt * t) ** 2 for t, m in pts))
    d_best = grid[errs.index(min(errs))]
    fig, ax = new_figure()
    ax.plot(grid, errs, color=BLUE, lw=2, zorder=3)
    ax.axvline(d_best, color=VERMILLION, ls="--", zorder=2, label=rf"$D^* = {d_best:.4f}\,$m$^2$/s")
    style_axes(ax, r"$D$ (m$^2$/s)", r"$E(D)$ (m$^4$)")
    ax.set_ylim(0, max(errs) * 1.35)
    apply_sci_axis(ax, "y")
    ax.legend(loc="upper center", frameon=True)
    save_figure(fig, OUT / "dcm_error.png")

    # Las cinco configuraciones (realización de ejemplo)
    fig, ax = new_figure()
    for r in rows:
        s = example[r["c"]]
        ax.plot([t for t, _ in s], [m for _, m in s], color=r["color"], lw=1.4, zorder=3, label=SHORT[r["c"]])
    style_axes(ax, "tiempo (s)", r"DCM (m$^2$)")
    ax.set_xlim(0, 30)
    ax.set_ylim(0, max(m for r in rows for _, m in example[r["c"]]) * 1.9)
    ax.legend(loc="upper left", ncol=2, frameon=True, columnspacing=0.8, handlelength=1.2)
    save_figure(fig, OUT / "dcm_configs.png")

    # Log-log de la mesa vacía (ejemplo): (v0 t)^2 y meseta esperada con las partículas repartidas
    plateau = ((L - 2 * R) ** 2 + (W - 2 * R) ** 2) / 6
    fig, ax = new_figure()
    pos = [(t, m) for t, m in example["vacia"] if t > 0]
    ax.plot([t for t, _ in pos], [m for _, m in pos], "o", color=BLUE, markersize=2, zorder=3,
            label="simulación")
    tb = [0.01, 0.2]
    ax.plot(tb, [t * t for t in tb], "--", color="gray", lw=1.8, zorder=2, label=r"$(v_0 t)^2$")
    ax.axhline(plateau, color=GREEN, ls=":", lw=2, zorder=2, label=r"$(L_e^2 + W_e^2)/6$")
    ax.set_xscale("log")
    ax.set_yscale("log")
    style_axes(ax, "tiempo (s)", r"DCM (m$^2$)")
    ax.legend(loc="lower right", frameon=True)
    save_figure(fig, OUT / "dcm_loglog.png")

    # D frente a <t90>: D de la realización única ± desvío entre realizaciones; <t90> ± desvío
    fig, ax = new_figure()
    for r, mk in zip(rows, tuple(MARKERS) + ("P", "X")):
        ax.errorbar(r["t90"], r["d"], xerr=r["t90_sd"], yerr=r["sd"], color=r["color"], marker=mk, markersize=8,
                    markeredgecolor="black", markeredgewidth=0.6, linestyle="none", capsize=4, zorder=3,
                    label=r["label"])
    style_axes(ax, r"$\langle t_{90}\rangle$ (s)", r"$D$ (m$^2$/s)")
    ax.set_ylim(0, max(r["d"] + r["sd"] for r in rows) * 2.7)
    apply_sci_axis(ax, "y")
    ax.legend(loc="upper left", frameon=True)
    save_figure(fig, OUT / "d_vs_t90.png")

    for name in ("dcm_vacia", "dcm_error", "dcm_configs", "dcm_loglog", "d_vs_t90"):
        shutil.copyfile(OUT / f"{name}.png", PRES / "images" / f"{name}.png")
    print("figuras copiadas a docs/presentation/images/; macros y tabla en docs/presentation/")


if __name__ == "__main__":
    main()
