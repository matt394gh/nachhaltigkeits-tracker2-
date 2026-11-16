import streamlit as st
from PIL import Image

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="EcoLens - Etiketten-Check",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- SESSION STATE FÜR NAVIGATION & VERLAUF ---
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "scan"
if "scan_history" not in st.session_state:
    st.session_state.scan_history = []

# --- ECHTES MOBILE-APP CSS (HANDY-FRAME & BOTTOM NAV) ---
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.stApp {
    background-color: #e6eee9;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
}

.block-container {
    max-width: 440px !important;
    padding-top: 1.2rem !important;
    padding-bottom: 6.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    background: linear-gradient(180deg, #f7faf8 0%, #edf4f0 100%);
    min-height: 100vh;
    box-shadow: 0 0 40px rgba(27, 48, 38, 0.08);
}

.app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.4rem 0.2rem 1rem 0.2rem;
    border-bottom: 1px solid #dce8e1;
    margin-bottom: 1.2rem;
}
.app-title {
    font-size: 1.45rem;
    font-weight: 800;
    color: #1b3026;
    letter-spacing: -0.5px;
    margin: 0;
}
.app-badge {
    background-color: #d8ebe1;
    color: #2d4a3e;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 20px;
}

.scan-card {
    background: #ffffff;
    border-radius: 24px;
    padding: 24px 18px;
    text-align: center;
    box-shadow: 0 8px 24px rgba(45, 74, 62, 0.07);
    border: 1px solid #e1ede6;
    margin-bottom: 1rem;
}
.scan-icon-circle {
    width: 64px;
    height: 64px;
    background: #edf5f0;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 12px auto;
    font-size: 28px;
}

.result-card {
    background: #ffffff;
    border-radius: 22px;
    padding: 20px;
    box-shadow: 0 8px 25px rgba(27, 48, 38, 0.08);
    border: 1px solid #dfece5;
    margin-top: 12px;
}
.score-pill {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 12px;
    font-weight: 700;
    font-size: 0.82rem;
    margin-bottom: 8px;
}

.stButton>button {
    background-color: #2d4a3e !important;
    color: #ffffff !important;
    border-radius: 14px !important;
    border: none !important;
    font-weight: 600 !important;
    padding: 0.65rem 1rem !important;
    width: 100%;
}
.stButton>button:hover {
    background-color: #1e332a !important;
}

[data-testid="stFileUploader"] {
    background-color: #ffffff;
    border-radius: 18px;
    padding: 10px;
    border: 1.5px dashed #a7c7b7;
}

