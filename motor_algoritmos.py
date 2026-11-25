import csv
import math
import time
from collections import deque
from pathlib import Path

DATOS = Path(__file__).resolve().parent / "dataset"

# %% 1. Lectura del dataset
def leer_csv(nombre, separador):
    with open(DATOS / nombre, encoding="utf-8-sig", newline="") as archivo:
        yield from csv.DictReader(archivo, delimiter=separador)

def cargar_datos():
    ubicaciones = {}
    for fila in leer_csv("Storage_Location.csv", ","):
        codigo = fila["originalLocation"].strip().upper()
        ubicaciones[codigo] = (float(fila["x"]), float(fila["y"]))

    apoyos = {}
    for fila in leer_csv("Support_Points_Navigation.csv", ";"):
        codigo = fila["labels"].strip().upper()
        x, y, z = fila["points_specified"].strip("() ").split(",")
        apoyos[codigo] = (float(x), float(y))

    return ubicaciones, apoyos

def ubicaciones_ola(numero, ubicaciones):
    codigos = []
    encontrados = 0
    for fila in leer_csv("Picking_Wave.csv", ";"):
        if fila["waveNumber"].strip() == str(numero):
            encontrados += 1
            codigo = fila["locations"].strip().upper()
            if codigo in ubicaciones and codigo not in codigos:
                codigos.append(codigo)
    if encontrados == 0:
        raise ValueError(f"La ola {numero} no existe en Picking_Wave.csv")
    if not codigos:
        raise ValueError("La ola no contiene ubicaciones válidas")
    return codigos, encontrados


# %% 2. Construcción del grafo
def construir_grafo(ubicaciones, apoyos):
    posiciones, tipos, adyacencia = {}, {}, {}
    grupos, por_y, corredores = {}, {}, {}
    acceso_ubicacion = {}

    def nodo(nombre, x, y, tipo):
        posiciones[nombre] = (x, y)
        tipos[nombre] = tipo
        adyacencia[nombre] = {}

    def arista(a, b, peso):
        adyacencia[a][b] = peso
        adyacencia[b][a] = peso

    for codigo, (x, y) in apoyos.items():
        nombre = "NAV:" + codigo
        nodo(nombre, x, y, "apoyo")
        por_y.setdefault(y, []).append(nombre)
        corredores.setdefault(codigo.split("-")[0], []).append(nombre)

    for codigo, (x, y) in ubicaciones.items():
        nodo("LOC:" + codigo, x, y, "ubicacion")
        partes = codigo.split("-")
        grupos.setdefault((partes[0], partes[1]), []).append(codigo)

    ejes_y = sorted(por_y)
    for (pasillo, columna), codigos in grupos.items():
        xs = sorted(ubicaciones[c][0] for c in codigos)
        x = xs[len(xs) // 2]
        y = min(ejes_y, key=lambda eje: (abs(eje - ubicaciones[codigos[0]][1]), eje))
        acceso = f"ACC:{pasillo}:{columna}"
        nodo(acceso, x, y, "acceso")
        por_y[y].append(acceso)
        for codigo in codigos:
            arista("LOC:" + codigo, acceso, 0)
            acceso_ubicacion[codigo] = acceso

    for nombres in por_y.values():
        nombres.sort(key=lambda n: posiciones[n][0])
        for a, b in zip(nombres, nombres[1:]):
            arista(a, b, abs(posiciones[a][0] - posiciones[b][0]))

    for nombres in corredores.values():
        nombres.sort(key=lambda n: posiciones[n][1])
        for a, b in zip(nombres, nombres[1:]):
            arista(a, b, abs(posiciones[a][1] - posiciones[b][1]))

    return posiciones, tipos, adyacencia, acceso_ubicacion


# %% 2.1. Bloqueos por posición física

def expandir_cierres(posiciones, tipos, codigos):
    """Un código de acceso bloquea todos los accesos de su coordenada X/Y."""
    codigos = set(codigos)
    if any(tipos.get(c) != "acceso" for c in codigos):
        raise ValueError("La lista de cierres contiene accesos no válidos")
    puntos = {posiciones[c] for c in codigos}
    if posiciones["NAV:CC-08"] in puntos:
        raise ValueError("No se puede bloquear la posición del depósito CC-08")
    return {n for n, xy in posiciones.items() if tipos[n] == "acceso" and xy in puntos}


def tramo_bloqueado(a, b, puntos):
    """Comprueba si un tramo recto de desplazamiento toca un punto cerrado."""
    x1, y1 = a
    x2, y2 = b
    if x1 == x2:
        return any(x == x1 and min(y1, y2) <= y <= max(y1, y2) for x, y in puntos)
    if y1 == y2:
        return any(y == y1 and min(x1, x2) <= x <= max(x1, x2) for x, y in puntos)
    # El modelo actual es ortogonal; esta comprobación cubre también una diagonal.
    return any(min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)
               and math.isclose((x-x1)*(y2-y1), (y-y1)*(x2-x1), abs_tol=1e-8)
               for x, y in puntos)


