import streamlit as st
import pandas as pd
import plotly.express as px

st.title('Análisis de Ventas y Ganancias de Productos')

# Cargar los datos
file_path = 'Orders Final Clean.xlsx'
df_orders = pd.read_excel(file_path)

# Calcular las ventas y ganancias totales por producto
ventas_por_producto = df_orders.groupby('Product Name')['Sales'].sum()
ganancias_por_producto = df_orders.groupby('Product Name')['Profit'].sum()

# Identificar los top 5 productos por ventas
top_5_productos_ventas = ventas_por_producto.sort_values(ascending=False).head(5)

# Función para dividir nombres largos en múltiples líneas
def wrap_text(text, length=15):
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        if sum(len(w) for w in current_line) + len(word) + len(current_line) > length:
            lines.append(' '.join(current_line))
            current_line = [word]
        else:
            current_line.append(word)
    if current_line:
        lines.append(' '.join(current_line))
    return '<br>'.join(lines)


# Crear la gráfica de barras de ventas
fig_ventas = px.bar(x=top_5_productos_ventas.index, y=top_5_productos_ventas.values, labels={'x':'Nombre del Producto', 'y':'Ventas Totales'}, title='Top 5 Productos Más Vendidos')
fig_ventas.update_layout(xaxis={'categoryorder':'total descending', 'tickangle': -45, 'tickmode': 'array', 'tickvals': top_5_productos_ventas.index, 'ticktext': [wrap_text(name) for name in top_5_productos_ventas.index]})


# Mostrar la gráfica de barras de ventas
st.header('Top 5 Productos Más Vendidos')
st.plotly_chart(fig_ventas)

# Identificar los top 5 productos por ganancias
top_5_productos_ganancias = ganancias_por_producto.sort_values(ascending=False).head(5)

# Crear la gráfica de barras de ganancias
fig_ganancias = px.bar(x=top_5_productos_ganancias.index, y=top_5_productos_ganancias.values, labels={'x':'Nombre del Producto', 'y':'Ganancias Totales'}, title='Top 5 Productos con Mayor Ganancia')
fig_ganancias.update_layout(xaxis={'categoryorder':'total descending', 'tickangle': -45, 'tickmode': 'array', 'tickvals': top_5_productos_ganancias.index, 'ticktext': [wrap_text(name) for name in top_5_productos_ganancias.index]})


# Mostrar la gráfica de barras de ganancias
st.header('Top 5 Productos con Mayor Ganancia')
st.plotly_chart(fig_ganancias)

# Preparar los datos para el gráfico de dispersión
df_product_summary = pd.concat([ventas_por_producto, ganancias_por_producto], axis=1)
df_product_summary.columns = ['Ventas Totales', 'Ganancias Totales']

# Crear el gráfico de dispersión
fig_scatter = px.scatter(df_product_summary, x='Ventas Totales', y='Ganancias Totales', hover_name=df_product_summary.index, title='Relación entre Ventas y Ganancias por Producto')

# Mostrar el gráfico de dispersión
st.header('Relación entre Ventas y Ganancias por Producto')
st.plotly_chart(fig_scatter)

st.markdown("""
## Resumen del Análisis:

### Hallazgos Clave

*   Se identificaron los 5 productos con mayores ventas y los 5 productos con mayores ganancias, destacando la importancia de productos como la "Canon imageCLASS 2200 Advanced Copier" en ambos aspectos.
*   El gráfico de dispersión muestra la relación entre las ventas y ganancias para todos los productos, permitiendo identificar productos de alto rendimiento y aquellos que podrían requerir atención debido a bajas ganancias a pesar de altas ventas.

### Próximos Pasos

*   Investigar más a fondo los productos con alta discrepancia entre ventas y ganancias para optimizar estrategias de precios o costos.
*   Considerar estrategias para replicar el éxito de los productos más rentables en otras categorías.
""")
