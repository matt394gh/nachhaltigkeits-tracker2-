import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import torch
from transformers import AutoProcessor, AutoModelForCausalLM
import re

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="EcoLens - Etiketten-Analyse",
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

# --- PRÄZISE WASCHETIKETTEN-ANALYSE ---
def analysiere_textmaterial(text):
    if not text:
        return None
    t_up = text.upper()

    # 1. Bio- & Recycling-Materialien (Top-Score)
    if any(w in t_up for w in ["BIO", "ORGANIC", "GOTS", "RECYCLED", "RECYCELT", "TENCEL", "LYOCELL", "HEMP", "HANF", "LINEN", "LEINEN"]):
        return {
            "name": "Nachhaltiges Bio- / Naturfaser-Textil",
            "score": 85,
            "kategorie": "Vorbildlich & Nachhaltig",
            "farbe": "#2e7d32",
            "begruendung": "Das Waschetikett weist zertifizierte Bio-Fasern, Recycling-Materialien oder nachhaltige Naturfasern (wie Leinen/Tencel) aus. Sehr geringer ökologischer Fußabdruck."
        }

    # 2. Reine Naturfasern (Standard Baumwolle / Wolle)
    if any(w in t_up for w in ["COTTON", "BAUMWOLLE", "COTON", "ALGODON", "WOOL", "WOLLE", "MERINO", "SEIDE", "SILK"]):
        return {
            "name": "Naturfaser (Konventionell)",
            "score": 50,
            "kategorie": "Mittelfeld",
            "farbe": "#ef6c00",
            "begruendung": "Reine Naturfaser (z.B. Baumwolle oder Wolle). Angenehm auf der Haut, aber im konventionellen Anbau oft mit hohem Wasser- und Pestizideinsatz verbunden."
        }

    # 3. Synthetik- & Kunstfasern (Kritisch wegen Mikroplastik)
    if any(w in t_up for w in ["POLYESTER", "ELASTHAN", "ELASTANE", "NYLON", "POLYAMID", "ACRYLIC", "AKRYL", "VISCOSE", "VISKOSE"]):
        return {
            "name": "Synthetik- / Kunstfaser-Mix",
            "score": 32,
            "kategorie": "Kritischer Stoff",
            "farbe": "#c62828",
            "begruendung": "Das Etikett zeigt erdölbasierte Kunstfasern oder energieintensiv verarbeitete Viskose. Diese Materialien sind langlebig, geben beim Waschen jedoch Mikroplastik an die Umwelt ab."
        }

    return None

# --- FLORENCE-2 KI-MODELL (MIT KONTRAST-OPTIMIERUNG) ---
@st.cache_resource
def lade_ki_modell():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        "microsoft/Florence-2-base",
        torch_dtype=torch.float32,
        trust_remote_code=True
    ).to(device)
    return processor, model, device

def lese_etikett_bild(image):
    try:
        processor, model, device = lade_ki_modell()
        # Bild für OCR schärfen
        img = ImageOps.exif_transpose(image.convert("RGB"))
        img = ImageEnhance.Contrast(img).enhance(1.4)
        img = ImageEnhance.Sharpness(img).enhance(1.6)

        inputs = processor(text="<OCR>", images=img, return_tensors="pt").to(device)
        with torch.no_grad():
            gen = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=256,
                num_beams=3
            )
        return processor.batch_decode(gen, skip_special_tokens=True)[0]
    except Exception:
        return ""

# --- TOP APP HEADER ---
st.markdown("""
<div class="app-header">
    <p class="app-title">🌿 EcoLens</p>
    <span class="app-badge">ETIKETTEN-CHECK</span>
</div>
""", unsafe_allow_html=True)

# ==========================================
# TAB 1: SCANNEN (WASCHETIKETTEN-ANALYSE)
# ==========================================
if st.session_state.active_tab == "scan":
    st.markdown("""
    <div class="scan-card">
        <div class="scan-icon-circle">🏷️</div>
        <h3 style="margin:0 0 6px 0; color:#1b3026; font-size:1.15rem;">Waschetikett analysieren</h3>
        <p style="margin:0; color:#5c7a6c; font-size:0.85rem;">
            Fotografiere das kleine weiße Waschetikett in der Kleidung (Materialzusammensetzung).
        </p>
    </div>
    """, unsafe_allow_html=True)

    input_mode = st.radio(
        "Modus",
        ["📁 Foto hochladen", "📷 Kamera öffnen", "⌨️ Text manuell eingeben"],
        horizontal=True,
        label_visibility="collapsed"
    )

    ocr_text = ""
    uploaded_file = None

    if input_mode == "📷 Kamera öffnen":
        uploaded_file = st.camera_input("Etikett fotografieren", label_visibility="collapsed")
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
            with st.spinner("Lese Etikett aus..."):
                ocr_text = lese_etikett_bild(image)

    elif input_mode == "📁 Foto hochladen":
        uploaded_file = st.file_uploader("Bild auswählen", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, use_container_width=True)
            with st.spinner("Lese Etikett aus..."):
                ocr_text = lese_etikett_bild(image)

    else:
        st.markdown("<p style='font-size:0.85rem; color:#2d4a3e; font-weight:600; margin-bottom:4px;'>Material vom Etikett eintippen:</p>", unsafe_allow_html=True)
        ocr_text = st.text_input("z.B. 100% Cotton, 80% Polyester, Bio Baumwolle", placeholder="Hier tippen...", label_visibility="collapsed")

    if ocr_text:
        ergebnis = analysiere_textmaterial(ocr_text)

        if not ergebnis:
            ergebnis = {
                "name": "Unbekannte Materialmischung",
                "score": 40,
                "kategorie": "Standard Textil",
                "farbe": "#607d8b",
                "begruendung": f"Ausgelesener Text: '{ocr_text}'. Es konnte kein eindeutiges Hauptmaterial (wie Baumwolle oder Polyester) zugeordnet werden."
            }

        # Im Verlauf speichern
        if not st.session_state.scan_history or st.session_state.scan_history[0]["name"] != ergebnis["name"]:
            st.session_state.scan_history.insert(0, ergebnis)

        st.markdown(f"""
        <div class="result-card">
            <span class="score-pill" style="background-color: {ergebnis['farbe']}18; color: {ergebnis['farbe']};">
                ● {ergebnis['kategorie']}
            </span>
            <h2 style="margin: 2px 0 4px 0; color: #1b3026; font-size: 1.35rem;">{ergebnis['name']}</h2>
            <p style="margin: 0; color: #5c7a6c; font-size: 0.8rem;">Gelesener Etikett-Text: <i>"{ocr_text[:60]}"</i></p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Eco Score", f"{ergebnis['score']} / 100")
        with col2:
            st.metric("Status", "Analysiert ✓")

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
    st.markdown("<h3 style='color:#1b3026; margin-bottom:12px;'>🌱 Über EcoLens Etikett-Check</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div class="result-card">
        <p style="color:#23382d; font-size:0.92rem; line-height:1.5;">
            Da Waschetiketten oft klein oder schwer lesbar sind, bietet dir dieser Modus eine zuverlässige Material-Auswertung. 
        </p>
        <p style="color:#23382d; font-size:0.92rem; line-height:1.5;">
            Falls die automatische Texterkennung bei einem Foto einmal unscharf ist, kannst du den Text im Eingabefeld ganz einfach selbst eintragen und blitzschnell auswerten lassen!
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
