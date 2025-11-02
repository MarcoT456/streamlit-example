import streamlit as st
import pandas as pd
import plotly.express as px
import textwrap
import pydeck as pdk
import numpy as np

# -------------------------
# Configuración de página
# -------------------------
st.set_page_config(page_title="Análisis de Ventas y Ganancias", layout="wide")
st.title("Análisis de Ventas y Ganancias de Productos")

# -------------------------
# Carga y limpieza de datos
# -------------------------
file_path = "Orders Final Clean.xlsx"
df_orders = pd.read_excel(file_path)

# 1) Eliminar duplicados exactos
df_orders = df_orders.drop_duplicates().reset_index(drop=True)

# 2) Corregir descuentos expresados como enteros (17 -> 0.17)
if "Discount" in df_orders.columns:
    mask_pct = (df_orders["Discount"] > 1) & (df_orders["Discount"] <= 100)
    df_orders.loc[mask_pct, "Discount"] = df_orders.loc[mask_pct, "Discount"] / 100.0

# 3) Unificar Ship Date y remover columna duplicada si existe
if "Ship Date" in df_orders.columns and "Ship date" in df_orders.columns:
    sd_main = pd.to_datetime(df_orders["Ship Date"], errors="coerce")
    sd_alt  = pd.to_datetime(df_orders["Ship date"], errors="coerce")
    df_orders["Ship Date"] = sd_main.fillna(sd_alt)
    df_orders = df_orders.drop(columns=["Ship date"])

# 4) Normalizar columna de fecha (Order Date)
col_fecha = "Order Date"
if pd.api.types.is_datetime64_any_dtype(df_orders[col_fecha]):
    pass
elif pd.api.types.is_numeric_dtype(df_orders[col_fecha]):
    origin_date = pd.Timestamp("1899-12-30")
    df_orders[col_fecha] = pd.to_timedelta(df_orders[col_fecha], unit="D") + origin_date
elif pd.api.types.is_timedelta64_dtype(df_orders[col_fecha]):
    origin_date = pd.Timestamp("1899-12-30")
    df_orders[col_fecha] = origin_date + df_orders[col_fecha]
else:
    df_orders[col_fecha] = pd.to_datetime(df_orders[col_fecha], errors="coerce")

if df_orders[col_fecha].isna().all():
    st.error("No se pudo convertir correctamente la columna 'Order Date' a fecha.")
    st.stop()

# -------------------------
# Filtros laterales
# -------------------------
with st.sidebar:
    st.header("Filtros")

    # Rango real disponible en datos
    min_date = df_orders[col_fecha].min().date()
    max_date = df_orders[col_fecha].max().date()

    rango = st.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="YYYY/MM/DD",
        help="Solo puedes elegir fechas dentro del rango disponible en los datos.",
    )

    if isinstance(rango, tuple) and len(rango) == 2:
        start_date, end_date = rango
    else:
        start_date, end_date = min_date, max_date

    # Validaciones adicionales (seguridad)
    clipped = False
    if start_date < min_date:
        start_date = min_date; clipped = True
    if end_date > max_date:
        end_date = max_date; clipped = True
    if clipped:
        st.info("Las fechas seleccionadas se ajustaron automáticamente al rango disponible en los datos.")

    if start_date > end_date:
        start_date, end_date = end_date, start_date
        st.warning("La fecha de inicio era mayor que la de fin. Se invirtieron para continuar.")

    # Filtros opcionales
    region = None
    estado = None
    if "Region" in df_orders.columns:
        region = st.selectbox("Selecciona Región", ["Todas"] + sorted(df_orders["Region"].dropna().unique().tolist()))
    if "State" in df_orders.columns:
        estado = st.selectbox("Selecciona Estado", ["Todas"] + sorted(df_orders["State"].dropna().unique().tolist()))

    mostrar_tabla = st.checkbox("Mostrar datos filtrados", value=True)

# Aplicación de filtros
start_ts = pd.Timestamp(start_date)
end_ts = pd.Timestamp(end_date)

mask = (df_orders[col_fecha] >= start_ts) & (df_orders[col_fecha] <= end_ts)
if region and region != "Todas":
    mask &= (df_orders["Region"] == region)
if estado and estado != "Todas":
    mask &= (df_orders["State"] == estado)

df_filtered = df_orders.loc[mask].copy()

if df_filtered.empty:
    st.warning("No hay datos para el rango de fechas (y filtros) seleccionado.")
    st.stop()

st.success("Datos cargados y filtrados correctamente.")

