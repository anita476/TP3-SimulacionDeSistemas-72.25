"""1.3: D contra <t90> a lo largo del barrido de columnas de la pared de R = r (punto 1.2).

    python python/dcm_barrido.py run       corre las simulaciones y guarda las curvas DCM(t)
    python python/dcm_barrido.py curvas    grafica las curvas de 30 s para elegir t_e a ojo
    python python/dcm_barrido.py report    ajusta D con los t_e de cortes_barrido.txt y grafica
    python python/dcm_barrido.py report --te 19=10 21=12   pisa esos t_e solo en esta corrida

Misma pared que pared.py (R = 0.0175 m, centro x = 0.60 m), mismos parámetros que
dcm_report.py: N = 100, k = 10, tf = 30 s, semillas 401..410. Se ajusta cada realización y
se informa <D> ± desvío estándar entre las 10. <t90> se reutiliza de
docs/results/1.2/pared_columnas.txt (no se recalcula).

Para no guardar 90 trayectorias de ~95 MB, cada corrida escribe su dump en un archivo
temporal, se calcula el DCM (promedio sobre las 100 partículas, un solo origen, cada
cuadro guardado por el motor en su tiempo físico) y se borra el dump. Queda
data/1.3/barrido/pared_<c>/msd_<semilla>.txt con columnas t DCM.
"""

import argparse
import shutil
import statistics as st
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "lib"))

from dcm_report import fit, parse_te, rounded
from pared import wall, write_config
from plot_style import BLUE, VERMILLION, new_figure, save_figure, style_axes
from run import DEFAULT_EXE, run_engine
from tables import load_table

COLUMNS = (1, 2, 4, 6, 8, 10, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24)  # las de pared_columnas.txt
SEEDS = range(401, 411)
EXAMPLE_SEED = 401
R = 0.0175
XC = 0.60
TMAX = 30.0
K = 10
DATA = ROOT / "data" / "1.3" / "barrido"
OUT = ROOT / "docs" / "results" / "1.3" / "barrido"
CUTS_FILE = ROOT / "docs" / "results" / "1.3" / "cortes_barrido.txt"
T90_TABLE = ROOT / "docs" / "results" / "1.2" / "pared_columnas.txt"
EMPTY = ("vacia", 23.76, 3.22)  # <t90> de la mesa vacía; D sale de data/1.3/t30


def msd_from_dump(path: Path) -> list[tuple[float, float]]:
    """DCM respecto del primer cuadro, leyendo el dump de a una línea."""
    out, origin, frame, t, n = [], None, [], None, None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if not parts or parts[0].startswith("#"):
                continue
            if parts[0] == "N":
                n = int(parts[1])
            elif parts[0] == "t":
                t, frame = float(parts[1]), []
            elif t is not None:
                frame.append((float(parts[0]), float(parts[1])))
                if len(frame) == n:
                    if origin is None:
                        origin = frame
                    out.append((t, sum((x - a) ** 2 + (y - b) ** 2 for (x, y), (a, b) in zip(frame, origin)) / n))
    return out


def one(task: tuple[int, int]) -> str:
    columns, seed = task
    folder = DATA / f"pared_{columns}"
    target = folder / f"msd_{seed}.txt"
    if target.exists():
        return f"{columns} {seed} ya estaba"
    with tempfile.TemporaryDirectory() as tmp:
        dump = Path(tmp) / "run.txt"
        summary = run_engine(DEFAULT_EXE, 100, R, seed, TMAX, K, folder / "obstacles.txt", dump)
        series = msd_from_dump(dump)
    target.write_text("".join(f"{t:.9g} {m:.9g}\n" for t, m in series), encoding="utf-8")
    return f"{columns} {seed} t90={summary.get('t90')} cuadros={len(series)}"


def read_msd(path: Path) -> list[tuple[float, float]]:
    return [tuple(map(float, line.split())) for line in path.read_text(encoding="utf-8").splitlines() if line]


def cmd_run() -> None:
    for c in COLUMNS:
        (DATA / f"pared_{c}").mkdir(parents=True, exist_ok=True)
        write_config(DATA / f"pared_{c}" / "obstacles.txt", wall(c, XC, R))
    tasks = [(c, s) for c in COLUMNS for s in SEEDS]
    with ProcessPoolExecutor() as pool:
        for msg in pool.map(one, tasks):
            print(msg, flush=True)


def cmd_curvas() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for c in COLUMNS:
        s = read_msd(DATA / f"pared_{c}" / f"msd_{EXAMPLE_SEED}.txt")
        fig, ax = new_figure()
        ax.plot([t for t, _ in s], [m for _, m in s], color=BLUE, lw=1.2)
        style_axes(ax, "tiempo (s)", r"DCM (m$^2$)")
        ax.set_xlim(0, 30)
        ax.set_xticks(range(0, 31, 2))
        ax.grid(True, alpha=0.4)
        ax.set_title(f"pared de {c} columnas")
        save_figure(fig, OUT / f"dcm30_pared_{c}.png")
    print("curvas en", OUT)


