# Taller de Búsqueda Local: Ascenso de Colinas vs. Temple Simulado

Entregable del taller de búsqueda local aplicada al 8-puzzle,
Introducción a la Inteligencia Artificial, Universidad Sergio
Arboleda.

Equipo: Mario Jiménez, Juan David Andrade y Camilo Díaz.

Esta carpeta es **autosuficiente**: tiene todo lo necesario para
revisar el trabajo y volver a ejecutar el notebook, sin el resto del
repositorio. La fuente LaTeX del informe (`informe.tex`), las
capturas de código y el historial de desarrollo están en el
repositorio del equipo:
<https://github.com/CamiloDG07/Taller_Colina-Temple>

## Cómo usar este entregable

- **`informe.pdf`** es el documento de entrega formal: metodología
  (con la teoría y las fórmulas en el punto donde se usan),
  resultados, análisis y conclusiones.
- **`notebook/taller_8puzzle.ipynb`** es el punto de entrada para
  revisar y sustentar el trabajo, y el soporte técnico y reproducible
  de los resultados del informe. Al abrirlo y ejecutarlo (Run All):
  - carga las métricas ya calculadas de `resultados/datos/`;
  - muestra las figuras ya generadas de `resultados/figuras/`;
  - muestra el código fuente de cada módulo de `src/` como
    referencia, junto a la explicación de cada decisión.
- **Ejecutar el notebook tarda unos segundos**, porque NO recalcula el
  experimento: solo reporta resultados ya generados.
- **Para reproducir el experimento desde cero** (30 tableros x 10
  semillas), correr desde la raíz de esta carpeta:

  ```bash
  python src/experimentos.py
  ```

  Esto regenera los CSV de `resultados/datos/` y las figuras de
  `resultados/figuras/` que el notebook consume después. Por defecto
  tarda unos pocos minutos: corre la tabla principal y lee los
  barridos de T0/alpha y de K ya calculados en
  `resultados/datos/temple_barrido.csv` y
  `resultados/datos/reinicios_barrido_k.csv`. Para recalcular también
  los barridos completos, cambiar `RECALCULAR_BARRIDOS = True` en
  `src/experimentos.py`; así tarda unos 50 minutos.

## Contenido

```
entregable/
├── informe.pdf            informe formal
├── notebook/
│   └── taller_8puzzle.ipynb
├── src/                   código del experimento
│   ├── formulacion.py     estado, vecindad, h(s), resolubilidad
│   ├── ascenso.py         steepest, estocástico, reinicios
│   ├── temple.py          temple simulado
│   ├── visualizacion.py   tableros y gráficas
│   └── experimentos.py    pipeline completo
├── resultados/
│   ├── datos/             métricas en CSV
│   └── figuras/           figuras en PNG
├── requirements.txt
└── README.md
```

## Dependencias

```bash
pip install -r requirements.txt
```

Para abrir y ejecutar el notebook hace falta además Jupyter
(`pip install notebook`).