# -------------------------
# Utilidad: envolver etiquetas largas
# -------------------------
def wrap_text(txt: str, width: int = 22) -> str:
    return "<br>".join(textwrap.wrap(str(txt), width=width))

# -------------------------
# Tabla de datos filtrados
# -------------------------
st.subheader("Datos filtrados")
if mostrar_tabla:
    cols_pref = [
        "Order Date","Discount","Sales","Quantity","Profit",
        "Region","State","Order ID","Ship Date","Product Name","City"
    ]
    cols_show = [c for c in cols_pref if c in df_filtered.columns]
    if not cols_show:
        cols_show = df_filtered.columns.tolist()

    st.dataframe(
        df_filtered[cols_show].sort_values(col_fecha),
        use_container_width=True,
        hide_index=True,
    )

# -------------------------
# Agregaciones para gráficas
# -------------------------
ventas_por_producto = df_filtered.groupby("Product Name")["Sales"].sum()
ganancias_por_producto = df_filtered.groupby("Product Name")["Profit"].sum()

# Top 5 por Ventas
top_5_v = ventas_por_producto.sort_values(ascending=False).head(5)
fig_ventas = px.bar(
    x=top_5_v.index,
    y=top_5_v.values,
    labels={"x": "Nombre del Producto", "y": "Ventas Totales"},
    title="Top 5 Productos Más Vendidos",
)
fig_ventas.update_layout(xaxis_tickangle=0, margin=dict(b=160))
fig_ventas.update_xaxes(
    tickmode="array",
    tickvals=list(top_5_v.index),
    ticktext=[wrap_text(n) for n in top_5_v.index],
)
st.header("Top 5 Productos Más Vendidos")
st.plotly_chart(fig_ventas, use_container_width=True)

# Top 5 por Ganancia
top_5_g = ganancias_por_producto.sort_values(ascending=False).head(5)
fig_ganancias = px.bar(
    x=top_5_g.index,
    y=top_5_g.values,
    labels={"x": "Nombre del Producto", "y": "Ganancias Totales"},
    title="Top 5 Productos con Mayor Ganancia",
)
fig_ganancias.update_layout(xaxis_tickangle=0, margin=dict(b=160))
fig_ganancias.update_xaxes(
    tickmode="array",
    tickvals=list(top_5_g.index),
    ticktext=[wrap_text(n) for n in top_5_g.index],
)
st.header("Top 5 Productos con Mayor Ganancia")
st.plotly_chart(fig_ganancias, use_container_width=True)

# Dispersión Ventas vs Ganancias
df_summary = pd.concat([ventas_por_producto, ganancias_por_producto], axis=1)
df_summary.columns = ["Ventas Totales", "Ganancias Totales"]
fig_scatter = px.scatter(
    df_summary,
    x="Ventas Totales",
    y="Ganancias Totales",
    hover_name=df_summary.index,
    title="Relación entre Ventas y Ganancias por Producto",
)
st.header("Relación entre Ventas y Ganancias por Producto")
st.plotly_chart(fig_scatter, use_container_width=True)

# -------------------------
# Mapa PyDeck: Ventas por Estado
# -------------------------
st.header("Mapa de Ventas por Estado (PyDeck)")

if "State" not in df_filtered.columns:
    st.info("No se encontró la columna 'State'; no es posible generar el mapa por estado.")
