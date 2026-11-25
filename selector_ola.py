# %% 1. Datos del plano
from functools import lru_cache

import plotly.graph_objects as go

from motor_algoritmos import cargar_datos, construir_grafo

AZUL = "#000059"
CELESTE = "#329AD6"
BLANCO = "#FFFFFF"


@lru_cache(maxsize=1)
def datos_selector():
    ubicaciones, apoyos = cargar_datos()
    return construir_grafo(ubicaciones, apoyos)


def lista_accesos():
    _, _, _, accesos = datos_selector()
    return sorted(set(accesos.values()))


# %% 2. Grafo interactivo

def crear_selector(seleccionados=()):
    posiciones, tipos, grafo, _ = datos_selector()
    orden = {punto: i for i, punto in enumerate(seleccionados, 1)}
    figura = go.Figure()
    xs, ys = [], []
    for a, vecinos in grafo.items():
        for b, peso in vecinos.items():
            if a < b and peso > 0:
                xs.extend([posiciones[a][0], posiciones[b][0], None])
                ys.extend([posiciones[a][1], posiciones[b][1], None])

    figura.add_trace(go.Scatter(
        x=xs, y=ys, mode="lines",
        line=dict(color="#DEE7F1", width=1),
        hoverinfo="skip", showlegend=False
    ))

    for tipo, etiqueta, tam in (("ubicacion", "Ubicaciones", 4),
                                ("apoyo", "Apoyos", 9)):
        nodos = [n for n in posiciones if tipos[n] == tipo and n != "NAV:CC-08"]
        figura.add_trace(go.Scatter(
            x=[posiciones[n][0] for n in nodos],
            y=[posiciones[n][1] for n in nodos],
            mode="markers", marker=dict(size=tam, color=CELESTE),
            name=etiqueta, hoverinfo="skip"
        ))

    deposito = posiciones["NAV:CC-08"]
    figura.add_trace(go.Scatter(
        x=[deposito[0]], y=[deposito[1]], mode="markers",
        marker=dict(size=12, color=CELESTE, symbol="diamond",
                    line=dict(color=AZUL, width=2)),
        name="Depósito CC-08", hovertemplate="Depósito CC-08<extra></extra>"
    ))

    puntos = lista_accesos()
    figura.add_trace(go.Scatter(
        x=[posiciones[n][0] for n in puntos],
        y=[posiciones[n][1] for n in puntos],
        mode="markers+text",
        customdata=[[n] for n in puntos],
        text=[str(orden[n]) if n in orden else "" for n in puntos],
        textposition="top center", textfont=dict(size=12, color=AZUL),
        marker=dict(
            size=[14 if n in orden else 9 for n in puntos],
            color=[CELESTE if n in orden else AZUL for n in puntos],
            line=dict(color=BLANCO, width=1)
        ),
        name="Accesos (clic para seleccionar)",
        hovertemplate="%{customdata[0]}<extra></extra>"
    ))
    figura.update_layout(
        height=800, clickmode="event+select", dragmode="zoom",
        margin=dict(l=50, r=20, t=15, b=70),
        paper_bgcolor=BLANCO, plot_bgcolor=BLANCO,
        font=dict(color=AZUL),
        legend=dict(orientation="h", y=-0.10)
    )
    figura.update_xaxes(title="X (unidades del plano)", range=[35, 715],
                        gridcolor="#E5E9F1", constrain="domain")
    figura.update_yaxes(title="Y (unidades del plano)", range=[-70, 1515],
                        gridcolor="#E5E9F1", scaleanchor="x", scaleratio=1)
    return figura


def puntos_del_evento(evento):
    # Solo aceptamos identificadores de accesos; ignoramos el resto de trazas.
    validos = set(lista_accesos())
    puntos = []
    for punto in evento.selection.points:
        dato = punto.get("customdata")
        if isinstance(dato, (list, tuple)) and dato and dato[0] in validos:
            if dato[0] not in puntos:
                puntos.append(dato[0])
    return puntos
