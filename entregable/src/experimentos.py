"""Orquesta la comparacion entre ascenso de colinas y temple simulado
sobre el conjunto de 30 tableros de prueba.

Criterio general: la tabla comparativa principal usa un unico
presupuesto de evaluaciones compartido por todas las configuraciones
aleatorias (reinicios, temple actividad y temple mejor), igual al que
se usa en el barrido de T0/alpha de temple y en el barrido de K
(largo de la perturbacion) de reinicios. Los parametros de ambos
algoritmos se eligen por barrido con el mismo criterio, no a ojo.

El presupuesto se fija como el promedio de evaluaciones que gasta
temple actividad cuando corre hasta su parada natural; esa corrida
sin tope se reporta aparte como contexto (techo de temple sin
restriccion de costo).

Todo lo aleatorio se repite con REPETICIONES semillas por tablero, y
la tasa de exito se reporta como promedio y desviacion entre semillas.
"""

import os
from collections import deque

import numpy as np
import pandas as pd

import ascenso as asc
import temple as tem
import visualizacion as viz
from formulacion import META, distancia_manhattan, generar_conjunto_pruebas
from formulacion import vecinos

SEMILLA_BASE = 1000
CANTIDAD_TABLEROS = 30
SEMILLA_TABLEROS = 42
REPETICIONES = 10

ITERACIONES_POR_TEMPERATURA = 100
# Se deja en 0.05 (el notebook exploratorio usaba 0.01). Con T = 0.05
# aceptar un empeoramiento de +1 tiene probabilidad exp(-20), asi que
# el temple ya esta congelado: con T_MINIMO = 0.01, temple actividad
# sin tope da la misma tasa de exito (70.3%) y solo gasta mas
# evaluaciones en la cola del enfriamiento (11395 contra 9823), lo
# que inflaria el presupuesto compartido sin cambiar el resultado.
T_MINIMO = 0.05

CONFIG_ACTIVIDAD = {"t0": 10.0, "alpha": 0.97}

# La grilla incluye T0 bajos (0.5, 1, 2) y alpha altos (0.995, 0.998)
# para cubrir la zona donde el notebook exploratorio encontro su mejor
# resultado (T0 = 1, alpha = 0.995).
VALORES_T0_BARRIDO = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0]
VALORES_ALPHA_BARRIDO = [
    0.50, 0.70, 0.90, 0.95, 0.97, 0.99, 0.995, 0.998]
VALORES_T0_INTERACCION = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 40.0]
VALORES_ALPHA_INTERACCION = [0.90, 0.95, 0.97, 0.99, 0.995, 0.998]

# Largo K de la caminata de perturbacion de reinicios. K pequeno deja
# el reinicio en la misma cuenca del optimo local; K grande se acerca
# a partir de un tablero al azar (pero siempre alcanzable desde el
# tablero asignado con movimientos legales).
#
# K_PRINCIPAL es el que va en la tabla comparativa. Se fija por el
# diametro del espacio de estados del 8-puzzle: ningun tablero
# resoluble necesita mas de 31 movimientos para llegar a la meta. Con
# K < 31 la caminata sigue siendo una modificacion local del tablero
# asignado; con K >= 31 ya tiene alcance para llegar a cualquier
# tablero resoluble y el reinicio se parece a generar un tablero al
# azar. K = 20 es el mayor K redondo por debajo de ese umbral.
#
# El barrido de K (VALORES_K_BARRIDO) NO elige la K principal: se
# reporta aparte como analisis del efecto de K sobre la tasa de exito
# y la longitud de la solucion.
DIAMETRO_8PUZZLE = 31
K_PRINCIPAL = 20
VALORES_K_BARRIDO = [10, 20, 50, 100, 200]

# Barridos congelados. Con RECALCULAR_BARRIDOS = False, ejecutar_todo
# lee los barridos de T0/alpha y de K desde los CSV ya generados
# (unos 40 minutos de computo) y solo corre la tabla principal. Solo
# hace falta recalcularlos si cambia algo estructural: T_MINIMO,
# ITERACIONES_POR_TEMPERATURA, tableros, semillas o grillas. Si el
# presupuesto calculado no coincide con PRESUPUESTO_BARRIDOS, el
# pipeline se detiene en vez de usar barridos desactualizados.
RECALCULAR_BARRIDOS = False
PRESUPUESTO_BARRIDOS = 9823
# Resultado del barrido T0 x alpha con el presupuesto compartido
# (96.3% de exito promedio en 10 semillas).
MEJOR_T0 = 1.0
MEJOR_ALPHA = 0.998

# Temple con enfriamiento casi inmediato, para mostrar que degenera en
# un ascenso de colinas. Mismas iteraciones por nivel que el resto.
ALPHA_DEGRADACION = 0.01
ITERACIONES_DEGRADACION = ITERACIONES_POR_TEMPERATURA

DIRECTORIO_DATOS = os.path.join(
    os.path.dirname(__file__), "..", "resultados", "datos")
RUTA_BARRIDO_TEMPLE = os.path.join(DIRECTORIO_DATOS, "temple_barrido.csv")
RUTA_BARRIDO_K = os.path.join(DIRECTORIO_DATOS, "reinicios_barrido_k.csv")

