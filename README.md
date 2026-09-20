# TP3 — Simulación dirigida por eventos: Billar-Metegol

Integrantes: Camila Lee, Matías Leporini, Ana Negre

## Requisitos y compilación

Ejecutar desde la raíz del proyecto:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j

python3 -m pip install -r python/requirements.txt
```

## Configuración de la simulación

### Parámetros del sistema

| Parámetro | Valor predeterminado | Descripción |
|---|---|---|
| `-L` | `1.20` | Largo de la mesa (m) |
| `-W` | `0.68` | Ancho de la mesa (m) |
| `-d` | `0.20` | Ancho de cada arco, centrado en las paredes cortas (m) |
| `-N` | `100` | Cantidad de partículas |
| `-r` | `0.0175` | Radio de las partículas (m) |
| `-m` | `0.025` | Masa de cada partícula (kg) |
| `-v0` | `1.0` | Rapidez inicial (m/s) |
| `-tmax` | `30` | Tiempo simulado máximo (s) |
| `-k` | `200` | Frecuencia de guardado: cada k colisiones físicas |
| `-seed` | `1` | Semilla del generador |
| `-obstacles` | — | Archivo de configuración de obstáculos |
| `--out` | — | Archivo de trayectoria; crea la carpeta si hace falta |
| `--raw` | desactivado | Resumen en formato `clave valor` para scripts |

Con `-k 0` se guardan únicamente el estado inicial y los goles.
Con `-k > 0` se guardan además cuadros cada k colisiones físicas.

### Configuración de obstáculos

Cada línea contiene las coordenadas del centro y el radio, en metros:
```text
0.60 0.34 0.05
0.30 0.20 0.02
```
El lector admite líneas vacías y comentarios con `#`.
Los obstáculos deben satisfacer las restricciones geométricas
implementadas en `validate_obstacles()` - R_k >= r y dentro de la mesa.

## Ejecución de la simulación

### Una realización

```bash
./build/EventDrivenSim \
    -N 100 \
    -tmax 100 \
    -k 100 \
    -seed 1 \
    -obstacles configs/obstacles_test.txt \
    --out data/run.txt
```

Para simular una mesa sin obstáculos, omitir `-obstacles`.

### Múltiples realizaciones

`run.py` ejecuta el motor con una semilla distinta por realización.
Las semillas son `seed`, `seed + 1`, ..., `seed + reps - 1`.

```bash
python3 python/run.py \
    --outdir data/runs/empty \
    --n 100 \
    --reps 5 \
    --seed 1 \
    --tmax 100 \
    --k 100
```

| Opción del runner | Default | Descripción |
|---|---|---|
| `--n` | `100` | Cantidad de partículas; admite varios valores con `--wall` |
| `--r` | `0.0175` | Radio de partícula (m) |
| `--reps` | `5` | Realizaciones por valor de N |
| `--seed` | `1` | Primera semilla |
| `--tmax` | `100` | Tiempo simulado máximo (s) |
| `--k` | `0` | Frecuencia de guardado; independiente del default del ejecutable |
| `--obstacles` | — | Archivo de obstáculos |
| `--jobs` | núcleos disponibles | Realizaciones concurrentes con `--outdir` |
| `--preview` | `first` | Generar vistas previas de la primera realización, todas o ninguna |
| `--exe` | `build/EventDrivenSim` | Ejecutable del motor |

Usar una carpeta nueva para cada experimento. El runner evita sobrescribir sus archivos de resultados y metadatos.

### Archivos de salida

```text
data/runs/empty/
    run_001.txt
    run_001.gif
    run_001.png
    run_002.txt
    ...
    summary.dat
    params.txt
    obstacles.txt
```

- `run_<semilla>.txt`: trayectoria de una realización.
- `summary.dat`: columnas `seed t90 Ng events engine_seconds`.
- `data/wall.txt` (modo `--wall`): columnas `N events wall_events pair_events time`; `time` es el tiempo del motor (cola inicial + loop de eventos), sin generación de la condición inicial ni escritura de archivos.
- `params.txt`: parámetros del runner, semillas, comando y commit.
- `obstacles.txt`: copia de la configuración, solo si se proporcionó.
- GIF y PNG: vistas previas, según `--preview`.

## Animación de las trayectorias
Por defecto, `run.py` llama a `animate.py` después de terminar todas las realizaciones y genera un GIF y un PNG de la primera.

```bash
# Vista previa de cada realización.
python3 python/run.py \
    --outdir data/runs/previews \
    --reps 3 --tmax 10 --k 100 --preview all
```
Usar `--preview none` para guardar únicamente los datos y resúmenes.

También puede animarse una trayectoria existente sin repetir la simulación:

```bash
python3 python/animate.py \
    --traj data/runs/empty/run_001.txt \
    --out data/runs/empty/run_001.gif \
    --png data/runs/empty/run_001.png
```

Para abrir una ventana interactiva:

```bash
python3 python/animate.py \
    --traj data/runs/empty/run_001.txt \
    --show
```

## Verificación de la simulación
### Tests automatizados

```bash
ctest --test-dir build --output-on-failure
```
TODO: capaz agregar un tester en python para ver si el output de los archivos es correcto (particulas dentro de la mesa y no hay solapamiento en ningun momento, que una particula usada no vuelva a frescaetc.)

