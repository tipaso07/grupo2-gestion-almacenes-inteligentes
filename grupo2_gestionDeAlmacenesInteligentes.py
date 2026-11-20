# %% 1. Interfaz y estilos
import streamlit as st

from motor_algoritmos import analizar
from graficos import crear_grafico, crear_csv, comprimir
from pathlib import Path

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
def analizar_ola(numero):
    return analizar(numero)


@st.cache_data(show_spinner=False, max_entries=3)
def generar_archivos(numero):
    datos = analizar_ola(numero)
    return {
        f"ola_{numero}_grafo.png": crear_grafico(datos, "Grafo del almacén"),
        f"ola_{numero}_ruta_referencia.png": crear_grafico(
            datos, f"Ola {numero} - Referencia (orden del CSV)", datos["ruta_referencia"]),
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
    numero = st.number_input("Número de ola", min_value=1, value=39772, step=1)
    enviado = st.button("Analizar ola", use_container_width=True, type="primary")
    st.divider()
    st.caption("Datos: de Assis (2024) · Mendeley Data")

if enviado:
    st.session_state["ola_analizada"] = int(numero)


# %% 4. Inicio
st.markdown("""
<div class="hero">
    <h1>Gestión de almacenes inteligentes</h1>
    <p>Análisis de grafos y optimización de recorridos de picking con Python</p>
</div>
""", unsafe_allow_html=True)

if "ola_analizada" not in st.session_state:
    st.markdown("""
    <div class="empty-state">
        <strong>Utiliza el panel lateral para elegir una ola y analizar sus rutas.</strong>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

ola = st.session_state["ola_analizada"]
try:
    with st.spinner(f"Analizando la ola {ola}..."):
        datos = analizar_ola(ola)
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

st.markdown(f"""
<div class="small-note">
    <strong>Ola {ola}</strong> · {datos['ubicaciones']} ubicaciones ·
    {datos['accesos']} puntos de acceso · BFS: {datos['conectados']} nodos alcanzables.<br>
    La ruta de referencia se basa en el orden de las filas del CSV (no es un recorrido operativo verificado).
    Las distancias están expresadas en unidades del plano.
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
        {"Método": "Referencia (orden CSV)", "Distancia (u)": datos["referencia"], "Tiempo (s)": "—"},
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
    archivos = generar_archivos(ola)

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
