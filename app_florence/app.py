import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
import easyocr
import torch

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="EcoLens - KI Etiketten-Scanner",
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

# --- 1. KI-MODELL LALDEN (EASYOCR CACHED) ---
@st.cache_resource
def lade_ocr_ki():
    # Lädt das neuronale OCR-Netzwerk für Deutsch und Englisch einmalig
    return easyocr.Reader(['en', 'de'], gpu=False)

# --- 2. AUTOMATISCHE KI-TEXTANALYSE DES ETIKETTS ---
def analysiere_ki_text(erkaennter_text):
    text_gesamt = " ".join(erkaennter_text).upper()

    if any(w in text_gesamt for w in ["BIO", "ORGANIC", "GOTS", "RECYCLED", "RECYCELT", "TENCEL", "LYOCELL", "HEMP", "HANF", "LINEN", "LEINEN"]):
        return {
            "name": "Bio- / Nachhaltiges Textil",
            "score": 88,
            "kategorie": "Vorbildlich & Nachhaltig",
            "farbe": "#2e7d32",
            "begruendung": f"Die KI hat auf dem Etikett nachhaltige Faser- oder Bio-Hinweise erkannt. Text-Snippets: '{text_gesamt[:60]}...'"
        }
    
    if any(w in text_gesamt for w in ["POLYESTER", "ELASTHAN", "ELASTANE", "NYLON", "POLYAMID", "ACRYLIC", "VISCOSE", "VISKOSE"]):
        return {
            "name": "Synthetik- / Kunstfaser",
            "score": 30,
            "kategorie": "Kritischer Stoff",
            "farbe": "#c62828",
            "begruendung": f"Die KI hat erdölbasierte Kunstfasern auf dem Waschetikett identifiziert. Text-Snippets: '{text_gesamt[:60]}...'"
        }

    if any(w in text_gesamt for w in ["COTTON", "BAUMWOLLE", "COTON", "ALGODON", "WOOL", "WOLLE"]):
        return {
            "name": "Konventionelle Baumwolle / Naturfaser",
            "score": 48,
            "kategorie": "Mittelfeld",
            "farbe": "#ef6c00",
            "begruendung": f"Die KI hat Naturfasern (wie Baumwolle/Wolle) ohne Biosiegel ausgelesen. Text-Snippets: '{text_gesamt[:60]}...'"
        }

    return {
        "name": "Standard Textil (KI-Analyse)",
        "score": 42,
        "kategorie": "Standard-Ware",
        "farbe": "#607d8b",
        "begruendung": f"Die KI hat das Etikett gescannt, aber keine spezifischen Öko-Zertifikate gefunden. Erkannter Text: '{text_gesamt[:50]}'"
    }

# --- TOP APP HEADER ---
st.markdown("""
<div class="app-header">
    <p class="app-title">🌿 EcoLens</p>
    <span class="app-badge">KI ETIKETTEN-SCANNER</span>
</div>
""", unsafe_allow_html=True)

# ==========================================
# TAB 1: KI-SCANNEN
# ==========================================
if st.session_state.active_tab == "scan":
    st.markdown("""
    <div class="scan-card">
        <div class="scan-icon-circle">📸</div>
        <h3 style="margin:0 0 6px 0; color:#1b3026; font-size:1.15rem;">Waschetikett mit KI scannen</h3>
        <p style="margin:0; color:#5c7a6c; font-size:0.85rem;">
            Lade ein Foto des Waschetiketts hoch. Die neuronale KI liest den Text automatisch aus und wertet ihn aus.
        </p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Etikett hochladen", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, use_container_width=True)

        with st.spinner("🤖 KI analysiert und liest das Etikett aus..."):
            try:
                # Bild für OCR optimieren (Kontrast & Schärfe erhöhen)
                img_cv = ImageOps.exif_transpose(image.convert("RGB"))
                img_cv = ImageEnhance.Contrast(img_cv).enhance(1.5)
                img_cv = ImageEnhance.Sharpness(img_cv).enhance(1.8)
                
                # Als temporäres Bild speichern für die OCR-KI
                img_path = "temp_etikett.jpg"
                img_cv.save(img_path)

                # EasyOCR ausführen
                reader = lade_ocr_ki()
                ergebnisse = reader.readtext(img_path, detail=0)
                
                # Text auswerten
                ergebnis = analysiere_ki_text(ergebnisse)

            except Exception as e:
                ergebnis = {
                    "name": "Analyse-Fehler",
                    "score": 40,
                    "kategorie": "Fehler bei KI-Auslese",
                    "farbe": "#c62828",
                    "begruendung": f"Die KI konnte das Bild nicht verarbeiten: {e}"
                }
                ergebnisse = []

        # In den Verlauf eintragen
        if not st.session_state.scan_history or st.session_state.scan_history[0]["name"] != ergebnis["name"]:
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
            st.metric("KI-Status", "Ausgelesen ✓")

        st.progress(ergebnis["score"] / 100.0)
        st.info(f"💡 **KI-Begründung:** {ergebnis['begruendung']}")

        with st.expander("🔍 Von der KI erkannte Roh-Wörter"):
            st.write(ergebnisse if ergebnisse else "Kein Text erkannt.")

# ==========================================
# TAB 2: VERLAUF
# ==========================================
elif st.session_state.active_tab == "history":
    st.markdown("<h3 style='color:#1b3026; margin-bottom:12px;'>🕒 KI-Scan Verlauf</h3>", unsafe_allow_html=True)
    if not st.session_state.scan_history:
        st.info("Noch keine Etiketten gescannt.")
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
    st.markdown("<h3 style='color:#1b3026; margin-bottom:12px;'>🌱 Über EcoLens KI</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div class="result-card">
        <p style="color:#23382d; font-size:0.92rem; line-height:1.5;">
            EcoLens nutzt ein neuronales OCR-Modell (Deep Learning / EasyOCR), um den Text auf Waschetiketten vollautomatisch zu erkennen und nach Nachhaltigkeitskriterien zu bewerten.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# FIXIERTE BOTTOM NAVIGATION BAR
# ==========================================
st.markdown('<div class="bottom-nav-container">', unsafe_allow_html=True)
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    if st.button("📸 Scannen", key="nav_scan"):
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
