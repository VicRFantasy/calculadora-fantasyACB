import streamlit as st
import pandas as pd
import re

# Configuración de la página
st.set_page_config(layout="wide", page_title="Fantasy ACB", page_icon="🏀", initial_sidebar_state="collapsed")

# Función para cargar datos
@st.cache_data
def load_data():
    try:
        df = pd.read_excel("jugadores.xlsx")
        df.columns = df.columns.str.strip()
        df["Posición"] = df["Posición"].astype(str).str.strip().str.upper()
        df["Nombre"] = df["Nombre"].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame(columns=["Nombre", "Posición", "Precio"])

# Parsing de precios
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

# Inicialización del estado
def init_session_state():
    if "seleccionados" not in st.session_state:
        st.session_state.seleccionados = {f"Ronda {i}": None for i in range(1, 9)}
    if "errores" not in st.session_state:
        st.session_state.errores = {f"Ronda {i}": "" for i in range(1, 9)}
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    if "last_action" not in st.session_state:
        st.session_state.last_action = {"type": None, "ronda": None}

# Helpers de formato
def format_euros(euros_amount):
    euros = int(round(euros_amount))
    return f"{euros:,}".replace(",", ".")

def safe_index_of(name, names_list):
    try:
        return names_list.index(name) + 1
    except ValueError:
        return 0

# Validaciones
def validar_seleccion(jugador, ronda_actual):
    if not jugador or jugador == "(vacío)":
        return True, ""
    
    # Verificar duplicados
    for ronda, seleccion in st.session_state.seleccionados.items():
        if ronda != ronda_actual and seleccion == jugador:
            return False, f"❌ {jugador} ya está seleccionado en {ronda}"
    
    # Verificar límites por posición
    pos = posicion_map.get(jugador, "B")
    limites = {"B": 2, "A": 3, "P": 3}
    
    contador = 0
    for ronda, seleccion in st.session_state.seleccionados.items():
        if ronda != ronda_actual and seleccion and posicion_map.get(seleccion, "") == pos:
            contador += 1
    
    if contador >= limites[pos]:
        return False, f"❌ Límite de {limites[pos]} {posicion_a_texto(pos)} alcanzado"
    
    # Verificar presupuesto
    total_actual = sum(price_euros.get(j, 0) for j in st.session_state.seleccionados.values() if j)
    precio_jugador = price_euros.get(jugador, 0)
    
    jugador_actual = st.session_state.seleccionados.get(ronda_actual)
    if jugador_actual:
        total_actual -= price_euros.get(jugador_actual, 0)
    
    if total_actual + precio_jugador > presupuesto_inicial:
        exceso = total_actual + precio_jugador - presupuesto_inicial
        return False, f"❌ Supera el presupuesto por {format_euros(exceso)} €"
    
    return True, ""

def posicion_a_texto(pos):
    mapping = {"B": "Bases", "A": "Aleros", "P": "Pívots"}
    return mapping.get(pos, pos)

# Render presupuesto y equipo
def render_budget_and_team(container):
    total_gastado = sum(price_euros.get(j, 0) for j in st.session_state.seleccionados.values() if j)
    restante = presupuesto_inicial - total_gastado
    pct = min(total_gastado / max(presupuesto_inicial, 1e-9), 1.0)
    
    container.markdown("**💰 Presupuesto**")
    container.write(f"**Gastado:** {format_euros(total_gastado)} € — ({int(pct*100)}%)")
    
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
    
    container.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.1),transparent);margin:10px 0"></div>', unsafe_allow_html=True)
    container.markdown("**👥 Tu equipo**")
    
    grouped = {"B": [], "A": [], "P": []}
    for ronda, jugador in st.session_state.seleccionados.items():
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
                container.markdown(f'<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin:6px 0;padding-right:4px"><div><span style="display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;margin-right:8px;font-weight:600;color:#fff;min-width:26px;text-align:center;background:{"#1D4ED8" if code=="B" else "#059669" if code=="A" else "#D97706"}">{code}</span> {name} – {precio} €</div></div>', unsafe_allow_html=True)
        else:
            container.write(" • _(vacío)_")
    
    container.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.1),transparent);margin:10px 0"></div>', unsafe_allow_html=True)

