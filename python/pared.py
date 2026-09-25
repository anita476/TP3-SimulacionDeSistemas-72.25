"""Pared de círculos para el 1.2.

Todos los círculos tienen el mismo radio. Una columna cubre el alto: el
primero y el último tocan las paredes largas, y el hueco entre círculos es
menor que el diámetro de una partícula. El ancho es la cantidad de columnas,
pegadas con ese mismo hueco.

    python python/pared.py --plan
    python python/pared.py --outdir data/runs/1.2/pared
    python python/pared.py --radius 0.0175 --columns 19 --centers 0.60 --plan
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "lib"))

from metrics import mean_std
from run import DEFAULT_EXE, run_engine

L = 1.20
W = 0.68
R_PARTICLE = 0.0175
TMAX = 100.0
N = 100
RADIUS = 0.035
COLUMNS = tuple(range(1, 11))
CENTERS = (0.40, 0.50, 0.60, 0.70, 0.80)


def column_ys(radius: float) -> tuple[list[float], float] | None:
    span = W - 2.0 * radius
    max_steps = int(span / (2.0 * radius))
    opening = 2.0 * radius + 2.0 * R_PARTICLE
    min_steps = int(span / opening) + 1
    if max_steps < 1 or min_steps > max_steps:
        return None
    pitch = span / max_steps
    gap = pitch - 2.0 * radius
    if gap < 0.0 or gap >= 2.0 * R_PARTICLE:
        return None
    ys = [radius + i * pitch for i in range(max_steps)]
    ys.append(W - radius)
    return ys, pitch


def wall(columns: int, xc: float, radius: float = RADIUS) -> list[tuple[float, float, float]] | None:
    laid = column_ys(radius)
    if laid is None or columns < 1:
        return None
    ys, pitch = laid
    offset0 = -0.5 * (columns - 1) * pitch
    discs = []
    for col in range(columns):
        x = xc + offset0 + col * pitch
        if x < radius or x > L - radius:
            return None
        discs.extend((x, y, radius) for y in ys)
    return discs


def write_config(path: Path, discs: list[tuple[float, float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{x:.17g} {y:.17g} {radius:.17g}\n" for x, y, radius in discs), encoding="utf-8")


def evaluate(exe: Path, discs: list[tuple[float, float, float]], seeds: list[int], jobs: int, config: Path) -> tuple[float, float, int]:
    write_config(config, discs)

    def one(seed: int) -> float:
        summary = run_engine(exe, N, R_PARTICLE, seed, TMAX, 0, config, None)
        return float(summary["t90"])

    with ThreadPoolExecutor(max_workers=min(jobs, len(seeds))) as pool:
        t90s = list(pool.map(one, seeds))
    reached = [t for t in t90s if t >= 0.0]
    if len(reached) != len(seeds):
        raise RuntimeError(f"{config}: llegaron {len(reached)} de {len(seeds)}")
    mean, std = mean_std(reached)
    return mean, std, len(discs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--outdir", type=Path)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--seed", type=int, default=601)
    parser.add_argument("--reps", type=int, default=12)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--columns", type=int, nargs="+", default=list(COLUMNS))
    parser.add_argument("--centers", type=float, nargs="+", default=list(CENTERS))
    parser.add_argument("--radius", type=float, nargs="+", default=[RADIUS])
    args = parser.parse_args()

    rows = []
    for radius in args.radius:
        if radius < R_PARTICLE:
            raise SystemExit(f"radio {radius} m es menor que r")
        laid = column_ys(radius)
        if laid is None:
            raise SystemExit(f"radio {radius} m no cierra el alto")
        _ys, pitch = laid
        gap = pitch - 2.0 * radius
        for columns in args.columns:
            ancho = (columns - 1) * pitch + 2.0 * radius
            for xc in args.centers:
                discs = wall(columns, xc, radius)
                if discs is None:
                    print(f"R {radius:.4f}  {columns} columnas  x {xc:.2f}: no entra en la mesa")
                    continue
                print(
                    f"R {radius:.4f} m  {columns} columnas  ancho {ancho:.3f} m  x {xc:.2f} m  "
                    f"K={len(discs)}  hueco {gap * 1000:.1f} mm"
                )
                rows.append((radius, columns, ancho, xc, discs))
    if args.plan:
        return
    if args.outdir is None:
        parser.error("--outdir es obligatorio salvo con --plan")

    exe = args.exe.resolve()
    if not exe.is_file():
        exe = exe.with_suffix(".exe")
    seeds = list(range(args.seed, args.seed + args.reps))
    out = args.outdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    table = out / "pared_t90.txt"
    lines = ["radio columnas ancho x K t90_mean t90_std"]
    for radius, columns, ancho, xc, discs in rows:
        config = out / f"r{radius:.4f}_c{columns}_x{xc:.2f}.txt"
        mean, std, k = evaluate(exe, discs, seeds, args.jobs, config)
        lines.append(f"{radius:.4f} {columns} {ancho:.6g} {xc:.2f} {k} {mean:.6g} {std:.6g}")
        table.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  <t90> = {mean:.4g} ± {std:.4g} s")
    print(f"se escribió {table}")


if __name__ == "__main__":
    main()
