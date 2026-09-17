# TP3 — Simulación dirigida por eventos

Integrantes: Camila Lee, Matías Leporini, Ana Negre

## Motor

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
```

## Figuras

```bash
pip install -r python/requirements.txt
python python/make.py
```

Dumps en `data/` (lo que falte se omite):

```
data/wall.txt                      1.1  columnas: N time  (wall-clock, no del dump)
data/runs/t90/<x>/*.txt            1.2  una carpeta por valor explorado
data/runs/empty/*.txt              mesa vacía para la banda de 1.2
data/runs/msd/*.txt                1.3  una realización para el DCM
data/runs/configs/<nombre>/*.txt   1.3  D vs t90
data/sample_traj.txt               GIF
```

Ajuste del DCM: `python python/make.py --t-min 2 --t-max 20`

```
python/make.py       pipeline (tablas + figuras + GIF)
python/animate.py    animación suelta
python/lib/          dump, métricas, estilo de figuras
python/plotters/     figuras 1.1–1.3
```