.bottom-nav-container {
    position: fixed;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
    max-width: 440px;
    background: rgba(255, 255, 255, 0.96);
    backdrop-filter: blur(12px);
    border-top: 1px solid #dce8e1;
    padding: 8px 16px 14px 16px;
    z-index: 9999;
    box-shadow: 0 -4px 20px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# --- DATENBANK FÜR DIE MATERIALIEN ---
MATERIAL_DATEN = {
    "🌿 Bio-Baumwolle / GOTS": {
        "score": 88,
        "kategorie": "Vorbildlich & Nachhaltig",
        "farbe": "#2e7d32",
        "begruendung": "Zertifizierte Bio-Naturfaser. Ohne synthetische Pestizide angebaut, schützt Grundwasser und Ökosysteme."
    },
    "♻️ Recyceltes Polyester / Nylon": {
        "score": 75,
        "kategorie": "Gutes Recycling-Material",
        "farbe": "#388e3c",
        "begruendung": "Hergestellt aus recycelten Plastikflaschen oder Alttextilien. Reduziert den Erdölbedarf erheblich."
    },
    "🌱 Leinen / Hanf / Tencel": {
        "score": 90,
        "kategorie": "Hervorragende Öko-Bilanz",
        "farbe": "#1b5e20",
        "begruendung": "Sehr nachhaltige Naturfasern, die extrem wenig Wasser im Anbau benötigen und biologisch abbaubar sind."
    },
    "☁️ Konventionelle Baumwolle": {
        "score": 48,
        "kategorie": "Mittelfeld (Konventionell)",
        "farbe": "#ef6c00",
        "begruendung": "Reine Naturfaser und biologisch abbaubar, aber im konventionellen Anbau mit hohem Wasser- und Pestizideinsatz belastet."
    },
    "🧪 Polyester / Viskose / Elastan": {
        "score": 30,
        "kategorie": "Kritischer Stoff",
        "farbe": "#c62828",
        "begruendung": "Erdölbasierte Kunstfaser. Verursacht beim Waschen Mikroplastik im Wasser und ist extrem langlebig in der Natur."
    }
}

# --- TOP APP HEADER ---
st.markdown("""
<div class="app-header">
    <p class="app-title">🌿 EcoLens</p>
    <span class="app-badge">ETIKETTEN-CHECK</span>
</div>
""", unsafe_allow_html=True)

# ==========================================
# TAB 1: SCANNEN & AUSWÄHLEN
# ==========================================
if st.session_state.active_tab == "scan":
    st.markdown("""
    <div class="scan-card">
        <div class="scan-icon-circle">🏷️</div>
        <h3 style="margin:0 0 6px 0; color:#1b3026; font-size:1.15rem;">Waschetikett analysieren</h3>
        <p style="margin:0; color:#5c7a6c; font-size:0.85rem;">
            Foto hochladen und Material vom Waschetikett auswählen für eine sofortige, präzise Bewertung.
        </p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Etikett-Foto hochladen", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, use_container_width=True)

    st.markdown("<p style='font-size:0.88rem; color:#1b3026; font-weight:700; margin-top:10px;'>👉 Was steht auf dem Waschetikett?</p>", unsafe_allow_html=True)
    
    ausgewaehltes_material = st.selectbox(
        "Material wählen",
        list(MATERIAL_DATEN.keys()),
        label_visibility="collapsed"
    )

    if st.button("🔍 Etikett auswerten"):
        info = MATERIAL_DATEN[ausgewaehltes_material]
        ergebnis = {
            "name": ausgewaehltes_material,
            "score": info["score"],
            "kategorie": info["kategorie"],
            "farbe": info["farbe"],
            "begruendung": info["begruendung"]
        }

        # In den Verlauf eintragen
        st.session_state.scan_history.insert(0, ergebnis)

        st.markdown(f"""
        <div class="result-card">
            <span class="score-pill" style="background-color: {ergebnis['farbe']}18; color: {ergebnis['farbe']};">
                ● {ergebnis['kategorie']}
            </span>
            <h2 style="margin: 2px 0 4px 0; color: #1b3026; font-size: 1.25rem;">{ergebnis['name']}</h2>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Eco Score", f"{ergebnis['score']} / 100")
        with col2:
            st.metric("Status", "Erfolgreich ✓")

        st.progress(ergebnis["score"] / 100.0)
        st.info(f"💡 **Auswertung:** {ergebnis['begruendung']}")

# ==========================================
# TAB 2: VERLAUF
# ==========================================
elif st.session_state.active_tab == "history":
    st.markdown("<h3 style='color:#1b3026; margin-bottom:12px;'>🕒 Analysierte Etiketten</h3>", unsafe_allow_html=True)
    if not st.session_state.scan_history:
        st.info("Noch keine Etiketten analysiert.")
    else:
        for item in st.session_state.scan_history:
            st.markdown(f"""
            <div class="result-card" style="padding: 14px 18px; margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <strong style="color:#1b3026; font-size:1.05rem;">{item['name']}</strong><br>
                        <span style="color:#5c7a6c; font-size:0.8rem;">{item['kategorie']}</span>
                    </div>
                    <div style="font-size:1.2rem; font-weight:800; color:{item['farbe']};">
                        {item['score']}/100
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        if st.button("🗑️ Verlauf löschen"):
            st.session_state.scan_history = []
            st.rerun()

# ==========================================
# TAB 3: INFO
# ==========================================
elif st.session_state.active_tab == "info":
    st.markdown("<h3 style='color:#1b3026; margin-bottom:12px;'>🌱 Über EcoLens</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div class="result-card">
        <p style="color:#23382d; font-size:0.92rem; line-height:1.5;">
            EcoLens liefert dir im minimalistischen Handy-Design sofortige Nachhaltigkeitsanalysen für Textilien basierend auf dem Waschetikett.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# FIXIERTE BOTTOM NAVIGATION BAR
# ==========================================
st.markdown('<div class="bottom-nav-container">', unsafe_allow_html=True)
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    if st.button("🏷️ Scannen", key="nav_scan"):
        st.session_state.active_tab = "scan"
        st.rerun()
with nav_col2:
    if st.button("🕒 Verlauf", key="nav_hist"):
        st.session_state.active_tab = "history"
        st.rerun()
with nav_col3:
    if st.button("ℹ️ Info", key="nav_info"):
        st.session_state.active_tab = "info"
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)
