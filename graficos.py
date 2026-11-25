import csv
import io
import math
import zipfile
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

AZUL = "#000059"
BLANCO = "#ffffff"
CELESTE = "#329AD6"
VERDE = "#16835D"
ROJO = "#D32F2F"


# %% 1. Verificación y comparación de recorridos

def verificar_recorrido(datos, tipo):
    """Comprueba la distancia con las aristas reales, incluyendo repeticiones."""
    if tipo not in ("referencia", "propuesta"):
        raise ValueError("Tipo de recorrido no válido")
    ruta = datos[f"ruta_{tipo}"]
    grafo = datos["grafo"]
    cerrados = set(datos.get("cerrados", ()))
    orden = datos[f"orden_{tipo}"]
    if not ruta or ruta[0] != "NAV:CC-08" or ruta[-1] != "NAV:CC-08":
        raise ValueError(f"La ruta de {tipo} no empieza y termina en el depósito")
    if any(n in cerrados or n not in grafo for n in ruta):
        raise ValueError(f"La ruta de {tipo} contiene nodos cerrados o no válidos")
    if not set(orden).issubset(ruta):
        raise ValueError(f"La ruta de {tipo} no incluye todas sus paradas")
    distancia = 0.0
    pasos = 0
    segmentos = Counter()
    direcciones = Counter()
    posiciones = datos["posiciones"]
    for a, b in zip(ruta, ruta[1:]):
        if b not in grafo[a]:
            raise ValueError(f"Arista no válida en la ruta de {tipo}: {a} → {b}")
        peso = grafo[a][b]
        distancia += peso
        if peso > 0:
            pasos += 1
            origen, destino = posiciones[a], posiciones[b]
            if origen != destino:
                # Agrupar por tramo visible, no por código lógico (pueden coincidir).
                segmentos[tuple(sorted((origen, destino)))] += 1
                direcciones[(origen, destino)] += 1
    if not math.isclose(distancia, datos[tipo], rel_tol=1e-9, abs_tol=1e-7):
        raise ValueError(f"La distancia de {tipo} no coincide con las aristas recorridas")
    return {"distancia": distancia, "pasos": pasos, "segmentos": segmentos,
            "direcciones": direcciones, "repeticiones": sum(n - 1 for n in segmentos.values())}


def comparar_recorridos(datos):
    ref = verificar_recorrido(datos, "referencia")
    prop = verificar_recorrido(datos, "propuesta")
    resumen = []
    for nombre, info in (("Referencia", ref), ("Propuesta", prop)):
        resumen.append({"Ruta": nombre, "Distancia verificada (u)": info["distancia"],
                        "Tramos transitados (con repeticiones)": info["pasos"],
                        "Tramos visibles distintos": len(info["segmentos"]),
                        "Repeticiones de tramos visibles": info["repeticiones"]})
    grupos = defaultdict(list)
    for codigo in datos["codigos_ubicaciones"]:
        grupos[datos["acceso_ubicacion"][codigo]].append(codigo)
    visitas = []
    for i, (a, b) in enumerate(zip(datos["orden_referencia"], datos["orden_propuesta"])):
        visitas.append({"Paso": i, "Referencia": a,
                        "Ubicaciones (ref.)": ", ".join(grupos[a]) or "Depósito",
                        "Propuesta": b,
                        "Ubicaciones (prop.)": ", ".join(grupos[b]) or "Depósito"})
    return resumen, visitas


# %% 2. Visualización

def _ancho(n):
    # Misma escala para ambas rutas. El crecimiento se limita para evitar saturación.
    return min(8.0, 1.3 + 1.05 * math.sqrt(n))


