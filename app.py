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
        # Si viene un número grande en euros -> directo
        try:
            v = float(val)
            if v > 10000:  # euros completos
                return int(round(v))
            else:
                # Si es un número pequeño, asumimos que está en millones
                return int(round(v * 1_000_000))
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
    # si la cifra es grande (>10000) tratamos como euros completos
    if euros > 10000:
        return int(round(euros))
    # si no, asumimos que está en millones y convertimos
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
else:
    bg_color = "#ffffff"
    text_color = "#000000"
    divider_color = "rgba(0,0,0,0.08)"
    progress_bg = "#e6f4ff"
    progress_border = "rgba(96,165,250,0.15)"

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

    def render_ronda_widget(parent, ronda):
        cols = parent.columns([5, 1])
        key_sel = f"sel_{ronda.replace(' ', '_')}"
        key_del = f"del_{ronda.replace(' ', '_')}"
        clear_key = f"clear_{ronda.replace(' ', '_')}"

        # Si hay una bandera de "clear" activa la usamos para fijar el valor antes de crear el widget
        if st.session_state.get(clear_key, False):
            st.session_state[key_sel] = "(vacío)"
            st.session_state[clear_key] = False
            st.session_state.seleccionados[ronda] = None

        if key_sel not in st.session_state:
            st.session_state[key_sel] = st.session_state.seleccionados.get(ronda) or "(vacío)"

        def _on_change(k=key_sel, r=ronda):
            val = st.session_state.get(k)
            st.session_state.seleccionados[r] = None if val == "(vacío)" else val

        with cols[0]:
            st.selectbox(
                f"{ronda}",
                options=["(vacío)"] + names,
                key=key_sel,
                on_change=_on_change
            )

        with cols[1]:
            st.markdown('<div style="padding-top: 1.7rem;">', unsafe_allow_html=True)
            if st.button("❌", key=key_del):
                st.session_state.seleccionados[ronda] = None
                st.session_state[clear_key] = True
                st.experimental_rerun()
            st.markdown('</div>', unsafe_allow_html=True)


    # Render de las 8 rondas (4 + 4)
    for r in rondas[:4]:
        render_ronda_widget(right_col1, r)
    for r in rondas[4:]:
        render_ronda_widget(right_col2, r)

    for r in rondas[:4]:
        render_ronda_widget(right_col1, r)
    for r in rondas[4:]:
        render_ronda_widget(right_col2, r)


