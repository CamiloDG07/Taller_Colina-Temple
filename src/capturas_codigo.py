"""Genera capturas de fragmentos de codigo con resaltado de sintaxis
para el informe (informe/figuras_codigo/*.png).

Los fragmentos se extraen del codigo real de src/, por nombre de
funcion o por lineas de inicio y fin, asi que los numeros de linea de
la captura coinciden con los del archivo. Todas las capturas usan el
mismo tamano de fuente y la misma resolucion: incluidas en LaTeX sin
escalar, el codigo se imprime a TAMANO_FUENTE_PT puntos en todas.
"""

import ast
import io
import os

from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import PythonLexer

DIRECTORIO_SRC = os.path.dirname(os.path.abspath(__file__))
DIRECTORIO_SALIDA = os.path.join(
    DIRECTORIO_SRC, "..", "informe", "figuras_codigo")

ESTILO = "vs"
FUENTE = "Consolas"
TAMANO_FUENTE_PX = 36
# Resolucion guardada en el PNG: con 288 dpi, 36 px equivalen a 9 pt,
# un tamano legible en el PDF sin tener que escalar la imagen.
DPI = 288
TAMANO_FUENTE_PT = TAMANO_FUENTE_PX / DPI * 72
# Ancho de texto del informe: A4 (21 cm) menos 3 cm por lado.
ANCHO_TEXTO_PT = 15 / 2.54 * 72
LARGO_MAXIMO_LINEA = 79

COLOR_BARRA = "#E4E6EB"
COLOR_TEXTO_BARRA = "#3C3C3C"
COLOR_BORDE = "#B8BCC4"
ALTO_BARRA_PX = 64
MARGEN_DERECHO_PX = 12

# (nombre del PNG, archivo, seleccion). La seleccion es el nombre de
# una funcion o una tupla (texto de la linea inicial, texto de la
# linea final) que se busca en el archivo.
FRAGMENTOS = [
    ("distancia_manhattan", "formulacion.py", "distancia_manhattan"),
    ("temple_aceptacion", "temple.py",
     ("        for _ in range(iteraciones_por_temperatura):",
      "                    movimientos_hasta_mejor = movimientos_aceptados")),
    ("caminata_aleatoria", "ascenso.py", "caminata_aleatoria"),
    ("reinicios_bucle", "ascenso.py",
     ("    while evaluaciones_totales < presupuesto_evaluaciones:",
      "        estado_partida, len(h_iniciales), longitud_solucion)")),
    ("k_principal", "experimentos.py",
     ("# K_PRINCIPAL es el que va en la tabla comparativa. Se fija por el",
      "K_PRINCIPAL = 20")),
    ("es_truncada", "experimentos.py", "_es_truncada"),
]


def _lineas_de_funcion(fuente, nombre):
    """(primera, ultima) linea, base 1, de la funcion `nombre`."""
    for nodo in ast.walk(ast.parse(fuente)):
        if isinstance(nodo, ast.FunctionDef) and nodo.name == nombre:
            return nodo.lineno, nodo.end_lineno
    raise ValueError(f"no existe la funcion {nombre}")


def _lineas_entre(lineas, inicio, fin):
    """(primera, ultima) linea, base 1, entre dos lineas exactas."""
    primera = lineas.index(inicio) + 1
    ultima = lineas.index(fin, primera - 1) + 1
    return primera, ultima


def extraer_fragmento(archivo, seleccion):
    """Texto del fragmento y numero de su primera linea."""
    with open(os.path.join(DIRECTORIO_SRC, archivo),
              encoding="utf-8") as manejador:
        fuente = manejador.read()
    lineas = fuente.splitlines()
    if isinstance(seleccion, str):
        primera, ultima = _lineas_de_funcion(fuente, seleccion)
    else:
        primera, ultima = _lineas_entre(lineas, *seleccion)
    fragmento = lineas[primera - 1:ultima]
    for numero, linea in enumerate(fragmento, start=primera):
        if len(linea) > LARGO_MAXIMO_LINEA:
            raise ValueError(
                f"{archivo}:{numero} supera {LARGO_MAXIMO_LINEA} "
                "caracteres")
    return "\n".join(fragmento) + "\n", primera, ultima


