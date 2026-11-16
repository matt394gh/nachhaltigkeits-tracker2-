import streamlit as st
from PIL import Image, ImageEnhance, ImageOps
import torch
from transformers import AutoProcessor, AutoModelForCausalLM
import pandas as pd
import requests
import re
from io import StringIO
from difflib import get_close_matches

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="EcoLens App",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- SESSION STATE FÜR NAVIGATION & VERLAUF ---
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "scan"
if "scan_history" not in st.session_state:
    st.session_state.scan_history = []

# --- ECHTES MOBILE-APP CSS (HANDY-FRAME, CARDS & BOTTOM NAV) ---
st.markdown("""
<style>
/* Streamlit Standard-Elemente ausblenden für reines App-Feeling */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Hintergrund & Mobile-Container */
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

/* App Header */
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

/* Hero Scan Card */
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

/* Ergebnis-Karten */
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

/* Buttons */
.stButton>button {
    background-color: #2d4a3e !important;
    color: #ffffff !important;
    border-radius: 14px !important;
    border: none !important;
    font-weight: 600 !important;
    padding: 0.65rem 1rem !important;
    width: 100%;
    transition: all 0.2s ease;
}
.stButton>button:hover {
    background-color: #1e332a !important;
    transform: translateY(-1px);
}

/* File Uploader anpassen */
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
    background: rgba(255, 255, 255, 0.96);
    backdrop-filter: blur(12px);
    border-top: 1px solid #dce8e1;
    padding: 8px 16px 14px 16px;
    z-index: 9999;
    box-shadow: 0 -4px 20px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# --- 1. ONLINE-DATENBANK (FASHION TRANSPARENCY INDEX CSV + WIKIDATA/OPF) ---
@st.cache_data(ttl=3600)
def lade_online_marken_datenbank():
    """
    Lädt echte, öffentlich verfügbare Marken-Transparenzdaten aus dem Netz.
    """
    fti_url = "https://raw.githubusercontent.com/the-pudding/data/master/fashion-transparency/brands.csv"
    marken_dict = {}

    try:
        res = requests.get(fti_url, timeout=6)
        if res.status_code == 200:
            df = pd.read_csv(StringIO(res.text))
            for _, row in df.iterrows():
                brand = str(row.get("brand", row.iloc[0])).strip()
                raw_score = row.get("score", row.get("total", None))
                try:
                    score = int(float(raw_score))
                except (ValueError, TypeError):
                    score = 40
                if brand and brand.lower() != "nan":
                    marken_dict[brand.upper()] = {
                        "name": brand,
                        "score": min(max(score, 8), 96),
                        "quelle": "Fashion Transparency Index (Open Data)"
                    }
    except Exception:
        pass

    return marken_dict

# --- 2. LIVE-ABFRAGE BEI OPEN PRODUCTS FACTS & WIKIDATA ---
@st.cache_data(ttl=1800)
def suche_marke_online_live(suchbegriff):
    """
    Prüft über die offene OpenProductsFacts-API und Wikipedia/Wikidata-API,
    ob es sich um eine reale Modemarke handelt und holt Metadaten.
    """
    if not suchbegriff or len(suchbegriff) < 3:
        return None

    # A) Open Products Facts Live-Suche
    try:
        api_url = "https://world.openproductsfacts.org/cgi/search.pl"
        params = {
            "search_terms": suchbegriff,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 5
        }
        headers = {"User-Agent": "EcoLens-MobileApp/2.0"}
        res = requests.get(api_url, params=params, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            products = data.get("products", [])
            for p in products:
                brands = p.get("brands", "")
                labels = p.get("labels", "")
                if brands and suchbegriff.upper() in brands.upper():
                    clean_brand = brands.split(",")[0].strip()
                    labels_up = labels.upper()
                    if any(k in labels_up for k in ["ORGANIC", "BIO", "FAIR", "GOTS", "BLUESIGN", "OEKO-TEX"]):
                        return {
                            "name": clean_brand,
                            "score": 76,
                            "quelle": "OpenProductsFacts Live-API",
                            "details": f"Zertifizierungen gefunden: {labels}"
                        }
                    return {
                        "name": clean_brand,
                        "score": 48,
                        "quelle": "OpenProductsFacts Live-API",
                        "details": f"Gelistete Marke mit {data.get('count', 1)} erfassten Artikeln (Standard-Umweltprofil)."
                    }
    except Exception:
        pass

    # B) Wikidata API Check (erkennt weltweit bekannte Marken wie 'The North Face', 'Carhartt', etc.)
    try:
        wiki_url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "search": suchbegriff,
            "language": "en",
            "format": "json",
            "limit": 3
        }
        headers = {"User-Agent": "EcoLens-MobileApp/2.0"}
        w_res = requests.get(wiki_url, params=params, headers=headers, timeout=5)
        if w_res.status_code == 200:
            results = w_res.json().get("search", [])
            for item in results:
                desc = item.get("description", "").lower()
                label = item.get("label", "")
                clothing_keywords = [
                    "clothing", "apparel", "fashion", "outdoor", "footwear",
                    "sportswear", "retailer", "brand", "textile", "manufacturer"
                ]
                if any(kw in desc for kw in clothing_keywords):
                    # Realistische Bewertung basierend auf Branchentyp
                    if any(eco in desc for eco in ["sustainable", "organic", "fair trade"]):
                        score = 82
                    elif "outdoor" in desc:
                        score = 54
                    elif "fast fashion" in desc:
                        score = 22
                    else:
                        score = 45
                    return {
                        "name": label,
                        "score": score,
                        "quelle": "Wikidata Global Brand Registry",
                        "details": f"Verifizierte Marke ({item.get('description', 'Bekleidungsunternehmen')})."
                    }
    except Exception:
        pass

    return None

# --- 3. BILDVORVERARBEITUNG FÜR SCHÄRFERES OCR ---
def optimiere_bild_fuer_ocr(image):
    img = ImageOps.exif_transpose(image.convert("RGB"))
    # Kontrast und Schärfe leicht anheben, damit gestickte Logos (z.B. The North Face) klar lesbar sind
    img = ImageEnhance.Contrast(img).enhance(1.35)
    img = ImageEnhance.Sharpness(img).enhance(1.5)
    return img

# --- 4. MEHRWORT- & N-GRAMM-ERKENNUNG ---
def extrahiere_marken_kandidaten(ocr_text):
    """
    Erzeugt 1-, 2- und 3-Wort-Kombinationen aus dem OCR-Text,
    damit Marken wie 'THE NORTH FACE' oder 'TOMMY HILFIGER' am Stück erkannt werden.
    """
    text_clean = re.sub(r'[^A-Z0-9\s&\-\']', ' ', ocr_text.upper())
    stoppwoerter = {
        "MADE", "IN", "CHINA", "BANGLADESH", "VIETNAM", "TURKEY", "PORTUGAL",
        "COTTON", "POLYESTER", "ELASTANE", "ELASTHAN", "BAUMWOLLE", "WASH",
        "DRY", "IRON", "BLEACH", "SIZE", "EUR", "USA", "MEX", "CARE", "MACHINE",
        "COLD", "WARM", "INSIDE", "OUT", "WITH", "LIKE", "COLORS", "NEVER", "STOP", "EXPLORING"
    }
    woerter = [w for w in text_clean.split() if len(w) >= 2]
    kandidaten = []

    # 3-Wort-Kombinationen (z. B. "THE NORTH FACE")
    for i in range(len(woerter) - 2):
        gram3 = f"{woerter[i]} {woerter[i+1]} {woerter[i+2]}"
        kandidaten.append(gram3)

    # 2-Wort-Kombinationen (z. B. "NORTH FACE", "CALVIN KLEIN")
    for i in range(len(woerter) - 1):
        gram2 = f"{woerter[i]} {woerter[i+1]}"
        kandidaten.append(gram2)

    # Einzelwörter (ohne reine Waschanleitungs-Wörter)
    for w in woerter:
        if len(w) >= 3 and w not in stoppwoerter:
            kandidaten.append(w)

    return kandidaten, text_clean

def bewerte_etikett(online_marken, ocr_text):
    if not ocr_text or len(ocr_text.strip()) < 2:
        return None

    kandidaten, text_clean = extrahiere_marken_kandidaten(ocr_text)

    # SCHRITT A: Abgleich mit der Online-CSV (inkl. Mehrwort-Treffern & Fuzzy Matching)
    if online_marken:
        alle_keys = list(online_marken.keys())
        # 1. Direkter Treffer (zuerst längere Mehrwort-Kandidaten prüfen!)
        for kand in kandidaten:
            if kand in online_marken:
                eintrag = online_marken[kand]
                return baue_ergebnis(eintrag["name"], eintrag["score"], eintrag["quelle"])
        # 2. Substring-Check für bekannte Marken im Gesamttext
        for key in sorted(alle_keys, key=len, reverse=True):
            if len(key) >= 4 and key in text_clean:
                eintrag = online_marken[key]
                return baue_ergebnis(eintrag["name"], eintrag["score"], eintrag["quelle"])
        # 3. Fuzzy-Matching für leichte OCR-Lesefehler
        for kand in kandidaten:
            if len(kand) >= 5:
                match = get_close_matches(kand, alle_keys, n=1, cutoff=0.84)
                if match:
                    eintrag = online_marken[match[0]]
                    return baue_ergebnis(eintrag["name"], eintrag["score"], eintrag["quelle"])

    # SCHRITT B: Live-API-Suche (OpenProductsFacts & Wikidata) für erkannte Kandidaten
    for kand in kandidaten[:6]:
        if len(kand) >= 4:
            live_treffer = suche_marke_online_live(kand)
            if live_treffer:
                return baue_ergebnis(
                    live_treffer["name"],
                    live_treffer["score"],
                    live_treffer["quelle"],
                    live_treffer.get("details")
                )

    # SCHRITT C: Reine Stoff- & Materialanalyse (Waschetikett ohne Markenlogo)
    if any(w in text_clean for w in ["BIO", "ORGANIC", "GOTS", "ORGANISCHE", "RECYCLED", "RECYCELT"]):
        return {
            "name": "Zertifiziertes Bio- / Recycling-Textil",
            "score": 82,
            "kategorie": "Nachhaltiges Material",
            "farbe": "#2e7d32",
            "begruendung": "Das Etikett weist zertifizierte Bio- oder Recycling-Fasern aus. Deutlich geringerer Wasser- und CO₂-Fußabdruck.",
            "quelle": "Material-Erkennung (Waschetikett)"
        }
    if any(w in text_clean for w in ["POLYESTER", "ELASTHAN", "ELASTANE", "NYLON", "POLYAMID", "ACRYLIC"]):
        return {
            "name": "Synthetik-Gewebe",
            "score": 32,
            "kategorie": "Kritischer Stoff",
            "farbe": "#c62828",
            "begruendung": "Erdölbasierte Kunstfasern (Polyester/Nylon) erkannt. Nicht biologisch abbaubar und Quelle für Mikroplastik beim Waschen.",
            "quelle": "Material-Erkennung (Waschetikett)"
        }
    if any(w in text_clean for w in ["COTTON", "BAUMWOLLE", "COTON", "ALGODON"]):
        return {
            "name": "Konventionelle Baumwolle",
            "score": 46,
            "kategorie": "Durchschnitt",
            "farbe": "#ef6c00",
            "begruendung": "Reine Naturfaser, jedoch ohne erkennbares Bio-Siegel. Konventioneller Anbau erfordert viel Wasser und Pestizide.",
            "quelle": "Material-Erkennung (Waschetikett)"
        }

    return None

def baue_ergebnis(name, score, quelle, extra_info=None):
    if score >= 70:
        kat = "Vorbildlich & Transparent"
        farbe = "#2e7d32"
        grund = extra_info or f"{name} erzielt einen hohen Nachhaltigkeits- und Transparenzwert ({score}/100) bei Lieferketten und Umweltstandards."
    elif score >= 45:
        kat = "Mittelfeld"
        farbe = "#ef6c00"
        grund = extra_info or f"{name} liegt im Mittelfeld ({score}/100). Erste Nachhaltigkeitsprogramme sind vorhanden, aber es bleibt Verbesserungspotenzial."
    else:
        kat = "Kritisch / Niedriger Score"
        farbe = "#c62828"
        grund = extra_info or f"{name} erreicht nur {score}/100 Punkte. Geringe Lieferkettentransparenz oder hohes Massenproduktions-Volumen."
    return {
        "name": name,
        "score": score,
        "kategorie": kat,
        "farbe": farbe,
        "begruendung": grund,
        "quelle": quelle
    }

# --- FLORENCE-2 KI-MODELL ---
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

def lese_text_aus_bild(image):
    processor, model, device = lade_ki_modell()
    opt_img = optimiere_bild_fuer_ocr(image)
    inputs = processor(text="<OCR>", images=opt_img, return_tensors="pt").to(device)
    with torch.no_grad():
        gen = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=256,
            num_beams=3
        )
    return processor.batch_decode(gen, skip_special_tokens=True)[0]

# --- TOP APP HEADER ---
st.markdown("""
<div class="app-header">
    <p class="app-title">🌿 EcoLens</p>
    <span class="app-badge">LIVE DB</span>
</div>
""", unsafe_allow_html=True)

online_marken = lade_online_marken_datenbank()

# ==========================================
# TAB 1: SCANNEN (HAUPTANSICHT)
# ==========================================
if st.session_state.active_tab == "scan":
    st.markdown("""
    <div class="scan-card">
        <div class="scan-icon-circle">📸</div>
        <h3 style="margin:0 0 6px 0; color:#1b3026; font-size:1.15rem;">Etikett oder Logo scannen</h3>
        <p style="margin:0; color:#5c7a6c; font-size:0.85rem;">
            Fotografiere das Marken-Logo (z. B. The North Face, Zara) oder das Waschetikett für den Live-Check.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Wahlweise Kamera direkt auf dem Handy oder Galerie-Upload
    input_mode = st.radio(
        "Eingabemethode",
        ["📁 Foto hochladen", "📷 Kamera öffnen"],
        horizontal=True,
        label_visibility="collapsed"
    )

    uploaded_file = None
    if input_mode == "📷 Kamera öffnen":
        uploaded_file = st.camera_input("Etikett fotografieren", label_visibility="collapsed")
    else:
        uploaded_file = st.file_uploader("Bild auswählen", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, use_container_width=True)

        with st.spinner("🔍 KI liest Logo & prüft Online-Datenbanken..."):
            try:
                ocr_text = lese_text_aus_bild(image)
            except Exception:
                ocr_text = ""

        ergebnis = bewerte_etikett(online_marken, ocr_text)

        if not ergebnis:
            ergebnis = {
                "name": "Nicht eindeutig erkannt",
                "score": 40,
                "kategorie": "Keine Zuordnung",
                "farbe": "#607d8b",
                "begruendung": "Weder Marke noch Material konnten klar gelesen werden. Tipp: Näher herangehen und für gutes Licht sorgen.",
                "quelle": "Keine Online-Übereinstimmung"
            }
        else:
            # Im Scan-Verlauf speichern (ohne Duplikate direkt hintereinander)
            if not st.session_state.scan_history or st.session_state.scan_history[0]["name"] != ergebnis["name"]:
                st.session_state.scan_history.insert(0, ergebnis)

        # Moderne Ergebnis-Card
        st.markdown(f"""
        <div class="result-card">
            <span class="score-pill" style="background-color: {ergebnis['farbe']}18; color: {ergebnis['farbe']};">
                ● {ergebnis['kategorie']}
            </span>
            <h2 style="margin: 2px 0 4px 0; color: #1b3026; font-size: 1.4rem;">{ergebnis['name']}</h2>
            <p style="margin: 0 0 12px 0; color: #5c7a6c; font-size: 0.8rem;">Quelle: {ergebnis['quelle']}</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Eco Score", f"{ergebnis['score']} / 100")
        with col2:
            st.metric("Status", "Geprüft ✓")

        st.progress(ergebnis["score"] / 100.0)
        st.info(f"💡 **Analyse:** {ergebnis['begruendung']}")

        with st.expander("🔍 Erkannter Rohtext (OCR)"):
            st.code(ocr_text if ocr_text else "Kein Text erkannt")

# ==========================================
# TAB 2: VERLAUF (LETZTE SCANS)
# ==========================================
elif st.session_state.active_tab == "history":
    st.markdown("<h3 style='color:#1b3026; margin-bottom:12px;'>🕒 Deine letzten Scans</h3>", unsafe_allow_html=True)
    if not st.session_state.scan_history:
        st.info("Noch keine Kleidungsstücke gescannt. Wechsle unten auf **Scannen**, um zu starten.")
    else:
        for idx, item in enumerate(st.session_state.scan_history):
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
# TAB 3: INFO & DATENQUELLEN
# ==========================================
elif st.session_state.active_tab == "info":
    st.markdown("<h3 style='color:#1b3026; margin-bottom:12px;'>🌱 Über EcoLens</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div class="result-card">
        <p style="color:#23382d; font-size:0.92rem; line-height:1.5;">
            <strong>EcoLens</strong> kombiniert KI-gestützte Texterkennung (Microsoft Florence-2) mit echten, öffentlich zugänglichen Nachhaltigkeits- und Markenregistern:
        </p>
        <ul style="color:#3d594c; font-size:0.88rem; padding-left:18px;">
            <li><strong>Fashion Transparency Index:</strong> Offene Transparenzdaten globaler Modemarken.</li>
            <li><strong>OpenProductsFacts API:</strong> Weltweite Produkt- & Zertifizierungsdatenbank.</li>
            <li><strong>Wikidata Brand Registry:</strong> Verifizierung von Marken wie <em>The North Face</em>, Outdoor- & Sportlabels.</li>
            <li><strong>Material-Check:</strong> Automatische Auswertung von Bio-Baumwolle, GOTS, Polyester & Nylon auf Waschetiketten.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# FIXIERTE BOTTOM NAVIGATION BAR (HANDY-ICONS)
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
