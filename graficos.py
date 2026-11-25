import csv
import io
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AZUL = "#000059"
BLANCO = "#ffffff"
CELESTE = "#329AD6"

def crear_grafico(datos, titulo, ruta=None):
    fig, ax = plt.subplots(figsize=(7, 11))
    posiciones, tipos, grafo = datos["posiciones"], datos["tipos"], datos["grafo"]
    for a, vecinos in grafo.items():
        for b, peso in vecinos.items():
            if a < b and peso > 0:
                x1, y1 = posiciones[a]
                x2, y2 = posiciones[b]
                ax.plot([x1, x2], [y1, y2], color="#DEE7F1", linewidth=0.65)
    for tipo, color, tam in (("ubicacion", CELESTE, 5),
                             ("acceso", AZUL, 5), ("apoyo", CELESTE, 28)):
        puntos = [posiciones[n] for n in posiciones if tipos[n] == tipo and n not in datos.get("cerrados", ())]
        ax.scatter([p[0] for p in puntos], [p[1] for p in puntos],
                   s=tam, c=color, label=tipo.capitalize(), zorder=3)
    elegidos = [posiciones["LOC:" + c] for c in datos.get("codigos_ubicaciones", [])]
    if elegidos:
        ax.scatter([p[0] for p in elegidos], [p[1] for p in elegidos], s=24,
                   color="#16835D", label="Ubicaciones de la ola", zorder=5)
    cerrados = [posiciones[n] for n in datos.get("cerrados", [])]
    if cerrados:
        ax.scatter([p[0] for p in cerrados], [p[1] for p in cerrados], s=35,
                   color="#D32F2F", marker="x", label="Acceso cerrado", zorder=6)
    if ruta:
        puntos = [posiciones[n] for n in ruta]
        ax.plot([p[0] for p in puntos], [p[1] for p in puntos],
                color=AZUL, linewidth=2.2, label="Recorrido", zorder=4)
        ax.scatter([puntos[0][0]], [puntos[0][1]], s=85,
                   c=CELESTE, edgecolors=AZUL, label="Depósito", zorder=5)
    ax.set_title(titulo, color=AZUL, fontsize=14, fontweight="bold")
    ax.set_xlabel("X (unidades del plano)", color=AZUL)
    ax.set_ylabel("Y (unidades del plano)", color=AZUL)
    ax.set_xlim(35, 715)
    ax.set_ylim(-70, 1515)
    ax.set_aspect("equal")
    ax.grid(alpha=0.15)
    ax.legend(loc="lower right")
    fig.tight_layout()
    salida = io.BytesIO()
    fig.savefig(salida, format="png", dpi=140, facecolor=BLANCO)
    plt.close(fig)
    return salida.getvalue()


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
