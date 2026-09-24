"""Formulacion del 8-puzzle como problema de busqueda local."""

import numpy as np

META = (1, 2, 3, 4, 5, 6, 7, 8, 0)
LADO = 3


def fila_columna(indice):
    """Convierte un indice de la tupla (0-8) en (fila, columna)."""
    return divmod(indice, LADO)


def _posiciones_meta(meta=META):
    """Indice en la tupla meta para cada ficha (incluyendo el 0)."""
    posiciones = [0] * len(meta)
    for indice, ficha in enumerate(meta):
        posiciones[ficha] = indice
    return posiciones


_POSICIONES_META = _posiciones_meta()


def distancia_manhattan(estado, meta=META):
    """Suma de distancias Manhattan de cada ficha a su lugar meta.

    El 0 (casilla vacia) no se cuenta: no es una ficha que deba
    moverse a un lugar especifico. h(s) = 0 unicamente en la meta,
    ya que la distancia Manhattan de una ficha es 0 solo si ya esta
    en su posicion objetivo, y la suma de terminos no negativos es
    0 solo si todos lo son.
    """
    posiciones_meta = (
        _POSICIONES_META if meta is META else _posiciones_meta(meta))
    total = 0
    for indice, ficha in enumerate(estado):
        if ficha == 0:
            continue
        fila_actual, columna_actual = fila_columna(indice)
        fila_meta, columna_meta = fila_columna(posiciones_meta[ficha])
        total += (abs(fila_actual - fila_meta)
                  + abs(columna_actual - columna_meta))
    return total


def vecinos(estado):
    """Estados alcanzables al mover el vacio a una casilla adyacente.

    Cada vecino intercambia la posicion del 0 con una ficha adyacente
    en la cuadricula (arriba, abajo, izquierda o derecha). Ese
    intercambio mueve exactamente una ficha una casilla: la acerca o
    la aleja en 1 de su posicion meta en esa coordenada, y deja el
    resto de las fichas intactas, por lo que h(s) cambia en
    exactamente +1 o -1 respecto al estado actual.
    """
    indice_vacio = estado.index(0)
    fila_vacio, columna_vacio = fila_columna(indice_vacio)
    movimientos = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    resultado = []
    for delta_fila, delta_columna in movimientos:
        fila_nueva = fila_vacio + delta_fila
        columna_nueva = columna_vacio + delta_columna
        if not (0 <= fila_nueva < LADO and 0 <= columna_nueva < LADO):
            continue
        indice_nuevo = fila_nueva * LADO + columna_nueva
        estado_lista = list(estado)
        estado_lista[indice_vacio], estado_lista[indice_nuevo] = (
            estado_lista[indice_nuevo], estado_lista[indice_vacio])
        resultado.append(tuple(estado_lista))
    return resultado


def verificar_delta_h(estado, meta=META):
    """Confirma que cada vecino cambia h(s) en exactamente +-1.

    Se usa como evidencia empirica de la propiedad que sustenta la
    regla de aceptacion del temple simulado (exp(-deltaE/T) con
    deltaE en {-1, +1}).
    """
    h_actual = distancia_manhattan(estado, meta)
    return all(
        abs(distancia_manhattan(vecino, meta) - h_actual) == 1
        for vecino in vecinos(estado)
    )


def contar_inversiones(estado):
    """Cuenta pares fuera de orden entre las fichas, ignorando el 0."""
    fichas = [ficha for ficha in estado if ficha != 0]
    inversiones = 0
    for i in range(len(fichas)):
        for j in range(i + 1, len(fichas)):
            if fichas[i] > fichas[j]:
                inversiones += 1
    return inversiones


def es_resoluble(estado, meta=META):
    """Indica si el estado es alcanzable desde la meta.

    En un tablero de lado impar (3x3) dos permutaciones pertenecen a
    la misma clase de alcanzabilidad si y solo si tienen la misma
    paridad de inversiones. Como la meta tiene 0 inversiones (par),
    un estado es resoluble si su numero de inversiones es par. Solo
    la mitad de las 9! permutaciones cumple esta condicion.
    """
    inversiones_estado = contar_inversiones(estado)
    inversiones_meta = contar_inversiones(meta)
    return inversiones_estado % 2 == inversiones_meta % 2


def generar_tablero_resoluble(generador_aleatorio, meta=META):
    """Genera un tablero resoluble con una permutacion aleatoria.

    Se muestrea una permutacion uniforme de las 9 fichas (no una
    secuencia de movimientos desde otro estado) y se reintenta hasta
    obtener una resoluble, de modo que el tablero resultante puede
    "aparecer" en cualquier punto del espacio de estados alcanzable.
    """
    fichas = list(meta)
    while True:
        generador_aleatorio.shuffle(fichas)
        candidato = tuple(fichas)
        if es_resoluble(candidato, meta):
            return candidato


def generar_conjunto_pruebas(cantidad=30, semilla=42, meta=META):
    """Genera un conjunto fijo de tableros resolubles y distintos.

    Se reutiliza el mismo conjunto en todos los algoritmos para que
    la comparacion de desempeno sea justa.
    """
    generador_aleatorio = np.random.default_rng(semilla)
    tableros = set()
    while len(tableros) < cantidad:
        tableros.add(generar_tablero_resoluble(generador_aleatorio, meta))
    return sorted(tableros)
