"""Variantes de ascenso de colinas para el 8-puzzle."""

from collections import namedtuple

from formulacion import distancia_manhattan, vecinos

# Largo de la caminata aleatoria con que se perturba el tablero
# asignado en cada reinicio. Del mismo orden de magnitud que la
# perturbacion usada en el notebook exploratorio: suficiente para
# salir de la cuenca del optimo local, pero partiendo siempre del
# tablero asignado.
MOVIMIENTOS_PERTURBACION = 20

ResultadoAscenso = namedtuple(
    "ResultadoAscenso",
    ["estado_final", "h_final", "evaluaciones", "movimientos"])

ResultadoReinicios = namedtuple(
    "ResultadoReinicios",
    ["estado_final", "h_final", "evaluaciones", "h_iniciales",
     "estado_partida", "cantidad_intentos", "longitud_solucion"])


def steepest(tablero_inicial):
    """Ascenso de colinas mas pronunciado.

    En cada paso evalua todos los vecinos y se mueve al mejor de
    ellos. Se detiene cuando ningun vecino mejora el h actual (optimo
    local o la meta).
    """
    estado_actual = tablero_inicial
    h_actual = distancia_manhattan(estado_actual)
    evaluaciones = 1
    movimientos = 0
    while True:
        candidatos = vecinos(estado_actual)
        valores_h = [distancia_manhattan(v) for v in candidatos]
        evaluaciones += len(candidatos)
        mejor_h = min(valores_h)
        if mejor_h >= h_actual:
            break
        mejor_vecino = candidatos[valores_h.index(mejor_h)]
        estado_actual, h_actual = mejor_vecino, mejor_h
        movimientos += 1
    return ResultadoAscenso(
        estado_actual, h_actual, evaluaciones, movimientos)


def estocastico(tablero_inicial, generador):
    """Ascenso de colinas estocastico.

    En cada paso evalua todos los vecinos, pero en vez de moverse
    siempre al mejor, elige al azar entre los que mejoran el h
    actual. Se detiene cuando ninguno mejora.
    """
    estado_actual = tablero_inicial
    h_actual = distancia_manhattan(estado_actual)
    evaluaciones = 1
    movimientos = 0
    while True:
        candidatos = vecinos(estado_actual)
        valores_h = [distancia_manhattan(v) for v in candidatos]
        evaluaciones += len(candidatos)
        mejores = [(v, h) for v, h in zip(candidatos, valores_h)
                   if h < h_actual]
        if not mejores:
            break
        indice = generador.integers(0, len(mejores))
        estado_actual, h_actual = mejores[indice]
        movimientos += 1
    return ResultadoAscenso(
        estado_actual, h_actual, evaluaciones, movimientos)


def caminata_aleatoria(tablero, cantidad_movimientos, generador):
    """Aplica `cantidad_movimientos` movimientos legales elegidos al
    azar (uniforme entre los vecinos) a partir de `tablero`."""
    estado = tablero
    for _ in range(cantidad_movimientos):
        candidatos = vecinos(estado)
        estado = candidatos[generador.integers(0, len(candidatos))]
    return estado


def reinicios_aleatorios(
        tablero_inicial, presupuesto_evaluaciones, generador,
        movimientos_perturbacion=MOVIMIENTOS_PERTURBACION):
    """Ascenso de colinas mas pronunciado con reinicios por
    perturbacion.

    El primer intento es steepest desde el tablero asignado, sin
    perturbacion. Si queda en un optimo local, cada reinicio hace una
    caminata aleatoria de `movimientos_perturbacion` movimientos
    legales partiendo SIEMPRE del tablero asignado (no del reinicio
    anterior) y corre steepest desde el tablero resultante, hasta
    resolver o agotar el presupuesto de evaluaciones.

    Todos los puntos de partida son alcanzables desde el tablero
    asignado con movimientos legales, asi que un intento exitoso
    (caminata mas ascenso) es una solucion real de ese tablero. Los
    movimientos de la caminata no evaluan h, por eso no cuentan como
    evaluaciones; solo cuenta el h del punto de partida.

    Para cada intento se guarda el h del punto de partida antes de
    optimizar. `estado_partida` es el tablero desde el que partio el
    intento que dio el mejor resultado (el exitoso, si lo hubo), y
    `cantidad_intentos` cuenta el intento inicial mas los reinicios.
    `longitud_solucion` es el largo de la secuencia de movimientos del
    mejor intento: los movimientos de su caminata (0 en el intento
    directo) mas los pasos que dio steepest desde ahi. La caminata se
    cuenta completa, sin simplificar movimientos que se deshacen.
    """
    evaluaciones_totales = 0
    longitud_solucion = None
    movimientos_caminata = 0
    h_iniciales = []
    mejor_estado = None
    mejor_h = None
    estado_partida = None
    tablero = tablero_inicial
    while evaluaciones_totales < presupuesto_evaluaciones:
        h_inicial = distancia_manhattan(tablero)
        evaluaciones_totales += 1
        h_iniciales.append(h_inicial)

        resultado = steepest(tablero)
        evaluaciones_totales += resultado.evaluaciones

        if mejor_h is None or resultado.h_final < mejor_h:
            mejor_estado, mejor_h = resultado.estado_final, resultado.h_final
            estado_partida = tablero
            longitud_solucion = movimientos_caminata + resultado.movimientos
        if mejor_h == 0:
            break
        tablero = caminata_aleatoria(
            tablero_inicial, movimientos_perturbacion, generador)
        movimientos_caminata = movimientos_perturbacion
    return ResultadoReinicios(
        mejor_estado, mejor_h, evaluaciones_totales, h_iniciales,
        estado_partida, len(h_iniciales), longitud_solucion)
