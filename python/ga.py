"""Búsqueda genética de la configuración de obstáculos que minimiza <t90>.

    python python/ga.py --outdir data/ga/run1 --pop 24 --gens 25 --jobs 8
    python python/ga.py --self-test

Evalúa cada layout con el motor (sin dump). Los parámetros físicos son los
fijos del enunciado 1.2 / 1.4; el CLI solo mueve el genético.

La población inicial no es uniforme en la mesa: incluye embudos y rieles que
apuntan a los arcos. Mutar y cruzar siguen siendo libres (sin simetría).
"""

from __future__ import annotations

import argparse
import math
import os
import random
import shlex
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "lib"))

from metrics import mean_std
from run import DEFAULT_EXE, run_engine

L = 1.20
W = 0.68
D = 0.20
N = 100
R_PARTICLE = 0.0175
TMAX = 100.0
DUMP_K = 0
MUT_P = 0.30
MOVE_SIGMA = 0.06
RADIUS_SIGMA = 0.02
CACHE_DECIMALS = 4
ELITE = 2
TOURNAMENT_K = 3
PLACE_FAIL = "no se pudo ubicar"
ENGINE_INVALID = (PLACE_FAIL, "overlaps", "Rk < r", "not inside table")
MID_Y = 0.5 * W
GOAL_HALF = 0.5 * D

Disc = tuple[float, float, float]
Config = list[Disc]


def discs_overlap(dx: float, dy: float, sum_radii: float) -> bool:
    return dx * dx + dy * dy < sum_radii * sum_radii


def disc_inside(x: float, y: float, radius: float) -> bool:
    return x >= radius and x <= L - radius and y >= radius and y <= W - radius


def blocks_goal(x: float, y: float, radius: float) -> bool:
    """True si el disco tapa el contacto de un gol (centro de partícula en el arco)."""
    step = GOAL_HALF / 3.0
    gy = MID_Y - GOAL_HALF
    while gy <= MID_Y + GOAL_HALF + 1e-12:
        if discs_overlap(x - R_PARTICLE, y - gy, radius + R_PARTICLE):
            return True
        if discs_overlap(x - (L - R_PARTICLE), y - gy, radius + R_PARTICLE):
            return True
        gy += step
    return False


def validate(config: Config) -> None:
    if len(config) < 1:
        raise ValueError("K debe ser >= 1")
    for i, (x, y, radius) in enumerate(config):
        where = f"obstáculo {i + 1}"
        if not math.isfinite(x) or not math.isfinite(y) or not math.isfinite(radius):
            raise ValueError(f"{where}: coordenadas y radio deben ser finitos")
        if radius < R_PARTICLE:
            raise ValueError(f"{where}: Rk < r")
        if not disc_inside(x, y, radius):
            raise ValueError(f"{where}: no está íntegramente en la mesa")
        for j in range(i):
            ox, oy, oradius = config[j]
            if discs_overlap(x - ox, y - oy, radius + oradius):
                raise ValueError(f"{where} solapa con el obstáculo {j + 1}")


def clamp_disc(x: float, y: float, radius: float) -> Disc:
    radius = min(max(radius, R_PARTICLE), L / 2.0, W / 2.0)
    x = min(max(x, radius), L - radius)
    y = min(max(y, radius), W - radius)
    return (x, y, radius)


def _clear_goal(x: float, y: float, radius: float) -> Disc | None:
    disc = clamp_disc(x, y, radius)
    for _ in range(12):
        if not blocks_goal(*disc):
            return disc
        x, y, radius = disc
        if x < 0.25 * L:
            x += 0.02
        elif x > 0.75 * L:
            x -= 0.02
        radius = max(R_PARTICLE, radius - 0.01)
        disc = clamp_disc(x, y, radius)
    return None