# Claves para derivar la semilla de cada corrida. Cada corrida usa su
# propio generador reproducible a partir de (clave, repeticion,
# tablero), nunca un unico generador compartido. En temple la clave
# depende de (T0, alpha) y no del experimento que la corre: la misma
# configuracion usa las mismas semillas en el barrido, en la tabla
# principal y en la corrida sin tope, asi que da los mismos numeros.
CLAVE_ESTOCASTICO = 1
CLAVE_REINICIOS = 2
CLAVE_TEMPLE = 3
CLAVE_DEGRADACION = 5

NOMBRES_CONFIGURACIONES = {
    "steepest": "Steepest",
    "estocastico": "Estocastico",
    "reinicios": "Reinicios aleatorios",
    "temple_actividad": "Temple (actividad)",
    "temple_mejor": "Temple (mejor)",
}

_cache_temple = {}
_cache_reinicios = {}
_distancias_optimas = {}


def _longitud_optima(tablero):
    """Largo de la solucion optima del tablero (minimo numero de
    movimientos hasta la meta).

    La primera llamada hace una busqueda en anchura desde la meta sobre
    todo el espacio de estados resolubles (9!/2 = 181440 tableros) y
    guarda la distancia de cada uno; las siguientes solo consultan.
    """
    if not _distancias_optimas:
        _distancias_optimas[META] = 0
        cola = deque([META])
        while cola:
            estado = cola.popleft()
            for vecino in vecinos(estado):
                if vecino not in _distancias_optimas:
                    _distancias_optimas[vecino] = (
                        _distancias_optimas[estado] + 1)
                    cola.append(vecino)
    return _distancias_optimas[tablero]


def _generador(clave, indice_tablero, repeticion):
    """Generador de numeros aleatorios con semilla determinista.

    `clave` es una tupla de enteros que identifica la configuracion.
    La semilla combina clave, repeticion e indice del tablero, para
    que cada corrida sea reproducible de forma aislada.
    """
    semilla = [SEMILLA_BASE, *clave, repeticion, indice_tablero]
    return np.random.default_rng(semilla)


def _clave_temple(t0, alpha):
    return (CLAVE_TEMPLE, round(t0 * 100), round(alpha * 1000))


def _fila(configuracion, indice, repeticion, tablero_inicial, resultado,
          truncada=False):
    return {
        "configuracion": configuracion,
        "tablero_indice": indice,
        "repeticion": repeticion,
        "estado_inicial": tablero_inicial,
        "estado_final": resultado.estado_final,
        "h_inicial": distancia_manhattan(tablero_inicial),
        "h_final": resultado.h_final,
        "evaluaciones": resultado.evaluaciones,
        "resuelto": resultado.h_final == 0,
        "truncada": truncada,
        "longitud_solucion": _longitud_solucion(resultado),
        "longitud_optima": _longitud_optima(tablero_inicial),
    }


def _longitud_solucion(resultado):
    """Movimientos de la secuencia que resuelve el tablero, o None si
    la corrida no llego a h = 0.

    Reinicios: movimientos de la caminata del intento exitoso mas los
    pasos de steepest. Temple: movimientos aceptados hasta llegar a
    h = 0. Steepest y estocastico: pasos de ascenso.
    """
    if resultado.h_final != 0:
        return None
    for campo in ("longitud_solucion", "movimientos_hasta_mejor",
                  "movimientos"):
        if hasattr(resultado, campo):
            return getattr(resultado, campo)
    return None


def _es_truncada(resultado, presupuesto_evaluaciones):
    """Una corrida queda truncada cuando la corto el presupuesto de
    evaluaciones sin llegar a h = 0, y no su parada natural. Mismo
    criterio para temple y para reinicios."""
    return (
        presupuesto_evaluaciones is not None
        and resultado.h_final > 0
        and resultado.evaluaciones >= presupuesto_evaluaciones)


def ejecutar_steepest(tableros):
    """Steepest es determinista: una sola repeticion por tablero."""
    return [
        _fila("steepest", indice, 0, tablero, asc.steepest(tablero))
        for indice, tablero in enumerate(tableros)
    ]


def ejecutar_estocastico(tableros):
    filas = []
    for repeticion in range(REPETICIONES):
        for indice, tablero in enumerate(tableros):
            generador = _generador(
                (CLAVE_ESTOCASTICO,), indice, repeticion)
            resultado = asc.estocastico(tablero, generador)
            filas.append(_fila(
                "estocastico", indice, repeticion, tablero, resultado))
    return filas


def ejecutar_reinicios(tableros, presupuesto_evaluaciones,
                       movimientos_perturbacion, etiqueta="reinicios"):
    """Reinicios por perturbacion con caminatas de largo K =
    `movimientos_perturbacion`. Los resultados se guardan en cache por
    (K, presupuesto), porque el K ganador del barrido se reutiliza en
    la tabla principal."""
    llave = (movimientos_perturbacion, presupuesto_evaluaciones)
    if llave not in _cache_reinicios:
        _cache_reinicios[llave] = _correr_reinicios(
            tableros, presupuesto_evaluaciones, movimientos_perturbacion)
    return [dict(f, configuracion=etiqueta)
            for f in _cache_reinicios[llave]]


