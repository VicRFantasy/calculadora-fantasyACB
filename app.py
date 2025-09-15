import streamlit as st
import pandas as pd
import re

# =======================
# Configuración de la página
# =======================
st.set_page_config(layout="wide", page_title="Fantasy ACB", page_icon="🏀")

# =======================
# Cargar jugadores desde Excel
# =======================
@st.cache_data
def load_data():
    df = pd.read_excel("jugadores.xlsx")
    df.columns = df.columns.str.strip()
    df["Posición"] = df["Posición"].astype(str).str.strip().str.upper()
    df["Nombre"] = df["Nombre"].astype(str).str.strip()
    return df

df = load_data()

# =======================
# Parsing robusto de precios
# =======================
def parse_price_to_euros(val):
    if pd.isna(val): 
        return 0 
    if isinstance(val, (int, float)): 
        try: 
            v = float(val)
            if v > 10000: 
                return int(round(v))
            else: 
                return int(round(v * 1_000_000))
        except: 
            return 0
    
    s = str(val).strip()
    s = s.replace('€', '').replace(' ', '')
    
    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        if s.count('.') > 1:
            s = s.replace('.', '')
        elif ',' in s and '.' not in s:
            s = s.replace(',', '.')
    
    s = re.sub(r'[^0-9.]', '', s)
    if s == "": 
        return 0
    
    try:
        euros = float(s)
    except:
        return 0
    
    if euros > 10000:
        return int(round(euros))
    
    return int(round(euros * 1_000_000))

df['Precio_Euros'] = df['Precio'].apply(parse_price_to_euros)

# lookups rápidos
price_euros = dict(zip(df['Nombre'], df['Precio_Euros']))
posicion_map = dict(zip(df['Nombre'], df['Posición']))

# =======================
# Estado inicial simplificado
# =======================
presupuesto_inicial = 5_000_000  # euros

# Inicializar estado de sesión
for i in range(1, 9):
    if f"ronda_{i}" not in st.session_state:
        st.session_state[f"ronda_{i}"] = None
    if f"error_{i}" not in st.session_state:
        st.session_state[f"error_{i}"] = ""

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# =======================
# Helpers de formato
# =======================
def format_euros(euros_amount):
    euros = int(round(euros_amount))
    return f"{euros:,}".replace(",", ".")  # separador de miles con punto

# =======================
# Validaciones
# =======================
def validar_seleccion(jugador, ronda_actual):
    """
    Valida si un jugador puede ser seleccionado
    Devuelve (es_valido, mensaje_error)
    """
    # Si no hay jugador seleccionado, es válido
    if not jugador or jugador == "(vacío)":
        return True, ""
    
    # 1. Verificar si el jugador ya está seleccionado en otra ronda
    for i in range(1, 9):
        if i != ronda_actual and st.session_state[f"ronda_{i}"] == jugador:
            return False, f"❌ {jugador} ya está seleccionado en Ronda {i}"
    
    # 2. Verificar límites por posición
    pos = posicion_map.get(jugador, "B")
    limites = {"B": 2, "A": 3, "P": 3}
    
    # Contar jugadores actuales de esta posición (excluyendo la selección actual)
    contador = 0
    for i in range(1, 9):
        if i != ronda_actual:
            jugador_existente = st.session_state[f"ronda_{i}"]
            if jugador_existente and posicion_map.get(jugador_existente, "") == pos:
                contador += 1
    
    # Si al añadir este jugador superaríamos el límite
    if contador >= limites[pos]:
        return False, f"❌ Límite de {limites[pos]} {posicion_a_texto(pos)} alcanzado"
    
    # 3. Verificar presupuesto
    total_actual = 0
    for i in range(1, 9):
        jugador_actual = st.session_state[f"ronda_{i}"]
        if jugador_actual:
            total_actual += price_euros.get(jugador_actual, 0)
    
    precio_jugador = price_euros.get(jugador, 0)
    
    # Si estamos reemplazando un jugador, restar su precio
    jugador_actual_ronda = st.session_state[f"ronda_{ronda_actual}"]
    if jugador_actual_ronda:
        total_actual -= price_euros.get(jugador_actual_ronda, 0)
    
    if total_actual + precio_jugador > presupuesto_inicial:
        exceso = total_actual + precio_jugador - presupuesto_inicial
        return False, f"❌ Supera el presupuesto por {format_euros(exceso)} €"
    
    return True, ""

def posicion_a_texto(pos):
    """Convierte código de posición a texto"""
    mapping = {"B": "Bases", "A": "Aleros", "P": "Pívots"}
    return mapping.get(pos, pos)