def random_disc(rng: random.Random) -> Disc:
    for _ in range(24):
        roll = rng.random()
        radius = rng.uniform(R_PARTICLE, 0.22 if roll < 0.25 else 0.12)
        if roll < 0.45:
            # Riel: cerca de una pared larga, para devolver hacia la altura del arco.
            y = radius + rng.uniform(0.0, 0.04)
            if rng.random() < 0.5:
                y = W - y
            x = rng.uniform(0.18, L - 0.18)
        elif roll < 0.80:
            # Costado del canal: fuera de la franja del arco, no tapando la boca.
            side = 1.0 if rng.random() < 0.5 else -1.0
            x = rng.uniform(0.20, L - 0.20)
            y = MID_Y + side * (GOAL_HALF + radius + rng.uniform(0.02, 0.10))
        else:
            x = rng.uniform(radius, L - radius)
            y = rng.uniform(radius, W - radius)
        cleared = _clear_goal(x, y, radius)
        if cleared is not None:
            return cleared
    return clamp_disc(rng.uniform(0.25, 0.95), rng.uniform(0.10, 0.24), rng.uniform(0.04, 0.08))


def _radius_clear_of(dx: float, dy: float, keep_r: float) -> float | None:
    """Mayor radio que no solapa con un disco de radio keep_r separado (dx, dy).

    sqrt puede dejar (R + keep_r)^2 un ulp por encima de dx^2+dy^2. El
    predicado de solape es estricto, así que sin ese paso se reasigna el
    mismo radio y el lazo no separa el par.
    """
    dist_sq = dx * dx + dy * dy
    if dist_sq <= 0.0:
        return None
    radius = math.sqrt(dist_sq) - keep_r
    while radius >= R_PARTICLE and discs_overlap(dx, dy, radius + keep_r):
        nxt = math.nextafter(radius, 0.0)
        if nxt == radius:
            return None
        radius = nxt
    if radius < R_PARTICLE:
        return None
    return radius


def _resolve_overlaps(config: Config) -> Config:
    discs = [clamp_disc(*disc) for disc in config]
    for _ in range(64):
        pair = None
        for i in range(len(discs)):
            for j in range(i):
                xi, yi, ri = discs[i]
                xj, yj, rj = discs[j]
                if discs_overlap(xi - xj, yi - yj, ri + rj):
                    pair = (i, j)
                    break
            if pair is not None:
                break
        if pair is None:
            return discs
        i, j = pair
        xi, yi, ri = discs[i]
        xj, yj, rj = discs[j]
        shrink, keep_r = (i, rj) if ri <= rj else (j, ri)
        new_r = _radius_clear_of(xi - xj, yi - yj, keep_r)
        if new_r is None:
            del discs[shrink]
        else:
            x, y, _old = discs[shrink]
            discs[shrink] = clamp_disc(x, y, new_r)
    # Si el shrink no separó, se borra el más chico del par que sigue solapado.
    leftover: Config = []
    for disc in discs:
        if any(discs_overlap(disc[0] - other[0], disc[1] - other[1], disc[2] + other[2]) for other in leftover):
            continue
        leftover.append(disc)
    return leftover


def _drop_goal_blockers(config: Config) -> Config:
    kept: Config = []
    for disc in config:
        cleared = _clear_goal(*disc)
        if cleared is not None:
            kept.append(cleared)
    return _resolve_overlaps(kept)


def repair(config: Config, rng: random.Random, k_max: int) -> Config:
    discs = _drop_goal_blockers(_resolve_overlaps(config))
    if k_max >= 1 and len(discs) > k_max:
        # El cruce concatena padres. Conservar los chicos borra los discos
        # que más desvían trayectorias; se quedan los de mayor radio.
        discs.sort(key=lambda disc: disc[2], reverse=True)
        discs = discs[:k_max]
        discs = _drop_goal_blockers(_resolve_overlaps(discs))
    if not discs:
        discs = [random_disc(rng)]
    validate(discs)
    return discs


def write_config(path: Path, config: Config) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{x:.17g} {y:.17g} {radius:.17g}\n" for x, y, radius in config),
        encoding="utf-8",
    )