def _codigo_resaltado(texto, primera_linea, ultima_linea):
    formateador = ImageFormatter(
        style=ESTILO, font_name=FUENTE, font_size=TAMANO_FUENTE_PX,
        line_numbers=True, line_number_start=primera_linea,
        line_number_chars=len(str(ultima_linea)),
        line_number_bg="#F3F3F3", line_number_fg="#8A8A8A",
        line_number_separator=True, line_number_pad=10,
        image_pad=12, line_pad=8)
    datos = highlight(texto, PythonLexer(), formateador)
    codigo = Image.open(io.BytesIO(datos)).convert("RGB")
    # Margen derecho: Pygments deja la linea mas larga pegada al borde.
    ancho, alto = codigo.size
    con_margen = Image.new("RGB", (ancho + MARGEN_DERECHO_PX, alto),
                           codigo.getpixel((ancho - 1, 0)))
    con_margen.paste(codigo, (0, 0))
    return con_margen


def _fuente_barra():
    try:
        return ImageFont.truetype("consola.ttf", 30)
    except OSError:
        return ImageFont.load_default()


def _componer(texto, primera, ultima, titulo):
    """Imagen final: barra superior tipo pestana de editor con
    `titulo` y el codigo resaltado debajo, con un borde fino."""
    codigo = _codigo_resaltado(texto, primera, ultima)
    ancho, alto = codigo.size
    imagen = Image.new(
        "RGB", (ancho + 2, alto + ALTO_BARRA_PX + 2), COLOR_BORDE)
    lienzo = ImageDraw.Draw(imagen)
    lienzo.rectangle([1, 1, ancho, ALTO_BARRA_PX], fill=COLOR_BARRA)
    lienzo.text(
        (24, ALTO_BARRA_PX // 2),
        titulo, fill=COLOR_TEXTO_BARRA, font=_fuente_barra(), anchor="lm")
    imagen.paste(codigo, (1, ALTO_BARRA_PX + 1))
    return imagen


def verificar_peor_caso():
    """Comprueba que el peor caso cabe en el ancho de texto: una linea
    de LARGO_MAXIMO_LINEA caracteres con numeros de linea de 3
    digitos. Si cabe, cualquier fragmento PEP8 de hasta 999 lineas
    cabe sin recorte ni escalado."""
    imagen = _componer(
        "x" * LARGO_MAXIMO_LINEA + "\n", 998, 999,
        "src/experimentos.py   lineas 998-999")
    ancho_pt = imagen.size[0] / DPI * 72
    if ancho_pt > ANCHO_TEXTO_PT:
        raise ValueError(
            f"una linea de {LARGO_MAXIMO_LINEA} caracteres mide "
            f"{ancho_pt:.0f} pt y no cabe en {ANCHO_TEXTO_PT:.0f} pt")
    return ancho_pt


def generar_captura(nombre, archivo, seleccion):
    """Crea la captura con una barra superior tipo pestana de editor
    (archivo y lineas) y devuelve su ruta y su ancho en puntos."""
    texto, primera, ultima = extraer_fragmento(archivo, seleccion)
    imagen = _componer(texto, primera, ultima,
                       f"src/{archivo}   lineas {primera}-{ultima}")
    ancho_pt = imagen.size[0] / DPI * 72
    if ancho_pt > ANCHO_TEXTO_PT:
        raise ValueError(
            f"{nombre}: {ancho_pt:.0f} pt supera el ancho de texto "
            f"({ANCHO_TEXTO_PT:.0f} pt)")
    os.makedirs(DIRECTORIO_SALIDA, exist_ok=True)
    ruta = os.path.join(DIRECTORIO_SALIDA, f"{nombre}.png")
    imagen.save(ruta, dpi=(DPI, DPI))
    return ruta, ancho_pt


def generar_todas(nombres=None):
    print(f"Peor caso ({LARGO_MAXIMO_LINEA} caracteres): "
          f"{verificar_peor_caso():.0f} pt de {ANCHO_TEXTO_PT:.0f} pt")
    for nombre, archivo, seleccion in FRAGMENTOS:
        if nombres is None or nombre in nombres:
            ruta, ancho_pt = generar_captura(nombre, archivo, seleccion)
            print(f"{os.path.basename(ruta)}: {ancho_pt:.0f} pt de "
                  f"ancho (texto: {ANCHO_TEXTO_PT:.0f} pt), fuente "
                  f"{TAMANO_FUENTE_PT:.0f} pt")


if __name__ == "__main__":
    generar_todas()