def _dibujar_recorrido(ax, datos, tipo, info):
    posiciones = datos["posiciones"]
    color = AZUL
    for (a, b), n in info["segmentos"].items():
        ax.plot([a[0], b[0]], [a[1], b[1]], color=color,
                linewidth=_ancho(n), solid_capstyle="round", zorder=4)
        largo = math.dist(a, b)
        # Flechas en el centro del tramo; si se usa en ambos sentidos, separar ambas.
        if largo >= 24:
            ux, uy = (b[0]-a[0])/largo, (b[1]-a[1])/largo
            doble = (a, b) in info["direcciones"] and (b, a) in info["direcciones"]
            mx, my = (a[0]+b[0])/2, (a[1]+b[1])/2
            for origen, destino, signo in ((a, b, 1), (b, a, -1)):
                if (origen, destino) not in info["direcciones"]:
                    continue
                desplaz = 5 * signo if doble else 0
                cx, cy = mx-uy*desplaz, my+ux*desplaz
                mitad = min(13, largo*.26)
                ax.annotate("", xy=(cx+ux*mitad*signo, cy+uy*mitad*signo),
                            xytext=(cx-ux*mitad*signo, cy-uy*mitad*signo),
                            arrowprops=dict(arrowstyle="-|>", color=CELESTE,
                                            lw=.9, mutation_scale=8, shrinkA=0, shrinkB=0),
                            zorder=7)
        if n > 1 and largo >= 40:
            ax.annotate(f"{n}×", ((a[0]+b[0])/2, (a[1]+b[1])/2),
                        xytext=(0, -8) if abs(b[0]-a[0]) > abs(b[1]-a[1]) else (8, 0),
                        textcoords="offset points", ha="center", va="center", fontsize=6,
                        color=AZUL, bbox=dict(fc=BLANCO, ec="none", alpha=.86, pad=.6), zorder=8)

    # Los números señalan el orden planificado de recogida por acceso, no cada tránsito.
    paradas_xy = defaultdict(list)
    for i, nodo in enumerate(datos[f"orden_{tipo}"][1:-1], 1):
        paradas_xy[posiciones[nodo]].append(str(i))
    for (x, y), numeros in paradas_xy.items():
        ax.scatter([x], [y], s=24, color=VERDE, edgecolors=BLANCO, linewidths=.5, zorder=9)
        ax.annotate(",".join(numeros), (x, y), xytext=(0, 7), textcoords="offset points",
                    ha="center", va="bottom", fontsize=7, fontweight="bold", color=AZUL,
                    bbox=dict(boxstyle="round,pad=.18", fc=BLANCO, ec=VERDE, lw=.65), zorder=10)

    # Conexión conceptual de producto a acceso (peso cero en el modelo).
    for codigo in datos.get("codigos_ubicaciones", []):
        x, y = posiciones["LOC:" + codigo]
        a, b = posiciones[datos["acceso_ubicacion"][codigo]]
        ax.plot([x, a], [y, b], color=VERDE, linestyle=":", linewidth=.85, alpha=.65, zorder=2.5)


