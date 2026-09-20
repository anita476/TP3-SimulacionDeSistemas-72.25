"""Arma tablas y figuras del TP desde data/. Un solo comando:

    python python/make.py
    python python/make.py --xlabel "posición $x$ (m)" --t-min 2 --t-max 20

Lo que no esté, se omite. Los dumps mandan sobre tablas viejas.

    data/wall.txt                      1.1  columnas: N events wall_events pair_events time (o menos)
    data/runs/t90/<x>/*.txt            1.2
    data/runs/empty/*.txt              mesa vacía (1.2)
    data/runs/msd/*.txt                1.3 DCM, una realización
    data/runs/configs/<nombre>/*.txt   1.3 D vs t90
    data/sample_traj.txt               animación
"""

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))

from metrics import diffusion, fit_line, mean_std, msd_series
from runs import dump_paths, read_realizations, run_folders, t90_summary
from tables import load_table
from traj import read_traj

ROOT = HERE.parent

def _write_table(path: Path, header: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n" + "".join(line + "\n" for line in lines), encoding="utf-8")
    print(f"se escribió {path}")


def _run(script: Path, *args: str) -> None:
    result = subprocess.run([sys.executable, str(script), *args], check=False)
    if result.returncode:
        raise SystemExit(result.returncode)


def _window(series: list[tuple[float, float]], t_min: float | None, t_max: float | None):
    xs, ys = [], []
    for t, value in series:
        if t_min is not None and t < t_min:
            continue
        if t_max is not None and t > t_max:
            continue
        xs.append(t)
        ys.append(value)
    return xs, ys


def runtime_table(wall: Path) -> list[tuple[int, float, float, dict[str, float]]]:
    """Agrupa wall.txt por N: (N, <tiempo>, desvío, {columna: promedio}) para las
    columnas de eventos presentes (events, wall_events, pair_events)."""
    with wall.open(encoding="utf-8") as stream:
        header = next((l.split() for l in stream if l.strip() and not l.startswith("#")), None)
    if header is None or header[0] != "N" or "time" not in header:
        raise ValueError(f"{wall}: se esperaban las columnas 'N [events wall_events pair_events] time'")
    counts = [c for c in ("events", "wall_events", "pair_events") if c in header]
    rows = load_table(wall, ("N", "time", *counts))
    grouped: dict[int, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(int(row["N"]), []).append(row)
    out = []
    for n in sorted(grouped):
        mean, std = mean_std([float(r["time"]) for r in grouped[n]])
        means = {c: sum(float(r[c]) for r in grouped[n]) / len(grouped[n]) for c in counts}
        out.append((n, mean, std, means))
    return out


def _step_runtime(data: Path) -> None:
    wall = data / "wall.txt"
    table = data / "runtime.txt"
    if wall.is_file():
        rows = runtime_table(wall)
        cols = ("events", "wall_events", "pair_events")
        _write_table(
            table,
            "N t_mean t_std events_mean wall_mean pair_mean",
            [f"{n} {m:.6g} {s:.6g} " + " ".join(f"{ev[c]:.6g}" if c in ev else "None" for c in cols)
             for n, m, s, ev in rows],
        )
    if not table.is_file():
        print(f"se omite 1.1: no hay {wall} ni {table}")
        return
    _run(
        HERE / "plotters" / "plot_runtime.py",
        "--input", str(table),
        "--output", str(data / "runtime.png"),
        "--loglog-output", str(data / "runtime_loglog.png"),
        "--error-output", str(data / "runtime_error.png"),
        "--events-output", str(data / "events_vs_n.png"),
        "--events-loglog-output", str(data / "events_vs_n_loglog.png"),
        "--per-event-output", str(data / "time_per_event.png"),
    )


def _step_t90(data: Path, xlabel: str) -> None:
    table = data / "t90.txt"
    rows = []
    for folder in run_folders(data / "runs" / "t90"):
        mean, std, _ng, _reached = t90_summary(read_realizations(folder))
        rows.append((float(folder.name), folder.name, mean, std))
    if rows:
        rows.sort()
        _write_table(
            table,
            "x t90_mean t90_std",
            [f"{name} {mean:.6g} {std:.6g}" for _x, name, mean, std in rows],
        )
    if not table.is_file():
        print(f"se omite 1.2: no hay {data / 'runs' / 't90'} ni {table}")
        return
    args = ["--input", str(table), "--output", str(data / "t90.png"), "--xlabel", xlabel]
    empty_dir = data / "runs" / "empty"
    empty_reals = read_realizations(empty_dir) if dump_paths(empty_dir) else []
    if empty_reals:
        mean, std, _ng, _reached = t90_summary(empty_reals)
        args.extend(["--empty", str(mean), str(std)])


def _step_msd(data: Path, t_min: float | None, t_max: float | None) -> None:
    table = data / "msd.txt"
    dumps = dump_paths(data / "runs" / "msd")
    if dumps:
        series = msd_series(read_traj(dumps[0]))
        _write_table(table, "t msd", [f"{t:.6g} {msd:.6g}" for t, msd in series])
    if not table.is_file():
        print(f"se omite 1.3 DCM: no hay {data / 'runs' / 'msd'} ni {table}")
        return
    args = ["--input", str(table), "--output", str(data / "msd.png")]
    if t_min is not None:
        args.extend(["--t-min", str(t_min)])
    if t_max is not None:
        args.extend(["--t-max", str(t_max)])
    _run(HERE / "plotters" / "plot_msd.py", *args)


def _step_d_vs_t90(data: Path, t_min: float | None, t_max: float | None) -> None:
    table = data / "d_vs_t90.txt"
    lines = []
    for folder in run_folders(data / "runs" / "configs"):
        paths = dump_paths(folder)
        xs, ys = _window(msd_series(read_traj(paths[0])), t_min, t_max)
        d = diffusion(fit_line(xs, ys)[0])
        mean, std = mean_std([t90(read_traj(path)) for path in paths])
        print(f"D = {d:.6g} m^2/s  (pendiente / 4)")
        lines.append(f"{folder.name} {d:.6g} {mean:.6g} {std:.6g}")
    if lines:
        lines.sort()
        _write_table(table, "config D t90 t90_std", lines)
    if not table.is_file():
        print(f"se omite 1.3 D vs t90: no hay {data / 'runs' / 'configs'} ni {table}")
        return
    _run(HERE / "plotters" / "plot_d_vs_t90.py", "--input", str(table), "--output", str(data / "d_vs_t90.png"))


def _step_anim(data: Path) -> None:
    traj = data / "sample_traj.txt"
    if not traj.is_file():
        print(f"se omite animación: no hay {traj}")
        return
    _run(
        HERE / "animate.py",
        "--traj",
        str(traj),
        "--out",
        str(data / "sample.gif"),
        "--png",
        str(data / "sample.png"),
    )

def run_folders_nested(root: Path) -> list[Path]:
    """Familias: subcarpetas de root que a su vez contienen carpetas con dumps."""
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and run_folders(p))

def _step_fu(data: Path) -> None:
    series: list[tuple[str, Path]] = []
    empty = data / "runs" / "empty"
    if dump_paths(empty):
        series.append(("mesa vacía", empty))
    best = None  # carpeta con menor <t90> entre todas las familias
    for family in run_folders_nested(data / "runs" / "t90"):
        for folder in run_folders(family):
            mean, _std, _ng, reached = t90_summary(read_realizations(folder))
            if reached and (best is None or mean < best[0]):
                best = (mean, folder)
    if best is not None:
        series.append((f"{best[1].parent.name} = {best[1].name}", best[1]))
    if not series:
        print("se omite Fu(t): no hay data/runs/empty ni data/runs/t90")
        return
    args = ["--output", str(data / "fu.png")]
    for label, folder in series:
        args += ["--series", label, str(folder)]
    _run(HERE / "plotters" / "plot_fu.py", *args)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--xlabel", default=r"posición $x$ (m)", help="eje x de 1.2")
    parser.add_argument("--t-min", type=float, default=None)
    parser.add_argument("--t-max", type=float, default=None)
    args = parser.parse_args()
    data = args.data
    data.mkdir(parents=True, exist_ok=True)
    try:
        _step_runtime(data)
        _step_t90(data, args.xlabel)
        _step_msd(data, args.t_min, args.t_max)
        _step_d_vs_t90(data, args.t_min, args.t_max)
        _step_fu(data)
        _step_anim(data)
    except (OSError, ValueError) as error:
        sys.exit(str(error))


if __name__ == "__main__":
    main()