else:
    df_state_sales = (
        df_filtered.groupby("State", as_index=False)["Sales"]
        .sum()
        .rename(columns={"Sales": "Ventas Totales"})
    )

    # Usar lat/lon del dataset si existen, sino centroides de USA
    has_latlon = ("Latitude" in df_filtered.columns) and ("Longitude" in df_filtered.columns)

    if has_latlon:
        # centros ponderados por ventas
        def wavg(g, val_col, w_col):
            d = g[val_col]; w = g[w_col]
            return d.mean() if w.sum() == 0 else (d * w).sum() / w.sum()

        latlon_state = (
            df_filtered.groupby("State")
            .apply(lambda g: pd.Series({
                "lat": wavg(g, "Latitude", "Sales"),
                "lon": wavg(g, "Longitude", "Sales")
            }))
            .reset_index()
        )
        df_map = df_state_sales.merge(latlon_state, on="State", how="left")
    else:
        us_state_centroids = {
            "Alabama": (32.806671, -86.791130), "Alaska": (61.370716, -152.404419),
            "Arizona": (33.729759, -111.431221), "Arkansas": (34.969704, -92.373123),
            "California": (36.116203, -119.681564), "Colorado": (39.059811, -105.311104),
            "Connecticut": (41.597782, -72.755371), "Delaware": (39.318523, -75.507141),
            "District of Columbia": (38.905985, -77.033418),
            "Florida": (27.766279, -81.686783), "Georgia": (33.040619, -83.643074),
            "Idaho": (44.240459, -114.478828), "Illinois": (40.349457, -88.986137),
            "Indiana": (39.849426, -86.258278), "Iowa": (42.011539, -93.210526),
            "Kansas": (38.526600, -96.726486), "Kentucky": (37.668140, -84.670067),
            "Louisiana": (31.169546, -91.867805), "Maine": (44.693947, -69.381927),
            "Maryland": (39.063946, -76.802101), "Massachusetts": (42.230171, -71.530106),
            "Michigan": (43.326618, -84.536095), "Minnesota": (45.694454, -93.900192),
            "Mississippi": (32.741646, -89.678696), "Missouri": (38.456085, -92.288368),
            "Montana": (46.921925, -110.454353), "Nebraska": (41.125370, -98.268082),
            "Nevada": (38.313515, -117.055374), "New Hampshire": (43.452492, -71.563896),
            "New Jersey": (40.298904, -74.521011), "New Mexico": (34.840515, -106.248482),
            "New York": (42.165726, -74.948051), "North Carolina": (35.630066, -79.806419),
            "North Dakota": (47.528912, -99.784012), "Ohio": (40.388783, -82.764915),
            "Oklahoma": (35.565342, -96.928917), "Oregon": (44.572021, -122.070938),
            "Pennsylvania": (40.590752, -77.209755), "Rhode Island": (41.680893, -71.511780),
            "South Carolina": (33.856892, -80.945007), "South Dakota": (44.299782, -99.438828),
            "Tennessee": (35.747845, -86.692345), "Texas": (31.054487, -97.563461),
            "Utah": (40.150032, -111.862434), "Vermont": (44.045876, -72.710686),
            "Virginia": (37.769337, -78.169968), "Washington": (47.400902, -121.490494),
            "West Virginia": (38.491226, -80.954453), "Wisconsin": (44.268543, -89.616508),
            "Wyoming": (42.755966, -107.302490)
        }
        df_map = df_state_sales.assign(
            lat=df_state_sales["State"].map(lambda s: us_state_centroids.get(s, (np.nan, np.nan))[0]),
            lon=df_state_sales["State"].map(lambda s: us_state_centroids.get(s, (np.nan, np.nan))[1]),
        )
        faltantes = df_map[df_map["lat"].isna()]["State"].tolist()
        if faltantes:
            st.info(f"Estados sin coordenadas conocidas (se omiten en el mapa): {', '.join(faltantes)}")
            df_map = df_map.dropna(subset=["lat", "lon"])

    if df_map.empty:
        st.info("No hay datos georreferenciados para mostrar en el mapa.")
    else:
        max_sales = float(df_map["Ventas Totales"].max())
        if max_sales <= 0:
            max_sales = 1.0
        df_map = df_map.assign(
            radius=(df_map["Ventas Totales"] / max_sales) * 40000 + 3000,
            color=df_map["Ventas Totales"].apply(
                lambda v: [255, int(255 * (1 - v / max_sales)), 80, 160]
            ),
        )

        view_state = pdk.ViewState(
            latitude=float(df_map["lat"].mean()),
            longitude=float(df_map["lon"].mean()),
            zoom=3.5,
            pitch=30,
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_map,
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius="radius",
            pickable=True,
            stroked=True,
            filled=True,
            radius_min_pixels=5,
            radius_max_pixels=120,
            line_width_min_pixels=1,
        )

        tooltip = {
            "html": "<b>Estado:</b> {State}<br/><b>Ventas totales:</b> ${Ventas Totales}",
            "style": {"backgroundColor": "white", "color": "black"}
        }

        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style="light",
            tooltip=tooltip,
        )

        st.pydeck_chart(deck, use_container_width=True)

# -------------------------
# Resumen final
# -------------------------
st.markdown("""
## Resumen del Análisis

**Hallazgos clave**
- Se identifican los 5 productos con mayores **ventas** y los 5 con mayor **ganancia** dentro del rango seleccionado.
- La dispersión **Ventas vs Ganancias** ayuda a detectar productos con **alta venta pero baja ganancia** (o viceversa).
- El mapa PyDeck muestra la **distribución geográfica** de las ventas por estado dentro del rango.

**Próximos pasos**
- Con la limpieza aplicada (duplicados, descuentos y fechas), las métricas reflejan mejor la realidad.
- Considera cruzar las ventas con **márgenes por estado** para priorizar acciones comerciales.
""")
