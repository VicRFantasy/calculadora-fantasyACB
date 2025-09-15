import streamlit as st
import pandas as pd
import re

# =======================
# Configuración de la página
# =======================
st.set_page_config(layout="wide", page_title="Fantasy ACB", page_icon="🏀", initial_sidebar_state="collapsed")

# =======================
# Cargar jugadores desde Excel
# =======================
df = pd.read_excel("jugadores.xlsx")
df.columns = df.columns.str.strip()

# Normalizar posiciones y nombres
df["Posición"] = df["Posición"].astype(str).str.strip().str.upper()
df["Nombre"] = df["Nombre"].astype(str).str.strip()

# =======================
# Parsing robusto de precios -> devuelve valor en euros (int)
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
# Estado inicial
# =======================
presupuesto_inicial = 5_000_000  # euros

if "seleccionados" not in st.session_state:
    st.session_state.seleccionados = {f"Ronda {i}": None for i in range(1, 9)} 

if "widget_counter" not in st.session_state:
    st.session_state.widget_counter = 0 

if "theme" not in st.session_state:
    st.session_state.theme = "dark" 

# =======================
# CSS dinámico basado en tema
# =======================
# Colores según tema
if st.session_state.theme == "dark":
    bg_color = "#0e1117"
    text_color = "#ffffff"
    divider_color = "rgba(255,255,255,0.1)"
    progress_bg = "#1a1a1a"
    progress_border = "rgba(255,255,255,0.1)"
    error_color = "#f87171"
else:
    bg_color = "#ffffff"
    text_color = "#000000"
    divider_color = "rgba(0,0,0,0.08)"
    progress_bg = "#e6f4ff"
    progress_border = "rgba(96,165,250,0.15)"
    error_color = "#dc2626"

st.markdown(f"""
<style>
/* Mostrar/ocultar según pantalla */
.desktop-only{{display:block;}}
.mobile-only{{display:none;}}
@media (max-width: 768px){{
    .desktop-only{{display:none !important;}}
    .mobile-only{{display:block !important;}}
    /* Reducir espaciado en móvil */
    .stSelectbox > div > div{{margin-bottom: 0.25rem !important;}}
    div[data-testid="column"] > div{{gap: 0.25rem !important;}}
    /* Mejor espaciado para selectboxes */
    .stSelectbox{{margin-bottom: 0.5rem !important;}}
}}
/* Tema dinámico - aplicar al contenedor principal */
.stApp, [data-testid="stAppViewContainer"] {{
    background-color: {bg_color} !important;
    color: {text_color} !important;
}}
.main-bg{{background-color: {bg_color}; color: {text_color};}}
/* Divider */
.divider{{height:1px;background:linear-gradient(90deg,transparent,{divider_color},transparent);margin:10px 0}}
/* Pastilla redondeada (chip) */
.chip{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;margin-right:8px;font-weight:600;color:#fff;min-width:26px;text-align:center}}
.chip.B{{background:#1D4ED8}}
.chip.A{{background:#059669}}
.chip.P{{background:#D97706}}
/* Player line */
.player-line{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:6px 0;padding-right:4px}}
/* Barra de presupuesto estilo: base azul y barra roja interior */
.progress-wrap{{width:100%;background:{progress_bg};border-radius:10px;height:14px;overflow:hidden;border:1px solid {progress_border}}}
.progress-inner{{height:100%;background:#ef4444;width:0%;transition:width .3s ease}}
/* Mensajes de error */
.error-message {{
    color: {error_color};
    font-size: 0.9rem;
    margin-top: 4px;
    padding: 4px 8px;
    border-radius: 4px;
    background-color: rgba(220, 38, 38, 0.1);
}}
/* Adaptaciones móviles */
@media (max-width: 480px){{
    .chip{{min-width:22px;padding:2px 6px;font-size:10px}}
    .player-line{{gap:8px}}
}}
</style>
""", unsafe_allow_html=True)

# =======================
# Helpers de formato
# =======================
def format_euros(euros_amount):
    euros = int(round(euros_amount))
    return f"{euros:,}".replace(",", ".")  # separador de miles con punto

def safe_index_of(name, names_list):
    try:
        return names_list.index(name) + 1
    except ValueError:
        return 0

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
    for ronda, seleccion in st.session_state.seleccionados.items():
        if ronda != ronda_actual and seleccion == jugador:
            return False, f"❌ {jugador} ya está seleccionado en {ronda}"
    
    # 2. Verificar límites por posición
    pos = posicion_map.get(jugador, "B")
    limites = {"B": 2, "A": 3, "P": 3}
    
    # Contar jugadores actuales de esta posición (excluyendo la selección actual)
    contador = 0
    for ronda, seleccion in st.session_state.seleccionados.items():
        if ronda != ronda_actual and seleccion and posicion_map.get(seleccion, "") == pos:
            contador += 1
    
    # Si al añadir este jugador superaríamos el límite
    if contador >= limites[pos]:
        return False, f"❌ Límite de {limites[pos]} {posicion_a_texto(pos)} alcanzado"
    
    # 3. Verificar presupuesto
    total_actual = sum(price_euros.get(j, 0) for j in st.session_state.seleccionados.values() if j)
    precio_jugador = price_euros.get(jugador, 0)
    
    # Si estamos reemplazando un jugador, restar su precio
    jugador_actual = st.session_state.seleccionados.get(ronda_actual)
    if jugador_actual:
        total_actual -= price_euros.get(jugador_actual, 0)
    
    if total_actual + precio_jugador > presupuesto_inicial:
        exceso = total_actual + precio_jugador - presupuesto_inicial
        return False, f"❌ Supera el presupuesto por {format_euros(exceso)} €"
    
    return True, ""

