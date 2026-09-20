"""Ejecuta el motor con una semilla distinta por realización.

Ejemplos:
    python3 python/run.py --outdir data/runs/smoke --reps 3 --tmax 5 --k 100
    python3 python/run.py --outdir data/runs/obstacles --obstacles configs/obstacles_test.txt
    python3 python/run.py --wall data/wall.txt --n 50 100 200 300 --reps 10 --tmax 30

--outdir:
    Guarda run_<seed>.txt, summary.dat, params.txt y, si corresponde,
    una copia de los obstáculos. Permite realizaciones en paralelo.

--wall:
    Guarda filas "N events wall_events pair_events time": eventos procesados en
    tmax (total, contra paredes y entre partículas) y engine_seconds
    (construcción de la cola inicial + loop de eventos; sin generación de la
    condición inicial ni escritura de archivos).
    Ejecuta secuencialmente y sin dumps para comparar tiempos.

El motor debe admitir --raw y emitir su resumen como líneas "clave valor".
"""

import argparse
import math
import os
import shlex
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_EXE = ROOT / "build" / "EventDrivenSim"

REQUIRED_SUMMARY_KEYS = {
    "N",
    "K",
    "tmax",
    "k",
    "packing",
    "events",
    "wall_events",
    "obstacle_events",
    "pair_events",
    "discarded",
    "zero_dt",
    "max_queue",
    "t_end",
    "Ng",
    "t90",
    "E0",
    "E_end",
    "energy_drift",
    "init_seconds",
    "loop_seconds",
    "engine_seconds",
}


def run_engine(
    exe: Path,
    n: int,
    r: float,
    seed: int,
    tmax: float,
    k: int,
    obstacles: Path | None,
    out: Path | None,
) -> dict[str, str]:
    cmd = [
        str(exe),
        "--raw",
        "-N", str(n),
        "-r", str(r),
        "-seed", str(seed),
        "-tmax", str(tmax),
        "-k", str(k),
    ]

    if obstacles is not None:
        cmd += ["-obstacles", str(obstacles)]

    if out is not None:
        cmd += ["--out", str(out)]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"El motor terminó con código {result.returncode}:\n"
            f"{shlex.join(cmd)}\n{detail}"
        )

    summary: dict[str, str] = {}

    for lineno, line in enumerate(result.stdout.splitlines(), 1):
        if not line.strip():
            continue

        parts = line.split()
        if len(parts) != 2:
            raise RuntimeError(
                f"Resumen inválido del motor en la línea {lineno}: {line!r}\n"
                "Se esperaba 'clave valor'. Recompilá el motor con soporte "
                "para --raw."
            )

        key, value = parts

        if key in summary:
            raise RuntimeError(f"Clave repetida en el resumen del motor: {key}")

        summary[key] = value

    missing = REQUIRED_SUMMARY_KEYS - summary.keys()
    if missing:
        raise RuntimeError(
            "Faltan claves en el resumen del motor: "
            + ", ".join(sorted(missing))
        )

    return summary


