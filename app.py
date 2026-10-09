import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# Configuración de página móvil
st.set_page_config(page_title="Contabilidad Familiar", page_icon="💰", layout="centered")

# CSS e inyección JS forzada para iOS / Android
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 1rem; padding-bottom: 2rem;}
    </style>
    <script>
    function forceNumericKeyboards() {
        var inputs = document.querySelectorAll('input[data-testid="stTextInput"]');
        inputs.forEach(function(input) {
            if (input.placeholder.includes("0.00") || input.id.includes("monto")) {
                input.setAttribute('inputmode', 'decimal');
                input.setAttribute('type', 'number');
                input.setAttribute('step', 'any');
                input.setAttribute('pattern', '[0-9]*');
            }
        });
    }
    var observer = new MutationObserver(forceNumericKeyboards);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener('load', forceNumericKeyboards);
    </script>
""", unsafe_allow_html=True)

# Inicializar cliente de Supabase desde los Secrets
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception:
    st.error("Error al conectar con la base de datos. Revisa los Secrets en Streamlit Cloud.")
    st.stop()

# Sistema de PIN
PIN_CORRECTO = "8411"

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
st.title("💰 Contabilidad")

# Obtener datos de Supabase
try:
    response = supabase.table("movimientos").select("*").order("fecha", desc=True).execute()
    datos = response.data or []
except Exception:
    datos = []

# Calcular Totales Globales
if datos:
    df = pd.DataFrame(datos)
    ingresos = df[df["tipo"] == "Ingreso"]["monto"].sum() if "tipo" in df.columns else 0.0
    gastos = df[df["tipo"] == "Gasto"]["monto"].sum() if "tipo" in df.columns else 0.0
else:
    df = pd.DataFrame()
    ingresos = 0.0
    gastos = 0.0

saldo_total = ingresos - gastos

# --- TARJETA DE SALDO PRINCIPAL ---
st.metric("Saldo Actual", f"{saldo_total:.2f} €")

col1, col2 = st.columns(2)
col1.metric("Total Ingresos", f"{ingresos:.2f} €")
col2.metric("Total Gastos", f"{gastos:.2f} €")

st.divider()

tab1, tab2 = st.tabs(["📝 Registrar", "📊 Historial / Gestionar"])

with tab1:
    st.subheader("Nuevo Registro")
    
    with st.form("form_gastos", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.now(), format="DD/MM/YYYY")
        tipo = st.selectbox("Tipo de movimiento", ["Gasto", "Ingreso"])
        concepto = st.text_input("Concepto / Descripción")
        
        # Campo de texto optimizado para teclado numérico
        monto_str = st.text_input("Importe (€)", value="1.00", placeholder="0.00", key="monto_input")
        
        submitted = st.form_submit_button("Guardar Movimiento", use_container_width=True)
        
        if submitted:
            if concepto.strip() == "":
                st.warning("Por favor, escribe un concepto.")
            else:
                try:
                    # Remplazar coma por punto si se introduce con formato europeo
                    monto_val = float(monto_str.replace(",", "."))
                    if monto_val <= 0:
                        st.warning("El importe debe ser mayor a 0.")
                    else:
                        data = {
                            "fecha": fecha.strftime("%Y-%m-%d"),
                            "tipo": str(tipo),
                            "concepto": str(concepto.strip()),
                            "monto": float(monto_val)
                        }
                        supabase.table("movimientos").insert(data).select().execute()
                        st.success(f"✅ {tipo} registrado correctamente.")
                        st.rerun()
                except ValueError:
                    st.error("Introduce un número válido en el importe.")
                except Exception as err:
                    st.error(f"Error al guardar: {err}")

with tab2:
    st.subheader("Historial de Movimientos")
    
    if not df.empty:
        df_mostrar = df[["fecha", "tipo", "concepto", "monto"]].copy()
        
        try:
            df_mostrar["fecha"] = pd.to_datetime(df_mostrar["fecha"]).dt.strftime("%d/%m/%Y")
        except Exception:
            pass
            
        df_mostrar.columns = ["Fecha", "Tipo", "Concepto", "Importe (€)"]
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🗑️ Eliminar un Apunte")
        
        opciones = {}
        for _, row in df.iterrows():
            try:
                fecha_fmt = datetime.strptime(str(row['fecha']), "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                fecha_fmt = str(row['fecha'])
            key_label = f"{fecha_fmt} | {row['tipo']} | {row['concepto']} ({row['monto']:.2f} €)"
            opciones[key_label] = row["id"]
        
        seleccion = st.selectbox("Selecciona el registro a borrar:", list(opciones.keys()))
        
        if st.button("Eliminar apunte seleccionado", type="primary", use_container_width=True):
            id_borrar = opciones[seleccion]
            try:
                supabase.table("movimientos").delete().eq("id", id_borrar).execute()
                st.success("🗑️ Apunte eliminado correctamente.")
                st.rerun()
            except Exception as err:
                st.error(f"Error al eliminar: {err}")
    else:
        st.info("Aún no hay movimientos registrados.")