### Conservación de la energía
TODO!!!

## Análisis de resultados
`make.py` lee los datos existentes y genera tablas y figuras. No ejecuta nuevamente el motor.

### Experimentos de entrada

Mesa sin obstáculos:

```bash
python3 python/run.py \
    --outdir data/runs/empty \
    --reps 5 --tmax 100 --k 100
```

Un punto del barrido de configuración:

```bash
python3 python/run.py \
    --outdir data/runs/t90/0.60 \
    --obstacles configs/x0.60.txt \
    --reps 5 --tmax 100 --k 100
```

Una realización para el desplazamiento cuadrático medio:

```bash
python3 python/run.py \
    --outdir data/runs/msd \
    --reps 1 --tmax 30 --k 20
```

### Generación de tablas y figuras

```bash
python3 python/make.py
```

Para elegir la ventana de ajuste del desplazamiento cuadrático medio:

```bash
python3 python/make.py --t-min 2 --t-max 20
```

Estructura esperada:

```text
data/wall.txt                          rendimiento: N events wall_events pair_events time
data/runs/t90/<x>/run_*.txt             barrido de t90
data/runs/empty/run_*.txt               referencia sin obstáculos
data/runs/msd/run_*.txt                 DCM
data/runs/configs/<nombre>/run_*.txt    comparación D vs. t90
```

## Evaluación del rendimiento computacional

```bash
python3 python/run.py \
    --wall data/wall.txt \
    --n 50 100 200 300 \
    --reps 10 \
    --tmax 30
```

## Estructura del proyecto

```text
src/                  motor de simulación
configs/              configuraciones de obstáculos
tests/                tests del motor
python/run.py         ejecución de realizaciones y previews
python/analyze.py     tablas y figuras de análisis
python/animate.py     animación independiente
python/lib/           lectura, métricas, chequeos y estilo
python/plotters/      generación de figuras
data/                 resultados generados
```
## Visualizaciones

Todas salen de `animate.py` y leen únicamente el dump. Cada cuadro es un evento (cada k eventos o un gol); `--fps` es solo la velocidad de reproducción, no un dt de la simulación. La animación no muestra tiempos; solo Ng y Fu.

| Opción | Qué agrega |
|---|---|
| (siempre) | Mesa, arcos (verde), obstáculos (gris), partículas frescas (azul) y usadas (rojo); arriba, Ng y Fu del cuadro |
| (siempre) | Anillo sobre la partícula que acaba de hacer un gol y arco resaltado en ese cuadro |
| `--inset` | Inset con Fu(t) que crece con la animación, con la línea Fu = 0.9 |
| `--arrows` | Flechas de velocidad (vx, vy exactas del cuadro). Útil con pocas partículas; con N = 100 tapan la mesa |
| `--frame N` | Cuadro del PNG; `0` es la condición inicial (default: el del medio) |
| `--mp4 ARCHIVO` | Video MP4 con ffmpeg, formato para YouTube/Vimeo. `--out` sigue generando GIF |
| `--fps N` | Cuadros por segundo de reproducción (default 8) |

### Versiones de la animación

Todas parten del mismo dump; solo cambian las opciones. `RUN` es una trayectoria, por ejemplo `data/runs/t90/0.60/run_001.txt`.

| Versión | Opciones | Para qué |
|---|---|---|
| Básica | (ninguna) | Mesa, arcos, obstáculos, partículas, Ng y Fu. Es la que genera `run.py` como vista previa |
| Con Fu(t) | `--inset` | Ver cuándo se alcanza Fu = 0.9 mientras corre la animación |
| Con flechas | `--arrows` | Dirección y módulo de la velocidad; solo con pocas partículas |
| Todo incluido | `--inset --arrows` | Demo con pocas partículas: choques y Fu(t) |

```bash
# Básica: GIF y PNG del cuadro del medio
python3 python/animate.py --traj RUN --out anim.gif --png cuadro.png

# Con Fu(t)
python3 python/animate.py --traj RUN --inset --mp4 anim.mp4

# Con flechas (pocas partículas)
python3 python/animate.py --traj RUN --arrows --mp4 anim.mp4

# Video para la presentación (misma figura que el PNG)
python3 python/animate.py --traj RUN --mp4 anim.mp4 --fps 12

# Todo incluido
python3 python/animate.py --traj RUN --inset --arrows --mp4 anim.mp4 --fps 10

# Un cuadro en particular: la condición inicial (0) o el primer gol
python3 python/animate.py --traj RUN --png inicial.png --frame 0
python3 python/animate.py --traj RUN --png gol.png --frame 1

# Ventana interactiva
python3 python/animate.py --traj RUN --show
```

Demo con pocas partículas guardando todos los eventos (`-k 1`), para mostrar los tres tipos de choque con todo incluido:

```bash
./build/EventDrivenSim -N 12 -tmax 3 -k 1 -seed 4 \
    -obstacles configs/x0.60.txt --out data/demo.txt
python3 python/animate.py --traj data/demo.txt \
    --inset --arrows --mp4 data/figs/demo.mp4 --fps 10
```

El MP4 requiere `ffmpeg`.
