"""Observables offline a partir de una trayectoria.

t90 y el DCM se calculan después del dump, no en el loop del motor.
En 2D, ⟨Δr²⟩ = 4 D t.
"""

from traj import Traj


def t90(traj: Traj) -> float:
    for frame in traj.frames:
        if frame.ng / traj.n >= 0.9:
            return frame.t
    last = traj.frames[-1]
    raise ValueError(f"no alcanzó Fu=0.9 (Fu={last.ng / traj.n:.3f} en t={last.t})")


def msd_series(traj: Traj) -> list[tuple[float, float]]:
    origin = traj.frames[0].particles
    series = []
    for frame in traj.frames:
        acc = 0.0
        for particle, (x0, y0, *_rest) in zip(frame.particles, origin):
            dx = particle[0] - x0
            dy = particle[1] - y0
            acc += dx * dx + dy * dy
        series.append((frame.t, acc / traj.n))
    series.sort(key=lambda row: row[0])
    return series


def fit_line(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    if n < 2:
        raise ValueError("la ventana de ajuste necesita al menos 2 puntos")
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x == 0:
        raise ValueError("no hay variación en t para ajustar")
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = cov / var_x
    return slope, mean_y - slope * mean_x


def diffusion(slope: float) -> float:
    return slope / 4.0


def mean_std(values: list[float]) -> tuple[float, float]:
    if len(values) < 2:
        raise ValueError("se necesitan al menos 2 realizaciones")
    mean = sum(values) / len(values)
    var = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return mean, var ** 0.5
