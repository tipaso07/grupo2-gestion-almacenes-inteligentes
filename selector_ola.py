# %% 1. Datos del plano
from collections import defaultdict
from functools import lru_cache

import plotly.graph_objects as go

from motor_algoritmos import cargar_datos, construir_grafo

AZUL = "#000059"
CELESTE = "#329AD6"
ROJO = "#D32F2F"


@lru_cache(maxsize=1)
def datos_selector():
    return construir_grafo(*cargar_datos())


def lista_accesos():
    return sorted(set(datos_selector()[3].values()))


def lista_ubicaciones():
    return sorted(datos_selector()[3])


def grupos_plano(tipo):
    posiciones, tipos, _, _ = datos_selector()
    grupos = defaultdict(list)
    for nodo, xy in posiciones.items():
        if tipos[nodo] == tipo:
            grupos[xy].append(nodo[4:] if tipo == "ubicacion" else nodo)
    return [(xy, sorted(codigos)) for xy, codigos in grupos.items()]


# %% 2. Grafo interactivo

def crear_selector(seleccionados=(), cerrados=()):
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
        marker=dict(size=9, color=CELESTE, symbol="diamond"), name="Navegación",
        hoverinfo="skip"))
    x, y = posiciones["NAV:CC-08"]
    figura.add_trace(go.Scatter(x=[x], y=[y], mode="markers",
        marker=dict(size=15, color=CELESTE, symbol="diamond", line=dict(color=AZUL,width=2)),
        name="Depósito CC-08", hovertemplate="Depósito CC-08<extra></extra>"))

    # Un marcador por coordenada; los códigos superpuestos se distinguen en la interfaz.
    for tipo, nombre in [("ubicacion", "Ubicaciones de almacenamiento"), ("acceso", "Puntos de acceso")]:
        grupos = grupos_plano(tipo)
        colores, tamanos, etiquetas, hover = [], [], [], []
        for xy, codigos in grupos:
            if tipo == "ubicacion":
                numeros = [str(orden[c]) for c in codigos if c in orden]
                colores.append("#16835D" if numeros else CELESTE)
                tamanos.append(10 if numeros else 6)
                etiquetas.append(",".join(numeros))
                hover.append("<br>".join(codigos))
            else:
                bloqueados = [c for c in codigos if c in cerrados]
                colores.append(ROJO if bloqueados else AZUL)
                tamanos.append(12 if bloqueados else 8)
                etiquetas.append("")
                hover.append("<br>".join(c + (" · cerrado" if c in cerrados else " · abierto") for c in codigos))
        figura.add_trace(go.Scatter(
            x=[xy[0] for xy, _ in grupos], y=[xy[1] for xy, _ in grupos],
            mode="markers+text", text=etiquetas, textposition="top center",
            textfont=dict(size=11, color=AZUL),
            customdata=[[tipo, *codigos] for _, codigos in grupos],
            hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
            marker=dict(size=tamanos, color=colores, line=dict(color="#FFFFFF", width=.5)), name=nombre))
    figura.update_layout(height=800, clickmode="event+select", dragmode="zoom",
        margin=dict(l=50,r=20,t=15,b=70), paper_bgcolor="white",plot_bgcolor="white",
        font=dict(color=AZUL), legend=dict(orientation="h", y=-.10))
    figura.update_xaxes(title="X (unidades del plano)",range=[35,715],gridcolor="#E5E9F1",constrain="domain")
    figura.update_yaxes(title="Y (unidades del plano)",range=[-70,1515],gridcolor="#E5E9F1",scaleanchor="x",scaleratio=1)
    return figura


def puntos_del_evento(evento):
    validos = {"ubicacion": set(lista_ubicaciones()), "acceso": set(lista_accesos())}
    for punto in evento.selection.points:
        dato = punto.get("customdata")
        if isinstance(dato,(list,tuple)) and len(dato)>1 and dato[0] in validos:
            codigos = [c for c in dato[1:] if c in validos[dato[0]]]
            if codigos:
                return dato[0], codigos
    return None
