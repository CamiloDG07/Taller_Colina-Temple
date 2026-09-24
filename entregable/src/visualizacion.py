"""Visualizacion del tablero y graficas de comparacion."""

import math
import os

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter, MultipleLocator, NullFormatter

from formulacion import distancia_manhattan

DIRECTORIO_FIGURAS = os.path.join(
    os.path.dirname(__file__), "..", "resultados", "figuras")

# Paleta Okabe-Ito. El septimo color es negro en vez del amarillo
# original, que casi no contrasta con el fondo blanco en las lineas.
PALETA_CATEGORICA = [
    "#0072B2", "#E69F00", "#009E73", "#D55E00",
    "#CC79A7", "#56B4E9", "#000000",
]

COLOR_FICHA = "#0072B2"
COLOR_VACIO = "#E5E5E5"


def _paleta_categorica(cantidad):
    """Primeros `cantidad` colores de la paleta, siempre en el mismo
    orden (identidad de la serie, no un ciclo aleatorio)."""
    if cantidad > len(PALETA_CATEGORICA):
        raise ValueError("faltan colores en la paleta categorica")
    return PALETA_CATEGORICA[:cantidad]


def _paso_redondo(valor_minimo, valor_maximo, cantidad_deseada=5):
    """Calcula un paso de eje "redondo" (1, 2 o 5 por potencia de 10)
    para que los ticks queden en incrementos como 0, 10, 20, ..."""
    rango = valor_maximo - valor_minimo
    if rango <= 0:
        return 1
    paso_crudo = rango / cantidad_deseada
    magnitud = 10 ** math.floor(math.log10(paso_crudo))
    residuo = paso_crudo / magnitud
    if residuo < 1.5:
        paso = 1 * magnitud
    elif residuo < 3:
        paso = 2 * magnitud
    elif residuo < 7:
        paso = 5 * magnitud
    else:
        paso = 10 * magnitud
    return paso


