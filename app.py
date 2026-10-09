import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# Configuración de página móvil
st.set_page_config(page_title="Contabilidad Familiar", page_icon="💰", layout="centered")

# Ocultar barra superior y menú para estética de App móvil
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    </style>
""", unsafe_allow_html=True)

# Inicializar cliente de Supabase desde los Secrets
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Sistema de PIN
PIN_CORRECTO = "1234"

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔒 Acceso Restringido")
    pin_input = st.text_input("Introduce tu PIN para acceder", type="password")
    if st.button("Entrar", use_container_width=True):
        if pin_input == PIN_CORRECTO:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("PIN incorrecto")
    st.stop()

# --- APLICACIÓN PRINCIPAL ---
st.title("💰 Contabilidad Familiar")

# Obtener datos de Supabase
try:
    response = supabase.table("movimientos").select("*").order("fecha", desc=True).execute()
    datos = response.data or []
except Exception as e:
    datos = []

# Calcular Totales Globale
if datos:
    df = pd.DataFrame(datos)
    ingresos = df[df["tipo"] == "Ingreso"]["monto"].sum() if "tipo" in df.columns else 0.0
    gastos = df[df["tipo"] == "Gasto"]["monto"].sum() if "tipo" in df.columns else 0.0
else:
    df = pd.DataFrame()
    ingresos = 0.0
    gastos = 0.0

saldo_total = ingresos - gastos

# --- TARJETA DE SALDO PRINCIPAL (Siempre visible arriba) ---
st.metric("Saldo Actual", f"{saldo_total:.2f} €", delta=f"{ingresos - gastos:.2f} €" if datos else None)

col1, col2 = st.columns(2)
col1.metric("Total Ingresos", f"{ingresos:.2f} €")
col2.metric("Total Gastos", f"{gastos:.2f} €")

st.divider()

# Pestañas para Registrar u Ordinar Movimientos
tab1, tab2 = st.tabs(["📝 Registrar", "📊 Historial"])

with tab1:
    st.subheader("Nuevo Registro")
    
    with st.form("form_gastos", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.now())
        tipo = st.selectbox("Tipo de movimiento", ["Gasto", "Ingreso"])
        concepto = st.text_input("Concepto / Descripción")
        monto = st.number_input("Importe (€)", min_value=0.01, step=0.50, format="%.2f")
        
        submitted = st.form_submit_button("Guardar Movimiento", use_container_width=True)
        
        if submitted:
            if concepto.strip() == "":
                st.warning("Por favor, escribe un concepto.")
            else:
                data = {
                    "fecha": fecha.strftime("%Y-%m-%d"),
                    "tipo": tipo,
                    "concepto": concepto.strip(),
                    "monto": float(monto)
                }
                supabase.table("movimientos").insert(data).execute()
                st.success(f"✅ {tipo} registrado correctamente.")
                st.rerun()

with tab2:
    st.subheader("Historial de Movimientos")
    
    if not df.empty:
        df_mostrar = df[["fecha", "tipo", "concepto", "monto"]].copy()
        df_mostrar.columns = ["Fecha", "Tipo", "Concepto", "Importe (€)"]
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay movimientos registrados.")