def read_config(path: Path) -> Config:
    config: Config = []
    with path.open(encoding="utf-8") as stream:
        for lineno, raw in enumerate(stream, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 3:
                raise ValueError(f"{path}:{lineno}: se esperaban 3 campos xk yk Rk")
            try:
                x, y, radius = (float(part) for part in parts)
            except ValueError as error:
                raise ValueError(f"{path}:{lineno}: campo no numérico") from error
            config.append((x, y, radius))
    validate(config)
    return config


def fitness_of(t90s: list[float], ngs: list[float]) -> tuple[float, float, float, float, int]:
    reached_times = [t90 for t90 in t90s if t90 >= 0.0]
    ng_mean = sum(ngs) / len(ngs)
    reached = len(reached_times)
    if reached == len(t90s):
        t90_mean, t90_std = mean_std(reached_times)
        return t90_mean, t90_mean, t90_std, ng_mean, reached
    t90_mean, t90_std = (math.nan, math.nan)
    if reached_times:
        t90_mean, t90_std = mean_std(reached_times)
    return TMAX + (N - ng_mean) / N, t90_mean, t90_std, ng_mean, reached


def cache_key(config: Config | None, seeds: list[int]) -> tuple:
    discs = None
    if config is not None:
        discs = tuple(sorted(
            (round(x, CACHE_DECIMALS), round(y, CACHE_DECIMALS), round(radius, CACHE_DECIMALS))
            for x, y, radius in config
        ))
    return (discs, tuple(seeds))


def _place_fail_row() -> dict:
    return {
        "fitness": TMAX + 1.0,
        "t90_mean": math.nan,
        "t90_std": math.nan,
        "ng_mean": math.nan,
        "reached": 0,
    }


def _one_run(exe: Path, seed: int, obstacles: Path | None) -> tuple[float, float]:
    summary = run_engine(exe, N, R_PARTICLE, seed, TMAX, DUMP_K, obstacles, None)
    return float(summary["t90"]), float(summary["Ng"])


def evaluate_batch(
    configs: list[Config | None],
    exe: Path,
    seeds: list[int],
    jobs: int,
    cache: dict,
) -> list[dict]:
    rows: list[dict | None] = [None] * len(configs)
    pending: list[int] = []
    paths: dict[int, Path | None] = {}
    try:
        for i, config in enumerate(configs):
            key = cache_key(config, seeds)
            hit = cache.get(key)
            if hit is not None:
                rows[i] = hit
                continue
            if config is not None:
                try:
                    validate(config)
                except ValueError:
                    row = _place_fail_row()
                    cache[key] = row
                    rows[i] = row
                    continue
            pending.append(i)
            if config is None:
                paths[i] = None
                continue
            handle = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", prefix="ga_obs_", delete=False, encoding="utf-8",
            )
            tmp = Path(handle.name)
            handle.close()
            write_config(tmp, config)
            paths[i] = tmp

        work = [(i, seed) for i in pending for seed in seeds]
        gathered: dict[int, list[tuple[float, float]]] = {i: [] for i in pending}
        failed: set[int] = set()

        def run_job(item: tuple[int, int]) -> tuple[int, tuple[float, float] | None, BaseException | None]:
            i, seed = item
            try:
                return i, _one_run(exe, seed, paths[i]), None
            except RuntimeError as error:
                return i, None, error

        if work:
            with ThreadPoolExecutor(max_workers=min(jobs, len(work))) as pool:
                for i, pair, error in pool.map(run_job, work):
                    if error is not None:
                        if not any(token in str(error) for token in ENGINE_INVALID):
                            raise error
                        failed.add(i)
                    elif pair is not None:
                        gathered[i].append(pair)

        for i in pending:
            if i in failed or len(gathered[i]) != len(seeds):
                row = _place_fail_row()
            else:
                t90s = [t90 for t90, _ng in gathered[i]]
                ngs = [ng for _t90, ng in gathered[i]]
                fitness, t90_mean, t90_std, ng_mean, reached = fitness_of(t90s, ngs)
                row = {
                    "fitness": fitness,
                    "t90_mean": t90_mean,
                    "t90_std": t90_std,
                    "ng_mean": ng_mean,
                    "reached": reached,
                }
            cache[cache_key(configs[i], seeds)] = row
            rows[i] = row
    finally:
        for path in paths.values():
            if path is not None:
                path.unlink(missing_ok=True)
    return [row if row is not None else _place_fail_row() for row in rows]


def evaluate(
    config: Config | None,
    exe: Path,
    seeds: list[int],
    jobs: int,
    cache: dict,
) -> dict:
    return evaluate_batch([config], exe, seeds, jobs, cache)[0]