def append_row(path: Path, header: str, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists() or path.stat().st_size == 0

    with path.open("a", encoding="utf-8") as file:
        if fresh:
            file.write(header + "\n")
        file.write(line + "\n")


def print_run_summary(
    summary: dict[str, str],
    seed: int,
    out: Path,
) -> None:
    n = int(summary["N"])
    goals = int(summary["Ng"])
    t90 = float(summary["t90"])
    k = int(summary["k"])
    drift = float(summary["energy_drift"])

    print(
        f"\n{'=' * 60}\n"
        f"Realization — seed {seed}\n"
        f"{'=' * 60}\n"
        "\nConfiguration\n"
        f"  Particles:                {n}\n"
        f"  Obstacles:                {summary['K']}\n"
        f"  Maximum simulated time:   {float(summary['tmax']):.3f} s\n"
        f"  Occupied area:            {100 * float(summary['packing']):.2f}%\n"
        f"  Trajectory file:          {out}"
    )

    if k == 0:
        print("  Frames:                   initial state and goals")
    else:
        print(
            f"  Frames:                   initial, every {k} collisions, "
            "and goals"
        )

    t90_text = "not reached" if t90 < 0 else f"{t90:.6f} s"

    print(
        "\nSimulation results\n"
        f"  Final simulated time:     {float(summary['t_end']):.6f} s\n"
        f"  Particles that scored:    {goals} / {n} ({100 * goals / n:.1f}%)\n"
        f"  Time to 90% scored:       {t90_text}\n"
        "\nPhysical collisions\n"
        f"  Total:                    {int(summary['events']):,}\n"
        f"  Particle-particle:        {int(summary['pair_events']):,}\n"
        f"  Particle-wall:            {int(summary['wall_events']):,}\n"
        f"  Particle-obstacle:        {int(summary['obstacle_events']):,}\n"
        "\nEnergy\n"
        f"  Initial:                  {float(summary['E0']):.12g} J\n"
        f"  Final:                    {float(summary['E_end']):.12g} J"
    )

    drift_text = "undefined" if math.isnan(drift) else f"{drift:.3e}"
    print(f"  Relative energy drift:    {drift_text}")

    print(
        "\nEvent queue diagnostics\n"
        f"  Stale events discarded:   {int(summary['discarded']):,}\n"
        f"  Zero-time events:         {int(summary['zero_dt']):,}\n"
        f"  Peak queue entries:       {int(summary['max_queue']):,}\n"
        "\nExecution time\n"
        f"  Initialization:           {1000 * float(summary['init_seconds']):.3f} ms\n"
        f"  Event processing:         {1000 * float(summary['loop_seconds']):.3f} ms\n"
        f"  Total engine:             {1000 * float(summary['engine_seconds']):.3f} ms\n"
        "  Event processing includes trajectory writes during run().",
        flush=True,
    )
    
    
def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument(
        "--n", type=int, nargs="+", default=[100],
        help="uno o más N; varios solo con --wall",
    )
    parser.add_argument(
        "--r", type=float, default=0.0175,
        help="radio de partícula (m)",
    )
    parser.add_argument("--tmax", type=float, default=100.0)
    parser.add_argument(
        "--k", type=int, default=0,
        help="cuadro cada k eventos físicos; 0 = inicial y goles",
    )
    parser.add_argument("--obstacles", type=Path)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--jobs", type=int, default=os.cpu_count() or 1,
        help="corridas en paralelo; solo con --outdir",
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--outdir", type=Path, help="carpeta de dumps")
    mode.add_argument(
        "--wall", type=Path,
        help="archivo N events wall_events pair_events time; sin dumps y secuencial",
    )
    
    parser.add_argument(
        "--preview",
        choices=("first", "all", "none"),
        default="first",
        help="generar GIF y PNG: primera realización, todas o ninguna",
    )

    args = parser.parse_args()

    args.exe = args.exe.resolve()
    if not args.exe.is_file():
        parser.error(
            f"no existe {args.exe}; compilá con cmake --build build"
        )

    if args.obstacles is not None:
        args.obstacles = args.obstacles.resolve()
        if not args.obstacles.is_file():
            parser.error(f"no existe {args.obstacles}")

    if args.reps < 1:
        parser.error("--reps debe ser >= 1")
    if args.jobs < 1:
        parser.error("--jobs debe ser >= 1")
    if any(n < 1 for n in args.n):
        parser.error("cada N debe ser >= 1")
    if not math.isfinite(args.r) or args.r <= 0:
        parser.error("--r debe ser finito y > 0")
    if not math.isfinite(args.tmax) or args.tmax <= 0:
        parser.error("--tmax debe ser finito y > 0")
    if args.k < 0:
        parser.error("--k debe ser >= 0")

    # El CLI actual del motor recibe la semilla como int de 32 bits.
    last_seed = args.seed + args.reps - 1
    if args.seed < 0 or last_seed > 2**31 - 1:
        parser.error("las semillas deben estar entre 0 y 2147483647")

    seeds = list(range(args.seed, last_seed + 1))

    if args.wall is not None:
        # Sin competencia entre realizaciones ni escritura de trayectorias.
        for n in args.n:
            for seed in seeds:
                summary = run_engine(
                    args.exe, n, args.r, seed,
                    args.tmax, args.k, args.obstacles, None,
                )

                append_row(
                    args.wall,
                    "N events wall_events pair_events time",
                    f"{n} {summary['events']} {summary['wall_events']} {summary['pair_events']} "
                    f"{summary['engine_seconds']}",
                )

                print(
                    f"N={n} seed={seed} "
                    f"events={summary['events']} "
                    f"engine={summary['engine_seconds']}s"
                )
        return

    if len(args.n) != 1:
        parser.error("--outdir admite un solo N")

    n = args.n[0]
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    outs = [outdir / f"run_{seed:03d}.txt" for seed in seeds]

    # Evita sobrescribir trayectorias o mezclar metadatos de distintas corridas.
    reserved = [
        outdir / "summary.dat",
        outdir / "params.txt",
        outdir / "obstacles.txt",
        *outs,
    ]
    existing = [path for path in reserved if path.exists()]
    if existing:
        parser.error(
            f"la carpeta ya contiene resultados o metadatos: {existing[0]}. "
            "Usá otra carpeta para esta corrida."
        )

    # Ejecutar contra la copia conserva exactamente la configuración utilizada.
    obstacles = None
    if args.obstacles is not None:
        obstacles = outdir / "obstacles.txt"
        shutil.copyfile(args.obstacles, obstacles)

    (outdir / "params.txt").write_text(
        f"# {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
        f"exe {args.exe}\n"
        f"N {n}\n"
        f"r {args.r}\n"
        f"tmax {args.tmax}\n"
        f"k {args.k}\n"
        f"reps {args.reps}\n"
        f"jobs {args.jobs}\n"
        f"seeds {seeds[0]}..{seeds[-1]}\n"
        f"obstacles_source {args.obstacles or '-'}\n"
        f"obstacles_copy {obstacles or '-'}\n"
        f"cmd {shlex.join(sys.argv)}\n",
        encoding="utf-8",
    )

    def run_one(job: tuple[int, Path]) -> dict[str, str]:
        seed, out = job
        return run_engine(
            args.exe, n, args.r, seed,
            args.tmax, args.k, obstacles, out,
        )

    workers = min(args.jobs, args.reps)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = pool.map(run_one, zip(seeds, outs))

        for seed, out, summary in zip(seeds, outs, results):
            append_row(
                outdir / "summary.dat",
                "seed t90 Ng events engine_seconds",
                f"{seed} {summary['t90']} {summary['Ng']} "
                f"{summary['events']} {summary['engine_seconds']}",
            )

        print_run_summary(summary, seed, out)
    
    # Postprocesamiento: fuera de las mediciones del motor y una vez
    # terminadas todas las realizaciones.
    if args.preview == "first":
        create_previews(outs[:1])
    elif args.preview == "all":
        create_previews(outs)

    print(f"\nResultados disponibles en: {outdir}")

def create_previews(paths: list[Path]) -> None:
    for traj_path in paths:
        gif_path = traj_path.with_suffix(".gif")
        png_path = traj_path.with_suffix(".png")

        print(f"\nGenerando vista previa de {traj_path.name}...", flush=True)

        result = subprocess.run(
            [
                sys.executable,
                str(HERE / "animate.py"),
                "--traj", str(traj_path),
                "--out", str(gif_path),
                "--png", str(png_path),
            ],
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"No se pudo generar la vista previa de {traj_path}. "
                "Los archivos de simulación ya generados se conservan."
            )

        print(f"  Animación: {gif_path}")
        print(f"  Imagen:    {png_path}")
        
if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)