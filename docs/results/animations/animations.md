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


## 1.3 Animaciones de difusión ?
