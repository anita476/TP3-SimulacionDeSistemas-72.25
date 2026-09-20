"""Carpetas de realizaciones escritas por run.py.

    <carpeta>/run_<semilla>.txt   trayectorias (solo estos son dumps)
    <carpeta>/summary.dat         seed t90 Ng events engine_seconds; t90 = -1 si no llegó
    <carpeta>/params.txt          metadatos del runner
    <carpeta>/obstacles.txt       copia de la configuración, si la hubo

summary.dat manda: t90 y Ng vienen del motor, que los mide en el evento
exacto. Si falta, se leen de los dumps (todo gol se guarda, así que el
cuadro del gol 90 existe en cualquier dump).
"""

from dataclasses import dataclass
from math import nan
from pathlib import Path

from metrics import mean_std, t90_or_none
from tables import load_table
from traj import read_traj


@dataclass(frozen=True)
class Realization:
    seed: int
    t90: float | None  # None = no alcanzó Fu = 0.9 antes de tmax
    ng: int  # goles al final de la corrida


def dump_paths(folder: Path) -> list[Path]:
    return sorted(p for p in folder.glob("run_*.txt") if p.is_file())


def run_folders(root: Path) -> list[Path]:
    """Subcarpetas directas de root que contienen al menos un dump."""
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and dump_paths(p))


def _seed_from_name(path: Path) -> int:
    return int(path.stem.split("_", 1)[1])


def read_realizations(folder: Path) -> list[Realization]:
    summary = folder / "summary.dat"
    if summary.is_file():
        reals = []
        for row in load_table(summary, ("seed", "t90", "Ng")):
            t90 = float(row["t90"])
            reals.append(Realization(int(row["seed"]), t90 if t90 >= 0 else None, int(row["Ng"])))
        return reals
    reals = []
    for path in dump_paths(folder):
        traj = read_traj(path)
        reals.append(Realization(_seed_from_name(path), t90_or_none(traj), traj.frames[-1].ng))
    if not reals:
        raise ValueError(f"{folder}: no hay run_*.txt ni summary.dat")
    return reals


def t90_summary(reals: list[Realization]) -> tuple[float, float, float, int]:
    """(<t90>, desvío, <Ng final>, cuántas llegaron). <t90> es nan si ninguna llegó."""
    reached = [r.t90 for r in reals if r.t90 is not None]
    ng_mean = sum(r.ng for r in reals) / len(reals)
    if not reached:
        return nan, nan, ng_mean, 0
    mean, std = mean_std(reached)
    return mean, std, ng_mean, len(reached)