def posicion_a_texto(pos):
    """Convierte código de posición a texto"""
    mapping = {"B": "Bases", "A": "Aleros", "P": "Pívots"}
    return mapping.get(pos, pos)

# =======================
# Render presupuesto y roster (con estilo pedido)
# =======================
def render_budget_and_team(container):
    total_gastado = sum(price_euros.get(j, 0) for j in st.session_state.seleccionados.values() if j)
    restante = presupuesto_inicial - total_gastado
    pct = min(total_gastado / max(presupuesto_inicial, 1e-9), 1.0)
    
    container.markdown("**💰 Presupuesto**")
    container.write(f"**Gastado:** {format_euros(total_gastado)} € — ({int(pct*100)}%)")
    
    # barra base azul (fondo) con barra roja interior proporcional
    container.markdown(f"""
    <div style="margin:6px 0">
        <div class="progress-wrap">
            <div class="progress-inner" style="width:{pct*100}%"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if restante < 0:
        container.error(f"⚠️ Te has pasado: -{format_euros(abs(restante))} €")
    else:
        container.write(f"**Restante:** {format_euros(restante)} €")
    
    container.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    container.markdown("**👥 Tu equipo**")
    
    # Agrupar por posición y mostrar con pastilla redondeada + nombre + precio
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
                container.markdown(f'<div class="player-line"><div><span class="chip {code}">{code}</span> {name} – {precio} €</div></div>', unsafe_allow_html=True)
        else:
            container.write(" • _(vacío)_")
    
    container.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =======================
# Cabecera
# =======================
# Theme toggle en la cabecera (visible en todos los dispositivos) - reduced spacing
header_col1, header_col2 = st.columns([3, 1])

with header_col1:
    st.markdown("""<h1 style="font-weight:700; background: linear-gradient(135deg, #60A5FA, #34D399); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-top: -1rem;">Calculadora The Fantasy Basket ACB</h1>""", unsafe_allow_html=True)

with header_col2:
    new_theme = st.selectbox("🎨 Tema", ["dark", "light"], index=0 if st.session_state.theme=="dark" else 1, key="theme_header")
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

st.markdown("### 🏆 Arma tu equipo ideal y controla tu presupuesto")
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =======================
# LAYOUT: Desktop (izq=presupuesto, der=selects) y Mobile (expander + selects)
# =======================
# Desktop layout: left narrow panel (presupuesto), right wide (selects)
col_left, col_right = st.columns([1, 3], gap="large")

with col_left:
    # Budget and team info for both desktop and mobile
    render_budget_and_team(col_left)

with col_right:
    st.markdown("### 🎯 Selección de Jugadores")
    right_col1, right_col2 = st.columns(2, gap="medium")
    
    rondas = list(st.session_state.seleccionados.keys())
    names = df["Nombre"].tolist()
    
    # Almacenar mensajes de error por ronda
    if "errores" not in st.session_state:
        st.session_state.errores = {ronda: "" for ronda in rondas}
    
    def render_ronda_widget(parent, ronda):
        cols = parent.columns([5, 1])
        key_sel = f"sel_{ronda}"
        
        with cols[0]:
            # Get the current selection from session state
            current_selection = st.session_state.seleccionados.get(ronda)
            idx = safe_index_of(current_selection, names)
            
            jugador = st.selectbox(
                f"{ronda}",
                options=["(vacío)"] + names,
                index=idx,
                key=key_sel
            )
            
            # Validar selección
            es_valido, mensaje_error = validar_seleccion(jugador, ronda)
            
            # Mostrar mensaje de error si existe
            if mensaje_error:
                st.markdown(f'<div class="error-message">{mensaje_error}</div>', unsafe_allow_html=True)
                st.session_state.errores[ronda] = mensaje_error
            else:
                st.session_state.errores[ronda] = ""
            
            # Actualizar selección solo si es válida
            if es_valido:
                if jugador != "(vacío)":
                    st.session_state.seleccionados[ronda] = jugador
                else:
                    st.session_state.seleccionados[ronda] = None
        
        with cols[1]:
            # Perfect X button alignment with CSS targeting
            st.markdown("""<style>
            div[data-testid="column"] > div > div > div > button {
                height: 2.4rem !important;
                margin-top: 0.2rem !important;
                padding: 0.25rem 0.5rem !important;
            }
            </style>""", unsafe_allow_html=True)
            
            if st.button("❌", key=f"del_{ronda}"):
                st.session_state.seleccionados[ronda] = None
                st.session_state.errores[ronda] = ""
                st.rerun()
    
    # Renderizar todas las rondas
    for r in rondas[:4]:
        render_ronda_widget(right_col1, r)
    
    for r in rondas[4:]:
        render_ronda_widget(right_col2, r)
    
    # Mostrar resumen de errores si existen
    errores_activos = [msg for msg in st.session_state.errores.values() if msg]
    if errores_activos:
        st.markdown("---")
        st.error("### Resumen de problemas:")
        for error in errores_activos:
            st.write(f"• {error}")