def funnel_pair(x: float, radius: float, gap: float) -> Config:
    y_lo = MID_Y - 0.5 * gap - radius
    y_hi = MID_Y + 0.5 * gap + radius
    return [(x, y_lo, radius), (x, y_hi, radius)]


def templates(rng: random.Random, k_max: int) -> list[Config]:
    """Layouts que canalizan hacia los arcos. El GA después los deforma libremente."""
    raw: list[Config] = []
    for x in (0.40, 0.60, 0.80):
        for radius in (0.16, 0.22):
            raw.append([(x, MID_Y, radius)])
    for x in (0.28, 0.40, 0.60, 0.80, 0.92):
        for radius in (0.06, 0.10):
            raw.append([(x, MID_Y, radius)])
    for x in (0.30, 0.45, 0.75, 0.90):
        for radius, gap in ((0.055, 0.22), (0.075, 0.24)):
            raw.append(funnel_pair(x, radius, gap))
    raw.append(funnel_pair(0.32, 0.07, 0.22) + funnel_pair(0.88, 0.07, 0.22))
    raw.append(funnel_pair(0.38, 0.08, 0.26) + funnel_pair(0.82, 0.08, 0.26))
    raw.append([
        (0.35, 0.08, 0.055),
        (0.85, 0.08, 0.055),
        (0.35, 0.60, 0.055),
        (0.85, 0.60, 0.055),
    ])
    out: list[Config] = []
    seen: set = set()
    for discs in raw:
        try:
            fixed = repair(discs, rng, k_max)
        except ValueError:
            continue
        key = cache_key(fixed, [])[0]
        if key in seen:
            continue
        seen.add(key)
        out.append(fixed)
    return out


def random_config(rng: random.Random, k_max: int) -> Config:
    count = rng.randint(1, min(4, k_max))
    return repair([random_disc(rng) for _ in range(count)], rng, k_max)


def unique_configs(configs: list[Config]) -> list[Config]:
    seen: set = set()
    out: list[Config] = []
    for config in configs:
        key = cache_key(config, [])[0]
        if key in seen:
            continue
        seen.add(key)
        out.append(config)
    return out


def fill_population(configs: list[Config], size: int, rng: random.Random, k_max: int) -> list[Config]:
    configs = unique_configs(configs)
    attempts = 0
    while len(configs) < size and attempts < size * 30:
        configs.append(random_config(rng, k_max))
        configs = unique_configs(configs)
        attempts += 1
    while len(configs) < size:
        configs.append(random_config(rng, k_max))
    return configs[:size]


def tournament(scored: list[tuple[Config, dict]], rng: random.Random) -> Config:
    picked = rng.sample(scored, min(TOURNAMENT_K, len(scored)))
    winner = min(picked, key=lambda item: item[1]["fitness"])
    return [disc for disc in winner[0]]


def crossover(a: Config, b: Config, rng: random.Random, k_max: int) -> Config:
    if rng.random() < 0.5:
        cut = rng.uniform(0.0, L)
        child = [disc for disc in a if disc[0] < cut]
        child.extend(disc for disc in b if disc[0] >= cut)
    else:
        cut = rng.uniform(0.0, W)
        child = [disc for disc in a if disc[1] < cut]
        child.extend(disc for disc in b if disc[1] >= cut)
    return repair(child, rng, k_max)


def mutate(config: Config, rng: random.Random, k_max: int) -> Config:
    discs = list(config)
    if discs and rng.random() < MUT_P:
        i = rng.randrange(len(discs))
        x, y, radius = discs[i]
        discs[i] = (x + rng.gauss(0.0, MOVE_SIGMA), y + rng.gauss(0.0, MOVE_SIGMA), radius)
    if discs and rng.random() < MUT_P:
        i = rng.randrange(len(discs))
        x, y, radius = discs[i]
        discs[i] = (x, y, radius + rng.gauss(0.0, RADIUS_SIGMA))
    if discs and rng.random() < MUT_P:
        i = rng.randrange(len(discs))
        discs[i] = random_disc(rng)
    if len(discs) < k_max and rng.random() < MUT_P:
        discs.append(random_disc(rng))
    if len(discs) > 1 and rng.random() < MUT_P:
        del discs[rng.randrange(len(discs))]
    return repair(discs, rng, k_max)