def aplicar_bloqueos(posiciones, tipos, grafo, codigos):
    cerrados = expandir_cierres(posiciones, tipos, codigos)
    puntos = {posiciones[c] for c in cerrados}
    # También se bloquean apoyos de navegación en la misma coordenada.
    nodos_bloqueados = {n for n, xy in posiciones.items()
                       if tipos[n] in ("acceso", "apoyo") and xy in puntos}
    # Un corredor puede contener una arista que cruza el punto sin tenerlo como extremo.
    activo = {n: {v: peso for v, peso in vecinos.items()
                  if v not in nodos_bloqueados and
                  not (puntos and peso > 0 and tramo_bloqueado(posiciones[n], posiciones[v], puntos))}
              for n, vecinos in grafo.items() if n not in nodos_bloqueados}
    return activo, cerrados, puntos, nodos_bloqueados


# %% 3. BFS y Bellman-Ford
def bfs(adyacencia, inicio, devolver_visitados=False):
    visitados = {inicio}
    cola = deque([inicio])
    while cola:
        actual = cola.popleft()
        for vecino in adyacencia[actual]:
            if vecino not in visitados:
                visitados.add(vecino)
                cola.append(vecino)
    return visitados if devolver_visitados else len(visitados)

def bellman_ford(adyacencia, inicio):
    distancias = {n: math.inf for n in adyacencia}
    padres = {}
    distancias[inicio] = 0
    aristas = [(a, b, peso) for a, vecinos in adyacencia.items()
               for b, peso in vecinos.items()]
    for _ in range(len(adyacencia) - 1):
        cambio = False
        for a, b, peso in aristas:
            if distancias[a] + peso < distancias[b]:
                distancias[b] = distancias[a] + peso
                padres[b] = a
                cambio = True
        if not cambio:
            break
    return distancias, padres

def camino(padres, inicio, final):
    ruta = [final]
    while ruta[-1] != inicio:
        if ruta[-1] not in padres:
            raise ValueError("No existe camino entre las ubicaciones")
        ruta.append(padres[ruta[-1]])
    return ruta[::-1]

def calcular_matriz(adyacencia, paradas):
    matriz, padres = [], {}
    for parada in paradas:
        distancias, predecesores = bellman_ford(adyacencia, parada)
        matriz.append([distancias[otro] for otro in paradas])
        padres[parada] = predecesores
    return matriz, padres


# %% 4. Optimización de rutas
def distancia_ruta(ruta, matriz):
    return sum(matriz[a][b] for a, b in zip(ruta, ruta[1:]))

def vecino_cercano(matriz):
    restantes = set(range(1, len(matriz)))
    ruta = [0]
    while restantes:
        siguiente = min(restantes, key=lambda j: (matriz[ruta[-1]][j], j))
        ruta.append(siguiente)
        restantes.remove(siguiente)
    return ruta + [0]

def mejorar_2opt(ruta, matriz):
    ruta = ruta[:]
    while True:
        mejoro = False
        for i in range(1, len(ruta) - 2):
            for j in range(i + 1, len(ruta) - 1):
                a, b, c, d = ruta[i-1], ruta[i], ruta[j], ruta[j+1]
                if matriz[a][c] + matriz[b][d] < matriz[a][b] + matriz[c][d]:
                    ruta[i:j+1] = reversed(ruta[i:j+1])
                    mejoro = True
        if not mejoro:
            return ruta

def programacion_dinamica(matriz):
    n = len(matriz) - 1
    dp = {(1 << j, j): (matriz[0][j+1], None) for j in range(n)}
    for mascara in range(1, 1 << n):
        for j in range(n):
            if not (mascara & (1 << j)) or mascara == 1 << j:
                continue
            previa = mascara ^ (1 << j)
            dp[mascara, j] = min(
                (dp[previa, k][0] + matriz[k+1][j+1], k)
                for k in range(n) if previa & (1 << k)
            )
    mascara = (1 << n) - 1
    ultimo = min(range(n), key=lambda j: dp[mascara, j][0] + matriz[j+1][0])
    ruta = []
    while ultimo is not None:
        ruta.append(ultimo + 1)
        anterior = dp[mascara, ultimo][1]
        mascara ^= 1 << ultimo
        ultimo = anterior
    return [0] + ruta[::-1] + [0]

