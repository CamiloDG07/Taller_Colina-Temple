# Taller de Búsqueda Local: Ascenso de Colinas vs. Temple Simulado

Taller del curso de Introducción a la Inteligencia Artificial
(Universidad Sergio Arboleda) sobre búsqueda local aplicada al
8-puzzle. Se implementan y comparan tres variantes de ascenso de
colinas (más pronunciado, estocástico y con reinicios por
perturbación) contra temple simulado, con el mismo presupuesto de
evaluaciones de h(s) y 10 semillas por tablero.

## Contenido del repositorio

- `src/`: módulos con la lógica de los algoritmos.
  - `formulacion.py`: estado, vecindad, función objetivo h(s),
    resolubilidad y generación de tableros.
  - `ascenso.py`: steepest, estocástico y reinicios por perturbación
    (caminata aleatoria de K movimientos desde el tablero asignado).
  - `temple.py`: temple simulado con enfriamiento geométrico.
  - `visualizacion.py`: grid 3x3 del tablero y gráficas de
    comparación.
  - `experimentos.py`: pipeline completo sobre los 30 tableros de
    prueba: presupuesto compartido, barridos de T0/alpha y de K,
    tabla principal, CSV y figuras.
- `notebook/taller_8puzzle.ipynb`: reporta los resultados ya
  calculados (CSV y figuras); no recalcula los experimentos.
- `resultados/datos/`: métricas en CSV.
- `resultados/figuras/`: figuras en PNG, referenciadas desde el
  informe.
- `informe/`: informe en LaTeX con el estilo institucional.

## Cómo reproducir los resultados

1. Crear un entorno con las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

2. Correr el pipeline desde la raíz del repositorio:

   ```bash
   python src/experimentos.py
   ```

   Por defecto (`RECALCULAR_BARRIDOS = False` en `experimentos.py`)
   lee los barridos de T0/alpha y de K desde los CSV ya generados y
   solo corre la tabla principal: tarda unos pocos minutos. Con
   `RECALCULAR_BARRIDOS = True` recalcula también los barridos
   completos (unos 50 minutos); solo hace falta si cambia algo
   estructural (`T_MINIMO`, `ITERACIONES_POR_TEMPERATURA`, tableros,
   semillas o grillas). Si el presupuesto calculado no coincide con el
   de los barridos guardados, el pipeline se detiene y lo avisa.

3. Abrir `notebook/taller_8puzzle.ipynb` (requiere Jupyter) para ver
   las tablas y figuras. Corre en segundos.

4. Compilar el informe desde `informe/`:

   ```bash
   latexmk -pdf informe.tex
   ```

## Equipo

- Mario Jiménez
- Juan David Andrade
- Camilo Díaz
