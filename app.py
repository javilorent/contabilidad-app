import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

# PIN de acceso (Cámbialo por el PIN que queráis utilizar)
PIN_CORRECTO = "8411"

# Configuración de la página para dispositivos móviles
st.set_page_config(
    page_title="Contabilidad", page_icon="💰", layout="centered"
)


# --- CONTROL DE ACCESO MEDIANTE PIN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔒 Acceso Privado")
    pin_introducido = st.text_input(
        "Introduce el PIN de acceso:", type="password"
    )

    if st.button("Entrar", type="primary"):
        if pin_introducido == PIN_CORRECTO:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("PIN incorrecto. Inténtalo de nuevo.")
    st.stop()  # Detiene la ejecución si no está autenticado


# --- INICIALIZACIÓN DE LA BASE DE DATOS LOCAL ---
conn = sqlite3.connect("contabilidad.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        tipo TEXT,
        concepto TEXT,
        monto REAL
    )
"""
)
conn.commit()


# --- CÁLCULO Y MUESTRA DEL SALDO ---
df_total = pd.read_sql_query("SELECT tipo, monto FROM movimientos", conn)
ingresos = (
    df_total[df_total["tipo"] == "Ingreso"]["monto"].sum()
    if not df_total.empty
    else 0.0
)
gastos = (
    df_total[df_total["tipo"] == "Gasto"]["monto"].sum()
    if not df_total.empty
    else 0.0
)
saldo = ingresos - gastos

st.title("📱 Contabilidad Diaria")
st.metric(label="Saldo Actual Total", value=f"{saldo:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))

st.divider()


# --- FORMULARIO PARA REGISTRAR MOVIMIENTOS ---
st.subheader("➕ Añadir Movimiento")

with st.form("nuevo_registro", clear_on_submit=True):
    fecha = st.date_input("Fecha", date.today())
    tipo = st.radio("Tipo de movimiento", ["Ingreso", "Gasto"], horizontal=True)
    concepto = st.text_input(
        "Concepto / Detalle", placeholder="Ej. Cobro cliente, Gasolina, Supermercado..."
    )
    monto = st.number_input("Importe (€)", min_value=0.0, step=1.0, format="%.2f")

    guardar = st.form_submit_button("Guardar Registro", type="primary")

    if guardar:
        if monto > 0:
            cursor.execute(
                "INSERT INTO movimientos (fecha, tipo, concepto, monto) VALUES (?, ?, ?, ?)",
                (fecha.strftime("%Y-%m-%d"), tipo, concepto, monto),
            )
            conn.commit()
            st.success("✅ Guardado correctamente")
            st.rerun()
        else:
            st.warning("Introduce un importe mayor que 0.")

st.divider()


# --- HISTORIAL Y EDICIÓN DE DÍAS ANTERIORES ---
st.subheader("📋 Historial y Edición")

df_historial = pd.read_sql_query(
    "SELECT id, fecha, tipo, concepto, monto FROM movimientos ORDER BY fecha DESC, id DESC",
    conn,
)

if not df_historial.empty:
    st.caption(
        "Puedes modificar cualquier casilla directamente en la tabla o borrar filas seleccionándolas."
    )

    df_editado = st.data_editor(
        df_historial,
        num_rows="dynamic",
        key="editor_tabla",
        disabled=["id"],
        use_container_width=True,
        column_config={
            "id": "ID",
            "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "tipo": st.column_config.SelectboxColumn(
                "Tipo", options=["Ingreso", "Gasto"]
            ),
            "concepto": st.column_config.TextColumn("Concepto"),
            "monto": st.column_config.NumberColumn("Importe (€)", format="%.2f €"),
        },
    )

    if st.button("💾 Aplicar Cambios Realizados"):
        cursor.execute("DELETE FROM movimientos")
        for _, row in df_editado.iterrows():
            cursor.execute(
                "INSERT INTO movimientos (id, fecha, tipo, concepto, monto) VALUES (?, ?, ?, ?, ?)",
                (
                    row["id"],
                    str(row["fecha"]),
                    row["tipo"],
                    row["concepto"],
                    row["monto"],
                ),
            )
        conn.commit()
        st.success("✅ Historial actualizado")
        st.rerun()
else:
    st.info("Aún no hay movimientos registrados.")
