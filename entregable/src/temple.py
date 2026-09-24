"""Temple simulado para el 8-puzzle."""

import math
from collections import namedtuple

from formulacion import distancia_manhattan, vecinos

ResultadoTemple = namedtuple(
    "ResultadoTemple",
    ["estado_final", "h_final", "evaluaciones", "traza",
     "movimientos_hasta_mejor"])

TrazaTemple = namedtuple(
    "TrazaTemple", ["temperatura", "h_actual", "h_mejor"])


def temple_simulado(
        tablero_inicial, t0, alpha, t_minimo,
        iteraciones_por_temperatura, generador, guardar_traza=False,
        presupuesto_evaluaciones=None):
    """Temple simulado con enfriamiento geometrico.

    La energia de un estado es h(s) (distancia Manhattan). En cada
    iteracion se elige un vecino al azar: si su energia es menor o
    igual a la actual se acepta directamente, si es mayor se acepta
    con probabilidad exp(-deltaE/T). La temperatura baja de forma
    geometrica, T_(k+1) = alpha * T_k, tras completar las
    iteraciones de cada nivel de temperatura.

    El estado actual puede empeorar (asi es como el temple escapa de
    optimos locales), pero el mejor estado visto se guarda aparte y
    nunca empeora.

    Se detiene cuando T <= t_minimo, cuando h llega a 0 (parada
    temprana) o, si se da presupuesto_evaluaciones, cuando se alcanza
    ese numero de evaluaciones. El presupuesto es opcional (por
    defecto None, sin limite) para poder acotar configuraciones con
    enfriamiento lento a la misma cantidad de evaluaciones que otras
    configuraciones o algoritmos, y comparar en igualdad de
    condiciones.
    """
    estado_actual = tablero_inicial
    h_actual = distancia_manhattan(estado_actual)
    evaluaciones = 1

    mejor_estado = estado_actual
    mejor_h = h_actual
    # Movimientos aceptados (incluye los que empeoran o dejan h igual)
    # desde el tablero inicial hasta el mejor estado. Si h llega a 0,
    # es el largo de la secuencia de movimientos que resuelve el
    # tablero.
    movimientos_aceptados = 0
    movimientos_hasta_mejor = 0

    traza = [] if guardar_traza else None
    temperatura = t0

    def presupuesto_agotado():
        return (presupuesto_evaluaciones is not None
                and evaluaciones >= presupuesto_evaluaciones)

    while temperatura > t_minimo and mejor_h > 0:
        if presupuesto_agotado():
            break
        for _ in range(iteraciones_por_temperatura):
            candidatos = vecinos(estado_actual)
            indice = generador.integers(0, len(candidatos))
            vecino = candidatos[indice]
            h_vecino = distancia_manhattan(vecino)
            evaluaciones += 1

            delta_energia = h_vecino - h_actual
            if delta_energia <= 0:
                aceptar = True
            else:
                probabilidad = math.exp(-delta_energia / temperatura)
                aceptar = generador.random() < probabilidad

            if aceptar:
                estado_actual, h_actual = vecino, h_vecino
                movimientos_aceptados += 1
                if h_actual < mejor_h:
                    mejor_estado, mejor_h = estado_actual, h_actual
                    movimientos_hasta_mejor = movimientos_aceptados

            if mejor_h == 0 or presupuesto_agotado():
                break

        if guardar_traza:
            traza.append(TrazaTemple(temperatura, h_actual, mejor_h))
        temperatura *= alpha

    return ResultadoTemple(
        mejor_estado, mejor_h, evaluaciones, traza,
        movimientos_hasta_mejor)
