import streamlit as st
import pandas as pd

@st.cache_data(ttl=3600)
def load_data():
    return pd.read_csv('output/variaciones_productos.csv')

df = load_data()
st.title("Monitor Inteligente de la Canasta Básica")
st.sidebar.header("Configuración")
productos = st.sidebar.multiselect("Productos", df['producto'].unique(), default=df['producto'].unique())
df_sel = df[df['producto'].isin(productos)]
chart = df_sel.pivot(index='mes', columns='producto', values='variacion')
st.line_chart(chart)
st.dataframe(df_sel)