# =======================
# Render presupuesto y roster
# =======================
def render_budget_and_team(container):
    total_gastado = 0
    for i in range(1, 9):
        jugador = st.session_state[f"ronda_{i}"]
        if jugador:
            total_gastado += price_euros.get(jugador, 0)
            
    restante = presupuesto_inicial - total_gastado
    pct = min(total_gastado / max(presupuesto_inicial, 1e-9), 1.0)
    
    container.markdown("**💰 Presupuesto**")
    container.write(f"**Gastado:** {format_euros(total_gastado)} € — ({int(pct*100)}%)")
    
    # barra de progreso
    container.markdown(f"""
    <div style="margin:6px 0">
        <div style="width:100%;background:#e6f4ff;border-radius:10px;height:14px;overflow:hidden;border:1px solid rgba(96,165,250,0.15)">
            <div style="height:100%;background:#ef4444;width:{pct*100}%"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if restante < 0:
        container.error(f"⚠️ Te has pasado: -{format_euros(abs(restante))} €")
    else:
        container.write(f"**Restante:** {format_euros(restante)} €")
    
    container.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(0,0,0,0.1),transparent);margin:10px 0"></div>', unsafe_allow_html=True)
    container.markdown("**👥 Tu equipo**")
    
    # Agrupar por posición y mostrar con pastilla redondeada + nombre + precio
    grouped = {"B": [], "A": [], "P": []}
    for i in range(1, 9):
        jugador = st.session_state[f"ronda_{i}"]
        if jugador:
            pos = posicion_map.get(jugador, "B")
            grouped.setdefault(pos, []).append(jugador)
    
    labels = {"B": "Bases", "A": "Aleros", "P": "Pívots"}
    caps = {"B": 2, "A": 3, "P": 3}
    
    for code in ["B", "A", "P"]:
        container.markdown(f"**{labels[code]}:** {len(grouped.get(code, []))}/{caps[code]}")
        if grouped.get(code):
            for name in grouped[code]:
                precio = format_euros(price_euros.get(name, 0))
                color = "#1D4ED8" if code == "B" else "#059669" if code == "A" else "#D97706"
                container.markdown(f'<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin:6px 0;padding-right:4px"><div><span style="display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;margin-right:8px;font-weight:600;color:#fff;min-width:26px;text-align:center;background:{color}">{code}</span> {name} – {precio} €</div></div>', unsafe_allow_html=True)
        else:
            container.write(" • _(vacío)_")
    
    container.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(0,0,0,0.1),transparent);margin:10px 0"></div>', unsafe_allow_html=True)

# =======================
# Interfaz de usuario
# =======================
# Cabecera
header_col1, header_col2 = st.columns([3, 1])

with header_col1:
    st.markdown("""<h1 style="font-weight:700; background: linear-gradient(135deg, #60A5FA, #34D399); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-top: -1rem;">Calculadora The Fantasy Basket ACB</h1>""", unsafe_allow_html=True)

with header_col2:
    new_theme = st.selectbox("🎨 Tema", ["dark", "light"], index=0 if st.session_state.theme=="dark" else 1, key="theme_header")
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

st.markdown("### 🏆 Arma tu equipo ideal y controla tu presupuesto")
st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(0,0,0,0.1),transparent);margin:10px 0"></div>', unsafe_allow_html=True)

# Layout principal
col_left, col_right = st.columns([1, 3], gap="large")

with col_left:
    render_budget_and_team(col_left)

with col_right:
    st.markdown("### 🎯 Selección de Jugadores")
    right_col1, right_col2 = st.columns(2, gap="medium")
    
    names = df["Nombre"].tolist()
    options = ["(vacío)"] + names
    
    # Función para renderizar cada selector de ronda
    def render_ronda_selector(col, ronda_num):
        ronda_key = f"ronda_{ronda_num}"
        error_key = f"error_{ronda_num}"
        
        # Obtener selección actual
        current_selection = st.session_state[ronda_key]
        default_index = 0 if current_selection is None else options.index(current_selection)
        
        # Crear selectbox
        col1, col2 = col.columns([5, 1])
        
        with col1:
            jugador = st.selectbox(
                f"Ronda {ronda_num}",
                options=options,
                index=default_index,
                key=f"selector_{ronda_num}"
            )
            
            # Procesar selección
            if jugador != current_selection:
                if jugador == "(vacío)":
                    st.session_state[ronda_key] = None
                    st.session_state[error_key] = ""
                else:
                    es_valido, mensaje_error = validar_seleccion(jugador, ronda_num)
                    if es_valido:
                        st.session_state[ronda_key] = jugador
                        st.session_state[error_key] = ""
                    else:
                        st.session_state[error_key] = mensaje_error
                        # Revertir a la selección anterior
                        st.session_state[f"selector_{ronda_num}"] = current_selection if current_selection else "(vacío)"
            
            # Mostrar mensaje de error si existe
            if st.session_state[error_key]:
                st.error(st.session_state[error_key])
        
        with col2:
            # Botón para eliminar
            st.markdown('<div style="display:flex;align-items:center;height:100%;padding-top:1.5rem">', unsafe_allow_html=True)
            if st.button("❌", key=f"delete_{ronda_num}"):
                st.session_state[ronda_key] = None
                st.session_state[error_key] = ""
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Renderizar selectores
    with right_col1:
        for i in range(1, 5):
            render_ronda_selector(right_col1, i)
    
    with right_col2:
        for i in range(5, 9):
            render_ronda_selector(right_col2, i)
    
    # Mostrar resumen de errores
    errores_activos = []
    for i in range(1, 9):
        error = st.session_state[f"error_{i}"]
        if error:
            errores_activos.append(error)
    
    if errores_activos:
        st.markdown("---")
        st.error("### Resumen de problemas:")
        for error in errores_activos:
            st.write(f"• {error}")