def ruta_completa(orden, paradas, padres):
    ruta = []
    for a, b in zip(orden, orden[1:]):
        tramo = camino(padres[paradas[a]], paradas[a], paradas[b])
        ruta.extend(tramo if not ruta else tramo[1:])
    return ruta

def analizar(numero, puntos_manuales=None, accesos_cerrados=()):
    ubicaciones, apoyos = cargar_datos()
    posiciones, tipos, grafo_original, accesos = construir_grafo(ubicaciones, apoyos)
    deposito = "NAV:CC-08"
    grafo, cerrados, puntos_cerrados, nodos_bloqueados = aplicar_bloqueos(
        posiciones, tipos, grafo_original, accesos_cerrados)

    if puntos_manuales is None:
        codigos, registros = ubicaciones_ola(numero, ubicaciones)
    else:
        codigos = list(dict.fromkeys(puntos_manuales))
        if not codigos:
            raise ValueError("Selecciona al menos una ubicación de almacenamiento")
        if any(c not in ubicaciones for c in codigos):
            raise ValueError("La selección contiene ubicaciones no válidas")
        registros = len(codigos)

    # La ola contiene ubicaciones, pero el recorrido visita sus accesos.
    paradas = [deposito] + list(dict.fromkeys(accesos[c] for c in codigos))
    bloqueadas = [c for c in codigos if accesos[c] in cerrados]
    if bloqueadas:
        raise ValueError("Ubicaciones con acceso cerrado: " + ", ".join(bloqueadas)
                         + ". Reabre sus accesos o modifica la ola.")

    alcanzables = bfs(grafo, deposito, devolver_visitados=True)
    conectados = len(alcanzables)
    # Con cierres pueden quedar zonas aisladas. Solo exigimos que todos los
    # destinos de la ola sean alcanzables desde el depósito.
    if cerrados:
        inaccesibles = [c for c in codigos if accesos[c] not in alcanzables]
        if inaccesibles:
            raise ValueError("No existe ruta hacia: " + ", ".join(inaccesibles)
                             + ". Revisa los accesos cerrados.")
    elif conectados != len(grafo):
        raise ValueError("El grafo no está conectado")
    cantidad_ubicaciones = len(codigos)

    inicio = time.perf_counter()
    matriz, padres = calcular_matriz(grafo, paradas)
    tiempo_bf = time.perf_counter() - inicio
    referencia = [0] + list(range(1, len(paradas))) + [0]
    inicio = time.perf_counter()
    heuristica = mejorar_2opt(vecino_cercano(matriz), matriz)
    tiempo_h = time.perf_counter() - inicio
    elegida, metodo = heuristica, "Vecino cercano + 2-opt (heurística)"
    tiempo_dp = None
    if len(paradas) - 1 <= 10:
        inicio = time.perf_counter()
        elegida = programacion_dinamica(matriz)
        tiempo_dp = time.perf_counter() - inicio
        metodo = "Programación dinámica (óptima en el modelo)"
    elif distancia_ruta(referencia, matriz) < distancia_ruta(heuristica, matriz):
        elegida, metodo = referencia, "Orden de referencia (sin mejora)"

    original = distancia_ruta(referencia, matriz)
    propuesta = distancia_ruta(elegida, matriz)
    return {
        "numero": numero, "posiciones": posiciones, "tipos": tipos, "grafo": grafo,
        "conectados": conectados, "registros": registros, "ubicaciones": cantidad_ubicaciones,
        "manual": puntos_manuales is not None,
        "codigos_ubicaciones": codigos,
        "acceso_ubicacion": {c: accesos[c] for c in codigos},
        "cerrados": sorted(cerrados),
        "puntos_cerrados": sorted(puntos_cerrados),
        "nodos_bloqueados": sorted(nodos_bloqueados),
        "nodos_originales": len(grafo_original),
        "aristas_originales": sum(len(v) for v in grafo_original.values()) // 2,
        "paradas": paradas,
        "orden_referencia": [paradas[i] for i in referencia],
        "orden_propuesta": [paradas[i] for i in elegida],
        "accesos": len(paradas)-1, "referencia": original, "propuesta": propuesta,
        "heuristica": distancia_ruta(heuristica, matriz), "metodo": metodo,
        "tiempo_bf": tiempo_bf, "tiempo_h": tiempo_h, "tiempo_dp": tiempo_dp,
        "ruta_referencia": ruta_completa(referencia, paradas, padres),
        "ruta_propuesta": ruta_completa(elegida, paradas, padres),
    }
