# %% 1. Interfaz y estilos
import streamlit as st

from motor_algoritmos import analizar
from graficos import crear_grafico, crear_csv, crear_csv_ubicaciones, crear_csv_cierres, comprimir
from pathlib import Path
from selector_ola import mostrar_selector, lista_accesos, lista_ubicaciones, puntos_del_evento, datos_selector, niveles_ubicaciones

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
def analizar_ola(numero, puntos_manuales=None, cerrados=()):
    return analizar(numero, puntos_manuales=puntos_manuales, accesos_cerrados=cerrados)


@st.cache_data(show_spinner=False, max_entries=3)
def generar_archivos(numero, puntos_manuales=None, cerrados=()):
    datos = analizar_ola(numero, puntos_manuales, cerrados)
    origen = "orden de selección" if datos["manual"] else "orden del CSV"
    return {
        f"ola_{numero}_grafo.png": crear_grafico(datos, "Grafo del almacén"),
        f"ola_{numero}_ruta_referencia.png": crear_grafico(
            datos, f"Ola {numero} - Referencia ({origen})", datos["ruta_referencia"]),
        f"ola_{numero}_ruta_propuesta.png": crear_grafico(
            datos, f"Ola {numero} - Ruta propuesta", datos["ruta_propuesta"]),
        f"ola_{numero}_comparacion.csv": crear_csv(datos),
        f"ola_{numero}_ubicaciones.csv": crear_csv_ubicaciones(datos),
        f"ola_{numero}_cierres.csv": crear_csv_cierres(datos),
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
        configurar_cierres = st.checkbox("Configurar accesos cerrados")
        if st.button("Analizar ola", use_container_width=True, type="primary"):
            st.session_state["analisis_csv"] = int(numero)
    else:
        st.caption("Selecciona las ubicaciones de almacenamiento en el plano.")
    st.divider()
    st.caption("Datos: de Assis (2024) · Mendeley Data")


# %% 4. Inicio
st.markdown("""
<div class="hero">
    <h1>Gestión de almacenes inteligentes</h1>
    <p>Análisis de grafos y optimización de recorridos de picking con Python</p>
</div>
""", unsafe_allow_html=True)

# %% 4.1. Selección de ubicaciones y control de accesos
# Los cierres son comunes a ambos modos durante la sesión actual.
for clave, inicial in (("ubicaciones_manuales", []), ("accesos_cerrados", []),
                       ("ultimo_evento_plano", None),):
    if clave not in st.session_state:
        st.session_state[clave] = inicial


def invalidar_resultados():
    st.session_state.pop("analisis_manual_v2", None)
    st.session_state.pop("analisis_csv", None)


def actualizar(clave, valores):
    st.session_state[clave] = valores
    invalidar_resultados()
    st.rerun()


def alternar(tipo, codigo):
    clave = "ubicaciones_manuales" if tipo == "ubicacion" else "accesos_cerrados"
    valores = list(st.session_state[clave])
    if codigo in valores:
        valores.remove(codigo)
    else:
        valores.append(codigo)
    actualizar(clave, valores)


es_manual = modo == "Ola manual"
seleccionados = st.session_state["ubicaciones_manuales"]
cerrados = st.session_state["accesos_cerrados"]
if es_manual or configurar_cierres:
    st.subheader("Crear ola manual" if es_manual else "Configurar accesos del almacén")
    herramientas = ["Seleccionar ubicaciones", "Cerrar / reabrir accesos"] if es_manual else ["Cerrar / reabrir accesos"]
    herramienta = st.radio("Acción en el plano", herramientas, horizontal=True)
    tipo_activo = "ubicacion" if herramienta == "Seleccionar ubicaciones" else "acceso"
    nivel = None
    if es_manual:
        nivel = st.radio("Nivel de almacenamiento", [1, 2, 3, 4], horizontal=True,
                         help="Las ubicaciones de distintos niveles pueden compartir coordenadas X/Y.")
    st.caption("Haz clic para marcar y vuelve a hacer clic para desmarcar. "
               "Verde = ubicación elegida; rojo = acceso cerrado. "
               "El número verde indica el orden de selección. El depósito permanece abierto. "
               "Los códigos superpuestos se separan visualmente; sus coordenadas reales no cambian.")
    try:
        if es_manual:
            en_nivel = sum(niveles_ubicaciones().get(c) == nivel for c in seleccionados)
            st.write(f"**Seleccionadas en el nivel {nivel}:** {en_nivel} · "
                     f"**En otros niveles:** {len(seleccionados) - en_nivel} · "
                     f"**Accesos cerrados:** {len(cerrados)}")

        evento = mostrar_selector(seleccionados if es_manual else (), cerrados,
                                 nivel, tipo_activo, st.session_state["ultimo_evento_plano"])
        if isinstance(evento, dict) and evento.get("id") and evento["id"] != st.session_state["ultimo_evento_plano"]:
            st.session_state["ultimo_evento_plano"] = evento["id"]
            punto = puntos_del_evento(evento, tipo_activo)
            if punto and evento.get("nivel") == nivel:
                tipo_punto, codigo = punto
                if tipo_punto == "acceso" or niveles_ubicaciones().get(codigo) == nivel:
                    alternar(tipo_punto, codigo)
            # Confirmar también los eventos obsoletos sin modificar la selección.
            st.rerun()

        with st.expander("Seleccionar por código (opcional)"):
            opciones = lista_ubicaciones(nivel) if tipo_activo == "ubicacion" else lista_accesos()
            valores = seleccionados if tipo_activo == "ubicacion" else cerrados
            codigo = st.selectbox("Código de ubicación" if tipo_activo == "ubicacion" else "Código de acceso",
                opciones, index=None, placeholder="Busca un código", key=f"codigo_v2_{tipo_activo}_{nivel}",
                format_func=lambda c: f"{c} {'✓' if c in valores else ''}")
            if st.button("Marcar / desmarcar", disabled=codigo is None, key="aplicar_codigo"):
                alternar(tipo_activo, codigo)
        _, _, _, accesos = datos_selector()
    except (FileNotFoundError, KeyError, ValueError) as error:
        st.error(f"No se pudo cargar el plano: {error}")
        st.stop()

    st.write(f"**Accesos cerrados:** {len(cerrados)}")
    if cerrados:
        st.write(", ".join(cerrados))
        if st.button("Reabrir todos los accesos", key="reabrir_todos"):
            actualizar("accesos_cerrados", [])
    if es_manual:
        st.write(f"**Ubicaciones seleccionadas:** {len(seleccionados)} · "
                 f"**Paradas distintas:** {len({accesos[c] for c in seleccionados})}")
        if seleccionados:
            st.table([{"Orden": i, "Ubicación": c, "Acceso": accesos[c],
                       "Estado": "Cerrado" if accesos[c] in cerrados else "Abierto"}
                      for i, c in enumerate(seleccionados, 1)])
        bloqueadas = [c for c in seleccionados if accesos[c] in cerrados]
        if bloqueadas:
            st.warning("Reabre los accesos de estas ubicaciones o retíralas de la ola: " + ", ".join(bloqueadas))
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Deshacer última ubicación", disabled=not seleccionados, use_container_width=True):
                actualizar("ubicaciones_manuales", seleccionados[:-1])
        with c2:
            if st.button("Limpiar ubicaciones", disabled=not seleccionados, use_container_width=True):
                actualizar("ubicaciones_manuales", [])
        with c3:
            if st.button("Analizar ola manual", disabled=not seleccionados or bool(bloqueadas),
                         type="primary", use_container_width=True):
                st.session_state["analisis_manual_v2"] = tuple(seleccionados)

if es_manual:
    if "analisis_manual_v2" not in st.session_state:
        st.stop()
    ola = "manual"
    puntos_manual = st.session_state["analisis_manual_v2"]
else:
    if "analisis_csv" not in st.session_state:
        st.info("Selecciona una ola y presiona Analizar ola en el panel lateral.")
        st.stop()
    ola = st.session_state["analisis_csv"]
    puntos_manual = None

cerrados_analisis = tuple(sorted(cerrados))
if not es_manual and cerrados:
    st.caption(f"Este análisis considera {len(cerrados)} accesos cerrados. Activa Configurar accesos cerrados para modificarlos.")

try:
    with st.spinner(f"Analizando la ola {ola}..."):
        datos = analizar_ola(ola, puntos_manual, cerrados_analisis)
except (FileNotFoundError, KeyError, ValueError) as error:
    st.error(f"No se pudo analizar la ola {ola}: {error}")
    if isinstance(error, (FileNotFoundError, KeyError)):
        st.info("Comprueba que los tres CSV originales estén dentro de dataset/.")
    st.stop()


# %% 5. Resultados
st.markdown('<div class="section-title">Resumen de la ola seleccionada</div>',
            unsafe_allow_html=True)

aristas = sum(len(vecinos) for vecinos in datos["grafo"].values()) // 2
reduccion = 100 * (datos["referencia"] - datos["propuesta"]) / datos["referencia"] if datos["referencia"] else 0
m1, m2, m3, m4 = st.columns(4)
m1.metric("Nodos activos", f"{len(datos['grafo']):,}")
m2.metric("Aristas activas", f"{aristas:,}")
m3.metric("Distancia de referencia", f"{datos['referencia']:,.0f} u")
m4.metric("Ruta propuesta", f"{datos['propuesta']:,.0f} u", f"-{reduccion:.2f}% vs. ref.", delta_color="inverse")

if datos["manual"]:
    detalle = f"{datos['ubicaciones']} ubicaciones · {datos['accesos']} puntos de acceso"
    nota = "La referencia sigue el orden de selección de ubicaciones, agrupadas por acceso."
    nombre_referencia = "Referencia (selección manual)"
else:
    detalle = f"{datos['ubicaciones']} ubicaciones · {datos['accesos']} puntos de acceso"
    nota = "La ruta de referencia se basa en el orden de las filas del CSV (no es un recorrido operativo verificado)."
    nombre_referencia = "Referencia (orden CSV)"

st.markdown(f"""
<div class="small-note">
    <strong>Ola {ola}</strong> · {detalle} · BFS: {datos['conectados']} nodos alcanzables · {len(datos['cerrados'])} accesos cerrados.<br>
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
    archivos = generar_archivos(ola, puntos_manual, cerrados_analisis)

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
    st.write("Descarga los resultados de esta ola, las ubicaciones a recoger y los accesos cerrados.")
    st.download_button("Descargar ubicaciones (CSV)", archivos[f"ola_{ola}_ubicaciones.csv"], file_name=f"ola_{ola}_ubicaciones.csv", mime="text/csv")
    st.download_button("Descargar cierres (CSV)", archivos[f"ola_{ola}_cierres.csv"], file_name=f"ola_{ola}_cierres.csv", mime="text/csv")
    st.download_button("Descargar gráficos y CSV (ZIP)", comprimir(archivos),
                       file_name=f"grupo2_ola_{ola}_resultados.zip",
                       mime="application/zip", use_container_width=True)
    st.download_button("Descargar comparación (CSV)", archivos[comparacion],
                       file_name=comparacion, mime="text/csv", use_container_width=True)

st.markdown("""
""", unsafe_allow_html=True)
