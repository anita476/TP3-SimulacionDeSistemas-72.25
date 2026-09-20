"""Dump de trayectoria escrito por el motor.

    L <m>
    W <m>
    d <m>
    r <m>
    m <kg>                    opcional; permite calcular E(t) desde los cuadros
    N <int>
    O <xk> <yk> <Rk>          cero o más obstáculos
    t <s> Ng <int>
    <x> <y> <vx> <vy> <used>  N líneas; used es 0 (fresca) o 1 (usada)
    t ...                     siguiente cuadro

Líneas vacías y comentarios (#) se ignoran. Ng tiene que coincidir con
cuántas partículas tienen used=1 en ese cuadro. La partícula i es la
fila i de cada cuadro.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Frame:
    t: float
    ng: int
    particles: list[tuple[float, float, float, float, int]]  # x, y, vx, vy, used


@dataclass
class Traj:
    L: float
    W: float
    d: float
    r: float
    n: int
    obstacles: list[tuple[float, float, float]]
    frames: list[Frame]
    m: float | None = None



def _fail(path: str, lineno: int, msg: str) -> None:
    raise ValueError(f"{path}:{lineno}: {msg}")


def _tokens(path: str, lineno: int, line: str, expected: int) -> list[str]:
    parts = line.split()
    if len(parts) != expected:
        _fail(path, lineno, f"se esperaban {expected} campos, hay {len(parts)}: {line!r}")
    return parts


def read_traj(path: str | Path) -> Traj:
    path_s = str(path)
    rows: list[tuple[int, str]] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.split("#", 1)[0].strip()
            if line:
                rows.append((lineno, line))
    if not rows:
        raise ValueError(f"{path_s}: archivo vacío")

    header: dict[str, float] = {}
    n: int | None = None
    obstacles: list[tuple[float, float, float]] = []
    i = 0
    while i < len(rows) and rows[i][1].split()[0] != "t":
        lineno, line = rows[i]
        tag = line.split()[0]
        if tag in ("L", "W", "d", "r", "m"):
            header[tag] = float(_tokens(path_s, lineno, line, 2)[1])
        elif tag == "N":
            n = int(_tokens(path_s, lineno, line, 2)[1])
        elif tag == "O":
            _, x, y, radius = _tokens(path_s, lineno, line, 4)
            obstacles.append((float(x), float(y), float(radius)))
        else:
            _fail(path_s, lineno, f"etiqueta de encabezado desconocida {tag!r}")
        i += 1

    missing = [key for key in ("L", "W", "d", "r") if key not in header]
    if "m" in header and header["m"] <= 0: raise ValueError(f"{path_s}: m must be > 0, but is {header['m']}")
    if n is None:
        missing.append("N")
    if missing:
        raise ValueError(f"{path_s}: faltan en el encabezado: {', '.join(missing)}")
    assert n is not None
    for key in ("L", "W", "d", "r"):
        if header[key] <= 0:
            raise ValueError(f"{path_s}: {key} debe ser > 0, es {header[key]}")
    if n < 1:
        raise ValueError(f"{path_s}: N debe ser >= 1, es {n}")

    frames: list[Frame] = []
    while i < len(rows):
        lineno, line = rows[i]
        parts = _tokens(path_s, lineno, line, 4)
        if parts[0] != "t" or parts[2] != "Ng":
            _fail(path_s, lineno, f"se esperaba 't <s> Ng <int>', se obtuvo {line!r}")
        t, ng = float(parts[1]), int(parts[3])
        i += 1
        if i + n > len(rows):
            raise ValueError(f"{path_s}: cuadro truncado en t={t}")
        particles: list[tuple[float, float, float, float, int]] = []
        for _ in range(n):
            lineno, line = rows[i]
            x, y, vx, vy, used_s = _tokens(path_s, lineno, line, 5)
            used = int(used_s)
            if used not in (0, 1):
                _fail(path_s, lineno, f"used debe ser 0 o 1, no {used_s!r}")
            particles.append((float(x), float(y), float(vx), float(vy), used))
            i += 1
        used_count = sum(p[4] for p in particles)
        if used_count != ng:
            _fail(path_s, lineno, f"Ng={ng} pero {used_count} partículas usadas")
        frames.append(Frame(t, ng, particles))

    if not frames:
        raise ValueError(f"{path_s}: no hay cuadros")

    return Traj(header["L"], header["W"], header["d"], header["r"], n, obstacles, frames, header.get("m"))
