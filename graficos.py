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
        puntos = [posiciones[n] for n in posiciones if tipos[n] == tipo]
        ax.scatter([p[0] for p in puntos], [p[1] for p in puntos],
                   s=tam, c=color, label=tipo.capitalize(), zorder=3)
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
    writer.writerow([datos["numero"], "Orden de filas CSV", datos["referencia"], ""])
    writer.writerow([datos["numero"], "Vecino cercano + 2-opt", datos["heuristica"], datos["tiempo_h"]])
    if datos["tiempo_dp"] is not None:
        writer.writerow([datos["numero"], "Programación dinámica", datos["propuesta"], datos["tiempo_dp"]])
    return archivo.getvalue().encode("utf-8-sig")


def comprimir(archivos):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_resultados:
        for nombre, contenido in archivos.items():
            zip_resultados.writestr(nombre, contenido)
    return buffer.getvalue()
