# %% 1. Interfaz y estilos
import streamlit as st

from motor_algoritmos import analizar
from graficos import crear_grafico, crear_csv, comprimir
from pathlib import Path
from selector_ola import crear_selector, lista_accesos, puntos_del_evento

st.set_page_config(
    page_title="Gestión de Almacenes Inteligentes",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent
st.markdown(f"<style>{(BASE / 'estilos.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)


# %% 2. Cálculo y archivos
@st.cache_data(show_spinner=False, max_entries=3)
def analizar_ola(numero, puntos_manuales=None):
    return analizar(numero, puntos_manuales=puntos_manuales)


@st.cache_data(show_spinner=False, max_entries=3)
def generar_archivos(numero, puntos_manuales=None):
    datos = analizar_ola(numero, puntos_manuales)
    origen = "orden de selección" if datos["manual"] else "orden del CSV"
    return {
        f"ola_{numero}_grafo.png": crear_grafico(datos, "Grafo del almacén"),
        f"ola_{numero}_ruta_referencia.png": crear_grafico(
            datos, f"Ola {numero} - Referencia ({origen})", datos["ruta_referencia"]),
        f"ola_{numero}_ruta_propuesta.png": crear_grafico(
            datos, f"Ola {numero} - Ruta propuesta", datos["ruta_propuesta"]),
        f"ola_{numero}_comparacion.csv": crear_csv(datos),
    }


# %% 3. Panel de selección
with st.sidebar:
    st.markdown("### GRUPO 2")
    st.caption("Complejidad Algorítmica · UPC")
    st.divider()
    st.markdown("### Configurar análisis")
    modo = st.radio("Tipo de ola", ["Ola del dataset", "Ola manual"])
    if modo == "Ola del dataset":
        numero = st.number_input("Número de ola", min_value=1, value=39772, step=1)
        if st.button("Analizar ola", use_container_width=True, type="primary"):
            st.session_state["analisis_csv"] = int(numero)
    else:
        st.caption("Selecciona accesos en el plano del almacén.")
    st.divider()
    st.caption("Datos: de Assis (2024) · Mendeley Data")


# %% 4. Inicio
st.markdown("""
<div class="hero">
    <h1>Gestión de almacenes inteligentes</h1>
    <p>Análisis de grafos y optimización de recorridos de picking con Python</p>
</div>
""", unsafe_allow_html=True)

# %% 4.1. Creación de una ola manual
if "puntos_manuales" not in st.session_state:
    st.session_state["puntos_manuales"] = []
if "version_selector" not in st.session_state:
    st.session_state["version_selector"] = 0


def actualizar_seleccion(puntos):
    st.session_state["puntos_manuales"] = puntos
    st.session_state.pop("analisis_manual", None)
    st.session_state["version_selector"] += 1
    st.rerun()


if modo == "Ola manual":
    st.subheader("Crear ola manual")
    st.caption("Haz clic en los puntos azul oscuro para añadir paradas. "
               "Los números indican el orden de selección. El depósito se incluye automáticamente.")
    seleccionados = st.session_state["puntos_manuales"]
    try:
        evento = st.plotly_chart(
            crear_selector(seleccionados),
            key=f"selector_manual_{st.session_state['version_selector']}",
            on_select="rerun", selection_mode="points",
            theme=None, use_container_width=True,
            config={"displaylogo": False, "scrollZoom": True}
        )
        nuevos = [p for p in puntos_del_evento(evento) if p not in seleccionados]
        if nuevos:
            actualizar_seleccion(seleccionados + nuevos)
        opciones = [p for p in lista_accesos() if p not in seleccionados]
    except (FileNotFoundError, KeyError, ValueError) as error:
        st.error(f"No se pudo cargar el plano: {error}")
        st.stop()

    st.write(f"**Paradas seleccionadas:** {len(seleccionados)}")
    if seleccionados:
        st.write(" → ".join(seleccionados))

    with st.expander("Seleccionar por código (opcional)"):
        codigo = st.selectbox("Punto de acceso", opciones, index=None,
                             placeholder="Busca un código de acceso")
        if st.button("Añadir acceso", disabled=codigo is None):
            actualizar_seleccion(seleccionados + [codigo])

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Deshacer último", disabled=not seleccionados,
                     use_container_width=True):
            actualizar_seleccion(seleccionados[:-1])
    with c2:
        if st.button("Limpiar selección", disabled=not seleccionados,
                     use_container_width=True):
            actualizar_seleccion([])
    with c3:
        if st.button("Analizar ola manual", disabled=not seleccionados,
                     type="primary", use_container_width=True):
            st.session_state["analisis_manual"] = tuple(seleccionados)

    if "analisis_manual" not in st.session_state:
        st.stop()
    ola = "manual"
    puntos_manual = st.session_state["analisis_manual"]
else:
    if "analisis_csv" not in st.session_state:
        st.markdown("""
        <div class="empty-state">
            <strong>Utiliza el panel lateral para elegir una ola y analizar sus rutas.</strong>
        </div>
        """, unsafe_allow_html=True)
        st.stop()
    ola = st.session_state["analisis_csv"]
    puntos_manual = None

try:
    with st.spinner(f"Analizando la ola {ola}..."):
        datos = analizar_ola(ola, puntos_manual)
except (FileNotFoundError, KeyError, ValueError) as error:
    st.error(f"No se pudo analizar la ola {ola}: {error}")
    st.info("Comprueba que los tres CSV originales estén dentro de dataset/.")
    st.stop()


# %% 5. Resultados
st.markdown('<div class="section-title">Resumen de la ola seleccionada</div>',
            unsafe_allow_html=True)

aristas = sum(len(vecinos) for vecinos in datos["grafo"].values()) // 2
reduccion = 100 * (datos["referencia"] - datos["propuesta"]) / datos["referencia"] if datos["referencia"] else 0
m1, m2, m3, m4 = st.columns(4)
m1.metric("Nodos del grafo", f"{len(datos['grafo']):,}")
m2.metric("Aristas", f"{aristas:,}")
m3.metric("Distancia de referencia", f"{datos['referencia']:,.0f} u")
m4.metric("Ruta propuesta", f"{datos['propuesta']:,.0f} u", f"-{reduccion:.2f}% vs. ref.", delta_color="inverse")

if datos["manual"]:
    detalle = f"{datos['accesos']} puntos de acceso seleccionados"
    nota = "La referencia sigue el orden de selección manual; no representa un pedido real."
    nombre_referencia = "Referencia (selección manual)"
else:
    detalle = f"{datos['ubicaciones']} ubicaciones · {datos['accesos']} puntos de acceso"
    nota = "La ruta de referencia se basa en el orden de las filas del CSV (no es un recorrido operativo verificado)."
    nombre_referencia = "Referencia (orden CSV)"

st.markdown(f"""
<div class="small-note">
    <strong>Ola {ola}</strong> · {detalle} · BFS: {datos['conectados']} nodos alcanzables.<br>
    {nota} Las distancias están expresadas en unidades del plano.
</div>
""", unsafe_allow_html=True)

with st.expander("Algoritmos y tiempos de ejecución", expanded=False):
    st.write(f"**Método seleccionado:** {datos['metodo']}")
    st.write(f"**Bellman-Ford:** {datos['tiempo_bf']:.4f} s")
    st.write(f"**Vecino cercano + 2-opt:** {datos['tiempo_h']:.6f} s")
    if datos["tiempo_dp"] is None:
        st.write("**Programación dinámica:** no se ejecutó (más de 10 accesos).")
    else:
        st.write(f"**Programación dinámica (Held-Karp):** {datos['tiempo_dp']:.6f} s")
    filas = [
        {"Método": nombre_referencia, "Distancia (u)": datos["referencia"], "Tiempo (s)": "—"},
        {"Método": "Vecino cercano + 2-opt", "Distancia (u)": datos["heuristica"],
         "Tiempo (s)": f"{datos['tiempo_h']:.6f}"},
    ]
    if datos["tiempo_dp"] is not None:
        filas.append({"Método": "Programación dinámica", "Distancia (u)": datos["propuesta"],
                      "Tiempo (s)": f"{datos['tiempo_dp']:.6f}"})
    st.table(filas)
    st.caption("2-opt es una heurística y no garantiza optimalidad. "
               "La programación dinámica encuentra la solución óptima para instancias pequeñas del modelo.")


# %% 6. Visualización y descargas
st.markdown('<div class="section-title">Grafo y recorridos</div>',
            unsafe_allow_html=True)

with st.spinner("Preparando los gráficos..."):
    archivos = generar_archivos(ola, puntos_manual)

grafo = f"ola_{ola}_grafo.png"
referencia = f"ola_{ola}_ruta_referencia.png"
propuesta = f"ola_{ola}_ruta_propuesta.png"
comparacion = f"ola_{ola}_comparacion.csv"

tab1, tab2, tab3, tab4 = st.tabs([
    "Grafo del almacén", "Ruta de referencia", "Ruta propuesta", "Descargas"
])
for pestana, nombre in [(tab1, grafo), (tab2, referencia), (tab3, propuesta)]:
    with pestana:
        st.image(archivos[nombre], use_container_width=True)
        st.download_button("Descargar imagen PNG", archivos[nombre], file_name=nombre,
                           mime="image/png", key=nombre)

with tab4:
    st.write("Descarga los resultados de esta ola para incorporarlos al informe.")
    st.download_button("Descargar gráficos y CSV (ZIP)", comprimir(archivos),
                       file_name=f"grupo2_ola_{ola}_resultados.zip",
                       mime="application/zip", use_container_width=True)
    st.download_button("Descargar comparación (CSV)", archivos[comparacion],
                       file_name=comparacion, mime="text/csv", use_container_width=True)

st.markdown("""
""", unsafe_allow_html=True)