def _correr_reinicios(tableros, presupuesto_evaluaciones,
                      movimientos_perturbacion):
    filas = []
    for repeticion in range(REPETICIONES):
        for indice, tablero in enumerate(tableros):
            generador = _generador((CLAVE_REINICIOS,), indice, repeticion)
            resultado = asc.reinicios_aleatorios(
                tablero, presupuesto_evaluaciones, generador,
                movimientos_perturbacion)
            fila = _fila(
                "reinicios", indice, repeticion, tablero, resultado,
                _es_truncada(resultado, presupuesto_evaluaciones))
            # Tablero desde el que partio el intento exitoso (o el
            # mejor): el asignado si bastaba el primer intento, o una
            # perturbacion del asignado si hicieron falta reinicios.
            fila["estado_partida"] = resultado.estado_partida
            fila["cantidad_intentos"] = resultado.cantidad_intentos
            fila["resuelto_sin_reinicio"] = (
                fila["resuelto"] and resultado.cantidad_intentos == 1)
            filas.append(fila)
    return filas


def _correr_temple(tableros, t0, alpha, presupuesto_evaluaciones):
    """Corre temple sobre todos los tableros y repeticiones.

    Los resultados se guardan en cache por (T0, alpha, presupuesto),
    porque varias configuraciones se repiten entre el barrido de T0,
    el de alpha, la interaccion y la tabla final. Solo se guarda la
    traza de la repeticion 0 del tablero 0.
    """
    llave = (t0, alpha, presupuesto_evaluaciones)
    if llave not in _cache_temple:
        corridas = []
        for repeticion in range(REPETICIONES):
            for indice, tablero in enumerate(tableros):
                generador = _generador(
                    _clave_temple(t0, alpha), indice, repeticion)
                con_traza = repeticion == 0 and indice == 0
                resultado = tem.temple_simulado(
                    tablero, t0, alpha, T_MINIMO,
                    ITERACIONES_POR_TEMPERATURA, generador,
                    guardar_traza=con_traza,
                    presupuesto_evaluaciones=presupuesto_evaluaciones)
                corridas.append((indice, repeticion, tablero, resultado))
        _cache_temple[llave] = corridas
    return _cache_temple[llave]


def ejecutar_temple(tableros, t0, alpha, etiqueta,
                    presupuesto_evaluaciones=None):
    """Filas de resultados de temple y la traza de la repeticion 0
    del tablero 0.

    Una corrida queda marcada como truncada cuando la corto el
    presupuesto y no la parada natural (T <= T_MINIMO o h = 0).
    """
    filas = []
    traza = None
    for indice, repeticion, tablero, resultado in _correr_temple(
            tableros, t0, alpha, presupuesto_evaluaciones):
        truncada = _es_truncada(resultado, presupuesto_evaluaciones)
        filas.append(_fila(
            etiqueta, indice, repeticion, tablero, resultado, truncada))
        if resultado.traza is not None:
            traza = resultado.traza
    return filas, traza


def calcular_metricas(filas, configuracion):
    """Metricas agregadas de una configuracion.

    La tasa de exito se calcula por separado en cada repeticion (sobre
    los 30 tableros) y se reporta el promedio y la desviacion estandar
    entre repeticiones. h final y evaluaciones se promedian sobre
    todas las corridas (tableros x repeticiones).
    """
    seleccion = [f for f in filas if f["configuracion"] == configuracion]
    repeticiones = sorted({f["repeticion"] for f in seleccion})
    tasas_por_repeticion = np.array([
        100.0 * np.mean(
            [f["resuelto"] for f in seleccion if f["repeticion"] == r])
        for r in repeticiones
    ])
    h_finales = np.array([f["h_final"] for f in seleccion], dtype=float)
    evaluaciones = np.array(
        [f["evaluaciones"] for f in seleccion], dtype=float)
    truncadas = np.array([f["truncada"] for f in seleccion])
    longitudes = np.array(
        [f["longitud_solucion"] for f in seleccion if f["resuelto"]],
        dtype=float)
    hay_resueltas = len(longitudes) > 0
    # Cuantas veces mas larga que la optima es cada solucion.
    razones = np.array(
        [f["longitud_solucion"] / f["longitud_optima"]
         for f in seleccion if f["resuelto"]], dtype=float)
    return {
        "configuracion": configuracion,
        "repeticiones": len(repeticiones),
        "tasa_exito_promedio": tasas_por_repeticion.mean(),
        "tasa_exito_desviacion": tasas_por_repeticion.std(),
        "tasa_exito_minima": tasas_por_repeticion.min(),
        "tasa_exito_maxima": tasas_por_repeticion.max(),
        "h_final_promedio": h_finales.mean(),
        "h_final_desviacion": h_finales.std(),
        "evaluaciones_promedio": evaluaciones.mean(),
        "porcentaje_truncadas": 100.0 * truncadas.mean(),
        "corridas_resueltas": len(longitudes),
        "longitud_solucion_promedio": (
            longitudes.mean() if hay_resueltas else np.nan),
        "longitud_solucion_desviacion": (
            longitudes.std() if hay_resueltas else np.nan),
        "longitud_solucion_minima": (
            longitudes.min() if hay_resueltas else np.nan),
        "longitud_solucion_maxima": (
            longitudes.max() if hay_resueltas else np.nan),
        "razon_sobre_optima_promedio": (
            razones.mean() if hay_resueltas else np.nan),
    }