# Función principal
def main():
    init_session_state()
    
    # Cargar datos
    df = load_data()
    if df.empty:
        st.error("No se pudieron cargar los datos de jugadores.")
        return
    
    # Procesar datos
    global price_euros, posicion_map, presupuesto_inicial
    df['Precio_Euros'] = df['Precio'].apply(parse_price_to_euros)
    price_euros = dict(zip(df['Nombre'], df['Precio_Euros']))
    posicion_map = dict(zip(df['Nombre'], df['Posición']))
    presupuesto_inicial = 5_000_000
    
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
    st.markdown('<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.1),transparent);margin:10px 0"></div>', unsafe_allow_html=True)
    
    # Layout principal
    col_left, col_right = st.columns([1, 3], gap="large")
    
    with col_left:
        render_budget_and_team(col_left)
    
    with col_right:
        st.markdown("### 🎯 Selección de Jugadores")
        right_col1, right_col2 = st.columns(2, gap="medium")
        
        rondas = list(st.session_state.seleccionados.keys())
        names = df["Nombre"].tolist()
        
        # Procesar acciones
        for ronda in rondas:
            # Manejar eliminaciones
            if f"eliminar_{ronda}" in st.session_state and st.session_state[f"eliminar_{ronda}"]:
                st.session_state.seleccionados[ronda] = None
                st.session_state.errores[ronda] = ""
                st.session_state[f"eliminar_{ronda}"] = False
                st.session_state.last_action = {"type": "delete", "ronda": ronda}
                st.rerun()
            
            # Manejar selecciones
            select_key = f"select_{ronda}"
            if select_key in st.session_state:
                jugador_seleccionado = st.session_state[select_key]
                jugador_actual = st.session_state.seleccionados.get(ronda)
                
                if jugador_seleccionado != jugador_actual:
                    if jugador_seleccionado == "(vacío)":
                        st.session_state.seleccionados[ronda] = None
                        st.session_state.errores[ronda] = ""
                    else:
                        es_valido, mensaje_error = validar_seleccion(jugador_seleccionado, ronda)
                        if es_valido:
                            st.session_state.seleccionados[ronda] = jugador_seleccionado
                            st.session_state.errores[ronda] = ""
                        else:
                            st.session_state.errores[ronda] = mensaje_error
                            # Revertir la selección
                            st.session_state[select_key] = jugador_actual if jugador_actual else "(vacío)"
        
        # Renderizar widgets
        def render_ronda_widget(parent, ronda):
            cols = parent.columns([5, 1])
            
            with cols[0]:
                current_selection = st.session_state.seleccionados.get(ronda)
                options = ["(vacío)"] + names
                default_index = 0 if current_selection is None else options.index(current_selection)
                
                jugador = st.selectbox(
                    f"{ronda}",
                    options=options,
                    index=default_index,
                    key=f"select_{ronda}"
                )
                
                if st.session_state.errores[ronda]:
                    st.markdown(f'<div style="color:#f87171;font-size:0.9rem;margin-top:4px;padding:4px 8px;border-radius:4px;background-color:rgba(220,38,38,0.1)">{st.session_state.errores[ronda]}</div>', unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown('<div style="display:flex;align-items:center;height:100%;padding-top:1.5rem">', unsafe_allow_html=True)
                if st.button("❌", key=f"btn_del_{ronda}"):
                    st.session_state[f"eliminar_{ronda}"] = True
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Renderizar todas las rondas
        for r in rondas[:4]:
            render_ronda_widget(right_col1, r)
        
        for r in rondas[4:]:
            render_ronda_widget(right_col2, r)
        
        # Mostrar resumen de errores
        errores_activos = [msg for msg in st.session_state.errores.values() if msg]
        if errores_activos:
            st.markdown("---")
            st.error("### Resumen de problemas:")
            for error in errores_activos:
                st.write(f"• {error}")

if __name__ == "__main__":
    main()
