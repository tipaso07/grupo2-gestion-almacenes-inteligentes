# %% 1. Datos del plano
from collections import defaultdict
from functools import lru_cache

import plotly.graph_objects as go

from motor_algoritmos import cargar_datos, construir_grafo, leer_csv

AZUL = "#000059"
CELESTE = "#329AD6"
VERDE = "#16835D"
ROJO = "#D32F2F"


@lru_cache(maxsize=1)
def datos_selector():
    return construir_grafo(*cargar_datos())


@lru_cache(maxsize=1)
def niveles_ubicaciones():
    return {fila["originalLocation"].strip().upper(): int(float(fila["z"]))
            for fila in leer_csv("Storage_Location.csv", ",")}


def lista_accesos():
    return sorted(set(datos_selector()[3].values()))


def lista_ubicaciones(nivel=None):
    niveles = niveles_ubicaciones()
    return sorted(c for c in datos_selector()[3]
                  if nivel is None or niveles.get(c) == nivel)


def grupos_plano(tipo, nivel=None):
    posiciones, tipos, _, _ = datos_selector()
    niveles = niveles_ubicaciones()
    grupos = defaultdict(list)
    for nodo, xy in posiciones.items():
        if tipos[nodo] != tipo:
            continue
        codigo = nodo[4:] if tipo == "ubicacion" else nodo
        if tipo == "ubicacion" and nivel is not None and niveles.get(codigo) != nivel:
            continue
        grupos[xy].append(codigo)
    return [(xy, sorted(codigos)) for xy, codigos in grupos.items()]


# %% 2. Grafo interactivo

def crear_selector(seleccionados=(), cerrados=(), nivel=None, tipo_activo="ubicacion"):
    posiciones, tipos, grafo, _ = datos_selector()
    orden = {c: i for i, c in enumerate(seleccionados, 1)}
    cerrados = set(cerrados)
    figura = go.Figure()
    xs, ys = [], []
    for a, vecinos in grafo.items():
        for b, peso in vecinos.items():
            if a < b and peso > 0 and a not in cerrados and b not in cerrados:
                xs.extend([posiciones[a][0], posiciones[b][0], None])
                ys.extend([posiciones[a][1], posiciones[b][1], None])
    figura.add_trace(go.Scatter(x=xs, y=ys, mode="lines",
        line=dict(color="#DEE7F1", width=1), hoverinfo="skip", showlegend=False))

    apoyos = [n for n in posiciones if tipos[n] == "apoyo" and n != "NAV:CC-08"]
    figura.add_trace(go.Scatter(x=[posiciones[n][0] for n in apoyos],
        y=[posiciones[n][1] for n in apoyos], mode="markers",
        marker=dict(size=8, color=CELESTE, symbol="diamond"), name="Navegación",
        hoverinfo="skip", selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=1))))
    x, y = posiciones["NAV:CC-08"]
    figura.add_trace(go.Scatter(x=[x], y=[y], mode="markers",
        marker=dict(size=14, color=CELESTE, symbol="diamond", line=dict(color=AZUL, width=2)),
        name="Depósito CC-08", hovertemplate="Depósito CC-08<extra></extra>",
        selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1))))

    # Las marcas verdes y rojas dependen de la selección persistida en Python,
    # no de la selección temporal de Plotly. Se dibujan al final, por encima del fondo.
    estados = {"disponible": [], "abierto": [], "elegido": [], "cerrado": []}
    for tipo in ("ubicacion", "acceso"):
        for xy, codigos in grupos_plano(tipo, nivel):
            marcados = [c for c in codigos if c in (orden if tipo == "ubicacion" else cerrados)]
            if tipo == "ubicacion":
                estado = "elegido" if marcados else "disponible"
                etiqueta = ",".join(str(orden[c]) for c in marcados)
                hover = "<br>".join(c + (" · seleccionada" if c in orden else " · disponible") for c in codigos)
            else:
                estado = "cerrado" if marcados else "abierto"
                etiqueta = "" if not marcados or len(marcados) == len(codigos) else f"{len(marcados)}/{len(codigos)}"
                hover = "<br>".join(c + (" · cerrado" if c in cerrados else " · abierto") for c in codigos)
            estados[estado].append((xy, [tipo, *codigos], etiqueta, hover))

    estilos = {
        "disponible": ("Ubicación disponible", CELESTE, 7, "circle", .6),
        "abierto": ("Acceso abierto", AZUL, 8, "circle", .6),
        "elegido": ("Ubicación seleccionada", VERDE, 15, "circle", 1.8),
        "cerrado": ("Acceso cerrado (total o parcial)", ROJO, 15, "x", 1.5),
    }
    # El tipo activo queda al frente para facilitar el clic cuando se solapan tipos.
    orden_trazas = (["abierto", "disponible", "cerrado", "elegido"] if tipo_activo == "ubicacion"
                    else ["disponible", "abierto", "elegido", "cerrado"])
    for estado in orden_trazas:
        puntos = estados[estado]
        nombre, color, tam, simbolo, borde = estilos[estado]
        figura.add_trace(go.Scatter(
            x=[p[0][0] for p in puntos], y=[p[0][1] for p in puntos],
            mode="markers+text" if estado in ("elegido", "cerrado") else "markers",
            text=[p[2] for p in puntos], textposition="top center",
            textfont=dict(size=12, color=color, family="Arial"),
            customdata=[p[1] for p in puntos], hovertext=[p[3] for p in puntos],
            hovertemplate="%{hovertext}<extra></extra>", name=nombre,
            marker=dict(size=tam, color=color, symbol=simbolo, opacity=1,
                        line=dict(color="#FFFFFF" if estado != "cerrado" else ROJO, width=borde)),
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)),
        ))
    figura.update_layout(height=930, clickmode="event+select", dragmode="pan",
        hovermode="closest", margin=dict(l=50, r=20, t=15, b=90),
        paper_bgcolor="white", plot_bgcolor="white", font=dict(color=AZUL),
        legend=dict(orientation="h", y=-.10))
    figura.update_xaxes(title="X (unidades del plano)", range=[35,715], gridcolor="#E5E9F1", constrain="domain")
    figura.update_yaxes(title="Y (unidades del plano)", range=[-70,1515], gridcolor="#E5E9F1", scaleanchor="x", scaleratio=1)
    return figura


def puntos_del_evento(evento, tipo_activo=None):
    validos = {"ubicacion": set(lista_ubicaciones()), "acceso": set(lista_accesos())}
    for punto in evento.selection.points:
        dato = punto.get("customdata")
        if isinstance(dato, (list, tuple)) and len(dato) > 1 and dato[0] in validos:
            if tipo_activo is not None and dato[0] != tipo_activo:
                continue
            codigos = [c for c in dato[1:] if c in validos[dato[0]]]
            if codigos:
                return dato[0], codigos
    return None
