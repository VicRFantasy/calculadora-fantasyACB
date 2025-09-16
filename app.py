import streamlit as st
import pandas as pd
import re

# =======================
# Configuración de la página
# =======================
st.set_page_config(layout="wide", page_title="The Fantasy Basket", page_icon="🏀", initial_sidebar_state="collapsed")

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
        # Si viene un número -> analizamos el rango
        try:
            v = float(val)
            if v > 100000:  # probablemente ya en euros completos
                return int(round(v))
            else:
                # números pequeños están en miles de euros (950 = 950,000€)
                return int(round(v * 1000))
        except:
            return 0
    s = str(val).strip()
    s = s.replace('€', '').replace(' ', '')
    # casos mixtos: '1.180.000', '950.00', '585.00'
    # si tiene '.' y ',' -> suponemos '.' miles y ',' decimales
    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        # si varios puntos -> eliminar puntos (son miles)
        if s.count('.') > 1:
            s = s.replace('.', '')
        else:
            # si tiene coma y no punto -> coma decimal
            if ',' in s and '.' not in s:
                s = s.replace(',', '.')
    # eliminar cualquier carácter no numérico salvo '.' 
    s = re.sub(r'[^0-9.]', '', s)
    if s == "":
        return 0
    try:
        euros = float(s)
    except:
        return 0
    # si la cifra es grande (>100000) tratamos como euros completos
    if euros > 100000:
        return int(round(euros))
    # si no, asumimos que está en miles y convertimos (950 = 950,000€)
    return int(round(euros * 1000))

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
    ronda_label_color = "#ffffff"
else:
    bg_color = "#ffffff"
    text_color = "#000000"
    divider_color = "rgba(0,0,0,0.08)"
    progress_bg = "#e6f4ff"
    progress_border = "rgba(96,165,250,0.15)"
    ronda_label_color = "#000000"

# Intentamos crear reglas específicas para Ronda 1..8 (si existen aria-labels),
# y también añadimos un fallback que colorea los labels de TODOS los selectboxes.
css_rondas_specific = "\n".join([
    f'div[data-testid="stSelectbox"][aria-label="Ronda {i}"] label {{ color: {ronda_label_color} !important; font-weight: 600; }}'
    for i in range(1, 9)
])

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

/* Fix white spaces and background consistency */
html, body, #root, .stApp, [data-testid="stAppViewContainer"], 
[data-testid="stHeader"], [data-testid="stToolbar"], 
.main, .main .block-container {{
    background-color: {bg_color} !important;
    color: {text_color} !important;
}}

/* Hide Streamlit's default header and toolbar to remove fixed menu */
[data-testid="stHeader"], 
[data-testid="stToolbar"],
header[data-testid="stHeader"] {{
    display: none !important;
    visibility: hidden !important;
}}

/* Remove top padding that was compensating for the header */
.main .block-container {{
    padding-top: 1rem !important;
}}

/* Tema dinámico - aplicar al contenedor principal */
.stApp, [data-testid="stAppViewContainer"] {{
    background-color: {bg_color} !important;
    color: {text_color} !important;
}}
.main-bg{{background-color: {bg_color}; color: {text_color};}}

/* Selectbox label styling for rounds */
{css_rondas_specific}

/* Fallback for all selectbox labels */
.stSelectbox label {{
    color: {ronda_label_color} !important;
    font-weight: 600 !important;
}}

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

/* Simple button styling for delete buttons */
.stButton > button {{
    height: 2.25rem !important;
    padding: 0.25rem 0.5rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}}

/* Reduce spacing between selectboxes */
.stSelectbox {{
    margin-bottom: 0.5rem !important;
}}

/* Compact column spacing without breaking title */
div[data-testid="column"] > div {{
    gap: 0.5rem !important;
}}

/* Mobile optimizations */
@media (max-width: 768px){{
  .stSelectbox {{
    margin-bottom: 0.25rem !important;
  }}
  
  div[data-testid="column"] > div {{
    gap: 0.25rem !important;
  }}
}}

@media (max-width: 480px){{
  .chip{{min-width:22px;padding:2px 6px;font-size:10px}}
  .player-line{{gap:8px}}
  
  .stSelectbox {{
    margin-bottom: 0.125rem !important;
  }}
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
# Render presupuesto y roster (con estilo pedido)
# =======================
def render_budget_and_team(container):

    total_gastado = sum(price_euros.get(j, 0) for j in st.session_state.seleccionados.values() if j)
    restante = presupuesto_inicial - total_gastado
    pct = min(total_gastado / max(presupuesto_inicial, 1e-9), 1.0)

    container.markdown("**💰 Presupuesto**")
    container.write(f"**Gastado:** {format_euros(total_gastado)} €  —  ({int(pct*100)}%)")

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
            container.write("  • _(vacío)_")
        container.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# =======================
# Cabecera
# =======================
# Theme toggle en la cabecera (visible en todos los dispositivos) - reduced spacing
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.markdown("""<h1 style="font-weight:700; background: linear-gradient(135deg, #60A5FA, #34D399); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-top: -1rem;">Calculadora ACB</h1>""", unsafe_allow_html=True)
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

    def handle_selection_change(ronda):
        """Handle immediate selection changes for player dropdowns"""
        key_sel = f"sel_{ronda}_{st.session_state.widget_counter}"
        if key_sel in st.session_state:
            selected_value = st.session_state[key_sel]
            new_selection = None if selected_value == "(vacío)" else selected_value
            st.session_state.seleccionados[ronda] = new_selection

    def render_ronda_widget(parent, ronda):
        cols = parent.columns([5, 1])
        key_sel = f"sel_{ronda}_{st.session_state.widget_counter}"
        key_del = f"del_{ronda}_{st.session_state.widget_counter}"
        with cols[0]:
            # Get the current selection from session state
            current_selection = st.session_state.seleccionados.get(ronda)
            idx = safe_index_of(current_selection, names)
            jugador = st.selectbox(
                f"{ronda}",
                options=["(vacío)"] + names,
                index=idx,
                key=key_sel,
                on_change=lambda ronda=ronda: handle_selection_change(ronda)
            )
            # Update selection immediately when changed
            new_selection = None if jugador == "(vacío)" else jugador
            if st.session_state.seleccionados[ronda] != new_selection:
                st.session_state.seleccionados[ronda] = new_selection
        with cols[1]:
            # Simple approach - use CSS to align button
            st.markdown('<div style="padding-top: 1.7rem;">', unsafe_allow_html=True)
            if st.button("❌", key=key_del):
                st.session_state.seleccionados[ronda] = None
                st.session_state.widget_counter += 1
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    for r in rondas[:4]:
        render_ronda_widget(right_col1, r)
    for r in rondas[4:]:
        render_ronda_widget(right_col2, r)














