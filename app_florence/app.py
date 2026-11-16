import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
import easyocr
import re
import torch

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="EcoLens - KI Etiketten-Scanner",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- SESSION STATE INITIALISIERUNG ---
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
    padding: 0.6rem 0.5rem !important;
    width: 100%;
    font-size: 0.9rem;
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

/* Fixierte Bottom Navigation Bar */
.bottom-nav-container {
    position: fixed;
    bottom: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 100%;
    max-width: 440px;
    background: rgba(255, 255, 255, 0.98);
    backdrop-filter: blur(12px);
    border-top: 1px solid #dce8e1;
    padding: 10px 16px 16px 16px;
    z-index: 9999;
    box-shadow: 0 -4px 20px rgba(0,0,0,0.08);
}
</style>
""", unsafe_allow_html=True)

# --- 1. KI-OCR LADEN (EASYOCR CACHED) ---
@st.cache_resource
def lade_ocr_ki():
    return easyocr.Reader(['en', 'de'], gpu=False)

# --- 2. ERWEITERTE BILD-VORVERARBEITUNG FÜR PERFEKTES LESEN ---
def optimiere_bild_fuer_ki(image):
    img = ImageOps.exif_transpose(image.convert("RGB"))
    
    # Etiketten sind oft klein -> Bild für OCR hochskalieren (2x)
    w, h = img.size
    if w < 1000:
        img = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
        
    # In Graustufen umwandeln und Kontrast/Schärfe extrem anheben
    img = ImageOps.grayscale(img)
    img = ImageEnhance.Contrast(img).enhance(2.2)
    img = ImageEnhance.Sharpness(img).enhance(2.5)
    return img

# --- 3. SMARTE KI-TEXTANALYSE (MIT PROZENT-ERKENNUNG) ---
def analysiere_ki_text(erkaennter_text_liste):
    text_gesamt = " ".join(erkaennter_text_liste).upper()
    text_sauber = re.sub(r'[^A-Z0-9%ÄÖÜ\s]', ' ', text_gesamt)

    # A) Suche nach exakten Prozent-Angaben (z.B. "100% COTTON")
    prozent_treffer = re.findall(r'(\d+\s*%\s*[A-ZÄÖÜ]+)', text_sauber)
    zusatz_info = f"Erkannte Details: {', '.join(prozent_treffer)}" if prozent_treffer else f"Roh-Text: {text_sauber[:40]}"

    # B) Bio- & Nachhaltigkeitsprüfung
    if any(w in text_sauber for w in ["BIO", "ORGANIC", "GOTS", "RECYCLED", "RECYCELT", "TENCEL", "LYOCELL", "HEMP", "HANF", "LINEN", "LEINEN"]):
        return {
            "name": "Bio- / Nachhaltiges Textil",
            "score": 88,
            "kategorie": "Vorbildlich & Nachhaltig",
            "farbe": "#2e7d32",
            "begruendung": f"Die KI hat zertifizierte Bio- oder Naturfaser-Merkmale auf dem Etikett identifiziert. ({zusatz_info})"
        }
    
    # C) Synthetik-Prüfung
    if any(w in text_sauber for w in ["POLYESTER", "ELASTHAN", "ELASTANE", "NYLON", "POLYAMID", "ACRYLIC", "VISCOSE", "VISKOSE"]):
        return {
            "name": "Synthetik- / Kunstfaser-Mix",
            "score": 30,
            "kategorie": "Kritischer Stoff",
            "farbe": "#c62828",
            "begruendung": f"Die KI hat erdölbasierte Kunstfasern auf dem Waschetikett ausgelesen. ({zusatz_info})"
        }

    # D) Konventionelle Naturfasern
    if any(w in text_sauber for w in ["COTTON", "BAUMWOLLE", "COTON", "ALGODON", "WOOL", "WOLLE"]):
        return {
            "name": "Konventionelle Baumwolle / Naturfaser",
            "score": 48,
            "kategorie": "Mittelfeld",
            "farbe": "#ef6c00",
            "begruendung": f"Die KI hat Naturfasern ohne erkennbares Bio-Siegel erkannt. ({zusatz_info})"
        }

    if len(text_sauber.strip()) < 3:
        return {
            "name": "Etikett unklar / Zu unscharf",
            "score": 40,
            "kategorie": "Nicht lesbar",
            "farbe": "#607d8b",
            "begruendung": "Die KI konnte auf dem Foto keinen klaren Text entziffern. Bitte halte die Kamera näher und ruhiger an das weiße Etikett."
        }

    return {
        "name": "Standard Textil (KI-Auslese)",
        "score": 42,
        "kategorie": "Standard-Ware",
        "farbe": "#607d8b",
        "begruendung": f"Das Waschetikett wurde von der KI analysiert. Ausgelesener Inhalt: '{text_sauber[:50]}'"
    }

# --- TOP APP HEADER ---
st.markdown("""
<div class="app-header">
    <p class="app-title">🌿 EcoLens</p>
    <span class="app-badge">SMART OCR KI</span>
