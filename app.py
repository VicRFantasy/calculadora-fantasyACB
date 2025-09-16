import streamlit as st
import pandas as pd
import re

# Configuración de la página
st.set_page_config(layout="wide", page_title="Fantasy ACB", page_icon="🏀")

# Cargar datos
@st.cache_data
def load_data():
    df = pd.read_excel("jugadores.xlsx")
    df.columns = df.columns.str.strip()
    df["Posición"] = df["Posición"].astype(str).str.strip().str.upper()
    df["Nombre"] = df["Nombre"].astype(str).str.strip()
    return df

df = load_data()

# Parsing de precios
def parse_price_to_euros(val):
    if pd.isna(val): return 0
    if isinstance(val, (int, float)):
        try:
            v = float(val)
            return int(round(v * 1_000_000)) if v <= 10000 else int(round(v))
        except:
            return 0
    
    s = str(val).strip().replace('€', '').replace(' ', '')
    
    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif s.count('.') > 1:
        s = s.replace('.', '')
    elif ',' in s and '.' not in s:
        s = s.replace(',', '.')
    
    s = re.sub(r'[^0-9.]', '', s)
    if not s: return 0
    
    try:
        euros = float(s)
        return int(round(euros * 1_000_000)) if euros <= 10000 else int(round(euros))
    except:
        return 0

df['Precio_Euros'] = df['Precio'].apply(parse_price_to_euros)
price_euros = dict(zip(df['Nombre'], df['Precio_Euros']))
posicion_map = dict(zip(df['Nombre'], df['Posición']))

# Inicializar estado
if 'jugadores_seleccionados' not in st.session_state:
    st.session_state.jugadores_seleccionados = [None] * 8
if 'errores' not in st.session_state:
    st.session_state.errores = [''] * 8

presupuesto_inicial = 5_000_000
nombres_jugadores = ['(vacío)'] + df['Nombre'].tolist()

# Helper functions
def format_euros(euros_amount):
    return f"{int(round(euros_amount)):,}".replace(",", ".")

def validar_seleccion(jugador, indice):
    if not jugador or jugador == "(vacío)":
        return True, ""
    
    # Verificar duplicados
    for i, j in enumerate(st.session_state.jugadores_seleccionados):
        if i != indice and j == jugador:
            return False, f"❌ {jugador} ya está seleccionado en Ronda {i+1}"
    
    # Verificar límites por posición
    pos = posicion_map.get(jugador, "B")
    limites = {"B": 2, "A": 3, "P": 3}
    
    contador = sum(1 for i, j in enumerate(st.session_state.jugadores_seleccionados) 
                  if i != indice and j and posicion_map.get(j, "") == pos)
    
    if contador >= limites[pos]:
        return False, f"❌ Límite de {limites[pos]} {pos} alcanzado"
    
    # Verificar presupuesto
    total_actual = sum(price_euros.get(j, 0) for j in st.session_state.jugadores_seleccionados if j)
    precio_jugador = price_euros.get(jugador, 0)
    
    jugador_actual = st.session_state.jugadores_seleccionados[indice]
    if jugador_actual:
        total_actual -= price_euros.get(jugador_actual, 0)
    
    if total_actual + precio_jugador > presupuesto_inicial:
        exceso = total_actual + precio_jugador - presupuesto_inicial
        return False, f"❌ Supera el presupuesto por {format_euros(exceso)} €"
    
    return True, ""

# Interfaz de usuario
st.title("🏀 Calculadora The Fantasy Basket ACB")
st.markdown("### 🏆 Arma tu equipo ideal y controla tu presupuesto")

# Layout principal
col1, col2 = st.columns([1, 2])

with col1:
    # Panel de presupuesto y equipo
    st.subheader("💰 Presupuesto")
    total_gastado = sum(price_euros.get(j, 0) for j in st.session_state.jugadores_seleccionados if j)
    restante = presupuesto_inicial - total_gastado
    pct = min(total_gastado / presupuesto_inicial, 1.0)
    
    st.write(f"**Gastado:** {format_euros(total_gastado)} € — ({pct:.0%})")
    st.progress(pct)
    st.write(f"**Restante:** {format_euros(restante)} €")
    
    st.subheader("👥 Tu equipo")
    for i, jugador in enumerate(st.session_state.jugadores_seleccionados):
        if jugador:
            pos = posicion_map.get(jugador, "B")
            precio = price_euros.get(jugador, 0)
            st.write(f"{i+1}. {pos} - {jugador} - {format_euros(precio)} €")
        else:
            st.write(f"{i+1}. _(vacío)_")

with col2:
    # Selectores de jugadores
    st.subheader("🎯 Selección de Jugadores")
    
    # Dividir en dos columnas
    col2_1, col2_2 = st.columns(2)
    
    with col2_1:
        for i in range(4):
            ronda_num = i + 1
            jugador_actual = st.session_state.jugadores_seleccionados[i]
            indice_actual = nombres_jugadores.index(jugador_actual) if jugador_actual else 0
            
            nuevo_jugador = st.selectbox(
                f"Ronda {ronda_num}",
                nombres_jugadores,
                index=indice_actual,
                key=f"selector_{i}"
            )
            
            # Botón de eliminar
            if st.button("❌", key=f"eliminar_{i}"):
                st.session_state.jugadores_seleccionados[i] = None
                st.session_state.errores[i] = ""
                st.rerun()
            
            # Validar y actualizar
            if nuevo_jugador != jugador_actual:
                if nuevo_jugador == "(vacío)":
                    st.session_state.jugadores_seleccionados[i] = None
                    st.session_state.errores[i] = ""
                else:
                    es_valido, mensaje_error = validar_seleccion(nuevo_jugador, i)
                    if es_valido:
                        st.session_state.jugadores_seleccionados[i] = nuevo_jugador
                        st.session_state.errores[i] = ""
                    else:
                        st.session_state.errores[i] = mensaje_error
            
            # Mostrar error
            if st.session_state.errores[i]:
                st.error(st.session_state.errores[i])
    
    with col2_2:
        for i in range(4, 8):
            ronda_num = i + 1
            jugador_actual = st.session_state.jugadores_seleccionados[i]
            indice_actual = nombres_jugadores.index(jugador_actual) if jugador_actual else 0
            
            nuevo_jugador = st.selectbox(
                f"Ronda {ronda_num}",
                nombres_jugadores,
                index=indice_actual,
                key=f"selector_{i}"
            )
            
            # Botón de eliminar
            if st.button("❌", key=f"eliminar_{i}"):
                st.session_state.jugadores_seleccionados[i] = None
                st.session_state.errores[i] = ""
                st.rerun()
            
            # Validar y actualizar
            if nuevo_jugador != jugador_actual:
                if nuevo_jugador == "(vacío)":
                    st.session_state.jugadores_seleccionados[i] = None
                    st.session_state.errores[i] = ""
                else:
                    es_valido, mensaje_error = validar_seleccion(nuevo_jugador, i)
                    if es_valido:
                        st.session_state.jugadores_seleccionados[i] = nuevo_jugador
                        st.session_state.errores[i] = ""
                    else:
                        st.session_state.errores[i] = mensaje_error
            
            # Mostrar error
            if st.session_state.errores[i]:
                st.error(st.session_state.errores[i])

# Mostrar resumen de errores
errores_activos = [e for e in st.session_state.errores if e]
if errores_activos:
    st.error("### Resumen de problemas:")
    for error in errores_activos:
        st.write(f"• {error}")