def _quitar_bordes_superiores(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def dibujar_tablero(estado, ax=None, titulo=None):
    """Dibuja el 8-puzzle como una cuadricula 3x3.

    Si se pasa un eje de matplotlib existente se dibuja sobre el
    (util para componer varios paneles); si no, se crea uno propio.
    La casilla vacia se sombrea distinto y no lleva numero.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(3, 3))

    for indice, ficha in enumerate(estado):
        fila, columna = divmod(indice, 3)
        fila_dibujo = 2 - fila
        color = COLOR_VACIO if ficha == 0 else COLOR_FICHA
        rectangulo = Rectangle(
            (columna, fila_dibujo), 1, 1,
            facecolor=color, edgecolor="white", linewidth=2)
        ax.add_patch(rectangulo)
        if ficha != 0:
            ax.text(
                columna + 0.5, fila_dibujo + 0.5, str(ficha),
                ha="center", va="center", fontsize=18,
                color="white", fontweight="bold")

    ax.set_xlim(0, 3)
    ax.set_ylim(0, 3)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for lado in ax.spines.values():
        lado.set_visible(False)
    if titulo:
        ax.set_title(titulo)
    return ax


def comparar_antes_despues(estado_inicial, estado_final, titulo=None):
    """Dos tableros lado a lado (antes/despues) con su h(s) cada uno."""
    fig, ejes = plt.subplots(1, 2, figsize=(6, 3.6))
    h_inicial = distancia_manhattan(estado_inicial)
    h_final = distancia_manhattan(estado_final)
    dibujar_tablero(
        estado_inicial, ax=ejes[0], titulo=f"Antes (h = {h_inicial})")
    dibujar_tablero(
        estado_final, ax=ejes[1], titulo=f"Despues (h = {h_final})")
    if titulo:
        fig.suptitle(titulo)
    fig.tight_layout()
    return fig


def grafico_barras_comparacion(
        nombres_config, valores, titulo, etiqueta_y, errores=None):
    """Barras para comparar una metrica entre configuraciones.

    Si se pasa `errores` (por ejemplo, la desviacion estandar entre
    semillas), se dibuja como barra de error sobre cada barra.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    colores = _paleta_categorica(len(nombres_config))
    posiciones = list(range(len(nombres_config)))
    ax.bar(posiciones, valores, color=colores, edgecolor="white",
           yerr=errores, capsize=5 if errores is not None else 0,
           error_kw={"ecolor": "#333333", "elinewidth": 1.2})
    ax.set_xticks(posiciones)
    ax.set_xticklabels(nombres_config, rotation=15, ha="right")
    ax.set_ylabel(etiqueta_y)
    ax.set_title(titulo)
    tope = max(valores)
    if errores is not None:
        tope = max(v + e for v, e in zip(valores, errores))
    # Valor escrito sobre cada barra, para que las barras en cero o
    # casi cero (steepest, estocastico) tambien se lean.
    for posicion, valor, error in zip(
            posiciones, valores, errores or [0] * len(valores)):
        ax.text(posicion, valor + error + 0.02 * tope, f"{valor:.1f}",
                ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, tope * 1.12)
    paso = _paso_redondo(0, tope)
    ax.yaxis.set_major_locator(MultipleLocator(paso))
    _quitar_bordes_superiores(ax)
    fig.tight_layout()
    return fig


def grafico_traza_temple(traza, titulo=None):
    """h_actual y h_mejor contra el paso de enfriamiento."""
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    pasos = list(range(len(traza)))
    h_actual = [punto.h_actual for punto in traza]
    h_mejor = [punto.h_mejor for punto in traza]

    ax.plot(pasos, h_actual, color=PALETA_CATEGORICA[0],
            linewidth=2, label="h actual")
    ax.plot(pasos, h_mejor, color=PALETA_CATEGORICA[1],
            linewidth=2, label="h mejor")

    ax.set_xlabel("Nivel de temperatura (valor al final de cada nivel)")
    ax.set_ylabel("h(s)")
    ax.set_title(titulo or "Evolucion de h durante el temple simulado")
    ax.legend()

    paso_y = _paso_redondo(0, max(h_actual + h_mejor))
    ax.yaxis.set_major_locator(MultipleLocator(paso_y))
    paso_x = _paso_redondo(0, len(pasos))
    ax.xaxis.set_major_locator(MultipleLocator(max(paso_x, 1)))
    ax.set_ylim(0, None)
    _quitar_bordes_superiores(ax)
    fig.tight_layout()
    return fig


def grafico_efecto_parametro(
        valores_parametro, series, etiqueta_x, titulo,
        etiqueta_series=None, desviaciones=None, linea_vertical=None,
        x_categorico=False, marcas_x=None):
    """Efecto de un parametro sobre la tasa de exito.

    `series` es un diccionario {nombre_serie: lista_tasa_exito}. Con
    una sola entrada se grafica una linea simple (efecto de T0 o de
    alpha por separado); con varias entradas se grafica una curva por
    serie (por ejemplo, una curva por cada T0, para el experimento de
    interaccion T0/alpha), en vez de un mapa de calor.

    `desviaciones` es opcional, con las mismas claves que `series`, y
    se dibuja como barras de error (desviacion entre semillas).
    `linea_vertical` es opcional, una tupla (x, etiqueta) que marca un
    umbral sobre el eje x.

    Con `x_categorico=True` los valores del parametro se ubican
    equiespaciados y cada marca del eje es el valor exacto probado
    (util cuando la grilla no es uniforme, como alpha = 0.99, 0.995,
    0.998, que en un eje lineal quedarian encimados). `marcas_x` fija
    las marcas del eje x en un eje numerico.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    nombres_series = list(series.keys())
    colores = _paleta_categorica(len(nombres_series))
    if x_categorico:
        posiciones_x = list(range(len(valores_parametro)))
    else:
        posiciones_x = valores_parametro
    for color, nombre in zip(colores, nombres_series):
        ax.plot(
            posiciones_x, series[nombre], color=color,
            linewidth=2, marker="o", markersize=5, label=nombre)
        if desviaciones is not None and nombre in desviaciones:
            ax.errorbar(
                posiciones_x, series[nombre],
                yerr=desviaciones[nombre], fmt="none", ecolor=color,
                elinewidth=1.2, capsize=4)

    if x_categorico:
        ax.set_xticks(posiciones_x)
        ax.set_xticklabels([f"{v:g}" for v in valores_parametro])
    elif marcas_x is not None:
        ax.set_xticks(marcas_x)
        ax.set_xticklabels([f"{v:g}" for v in marcas_x])

    if linea_vertical is not None:
        posicion, etiqueta_linea = linea_vertical
        ax.axvline(posicion, color="#555555", linestyle="--",
                   linewidth=1.2, label=etiqueta_linea)

    ax.set_xlabel(etiqueta_x)
    ax.set_ylabel("Tasa de exito (%)")
    ax.set_title(titulo)
    if len(nombres_series) > 1:
        # Muchas series: leyenda fuera del area de datos.
        ax.legend(title=etiqueta_series, loc="upper left",
                  bbox_to_anchor=(1.01, 1.0))
    elif linea_vertical is not None:
        ax.legend(loc="lower right")

    ax.set_ylim(0, 100)
    ax.yaxis.set_major_locator(MultipleLocator(_paso_redondo(0, 100)))
    _quitar_bordes_superiores(ax)
    fig.tight_layout()
    return fig


def grafico_exito_vs_presupuesto(series, presupuesto, titulo):
    """Porcentaje de corridas resueltas con a lo sumo x evaluaciones.

    `series` es un diccionario {nombre: (evaluaciones_resueltas,
    total_corridas)}, donde evaluaciones_resueltas tiene las
    evaluaciones que gasto cada corrida que llego a h = 0. Una linea
    vertical marca el presupuesto compartido de la tabla principal.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    nombres_series = list(series.keys())
    colores = _paleta_categorica(len(nombres_series))
    tope_x = presupuesto
    for color, nombre in zip(colores, nombres_series):
        evaluaciones, total = series[nombre]
        ordenadas = sorted(evaluaciones)
        tope_x = max([tope_x] + ordenadas)
        eje_x = [0] + ordenadas
        eje_y = [100.0 * i / total for i in range(len(eje_x))]
        ax.step(eje_x, eje_y, where="post", color=color,
                linewidth=2, label=nombre)
        ax.hlines(eje_y[-1], eje_x[-1], tope_x * 1.05, color=color,
                  linewidth=2)

    ax.axvline(presupuesto, color="#555555", linestyle="--",
               linewidth=1.2,
               label=f"Presupuesto compartido ({presupuesto})")
    ax.set_xlabel("Evaluaciones de h(s)")
    ax.set_ylabel("Corridas resueltas (%)")
    ax.set_title(titulo)
    ax.legend(loc="upper left")
    ax.set_xlim(0, tope_x * 1.05)
    ax.set_ylim(0, 100)
    ax.yaxis.set_major_locator(MultipleLocator(_paso_redondo(0, 100)))
    ax.xaxis.set_major_locator(
        MultipleLocator(_paso_redondo(0, tope_x * 1.05)))
    _quitar_bordes_superiores(ax)
    fig.tight_layout()
    return fig


def grafico_h_por_tablero(series, titulo):
    """h(s) por tablero para varias configuraciones.

    `series` es un diccionario {nombre: lista_h}, una entrada por
    tablero en el mismo orden. Sirve para comparar, tablero a tablero,
    donde termina cada algoritmo (por ejemplo, steepest contra temple
    con alpha muy pequeno).
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    nombres_series = list(series.keys())
    colores = _paleta_categorica(len(nombres_series))
    marcadores = ["o", "s", "^", "D", "v", "P", "X"]
    for color, marcador, nombre in zip(colores, marcadores, nombres_series):
        valores = series[nombre]
        tableros = list(range(1, len(valores) + 1))
        ax.plot(tableros, valores, color=color, linewidth=1.2,
                marker=marcador, markersize=5, label=nombre)

    tope = max(max(v) for v in series.values())
    ax.set_xlabel("Tablero")
    ax.set_ylabel("h(s)")
    ax.set_title(titulo)
    ax.set_ylim(0, tope * 1.08)
    ax.yaxis.set_major_locator(MultipleLocator(_paso_redondo(0, tope)))
    cantidad = len(series[nombres_series[0]])
    ax.set_xlim(0.5, cantidad + 0.5)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2,
              frameon=False)
    _quitar_bordes_superiores(ax)
    fig.tight_layout()
    return fig


def grafico_longitud_vs_k(valores_k, longitudes, diametro, referencias,
                          titulo):
    """Longitud promedio de la solucion de reinicios segun K.

    Una linea horizontal marca el diametro del espacio de estados (la
    solucion optima nunca es mas larga) y `referencias` agrega lineas
    horizontales {nombre: longitud} de otros algoritmos. El eje y es
    logaritmico (ticks 10, 100, 1000, ...) porque las longitudes
    abarcan varios ordenes de magnitud.
    """
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    colores = _paleta_categorica(1 + len(referencias))
    ax.plot(valores_k, longitudes, color=colores[0], linewidth=2,
            marker="o", markersize=5, label="Reinicios")
    ax.axhline(diametro, color="#555555", linestyle="--", linewidth=1.2,
               label=f"Solucion optima maxima ({diametro})")
    for color, (nombre, valor) in zip(colores[1:], referencias.items()):
        ax.axhline(valor, color=color, linestyle="-.", linewidth=1.5,
                   label=f"{nombre}: {valor:.0f}")

    ax.set_yscale("log")
    ax.set_ylim(10, 10000)
    ax.set_yticks([10, 100, 1000, 10000])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("K (movimientos de la caminata de perturbacion)")
    ax.set_ylabel("Movimientos de la solucion (escala log)")
    ax.set_title(titulo)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, -0.18), ncol=1,
              frameon=False)
    ax.set_xticks(valores_k)
    ax.set_xlim(0, max(valores_k) * 1.05)
    _quitar_bordes_superiores(ax)
    fig.tight_layout()
    return fig


def guardar_figura(fig, nombre):
    """Guarda la figura en resultados/figuras/{nombre}.png."""
    os.makedirs(DIRECTORIO_FIGURAS, exist_ok=True)
    ruta = os.path.join(DIRECTORIO_FIGURAS, f"{nombre}.png")
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    return ruta