def read_cuts() -> dict[int, float]:
    cuts = {}
    for line in CUTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            c, v = line.split()
            cuts[int(c)] = float(v)
    missing = [c for c in COLUMNS if c not in cuts]
    if missing:
        raise SystemExit(f"{CUTS_FILE}: falta t_e de {missing}")
    return cuts


def cmd_report(te: list[str]) -> None:
    cuts = read_cuts()
    cuts.update({int(c): v for c, v in parse_te(te, [str(c) for c in COLUMNS]).items()})
    if te:
        print("t_e por parámetro:", ", ".join(te), "(cortes_barrido.txt no se modifica)")
    t90 = {int(r["columnas"]): (float(r["t90_mean"]), float(r["t90_std"])) for r in load_table(
        T90_TABLE, ("radio", "columnas", "ancho", "x", "K", "t90_mean", "t90_std"))}
    rows = []
    for c in COLUMNS:
        ds = [fit(read_msd(DATA / f"pared_{c}" / f"msd_{s}.txt"), 0.0, cuts[c])[0] for s in SEEDS]
        rows.append((c, cuts[c], st.mean(ds), st.stdev(ds), *t90[c]))
    OUT.mkdir(parents=True, exist_ok=True)
    lines = ["columnas t_e D_media D_sd t90_mean t90_std"]
    lines += [f"{c} {te:g} {d:.6g} {sd:.6g} {m:g} {s:g}" for c, te, d, sd, m, s in rows]
    (OUT / "d_barrido.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for c, te, d, sd, m, s in rows:
        dv, de = rounded(d, sd)
        print(f"{c:>3} col  t_e={te:g}  D={dv} ± {de}  <t90>={m:.1f} ± {s:.1f}")

    cs = [r[0] for r in rows]
    fig, ax = new_figure()
    ax.errorbar(cs, [r[2] for r in rows], yerr=[r[3] for r in rows], color=BLUE, marker="o",
                markeredgecolor="black", markeredgewidth=0.6, capsize=4)
    style_axes(ax, "columnas", r"$D$ (m$^2$/s)")
    save_figure(fig, OUT / "d_vs_columnas.png")

    fig, ax = new_figure()
    ax.errorbar([r[4] for r in rows], [r[2] for r in rows], xerr=[r[5] for r in rows], yerr=[r[3] for r in rows],
                color=BLUE, marker="o", markeredgecolor="black", markeredgewidth=0.6, capsize=4, ls="none")
    for c, _, d, _, m, _ in rows:
        ax.annotate(f"{c}", (m, d), textcoords="offset points", xytext=(6, 6), fontsize=12)
    best = min(rows, key=lambda r: r[4])  # menor <t90>
    ax.plot(best[4], best[2], "o", color=VERMILLION, markeredgecolor="black", markeredgewidth=0.6, zorder=5)
    style_axes(ax, r"$\langle t_{90}\rangle$ (s)", r"$D$ (m$^2$/s)")
    save_figure(fig, OUT / "d_vs_t90_barrido.png")
    shutil.copyfile(OUT / "d_vs_t90_barrido.png", ROOT / "docs" / "presentation" / "images" / "d_vs_t90_barrido.png")

    # <t90> arriba y D abajo contra las columnas, mismo eje x
    import matplotlib.pyplot as plt
    fig, (top, bottom) = plt.subplots(2, 1, sharex=True, figsize=(6.4, 6.4), layout="constrained")
    for ax, i, ylabel in ((top, 4, r"$\langle t_{90}\rangle$ (s)"), (bottom, 2, r"$D$ (m$^2$/s)")):
        ax.errorbar(cs, [r[i] for r in rows], yerr=[r[i + 1] for r in rows], color=BLUE, marker="o",
                    markeredgecolor="black", markeredgewidth=0.6, capsize=4)
        ax.axvline(best[0], color=VERMILLION, ls="--", lw=1.5, zorder=0)
        style_axes(ax, "columnas" if ax is bottom else "", ylabel)
    top.tick_params(labelbottom=False)
    save_figure(fig, OUT / "t90_d_vs_columnas.png")
    shutil.copyfile(OUT / "t90_d_vs_columnas.png", ROOT / "docs" / "presentation" / "images" / "t90_d_vs_columnas.png")
    print("figuras en", OUT)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="1.3: D contra <t90> en el barrido de columnas")
    ap.add_argument("cmd", choices=("run", "curvas", "report"))
    ap.add_argument("--te", nargs="+", default=[], metavar="columnas=t_e",
                    help="solo con report: pisa el t_e de cortes_barrido.txt, p. ej. --te 19=10 21=12")
    cli = ap.parse_args()
    if cli.cmd == "report":
        cmd_report(cli.te)
    else:
        {"run": cmd_run, "curvas": cmd_curvas}[cli.cmd]()