def local_neighbors(config: Config, rng: random.Random, k_max: int) -> list[Config]:
    steps = (
        (0.03, 0.0, 0.0),
        (-0.03, 0.0, 0.0),
        (0.0, 0.03, 0.0),
        (0.0, -0.03, 0.0),
        (0.0, 0.0, 0.015),
        (0.0, 0.0, -0.015),
    )
    neighbors: list[Config] = []
    for i, (x, y, radius) in enumerate(config):
        for dx, dy, d_r in steps:
            discs = list(config)
            discs[i] = (x + dx, y + dy, radius + d_r)
            try:
                neighbors.append(repair(discs, rng, k_max))
            except ValueError:
                continue
    return unique_configs(neighbors)


def polish(
    config: Config,
    exe: Path,
    seeds: list[int],
    jobs: int,
    cache: dict,
    rng: random.Random,
    k_max: int,
    rounds: int = 2,
) -> tuple[Config, dict]:
    best = config
    best_row = evaluate(best, exe, seeds, jobs, cache)
    for _ in range(rounds):
        candidates = [best, *local_neighbors(best, rng, k_max)]
        rows = evaluate_batch(candidates, exe, seeds, jobs, cache)
        ranked = sorted(zip(candidates, rows), key=lambda item: item[1]["fitness"])
        if ranked[0][1]["fitness"] + 1e-12 >= best_row["fitness"]:
            break
        best, best_row = ranked[0]
    return best, best_row


def _fmt(value: float) -> str:
    if isinstance(value, float) and math.isnan(value):
        return "nan"
    return f"{value:.6g}"


def _append_history(path: Path, gen: int, config: Config, row: dict) -> None:
    line = (
        f"{gen} {len(config)} {_fmt(row['fitness'])} {_fmt(row['t90_mean'])} "
        f"{_fmt(row['t90_std'])} {_fmt(row['ng_mean'])} {row['reached']}"
    )
    fresh = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8") as stream:
        if fresh:
            stream.write("gen K fitness t90_mean t90_std ng_mean reached\n")
        stream.write(line + "\n")


def _report(label: str, row: dict) -> str:
    if row["reached"] > 0 and not math.isnan(row["t90_mean"]):
        return (
            f"{label}: <t90> = {row['t90_mean']:.4g} ± {row['t90_std']:.4g} s "
            f"(alcanzaron {row['reached']}, <Ng> = {row['ng_mean']:.4g})"
        )
    return f"{label}: no alcanzó Fu=0.9; <Ng> = {row['ng_mean']:.4g}; fitness = {row['fitness']:.6g}"


