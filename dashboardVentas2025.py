import streamlit as st
import pandas as pd
import plotly.express as px
import textwrap

# --- Configuración de página ---
st.set_page_config(page_title="Análisis de Ventas y Ganancias", layout="wide")

st.title("Análisis de Ventas y Ganancias de Productos")

# --- Cargar los datos ---
file_path = "Orders Final Clean.xlsx"
df_orders = pd.read_excel(file_path)

# --- Normalizar columna de fecha ('Order Date') ---
# Soporta datetime ya correcto, números de serie de Excel, timedelta o strings
col = "Order Date"
if pd.api.types.is_datetime64_any_dtype(df_orders[col]):
    pass  # ya está bien
elif pd.api.types.is_numeric_dtype(df_orders[col]):
    # Excel serial date (origen 1899-12-30)
    origin_date = pd.Timestamp("1899-12-30")
    df_orders[col] = pd.to_timedelta(df_orders[col], unit="D") + origin_date
elif pd.api.types.is_timedelta64_dtype(df_orders[col]):
    origin_date = pd.Timestamp("1899-12-30")
    df_orders[col] = origin_date + df_orders[col]
else:
    # intentar parseo por texto
    df_orders[col] = pd.to_datetime(df_orders[col], errors="coerce")

if df_orders[col].isna().all():
    st.error("No se pudo convertir correctamente la columna 'Order Date' a fecha.")
    st.stop()

# --- Filtros laterales ---
with st.sidebar:
    st.header("Filtros")
    min_date = df_orders[col].min().date()
    max_date = df_orders[col].max().date()

    # Selector de rango de fechas en un solo control
    rango = st.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        format="YYYY/MM/DD",
    )

    # Filtros opcionales si existen columnas
    region = None
    estado = None
    if "Region" in df_orders.columns:
        region = st.selectbox("Selecciona Región", ["Todas"] + sorted(df_orders["Region"].dropna().unique().tolist()))
    if "State" in df_orders.columns:
        estado = st.selectbox("Selecciona Estado", ["Todas"] + sorted(df_orders["State"].dropna().unique().tolist()))

    mostrar_tabla = st.checkbox("Mostrar datos filtrados", value=True)

# Asegurar que el rango siempre tenga (inicio, fin)
if isinstance(rango, tuple) and len(rango) == 2:
    start_date, end_date = rango
else:
    # compatibilidad por si el widget devuelve una sola fecha
    start_date, end_date = min_date, max_date

start_ts = pd.Timestamp(start_date)
end_ts = pd.Timestamp(end_date)

# --- Aplicar filtros ---
mask = (df_orders[col] >= start_ts) & (df_orders[col] <= end_ts)

if region and region != "Todas":
    mask &= (df_orders["Region"] == region)
if estado and estado != "Todas":
    mask &= (df_orders["State"] == estado)

df_filtered = df_orders.loc[mask].copy()

if df_filtered.empty:
    st.warning("No hay datos para el rango de fechas (y filtros) seleccionado.")
    st.stop()

st.success("Datos cargados correctamente.")

# --- Función para envolver etiquetas largas en varias líneas ---
def wrap_text(txt: str, width: int = 22) -> str:
    return "<br>".join(textwrap.wrap(str(txt), width=width))

# --- Tabla (dinámica con los filtros) ---
st.subheader("Datos filtrados")
if mostrar_tabla:
    # Selección de columnas más comunes si existen
    cols_pref = ["Order Date", "Discount", "Sales", "Quantity", "Profit", "Region", "State", "Order ID", "Ship Date", "Product Name"]
    cols_show = [c for c in cols_pref if c in df_filtered.columns]
    if not cols_show:
        cols_show = df_filtered.columns.tolist()
    st.dataframe(
        df_filtered[cols_show].sort_values(col),
        use_container_width=True,
        hide_index=True,
    )

# --- Agregaciones para gráficos ---
ventas_por_producto = df_filtered.groupby("Product Name")["Sales"].sum()
ganancias_por_producto = df_filtered.groupby("Product Name")["Profit"].sum()

# Top 5 por ventas
top_5_v = ventas_por_producto.sort_values(ascending=False).head(5)

# --- Gráfico: Top 5 Productos Más Vendidos ---
fig_ventas = px.bar(
    x=top_5_v.index,
    y=top_5_v.values,
    labels={"x": "Nombre del Producto", "y": "Ventas Totales"},
    title="Top 5 Productos Más Vendidos",
)
fig_ventas.update_layout(
    xaxis_tickangle=0,
    margin=dict(b=160),
)
fig_ventas.update_xaxes(
    tickmode="array",
    tickvals=list(top_5_v.index),
    ticktext=[wrap_text(n) for n in top_5_v.index],
)

st.header("Top 5 Productos Más Vendidos")
st.plotly_chart(fig_ventas, use_container_width=True)

# Top 5 por ganancias
top_5_g = ganancias_por_producto.sort_values(ascending=False).head(5)

# --- Gráfico: Top 5 Productos con Mayor Ganancia ---
fig_ganancias = px.bar(
    x=top_5_g.index,
    y=top_5_g.values,
    labels={"x": "Nombre del Producto", "y": "Ganancias Totales"},
    title="Top 5 Productos con Mayor Ganancia",
)
fig_ganancias.update_layout(
    xaxis_tickangle=0,
    margin=dict(b=160),
)
fig_ganancias.update_xaxes(
    tickmode="array",
    tickvals=list(top_5_g.index),
    ticktext=[wrap_text(n) for n in top_5_g.index],
)

st.header("Top 5 Productos con Mayor Ganancia")
st.plotly_chart(fig_ganancias, use_container_width=True)

# --- Dispersión Ventas vs Ganancias ---
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

# --- Resumen ---
st.markdown("""
## Resumen del Análisis

**Hallazgos clave**
- Se identifican los 5 productos con mayores **ventas** y los 5 con mayor **ganancia** dentro del rango seleccionado.
- La dispersión **Ventas vs Ganancias** ayuda a detectar productos con **alta venta pero baja ganancia** (o viceversa).

**Próximos pasos**
- Analizar productos con discrepancias entre ventas y ganancias para ajustar **precios**, **costos** o **promociones**.
- Replicar prácticas de los **más rentables** en otras categorías o segmentos.
""")
