"""Tablas de texto: una fila de encabezado y columnas separadas por espacios.

Líneas vacías y comentarios (#) se ignoran. Es el formato de wall.txt,
summary.dat y de todas las tablas que escribe make.py.
"""

from pathlib import Path


def load_table(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    header = None
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if header is None:
                header = parts
                if not set(required).issubset(header):
                    raise ValueError(f"{path}: se esperaban las columnas {' '.join(required)}")
                continue
            raw = dict(zip(header, parts))
            missing = [key for key in required if not raw.get(key)]
            if missing:
                raise ValueError(f"{path}: falta {', '.join(missing)}")
            rows.append({key: raw[key] for key in required})
    if not rows:
        raise ValueError(f"{path}: no hay filas de datos")
    return rows