def self_test() -> None:
    validate([(0.60, 0.34, 0.05), (0.71, 0.34, 0.05)])
    validate([(0.60, 0.34, R_PARTICLE)])
    validate([(1.15, 0.34, 0.05)])

    if not blocks_goal(0.05, MID_Y, 0.05):
        raise AssertionError("un disco sobre el arco izquierdo debería tapar el gol")
    if blocks_goal(0.60, MID_Y, 0.05):
        raise AssertionError("un disco central no tapa el arco")

    for bad in (
        [],
        [(0.60, 0.34, 0.01)],
        [(0.03, 0.34, 0.05)],
        [(0.60, 0.66, 0.05)],
        [(0.60, 0.34, 0.05), (0.66, 0.34, 0.05)],
    ):
        try:
            validate(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"validate debió fallar: {bad}")

    rng = random.Random(1)
    fixed = repair([(0.60, 0.34, 0.05), (0.66, 0.34, 0.05)], rng, 8)
    validate(fixed)
    if len(fixed) < 1:
        raise AssertionError("repair dejó K = 0")
    if any(blocks_goal(*disc) for disc in fixed):
        raise AssertionError("repair dejó un disco tapando un arco")

    blocked = repair([(0.05, MID_Y, 0.06)], rng, 8)
    if any(blocks_goal(*disc) for disc in blocked):
        raise AssertionError("repair no liberó la boca del arco")

    # El achique por hypot dejaba el solape por un ulp y se terminaba borrando el disco.
    hung = repair([
        (0.32704603460169224, 0.3956382026778946, 0.05258703546055486),
        (0.2506502400160179, 0.3242712405432818, 0.06283718845415559),
        (0.6747087561536526, 0.34482440974861217, 0.05951530305489934),
    ], rng, 8)
    validate(hung)
    if len(hung) != 3:
        raise AssertionError(f"el ulp de solape borró un disco: {hung}")

    trimmed = repair([
        (0.30, 0.20, 0.12),
        (0.90, 0.40, 0.10),
        (0.50, 0.15, 0.03),
        (0.70, 0.50, 0.03),
    ], rng, 2)
    if len(trimmed) != 2 or min(disc[2] for disc in trimmed) < 0.09:
        raise AssertionError(f"k_max descartó los discos grandes: {trimmed}")

    child = crossover(
        [(0.30, 0.34, 0.05)],
        [(0.90, 0.34, 0.05)],
        rng,
        8,
    )
    validate(child)

    seeds = templates(rng, 8)
    if len(seeds) < 8:
        raise AssertionError(f"pocos templates válidos: {len(seeds)}")
    for config in seeds:
        validate(config)

    fit, t90_mean, _std, _ng, reached = fitness_of([10.0, 12.0, 11.0, 9.0, 13.0], [90] * 5)
    if reached != 5 or abs(fit - t90_mean) > 1e-12 or abs(fit - 11.0) > 1e-12:
        raise AssertionError(f"fitness con t90 alcanzado: {fit}")
    fit, _t90, _std, ng_mean, reached = fitness_of([10.0, -1.0, 12.0, 11.0, 9.0], [80, 70, 90, 85, 75])
    if reached != 4 or ng_mean != 80.0:
        raise AssertionError(f"reached/Ng mal: {reached} {ng_mean}")
    expected = TMAX + (N - 80.0) / N
    if abs(fit - expected) > 1e-12 or fit <= 13.0:
        raise AssertionError(f"penalización 1.4 mal: {fit}")

    print("self-test: ok")


def resolve_exe(path: Path) -> Path:
    path = path.resolve()
    if path.is_file():
        return path
    exe = path.with_suffix(".exe")
    if exe.is_file():
        return exe
    raise SystemExit(f"no existe {path}; compilá con cmake --build build")


