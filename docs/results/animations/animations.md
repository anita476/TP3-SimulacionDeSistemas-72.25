## Animations 


## 1.1 Animaciones según N 
```bash
./build/EventDrivenSim \
    -N 25 \
    -tmax 30 \
    -k 100 \
    -seed 1 \
    --out data/run_n25.txt

python3 python/animate.py \
    --traj data/run_n25.txt \
    --out results/animations/run_n25.gif \
    --png results/animations/run_n25.png
```

```bash
./build/EventDrivenSim \
    -N 300 \
    -tmax 30 \
    -k 100 \
    -seed 1 \
    --out data/run_n300.txt

python3 python/animate.py \
    --traj data/run_n300.txt \
    --out results/animations/run_n300.gif \
    --png results/animations/run_n300.png
```



## 1.2 Animaciones configuración final

Semilla 601, la primera del barrido del 1.2. tmax = 20 s cubre el t90 de las dos (12.01 s la pared, 16.27 s el disco). k = 100, igual que las de N. `--realtime --fps 30` deja el mp4 en 20 s: un segundo de video es un segundo de mesa.

```bash
printf '0.60 0.34 0.34\n' > data/runs/1.2/anim/disco_r034.txt

./build/EventDrivenSim \
    -N 100 -r 0.0175 -m 0.025 -v0 1 \
    -tmax 20 -k 100 -seed 601 \
    -obstacles data/runs/1.2/anim/disco_r034.txt \
    --out data/runs/1.2/anim/disco_r034_traj.txt

python3 python/animate.py \
    --traj data/runs/1.2/anim/disco_r034_traj.txt \
    --mp4 docs/presentation/animations/disco_r034.mp4 \
    --realtime --fps 30
```

La pared de 18 columnas sale de `pared.wall(18, 0.60, 0.0175)`: ancho 0.644 m, R = r.

```bash
python3 -c "import sys; sys.path.insert(0, 'python'); from pathlib import Path; from pared import wall, write_config; write_config(Path('data/runs/1.2/anim/pared_18_obstacles.txt'), wall(18, 0.60, 0.0175))"

./build/EventDrivenSim \
    -N 100 -r 0.0175 -m 0.025 -v0 1 \
    -tmax 20 -k 100 -seed 601 \
    -obstacles data/runs/1.2/anim/pared_18_obstacles.txt \
    --out data/runs/1.2/anim/pared_18_traj.txt

python3 python/animate.py \
    --traj data/runs/1.2/anim/pared_18_traj.txt \
    --mp4 docs/presentation/animations/pared_18.mp4 \
    --realtime --fps 30
```

## 1.3 Animaciones de difusión ?