def _metricas_temple(tableros, t0, alpha, presupuesto_evaluaciones):
    etiqueta = f"temple_{t0}_{alpha}"
    filas, _ = ejecutar_temple(
        tableros, t0, alpha, etiqueta, presupuesto_evaluaciones)
    return calcular_metricas(filas, etiqueta)


def barrido_t0(tableros, alpha_fijo, presupuesto_evaluaciones):
    """Tasa de exito variando T0, con alpha fijo en el de la
    configuracion de la actividad. Cada corrida tiene el mismo
    presupuesto de evaluaciones que la tabla principal, para que un
    T0 mas grande no gane solo por gastar mas evaluaciones."""
    return {
        t0: _metricas_temple(
            tableros, t0, alpha_fijo, presupuesto_evaluaciones)
        for t0 in VALORES_T0_BARRIDO
    }


def barrido_alpha(tableros, t0_fijo, presupuesto_evaluaciones):
    """Tasa de exito variando alpha, con T0 fijo en el de la
    configuracion de la actividad. Incluye un alpha muy pequeno
    (0.50, 0.70) para reforzar la comparacion con steepest. Mismo
    presupuesto de evaluaciones que la tabla principal."""
    return {
        alpha: _metricas_temple(
            tableros, t0_fijo, alpha, presupuesto_evaluaciones)
        for alpha in VALORES_ALPHA_BARRIDO
    }


def barrido_interaccion(tableros, presupuesto_evaluaciones):
    """Grilla T0 x alpha: una curva de tasa de exito por cada T0.

    Mismo presupuesto que la tabla principal. Las combinaciones que
    enfrian mas lento no alcanzan a llegar a T_MINIMO dentro del
    presupuesto y quedan truncadas (ver porcentaje_truncadas). Se
    dejan competir asi a proposito: el barrido responde que
    configuracion rinde mas con el mismo costo, y enfriar lento es
    justamente gastar mas evaluaciones.
    """
    return {
        t0: {
            alpha: _metricas_temple(
                tableros, t0, alpha, presupuesto_evaluaciones)
            for alpha in VALORES_ALPHA_INTERACCION
        }
        for t0 in VALORES_T0_INTERACCION
    }


def barrido_k(tableros, presupuesto_evaluaciones):
    """Tasa de exito y longitud de la solucion de reinicios variando
    el largo K de la caminata de perturbacion, con el presupuesto
    compartido. Es analisis: no elige la K de la tabla principal (ver
    K_PRINCIPAL)."""
    resultados = {}
    for k in VALORES_K_BARRIDO:
        etiqueta = f"reinicios_k_{k}"
        filas = ejecutar_reinicios(
            tableros, presupuesto_evaluaciones, k, etiqueta)
        resultados[k] = calcular_metricas(filas, etiqueta)
    return resultados


def _ordenar_por_criterio(candidatos):
    """Criterio de seleccion del barrido: mayor tasa de exito
    promedio; en empate, menor numero de evaluaciones promedio.
    `candidatos` es una lista de (parametros, metricas)."""
    return sorted(
        candidatos,
        key=lambda c: (-c[1]["tasa_exito_promedio"],
                       c[1]["evaluaciones_promedio"]))


def elegir_mejor_configuracion(resultados_interaccion):
    """Mejor combinacion T0/alpha por tasa de exito promedio; en
    empate, por menor numero de evaluaciones promedio."""
    candidatos = [
        ((t0, alpha), metricas)
        for t0, por_alpha in resultados_interaccion.items()
        for alpha, metricas in por_alpha.items()
    ]
    mejor_t0, mejor_alpha = _ordenar_por_criterio(candidatos)[0][0]
    return mejor_t0, mejor_alpha


def _elegir_caso_representativo(filas, configuracion):
    """Un tablero resuelto de esa configuracion en la repeticion 0
    (o, si ninguno se resolvio, el de menor h final) para mostrar
    antes/despues."""
    seleccion = [
        f for f in filas
        if f["configuracion"] == configuracion and f["repeticion"] == 0]
    resueltos = [f for f in seleccion if f["resuelto"]]
    if resueltos:
        return resueltos[0]
    return min(seleccion, key=lambda f: f["h_final"])


def _evaluaciones_hasta_resolver(filas):
    return [f["evaluaciones"] for f in filas if f["resuelto"]]


def _guardar_csv_detalle(filas, ruta):
    filas_planas = []
    for fila in filas:
        fila_plana = dict(fila)
        fila_plana["estado_inicial"] = "-".join(
            str(x) for x in fila["estado_inicial"])
        fila_plana["estado_final"] = "-".join(
            str(x) for x in fila["estado_final"])
        if "estado_partida" in fila:
            fila_plana["estado_partida"] = "-".join(
                str(x) for x in fila["estado_partida"])
        filas_planas.append(fila_plana)
    pd.DataFrame(filas_planas).to_csv(ruta, index=False)