def run_search(args: argparse.Namespace) -> None:
    exe = resolve_exe(args.exe)

    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    history = outdir / "history.csv"
    params = outdir / "params.txt"
    best_path = outdir / "best.txt"
    reserved = [history, params, best_path]
    existing = [path for path in reserved if path.exists()]
    if existing:
        raise SystemExit(f"la carpeta ya contiene resultados: {existing[0]}")

    last_confirm = args.seed + 100 + args.reps - 1
    if args.seed < 0 or last_confirm > 2**31 - 1:
        raise SystemExit("las semillas deben estar entre 0 y 2147483647")

    search_seeds = list(range(args.seed, args.seed + args.reps))
    confirm_seeds = list(range(args.seed + 100, args.seed + 100 + args.reps))
    rng = random.Random(args.seed)
    cache: dict = {}
    print(f"motor {exe}  pop={args.pop} gens={args.gens} reps={args.reps} jobs={args.jobs}", flush=True)

    population: list[Config] = []
    for path in args.seed_config:
        population.append(read_config(path.resolve()))
    population.extend(templates(rng, args.k_max))
    population = fill_population(population, args.pop, rng, args.k_max)
    print(f"población inicial: {len(population)} configs", flush=True)

    scored: list[tuple[Config, dict]] = []
    for gen in range(args.gens):
        if gen == 0:
            current = population
        else:
            current = [config for config, _row in scored[:ELITE]]
            bred: list[Config] = []
            while len(current) + len(bred) < args.pop:
                a = tournament(scored, rng)
                b = tournament(scored, rng)
                bred.append(mutate(crossover(a, b, rng, args.k_max), rng, args.k_max))
            current = fill_population(current + bred, args.pop, rng, args.k_max)

        print(f"evaluando gen {gen + 1}/{args.gens} ({len(current)} configs × {len(search_seeds)} reps)...", flush=True)
        rows = evaluate_batch(current, exe, search_seeds, args.jobs, cache)
        scored = list(zip(current, rows))
        for config, row in scored:
            _append_history(history, gen, config, row)
        scored.sort(key=lambda item: item[1]["fitness"])
        best_fit = scored[0][1]["fitness"]
        print(
            f"gen {gen + 1}/{args.gens}  best_fitness={best_fit:.6g}  "
            f"K={len(scored[0][0])}  <t90>={_fmt(scored[0][1]['t90_mean'])}",
            flush=True,
        )

    finalists = [config for config, _row in scored[:6]]
    polished, polish_row = polish(
        scored[0][0], exe, search_seeds, args.jobs, cache, rng, args.k_max,
    )
    _append_history(history, args.gens, polished, polish_row)
    candidates = unique_configs([*finalists, polished])
    print(f"confirmando {len(candidates)} candidatas + mesa vacía...", flush=True)
    confirm_rows = evaluate_batch(candidates, exe, confirm_seeds, args.jobs, cache)
    empty = evaluate(None, exe, confirm_seeds, args.jobs, cache)
    ranked = sorted(zip(candidates, confirm_rows), key=lambda item: item[1]["fitness"])
    winner, confirm = ranked[0]

    write_config(best_path, winner)
    shipped = ROOT / "configs" / "ga_best.txt"
    write_config(shipped, winner)

    params.write_text(
        f"# {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
        f"exe {exe}\n"
        f"N {N}\n"
        f"L {L}\n"
        f"W {W}\n"
        f"d {D}\n"
        f"r {R_PARTICLE}\n"
        f"tmax {TMAX}\n"
        f"pop {args.pop}\n"
        f"gens {args.gens}\n"
        f"reps {args.reps}\n"
        f"jobs {args.jobs}\n"
        f"k_max {args.k_max}\n"
        f"search_seeds {search_seeds[0]}..{search_seeds[-1]}\n"
        f"confirm_seeds {confirm_seeds[0]}..{confirm_seeds[-1]}\n"
        f"winner_K {len(winner)}\n"
        f"winner_fitness {confirm['fitness']}\n"
        f"winner_t90_mean {confirm['t90_mean']}\n"
        f"winner_t90_std {confirm['t90_std']}\n"
        f"winner_ng_mean {confirm['ng_mean']}\n"
        f"winner_reached {confirm['reached']}\n"
        f"empty_fitness {empty['fitness']}\n"
        f"empty_t90_mean {empty['t90_mean']}\n"
        f"empty_t90_std {empty['t90_std']}\n"
        f"empty_ng_mean {empty['ng_mean']}\n"
        f"empty_reached {empty['reached']}\n"
        f"best {best_path}\n"
        f"configs_copy {shipped}\n"
        f"cmd {shlex.join(sys.argv)}\n",
        encoding="utf-8",
    )

    print(_report("ganador (semillas de confirmación)", confirm))
    print(_report("mesa vacía (mismas semillas)", empty))
    if empty["fitness"] + 1e-12 < confirm["fitness"]:
        print("aviso: la mesa vacía ganó en confirmación; el layout no mejora t90 en esas semillas")
    print(f"best.txt: {best_path}")
    print(f"copia:    {shipped}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--outdir", type=Path, help="carpeta de history.csv, params.txt y best.txt")
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--pop", type=int, default=24)
    parser.add_argument("--gens", type=int, default=25)
    parser.add_argument("--reps", type=int, default=5, help="realizaciones por evaluación (default 5)")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--k-max", type=int, default=8, dest="k_max")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--seed-config", type=Path, action="append", default=[])
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return
    if args.outdir is None:
        parser.error("--outdir es obligatorio salvo con --self-test")
    if args.pop < 2:
        parser.error("--pop debe ser >= 2")
    if args.gens < 1:
        parser.error("--gens debe ser >= 1")
    if args.reps < 1:
        parser.error("--reps debe ser >= 1")
    if args.jobs < 1:
        parser.error("--jobs debe ser >= 1")
    if args.k_max < 1:
        parser.error("--k-max debe ser >= 1")
    if args.pop < ELITE:
        parser.error(f"--pop debe ser >= {ELITE} (elitismo)")

    run_search(args)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
