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

# USO INTERNO - completed so far

1. Collision.hpp/.cpp: collision *times* (particle-wall, particle-particle, particle-obstacle -> obstacle == resting particle) AND post-collision *velocities* (wall bounce, with impulse, and obstacle reflection v'=v-2(v*n)*n [formulas as presented in class]

2. Obstacle.hpp/.cpp: reads config file (one 'xk yk Rk' line per obstacle) and validates: 1. Rk >= r, 2. no overlap between obstacles (exactly touching is fine), 3. fully inside the table (touching wall is fine)

3. Geometry.hpp: added discs_overlap and disc_inside inside 

4. TESTS
- One test for different types of collisions and whether it detects properly the collisions
- Test for obstacles 

TO BUILD AND RUN THE TEST:
`cmake --build build -j && ctest --test-dir build --output-on-failure`
Should output: 100% tests passed