def _barridos_temple_a_filas(resultados_t0, resultados_alpha,
                             resultados_interaccion):
    t0_actividad = CONFIG_ACTIVIDAD["t0"]
    alpha_actividad = CONFIG_ACTIVIDAD["alpha"]
    filas_barrido = []
    for t0, metricas in resultados_t0.items():
        filas_barrido.append({
            "tipo": "t0", "t0": t0, "alpha": alpha_actividad,
            **metricas})
    for alpha, metricas in resultados_alpha.items():
        filas_barrido.append({
            "tipo": "alpha", "t0": t0_actividad, "alpha": alpha,
            **metricas})
    for t0, por_alpha in resultados_interaccion.items():
        for alpha, metricas in por_alpha.items():
            filas_barrido.append(
                {"tipo": "interaccion", "t0": t0, "alpha": alpha,
                 **metricas})
    return filas_barrido


def guardar_barrido_k(resultados_k):
    """Guarda el barrido de K con dos marcas: la K principal (la que
    va en la tabla comparativa) y si la K supera el diametro del
    espacio de estados."""
    pd.DataFrame([
        {"k": k, "principal": k == K_PRINCIPAL,
         "supera_diametro": k >= DIAMETRO_8PUZZLE, **metricas}
        for k, metricas in resultados_k.items()
    ]).to_csv(RUTA_BARRIDO_K, index=False)


def _buscar(tabla, **condiciones):
    """Fila unica de `tabla` que cumple las condiciones, como dict."""
    mascara = np.ones(len(tabla), dtype=bool)
    for columna, valor in condiciones.items():
        mascara &= np.isclose(tabla[columna], valor)
    seleccion = tabla[mascara]
    if len(seleccion) != 1:
        raise RuntimeError(
            f"El CSV de barridos no tiene {condiciones}: hay que "
            "recalcular los barridos (RECALCULAR_BARRIDOS = True).")
    return seleccion.iloc[0].to_dict()


def cargar_barridos():
    """Lee los barridos ya calculados desde los CSV, con la misma forma
    que devuelven barrido_t0, barrido_alpha, barrido_interaccion y
    barrido_k."""
    temple = pd.read_csv(RUTA_BARRIDO_TEMPLE)
    alpha_actividad = CONFIG_ACTIVIDAD["alpha"]
    t0_actividad = CONFIG_ACTIVIDAD["t0"]
    por_tipo = {tipo: temple[temple["tipo"] == tipo]
                for tipo in ("t0", "alpha", "interaccion")}
    resultados_t0 = {
        t0: _buscar(por_tipo["t0"], t0=t0, alpha=alpha_actividad)
        for t0 in VALORES_T0_BARRIDO}
    resultados_alpha = {
        alpha: _buscar(por_tipo["alpha"], t0=t0_actividad, alpha=alpha)
        for alpha in VALORES_ALPHA_BARRIDO}
    resultados_interaccion = {
        t0: {alpha: _buscar(por_tipo["interaccion"], t0=t0, alpha=alpha)
             for alpha in VALORES_ALPHA_INTERACCION}
        for t0 in VALORES_T0_INTERACCION}
    tabla_k = pd.read_csv(RUTA_BARRIDO_K)
    resultados_k = {k: _buscar(tabla_k, k=k) for k in VALORES_K_BARRIDO}
    return (resultados_t0, resultados_alpha, resultados_interaccion,
            resultados_k)


