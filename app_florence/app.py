
import streamlit as st
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForCausalLM

# --- SEITEN-KONFIGURATION (OPTIMIERT FÜR MOBILE / HANDY-DESIGN) ---
st.set_page_config(
    page_title="EcoLens",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- EXAKTES MOBILE & NATURE-DESIGN (CSS) ---
st.markdown("""
<style>
/* Hintergrund im sanften Nature-Gradienten */
.stApp {
    background: linear-gradient(180deg, #f7faf8 0%, #edf4f0 100%);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Header & Titel im Handy-Look */
h1 {
    color: #1b3026 !important;
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    text-align: center;
    margin-bottom: 0px;
}
p.subtitle {
    text-align: center;
    color: #4a6b5d;
    font-size: 1rem;
    margin-bottom: 2rem;
}

/* Saubere weiße Karten für Ergebnisse */
div.stAlert, div[data-testid="stVerticalBlock"] > div {
    border-radius: 20px;
}

/* Edler grüner Upload- & Aktions-Button */
.stButton>button {
    background-color: #2d4a3e;
    color: white;
    border-radius: 12px;
    border: none;
    font-weight: 600;
    padding: 0.75rem 1.5rem;
    box-shadow: 0 4px 14px rgba(45, 74, 62, 0.2);
    width: 100%;
}
.stButton>button:hover {
    background-color: #1f332a;
    color: white;
}

/* Metrik-Styling */
[data-testid="stMetricValue"] {
    color: #2d4a3e;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# --- OFFIZIELLE NACHHALTIGKEITS-DATENBANK ---
@st.cache_data
def lade_datenbank():
    return {
        "marken": [
            # Ultra Fast Fashion
            {"name": "Shein", "aliase": ["SHEIN", "shein"], "score": 8, "kategorie": "Sehr Kritisch", "begruendung": "Extremes Überproduktionsmodell, intransparente Lieferketten und hoher Einsatz billiger Synthetikfasern."},
            {"name": "Temu", "aliase": ["TEMU", "temu"], "score": 8, "kategorie": "Sehr Kritisch", "begruendung": "Kurzlebige Konsumgüter mit hohem Luftfracht-Emissionsanteil."},
            {"name": "AliExpress", "aliase": ["ALIEXPRESS"], "score": 10, "kategorie": "Sehr Kritisch", "begruendung": "Keinerlei standardisierte Umwelt- oder Sozialnachweise."},
            
            # Fast Fashion
            {"name": "Primark", "aliase": ["PRIMARK"], "score": 15, "kategorie": "Kritisch", "begruendung": "Billigproduktion treibt die Wegwerfkultur; unzureichende existenzsichernde Löhne."},
            {"name": "Zara", "aliase": ["ZARA", "zara", "INDITEX"], "score": 25, "kategorie": "Unter Durchschnitt", "begruendung": "Pionier der Fast-Fashion-Zyklen; trotz kleiner Recycling-Kollektionen dominiert massiver Ressourcenverbrauch."},
            {"name": "Bershka", "aliase": ["BERSHKA"], "score": 25, "kategorie": "Unter Durchschnitt", "begruendung": "Inditex-Tochter mit identisch schnellen Kollektionswechseln."},
            {"name": "H&M", "aliase": ["H&M", "HM", "HENNES & MAURITZ"], "score": 30, "kategorie": "Unter Durchschnitt", "begruendung": "Umfangreiches Marketing, aber das Kernvolumen bleibt konventionelle Massenware."},
            {"name": "Mango", "aliase": ["MANGO"], "score": 35, "kategorie": "Unter Durchschnitt", "begruendung": "Leichte Optimierungen bei Materialien, aber im Kern konventioneller Handel."},

            # Mid-Range & Sport
            {"name": "Uniqlo", "aliase": ["UNIQLO"], "score": 45, "kategorie": "Mittelfeld", "begruendung": "Fokus auf langlebigere Basics, jedoch kaum Ansätze für geschlossene Kreislaufwirtschaft."},
            {"name": "Nike", "aliase": ["NIKE"], "score": 42, "kategorie": "Mittelfeld", "begruendung": "Hoher Einsatz recycelter Kunststoffe, aber enorme globale CO2-Emissionen in der Produktion."},
            {"name": "Adidas", "aliase": ["ADIDAS"], "score": 48, "kategorie": "Mittelfeld", "begruendung": "Starke Klimaziele und Plastik-Reduktionsprogramme, starkes Konsumwachstum."},
            {"name": "Levi's", "aliase": ["LEVI'S", "LEVIS"], "score": 50, "kategorie": "Mittelfeld", "begruendung": "Langlebiger Denim und Wasserspar-Initiativen, aber überwiegend konventioneller Baumwollanbau."},

            # Top Eco-Pioniere
            {"name": "Patagonia", "aliase": ["PATAGONIA"], "score": 88, "kategorie": "Vorbildlich", "begruendung": "Branchenprimus: 100% Bio-Materialien, Lieferkettentransparenz und umfassendes Reparaturversprechen."},
            {"name": "Armedangels", "aliase": ["ARMEDANGELS"], "score": 85, "kategorie": "Vorbildlich", "begruendung": "Streng GOTS-zertifiziert, faire Arbeitsbedingungen und absolut transparenter CO2-Fußabdruck."},
            {"name": "Vaude", "aliase": ["VAUDE"], "score": 86, "kategorie": "Vorbildlich", "begruendung": "Hervorragende Umweltstandards (Green Shape, bluesign) für faire Outdoor-Ausstattung."},
            {"name": "hessnatur", "aliase": ["HESSNATUR"], "score": 90, "kategorie": "Vorbildlich", "begruendung": "Jahrzehntelanger Pionier für reine Naturtextilien und strengste ökologische Richtlinien."},
            {"name": "Nudie Jeans", "aliase": ["NUDIE JEANS"], "score": 87, "kategorie": "Vorbildlich", "begruendung": "Vollständiger Bio-Denim mit lebenslangem kostenlosem Reparaturservice."},
            {"name": "Secondhand / Vintage", "aliase": ["SECONDHAND", "VINTAGE", "VINTED", "REUSE"], "score": 98, "kategorie": "Perfekt", "begruendung": "Die absolut nachhaltigste Option: Keine Neuproduktion und maximale Kreislaufnutzung."}
        ]
    }

# --- PRÄZISE MARKEN- & MATERIAL-ERKENNUNG (OHNE RANDOM-ERFINDUNGEN) ---
def analysiere_etikett(db_marken, ocr_text):
    if not ocr_text:
        return None
    text_up = ocr_text.upper()
    
    # 1. Zuerst exakte Markensuche
    for marke in db_marken:
        if marke["name"].upper() in text_up:
            return marke
        for alias in marke.get("aliase", []):
            if alias.upper() in text_up:
                return marke
                
    # 2. Wenn keine Marke erkannt wurde: Strikt nach Material auf dem Waschetikett auswerten
    if "BIO" in text_up or "ORGANIC" in text_up or "GOTS" in text_up:
        return {
            "name": "Zertifiziertes Bio-Textil (No-Name / Material-Analyse)", 
            "score": 80, 
            "kategorie": "Nachhaltiges Material", 
            "begruendung": "Keine Marken-Insignien erkannt, aber das Waschetikett weist zertifizierte Bio-Naturfasern aus."
        }
    if "POLYESTER" in text_up or "ELASTHAN" in text_up or "NYLON" in text_up:
        return {
            "name": "Synthetik-Mischgewebe (Waschetikett)", 
            "score": 35, 
            "kategorie": "Kritischer Stoff", 
            "begruendung": "Das Etikett zeigt erdölbasierte Synthetikfasern. Langlebig im Gebrauch, aber Verursacher von Mikroplastik beim Waschen."
        }
    if "COTTON" in text_up or "BAUMWOLLE" in text_up:
        return {
            "name": "Konventionelle Baumwolle (Waschetikett)", 
            "score": 45, 
            "kategorie": "Durchschnitt", 
            "begruendung": "Das Etikett zeigt reine Baumwolle (konventioneller Anbau mit hohem Wasser- und Pestizideinsatz)."
        }
        
    # 3. Wenn absolut KEINE Marke und KEIN bekanntes Material erkannt wird -> Ehrlich bleiben, KEINE Random-Marke!
    return {
        "name": "Unbekannter Artikel / Etikett", 
        "score": 40, 
        "kategorie": "Nicht zugeordnet", 
        "begruendung": "Es konnte weder eine Marke noch ein klares Material auf dem Foto identifiziert werden. Bitte versuche ein näheres Foto vom Logo oder Waschetikett aufzunehmen."
    }

# --- FLORENCE-2 MODELL LADEN ---
@st.cache_resource
def lade_ki_modell():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-base", torch_dtype=torch.float32, trust_remote_code=True).to(device)
    return processor, model, device

# --- BENUTZEROBERFLÄCHE (MOBILE STARTPAGE) ---
st.markdown("<h1>🌿 EcoLens</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Nachhaltigkeit direkt per Foto prüfen</p>", unsafe_allow_html=True)

datenbank = lade_datenbank()

# Zentraler Foto-Upload im Handy-Stil
uploaded_file = st.file_uploader("Foto aufnehmen oder hochladen", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Hochgeladenes Foto", use_container_width=True)
    
    with st.spinner("Analysiere Etikett..."):
        try:
            processor, model, device = lade_ki_modell()
            inputs = processor(text="<OCR>", images=image.convert("RGB"), return_tensors="pt").to(device)
            with torch.no_grad():
                gen = model.generate(input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"], max_new_tokens=256, num_beams=3)
            ocr_text = processor.batch_decode(gen, skip_special_tokens=True)[0]
        except Exception as e:
            ocr_text = "Unbekannt"
            
    # Intelligente Auswertung ohne Willkür
    ergebnis = analysiere_etikett(datenbank["marken"], ocr_text)

    st.markdown("---")
    
    # Metriken-Layout
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Erkannt", ergebnis["name"])
    with col2:
        st.metric("Eco Score", f"{ergebnis['score']} / 100")
        
    st.markdown(f"### Bewertung: {ergebnis['kategorie']}")
    st.progress(ergebnis["score"] / 100.0)
    
    st.info(f"💡 **Fundierte Begründung:** {ergebnis['begruendung']}")
    
    with st.expander("🔍 Gelesener Text (OCR)"):
        st.write(ocr_text if ocr_text else "Kein Text erkannt.")

else:
    # Minimalistischer Start-Zustand (exakt aufgeräumt)
    st.markdown("")
    st.markdown("""
    <div style="background-color: #ffffff; padding: 25px; border-radius: 20px; border: 1px dashed #c2d6cb; text-align: center;">
        <p style="color: #2d4a3e; font-weight: 600; margin-bottom: 5px;">📸 Foto hochladen oder aufnehmen</p>
        <p style="color: #718f82; font-size: 0.85rem;">Halte die Kamera auf das Markenlogo oder das weiße Waschetikett in der Kleidung.</p>
    </div>
    """, unsafe_allow_html=True)