def crear_grafico(datos, titulo, ruta=None, tipo=None):
    posiciones, tipos, grafo = datos["posiciones"], datos["tipos"], datos["grafo"]
    if ruta is not None:
        if tipo is None:
            tipo = "referencia" if ruta == datos["ruta_referencia"] else "propuesta"
        if ruta != datos[f"ruta_{tipo}"]:
            raise ValueError("El recorrido no corresponde al tipo solicitado")
        info = verificar_recorrido(datos, tipo)
    else:
        info = None
    fig, ax = plt.subplots(figsize=(8, 12))
    cerrados = set(datos.get("cerrados", ()))
    for a, vecinos in grafo.items():
        for b, peso in vecinos.items():
            if a < b and peso > 0:
                x1, y1 = posiciones[a]
                x2, y2 = posiciones[b]
                ax.plot([x1, x2], [y1, y2], color="#DEE7F1", linewidth=.65, zorder=1)
    for clase, color, tam, nombre in (("ubicacion", CELESTE, 5, "Ubicación"),
                                      ("acceso", AZUL, 5, "Acceso abierto"),
                                      ("apoyo", CELESTE, 28, "Apoyo")):
        puntos = [posiciones[n] for n in posiciones if tipos[n] == clase and n not in cerrados]
        ax.scatter([p[0] for p in puntos], [p[1] for p in puntos], s=tam,
                   c=color, label=nombre, zorder=3)
    elegidos = [posiciones["LOC:" + c] for c in datos.get("codigos_ubicaciones", [])]
    if elegidos:
        ax.scatter([p[0] for p in elegidos], [p[1] for p in elegidos], s=24,
                   color=VERDE, label="Ubicaciones de la ola", zorder=8)
    if info is not None:
        _dibujar_recorrido(ax, datos, tipo, info)
    # En coordenadas compartidas, no representar un cierre parcial como cierre total.
    accesos_xy = defaultdict(list)
    for n, xy in posiciones.items():
        if tipos[n] == "acceso":
            accesos_xy[xy].append(n)
    parcial, total = [], []
    for xy, nodos in accesos_xy.items():
        cantidad = sum(n in cerrados for n in nodos)
        if cantidad:
            (total if cantidad == len(nodos) else parcial).append(xy)
    if total:
        ax.scatter([p[0] for p in total], [p[1] for p in total], s=48,
                   color=ROJO, marker="x", linewidths=1.6, label="Acceso cerrado (total)", zorder=11)
    if parcial:
        ax.scatter([p[0] for p in parcial], [p[1] for p in parcial], s=72,
                   facecolors="none", edgecolors=ROJO, marker="o", linewidths=1.5,
                   label="Cierre parcial (accesos superpuestos)", zorder=11)
    x, y = posiciones["NAV:CC-08"]
    ax.scatter([x], [y], s=85, c=CELESTE, edgecolors=AZUL, label="Depósito CC-08", zorder=12)
    if info is not None:
        subtitulo = (f"{info['distancia']:,.0f} u · {info['pasos']} tránsitos · "
                     f"{info['repeticiones']} repeticiones visibles")
    else:
        subtitulo = f"{len(grafo):,} nodos activos · {sum(len(v) for v in grafo.values())//2:,} aristas activas"
    fig.suptitle(titulo, color=AZUL, fontsize=15, fontweight="bold", y=.975)
    ax.set_title(subtitulo, color=AZUL, fontsize=10, pad=9)
    ax.set_xlabel("X (unidades del plano)", color=AZUL)
    ax.set_ylabel("Y (unidades del plano)", color=AZUL)
    ax.set_xlim(35, 715)
    ax.set_ylim(-70, 1515)
    ax.set_aspect("equal")
    ax.grid(alpha=.15)
    handles, labels = ax.get_legend_handles_labels()
    if info is not None:
        handles.extend([Line2D([0],[0],color=AZUL,lw=_ancho(1)),
                        Line2D([0],[0],color=AZUL,lw=_ancho(4)),
                        Line2D([0],[0],color=CELESTE,marker=">",lw=1),
                        Line2D([0],[0],color=VERDE,ls=":",lw=1)])
        labels.extend(["Tramo: 1 tránsito", "Tramo: 4 tránsitos", "Sentido del tránsito", "Ubicación → acceso (sin costo)"])
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(.5,.018),
               ncol=2, fontsize=8, frameon=False)
    if info is not None:
        fig.text(.5,.135,"Recuadros numerados: orden de recogida. n×: cantidad de tránsitos.",
                 color=AZUL, ha="center", fontsize=8)
    fig.subplots_adjust(top=.925, bottom=.185 if info is not None else .12, left=.11, right=.96)
    salida = io.BytesIO()
    fig.savefig(salida, format="png", dpi=160, facecolor=BLANCO)
    plt.close(fig)
    return salida.getvalue()


# %% 3. Exportaciones
def crear_csv(datos):
    archivo = io.StringIO()
    writer = csv.writer(archivo)
    writer.writerow(["ola", "metodo", "distancia_u", "tiempo_segundos"])
    origen = "Orden de selección manual" if datos.get("manual") else "Orden de filas CSV"
    writer.writerow([datos["numero"], origen, datos["referencia"], ""])
    writer.writerow([datos["numero"], "Vecino cercano + 2-opt", datos["heuristica"], datos["tiempo_h"]])
    if datos["tiempo_dp"] is not None:
        writer.writerow([datos["numero"], "Programación dinámica", datos["propuesta"], datos["tiempo_dp"]])
    return archivo.getvalue().encode("utf-8-sig")


def crear_csv_ubicaciones(datos):
    archivo = io.StringIO()
    writer = csv.writer(archivo)
    writer.writerow(["orden_recogida", "ubicacion", "acceso"])
    orden = {a: i for i, a in enumerate(datos["orden_propuesta"][:-1])}
    ubicaciones = sorted(datos["codigos_ubicaciones"], key=lambda c: orden[datos["acceso_ubicacion"][c]])
    for i, c in enumerate(ubicaciones, 1):
        writer.writerow([i, c, datos["acceso_ubicacion"][c]])
    return archivo.getvalue().encode("utf-8-sig")


def crear_csv_cierres(datos):
    archivo = io.StringIO()
    writer = csv.writer(archivo)
    writer.writerow(["acceso_cerrado"])
    writer.writerows([c] for c in datos["cerrados"])
    return archivo.getvalue().encode("utf-8-sig")


def comprimir(archivos):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_resultados:
        for nombre, contenido in archivos.items():
            zip_resultados.writestr(nombre, contenido)
    return buffer.getvalue()