def ejecutar_todo():
    """Corre el experimento completo y genera CSV y figuras.

    Con RECALCULAR_BARRIDOS = False (por defecto) los barridos de
    T0/alpha y de K se leen de los CSV ya calculados y solo se corre
    la tabla principal, la tabla de temple sin tope y las figuras.
    Antes de usar los CSV se verifica que el presupuesto compartido
    siga siendo el mismo con que se calcularon y que el mejor T0/alpha
    del barrido coincida con las constantes congeladas.

    Devuelve un diccionario con las metricas resumidas de la tabla
    principal, la tabla de temple sin tope y los barridos.
    """
    _cache_temple.clear()
    _cache_reinicios.clear()
    os.makedirs(DIRECTORIO_DATOS, exist_ok=True)
    tableros = generar_conjunto_pruebas(
        cantidad=CANTIDAD_TABLEROS, semilla=SEMILLA_TABLEROS)
    t0_actividad = CONFIG_ACTIVIDAD["t0"]
    alpha_actividad = CONFIG_ACTIVIDAD["alpha"]

    # 1. Temple actividad hasta su parada natural, sin presupuesto.
    # Su promedio de evaluaciones fija el presupuesto compartido de
    # toda la comparacion. Esta corrida NO entra en la tabla
    # principal: va en una tabla aparte como techo de temple sin
    # restriccion de costo.
    filas_sin_tope, _ = ejecutar_temple(
        tableros, t0_actividad, alpha_actividad,
        "temple_actividad_sin_tope")
    presupuesto_evaluaciones = round(np.mean(
        [f["evaluaciones"] for f in filas_sin_tope]))

    # 2. Barridos: se recalculan o se leen de los CSV congelados.
    if RECALCULAR_BARRIDOS:
        resultados_k = barrido_k(tableros, presupuesto_evaluaciones)
        resultados_t0 = barrido_t0(
            tableros, alpha_actividad, presupuesto_evaluaciones)
        resultados_alpha = barrido_alpha(
            tableros, t0_actividad, presupuesto_evaluaciones)
        resultados_interaccion = barrido_interaccion(
            tableros, presupuesto_evaluaciones)
        pd.DataFrame(_barridos_temple_a_filas(
            resultados_t0, resultados_alpha, resultados_interaccion)
        ).to_csv(RUTA_BARRIDO_TEMPLE, index=False)
        guardar_barrido_k(resultados_k)
    else:
        if presupuesto_evaluaciones != PRESUPUESTO_BARRIDOS:
            raise RuntimeError(
                f"El presupuesto compartido ({presupuesto_evaluaciones})"
                f" no coincide con el de los barridos congelados "
                f"({PRESUPUESTO_BARRIDOS}): cambio algo estructural "
                "(T_MINIMO, tableros, semillas...). Hay que correr con "
                "RECALCULAR_BARRIDOS = True.")
        (resultados_t0, resultados_alpha, resultados_interaccion,
         resultados_k) = cargar_barridos()

    mejor_t0, mejor_alpha = elegir_mejor_configuracion(
        resultados_interaccion)
    if (mejor_t0, mejor_alpha) != (MEJOR_T0, MEJOR_ALPHA):
        mensaje = (
            f"El barrido eligio T0={mejor_t0}, alpha={mejor_alpha}, "
            f"distinto de las constantes congeladas MEJOR_T0="
            f"{MEJOR_T0}, MEJOR_ALPHA={MEJOR_ALPHA}.")
        if not RECALCULAR_BARRIDOS:
            raise RuntimeError(mensaje)
        print("AVISO:", mensaje, "Actualizar las constantes.")

    # 3. Tabla principal: las 5 configuraciones con el presupuesto
    # compartido. Reinicios usa K_PRINCIPAL (no el K de mayor exito
    # del barrido, ver la justificacion junto a la constante).
    filas_steepest = ejecutar_steepest(tableros)
    filas_estocastico = ejecutar_estocastico(tableros)
    filas_reinicios = ejecutar_reinicios(
        tableros, presupuesto_evaluaciones, K_PRINCIPAL)
    filas_actividad, traza_actividad = ejecutar_temple(
        tableros, t0_actividad, alpha_actividad, "temple_actividad",
        presupuesto_evaluaciones)
    filas_mejor, traza_mejor = ejecutar_temple(
        tableros, mejor_t0, mejor_alpha, "temple_mejor",
        presupuesto_evaluaciones)

    # 4. Degradacion: temple con alpha muy pequeno (enfriamiento casi
    # inmediato) sobre los 30 tableros, para compararlo tablero a
    # tablero contra steepest. Tras el primer nivel la temperatura ya
    # es tan baja que solo acepta mejoras, como un ascenso de colinas.
    resultados_degradacion = [
        tem.temple_simulado(
            tablero, t0_actividad, ALPHA_DEGRADACION, T_MINIMO,
            ITERACIONES_DEGRADACION,
            _generador((CLAVE_DEGRADACION,), indice, 0))
        for indice, tablero in enumerate(tableros)]
    filas_degradacion = [
        _fila("temple_alpha_pequeno", indice, 0, tablero, resultado)
        for indice, (tablero, resultado) in enumerate(
            zip(tableros, resultados_degradacion))]
    _guardar_csv_detalle(
        filas_degradacion,
        os.path.join(DIRECTORIO_DATOS, "temple_alpha_pequeno.csv"))

    filas_finales = (
        filas_steepest + filas_estocastico + filas_reinicios
        + filas_actividad + filas_mejor)
    _guardar_csv_detalle(
        filas_finales,
        os.path.join(DIRECTORIO_DATOS, "metricas_por_tablero.csv"))

    nombres_config = list(NOMBRES_CONFIGURACIONES.keys())
    metricas_resumen = pd.DataFrame([
        calcular_metricas(filas_finales, configuracion)
        for configuracion in nombres_config
    ])
    notas = {
        "reinicios": (
            f"K = {K_PRINCIPAL}: mayor K redondo por debajo del "
            f"diametro del espacio de estados ({DIAMETRO_8PUZZLE}); "
            "el barrido completo de K esta en reinicios_barrido_k.csv"),
        "temple_mejor": (
            f"T0 = {mejor_t0:g}, alpha = {mejor_alpha:g}: mejor "
            "combinacion del barrido T0 x alpha con el presupuesto "
            "compartido (temple_barrido.csv)"),
    }
    metricas_resumen["nota"] = [
        notas.get(c, "") for c in metricas_resumen["configuracion"]]
    metricas_resumen.to_csv(
        os.path.join(DIRECTORIO_DATOS, "metricas_resumen.csv"),
        index=False)

    # 5. Tabla aparte: temple actividad con presupuesto compartido
    # contra la misma configuracion y las mismas semillas sin tope.
    # Como las semillas coinciden, la unica diferencia es el tope.
    metricas_sin_tope = pd.DataFrame([
        calcular_metricas(filas_actividad, "temple_actividad"),
        calcular_metricas(filas_sin_tope, "temple_actividad_sin_tope"),
    ])
    metricas_reinicios = calcular_metricas(filas_finales, "reinicios")
    sin_tope = metricas_sin_tope.iloc[1]
    comparacion = (
        "MAS" if sin_tope["evaluaciones_promedio"]
        > metricas_reinicios["evaluaciones_promedio"] else "MENOS")
    metricas_sin_tope["nota"] = ""
    metricas_sin_tope.loc[1, "nota"] = (
        f"Sin limite de costo, temple actividad llega a "
        f"{sin_tope['tasa_exito_promedio']:.1f}% gastando "
        f"{sin_tope['evaluaciones_promedio']:.0f} evaluaciones en "
        f"promedio, {comparacion} que reinicios (K = {K_PRINCIPAL}), "
        f"que gasta {metricas_reinicios['evaluaciones_promedio']:.0f} "
        f"y llega a {metricas_reinicios['tasa_exito_promedio']:.1f}%")
    metricas_sin_tope.to_csv(
        os.path.join(DIRECTORIO_DATOS, "temple_sin_tope.csv"),
        index=False)
    _guardar_csv_detalle(
        filas_sin_tope,
        os.path.join(DIRECTORIO_DATOS, "temple_sin_tope_por_tablero.csv"))

    # 6. Figuras.
    for clave in nombres_config:
        caso = _elegir_caso_representativo(filas_finales, clave)
        nombre_bonito = NOMBRES_CONFIGURACIONES[clave]
        etiqueta_estado = (
            "caso resuelto" if caso["resuelto"]
            else "mejor caso (no resuelve ninguno)")
        # En reinicios el "antes" es el tablero asignado: cualquier
        # intento exitoso (directo o con perturbacion) es una secuencia
        # de movimientos legales desde ese tablero.
        titulo = f"{nombre_bonito}: {etiqueta_estado}"
        if clave == "reinicios":
            if caso["cantidad_intentos"] == 1:
                titulo += "\n(intento directo, sin perturbacion)"
            else:
                titulo += (
                    f"\n(con perturbacion de {K_PRINCIPAL} "
                    f"movimientos, {caso['cantidad_intentos']} intentos)")
        if caso["resuelto"] and clave != "steepest":
            titulo += f"\nSolucion de {caso['longitud_solucion']} movimientos"
        fig = viz.comparar_antes_despues(
            caso["estado_inicial"], caso["estado_final"], titulo=titulo)
        viz.guardar_figura(fig, f"antes_despues_{clave}")

    fig_traza_actividad = viz.grafico_traza_temple(
        traza_actividad,
        titulo="Traza de temple (config. actividad: "
               "T0 = 10, alpha = 0.97)")
    viz.guardar_figura(fig_traza_actividad, "temple_actividad_traza")

    fig_traza_mejor = viz.grafico_traza_temple(
        traza_mejor,
        titulo=f"Traza de temple (mejor config.: T0 = {mejor_t0:g}, "
               f"alpha = {mejor_alpha:g})")
    viz.guardar_figura(fig_traza_mejor, "temple_mejor_traza")

    def h_finales_rep0(filas):
        return [f["h_final"] for f in filas if f["repeticion"] == 0]

    fig_degradacion = viz.grafico_h_por_tablero(
        {"h inicial": [f["h_inicial"] for f in filas_steepest],
         "Steepest": h_finales_rep0(filas_steepest),
         f"Temple alpha = {ALPHA_DEGRADACION:g}": [
             f["h_final"] for f in filas_degradacion],
         f"Temple mejor (T0 = {mejor_t0:g}, alpha = {mejor_alpha:g})":
             h_finales_rep0(filas_mejor)},
        "h final por tablero: temple con alpha muy pequeno "
        "frente a steepest")
    viz.guardar_figura(fig_degradacion, "temple_alpha_pequeno_vs_ascenso")

    nombres_bonitos = [NOMBRES_CONFIGURACIONES[c] for c in nombres_config]
    fig_tasa_exito = viz.grafico_barras_comparacion(
        nombres_bonitos, list(metricas_resumen["tasa_exito_promedio"]),
        "Tasa de exito por configuracion (promedio de "
        f"{REPETICIONES} semillas)", "Tasa de exito (%)",
        errores=list(metricas_resumen["tasa_exito_desviacion"]))
    viz.guardar_figura(fig_tasa_exito, "ascenso_temple_tasa_exito")

    fig_evaluaciones = viz.grafico_barras_comparacion(
        nombres_bonitos, list(metricas_resumen["evaluaciones_promedio"]),
        "Evaluaciones promedio por configuracion",
        "Evaluaciones promedio")
    viz.guardar_figura(
        fig_evaluaciones, "ascenso_temple_evaluaciones_promedio")

    fig_efecto_t0 = viz.grafico_efecto_parametro(
        VALORES_T0_BARRIDO,
        {"alpha = 0.97": [
            resultados_t0[t0]["tasa_exito_promedio"]
            for t0 in VALORES_T0_BARRIDO]},
        "T0", "Efecto de T0 sobre la tasa de exito (alpha = 0.97)",
        desviaciones={"alpha = 0.97": [
            resultados_t0[t0]["tasa_exito_desviacion"]
            for t0 in VALORES_T0_BARRIDO]},
        x_categorico=True)
    viz.guardar_figura(fig_efecto_t0, "temple_efecto_t0")

    fig_efecto_alpha = viz.grafico_efecto_parametro(
        VALORES_ALPHA_BARRIDO,
        {"T0 = 10": [
            resultados_alpha[alpha]["tasa_exito_promedio"]
            for alpha in VALORES_ALPHA_BARRIDO]},
        "alpha", "Efecto de alpha sobre la tasa de exito (T0 = 10)",
        desviaciones={"T0 = 10": [
            resultados_alpha[alpha]["tasa_exito_desviacion"]
            for alpha in VALORES_ALPHA_BARRIDO]},
        x_categorico=True)
    viz.guardar_figura(fig_efecto_alpha, "temple_efecto_alpha")

    series_interaccion = {
        f"{t0:g}": [
            resultados_interaccion[t0][alpha]["tasa_exito_promedio"]
            for alpha in VALORES_ALPHA_INTERACCION]
        for t0 in VALORES_T0_INTERACCION
    }
    fig_interaccion = viz.grafico_efecto_parametro(
        VALORES_ALPHA_INTERACCION, series_interaccion, "alpha",
        "Interaccion T0 x alpha sobre la tasa de exito",
        etiqueta_series="T0", x_categorico=True)
    viz.guardar_figura(fig_interaccion, "temple_interaccion_t0_alpha")

    fig_efecto_k = viz.grafico_efecto_parametro(
        VALORES_K_BARRIDO,
        {"Reinicios": [
            resultados_k[k]["tasa_exito_promedio"]
            for k in VALORES_K_BARRIDO]},
        "K (movimientos de la caminata de perturbacion)",
        "Efecto de K sobre la tasa de exito de reinicios",
        desviaciones={"Reinicios": [
            resultados_k[k]["tasa_exito_desviacion"]
            for k in VALORES_K_BARRIDO]},
        linea_vertical=(DIAMETRO_8PUZZLE,
                        f"Diametro del espacio ({DIAMETRO_8PUZZLE})"),
        marcas_x=VALORES_K_BARRIDO)
    viz.guardar_figura(fig_efecto_k, "reinicios_efecto_k")

    metricas_mejor = calcular_metricas(filas_mejor, "temple_mejor")
    fig_longitud_k = viz.grafico_longitud_vs_k(
        VALORES_K_BARRIDO,
        [resultados_k[k]["longitud_solucion_promedio"]
         for k in VALORES_K_BARRIDO],
        DIAMETRO_8PUZZLE,
        {f"Temple mejor (T0 = {mejor_t0:g}, alpha = {mejor_alpha:g})":
         metricas_mejor["longitud_solucion_promedio"]},
        "Longitud de la solucion encontrada segun K")
    viz.guardar_figura(fig_longitud_k, "reinicios_longitud_vs_k")

    total_corridas = CANTIDAD_TABLEROS * REPETICIONES
    fig_sin_tope = viz.grafico_exito_vs_presupuesto(
        {"Temple actividad sin tope (T0 = 10, alpha = 0.97)": (
            _evaluaciones_hasta_resolver(filas_sin_tope),
            total_corridas)},
        presupuesto_evaluaciones,
        "Temple sin tope: exito acumulado segun evaluaciones gastadas")
    viz.guardar_figura(fig_sin_tope, "temple_sin_tope_exito_acumulado")

    return {
        "presupuesto_evaluaciones": presupuesto_evaluaciones,
        "mejor_t0": mejor_t0,
        "mejor_alpha": mejor_alpha,
        "resultados_k": resultados_k,
        "metricas_resumen": metricas_resumen,
        "metricas_sin_tope": metricas_sin_tope,
        "filas_finales": filas_finales,
        "filas_sin_tope": filas_sin_tope,
        "resultados_t0": resultados_t0,
        "resultados_alpha": resultados_alpha,
        "resultados_interaccion": resultados_interaccion,
        "filas_degradacion": filas_degradacion,
    }