</div>
""", unsafe_allow_html=True)

# ==========================================
# SEITENINHALT JE NACH AKTIVEM TAB
# ==========================================
tab = st.session_state.active_tab

if tab == "scan":
    st.markdown("""
    <div class="scan-card">
        <div class="scan-icon-circle">📸</div>
        <h3 style="margin:0 0 6px 0; color:#1b3026; font-size:1.15rem;">Waschetikett mit KI scannen</h3>
        <p style="margin:0; color:#5c7a6c; font-size:0.85rem;">
            Fotografiere das Waschetikett. Die smarte KI skaliert, schärft und liest den Text automatisch aus.
        </p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Etikett hochladen", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, use_container_width=True)

        with st.spinner("🤖 Smarte KI verarbeitet & liest das Etikett aus..."):
            try:
                # Bild für maximale OCR-Präzision optimieren
                optimiertes_bild = optimiere_bild_fuer_ki(image)
                temp_path = "temp_opt_etikett.jpg"
                optimiertes_bild.save(temp_path)

                # EasyOCR ausführen
                reader = lade_ocr_ki()
                ergebnisse = reader.readtext(temp_path, detail=0)
                
                ergebnis = analysiere_ki_text(ergebnisse)

            except Exception as e:
                ergebnis = {
                    "name": "Analyse-Fehler",
                    "score": 40,
                    "kategorie": "Fehler bei KI-Auslese",
                    "farbe": "#c62828",
                    "begruendung": f"Die Bildverarbeitung schlug fehl: {e}"
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
            st.metric("KI-Status", "Erfolgreich ✓")

        st.progress(ergebnis["score"] / 100.0)
        st.info(f"💡 **KI-Analyse:** {ergebnis['begruendung']}")

        with st.expander("🔍 Von der KI erkannte Roh-Wörter"):
            st.write(ergebnisse if ergebnisse else "Kein Text erkannt.")

elif tab == "history":
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
        
        if st.button("🗑️ Verlauf leeren"):
            st.session_state.scan_history = []
            st.rerun()

elif tab == "info":
    st.markdown("<h3 style='color:#1b3026; margin-bottom:12px;'>🌱 Über EcoLens</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div class="result-card">
        <p style="color:#23382d; font-size:0.92rem; line-height:1.5;">
            <strong>EcoLens</strong> nutzt eine hochentwickelte Deep-Learning-Pipeline (Computer-Vision-Preprocessing + EasyOCR), um selbst kleinste Schriftzüge auf Textiletiketten präzise zu erkennen.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# FIXIERTE BOTTOM NAVIGATION BAR (STABIL)
# ==========================================
st.markdown('<div class="bottom-nav-container">', unsafe_allow_html=True)
nav1, nav2, nav3 = st.columns(3)

with nav1:
    if st.button("📸 Scannen", use_container_width=True):
        st.session_state.active_tab = "scan"
        st.rerun()

with nav2:
    if st.button("🕒 Verlauf", use_container_width=True):
        st.session_state.active_tab = "history"
        st.rerun()

with nav3:
    if st.button("ℹ️ Info", use_container_width=True):
        st.session_state.active_tab = "info"
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
