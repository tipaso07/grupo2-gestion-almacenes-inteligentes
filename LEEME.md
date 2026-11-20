# Grupo 2 — Gestión de Almacenes Inteligentes

Aplicación con Python y Streamlit

## Estructura

- `grupo2_gestionDeAlmacenesInteligentes.py`: interfaz de Streamlit, menús, métricas y botones
- `motor_algoritmos.py`: lectura de CSV, construcción del grafo, BFS, Bellman-Ford, optimización y programación dinámica
- `graficos.py`: generación de imágenes PNG, CSV y ZIP de resultados
- `estilos.css`: diseño visual
- `.streamlit/config.toml`: tema nativo de Streamlit
- `requirements.txt`: dependencias de Python
- `grupo2_abrir.bat`: acceso rápido en Windows
- `dataset/`: carpeta para los csv de Mendeley Data

## Configuración

Pon los archivos de Mendeley Data a `dataset/`:

1. `Storage_Location.csv`
2. `Support_Points_Navigation.csv`
3. `Picking_Wave.csv`

En una terminal, dentro de la carpeta principal:


python -m pip install -r requirements.txt
python -m streamlit run grupo2_gestionDeAlmacenesInteligentes.py


En Windows también puedes ejecutar `grupo2_abrir.bat` después de instalar las dependencias.

## Prueba sugerida

- Ola **39772**: modelo de 2636 nodos, distancia de referencia 5254 u, propuesta heurística 4158 u.
- Ola **33179**: usa programación dinámica para instancias pequeñas.