if __name__ == "__main__":
    columnas = [
        "configuracion", "tasa_exito_promedio", "tasa_exito_desviacion",
        "tasa_exito_minima", "tasa_exito_maxima", "h_final_promedio",
        "h_final_desviacion", "evaluaciones_promedio",
        "porcentaje_truncadas"]
    columnas_longitud = [
        "configuracion", "corridas_resueltas",
        "longitud_solucion_promedio", "longitud_solucion_desviacion",
        "longitud_solucion_minima", "longitud_solucion_maxima",
        "razon_sobre_optima_promedio"]
    salida = ejecutar_todo()
    print("Presupuesto compartido de evaluaciones:",
          salida["presupuesto_evaluaciones"])
    print("Temple mejor: T0=%g alpha=%g" % (
        salida["mejor_t0"], salida["mejor_alpha"]))
    print("K principal de reinicios:", K_PRINCIPAL)
    print()
    print("Tabla principal (mismo presupuesto):")
    print(salida["metricas_resumen"][columnas].round(2).to_string(
        index=False))
    print()
    print("Longitud de la solucion (solo corridas resueltas):")
    print(salida["metricas_resumen"][columnas_longitud].round(1)
          .to_string(index=False))
    print()
    print("Barrido de K (analisis aparte):")
    tabla_k = pd.DataFrame([
        {"k": k, **{c: m[c] for c in columnas[1:] + columnas_longitud[1:]
                    if c in m}}
        for k, m in salida["resultados_k"].items()])
    print(tabla_k.round(1).to_string(index=False))
    print()
    print("Temple actividad con presupuesto vs sin tope:")
    print(salida["metricas_sin_tope"][columnas].round(2).to_string(
        index=False))
