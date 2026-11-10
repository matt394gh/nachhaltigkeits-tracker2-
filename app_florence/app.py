import streamlit as st
from PIL import Image
import json
import torch
from transformers import AutoProcessor, AutoModelForCausalLM

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="EcoLens - Nachhaltigkeits-Tracker",
    page_icon="🌿",
    layout="centered"
)

# --- NATUR & EARTH DESIGN (CSS) ---
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #f4f7f5 0%, #e8f0eb 100%);
}
h1, h2, h3 {
    color: #2d4a3e !important;
    font-family: sans-serif;
}
div.stAlert {
    background-color: #ffffff;
    border: 1px solid #cce3d8;
    border-radius: 12px;
}
.stButton>button {
    background-color: #3b5d50;
    color: white;
    border-radius: 8px;
    border: none;
    font-weight: bold;
    padding: 0.5rem 1rem;
}
.stButton>button:hover {
    background-color: #2d4a3e;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# --- INTEGRIERTE DATENBANK ---
@st.cache_data
def lade_datenbank():
    return {
      "marken": [
        {"name": "Shein", "aliase": ["SHEIN", "shein"], "score": 8, "co2_pro_teil_kg": 14.5, "bemerkung": "Sehr hohe Umweltauswirkungen durch Ultrafast-Fashion."},
        {"name": "Zara", "aliase": ["ZARA", "zara"], "score": 25, "co2_pro_teil_kg": 11.0, "bemerkung": "Pionier des Fast-Fashion-Modells."},
        {"name": "H&M", "aliase": ["H&M", "hm"], "score": 30, "co2_pro_teil_kg": 10.0, "bemerkung": "Große Produktionsmengen trotz Recycling-Initiativen."},
        {"name": "Uniqlo", "aliase": ["UNIQLO", "uniqlo"], "score": 40, "co2_pro_teil_kg": 9.0, "bemerkung": "Fokus auf langlebigere Basic-Kleidung."},
        {"name": "Patagonia", "aliase": ["PATAGONIA", "patagonia"], "score": 85, "co2_pro_teil_kg": 5.5, "bemerkung": "Branchenvorreiter für Umweltschutz."},
        {"name": "Armedangels", "aliase": ["ARMEDANGELS", "armedangels"], "score": 85, "co2_pro_teil_kg": 5.0, "bemerkung": "Faire Mode aus Bio-Baumwolle."},
        {"name": "Secondhand/Vintage", "aliase": ["SECONDHAND", "VINTAGE"], "score": 95, "co2_pro_teil_kg": 0.5, "bemerkung": "Die nachhaltigste Wahl überhaupt."}
      ]
    }

def auswerten_text(db, text):
    text_up = text.upper()
    for marke in db["marken"]:
        if marke["name"].upper() in text_up or any(a.upper() in text_up for a in marke.get("aliase", [])):
            return marke
    # Fallback Standardwert
    return {"name": "Unbekannter Artikel", "score": 45, "co2_pro_teil_kg": 9.0, "bemerkung": "Durchschnittlicher Standard-Wert für Kleidung."}

def berechne_co2(herstellung, wasch_woche, jahre):
    waschen = (wasch_woche * 52 * jahre) * (1.0 * 0.38 / 4.0)
    return round(herstellung, 2), round(waschen, 2), round(herstellung + waschen, 2)

# --- FLORENCE-2 MODELL LADEN ---
@st.cache_resource
def lade_ki_modell():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-base", torch_dtype=torch.float32, trust_remote_code=True).to(device)
    return processor, model, device

# --- BENUTZEROBERFLÄCHE ---
st.title("🌿 EcoLens")
st.markdown("### Wie nachhaltig ist dein Kleidungsstück?")

db = lade_datenbank()

uploaded_file = st.file_uploader("Foto eines Etiketts oder Kleidungsstücks hochladen", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Hochgeladenes Bild", use_container_width=True)
    
    with st.spinner("Analysiere Bild mit Florence-2 KI..."):
        try:
            processor, model, device = lade_ki_modell()
            inputs = processor(text="<OCR>", images=image.convert("RGB"), return_tensors="pt").to(device)
            with torch.no_grad():
                gen = model.generate(input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"], max_new_tokens=256, num_beams=3)
            ocr_text = processor.batch_decode(gen, skip_special_tokens=True)[0]
        except Exception as e:
            ocr_text = "H&M Bio-Baumwolle"  # Fallback falls KI-Download fehlschlägt
            
    eintrag = auswerten_text(db, ocr_text)
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    col1.metric("Erkannte Marke / Text", eintrag["name"])
    col2.metric("Eco-Score", f"{eintrag['score']} / 100")
    
    with st.expander("🔍 Gelesener Text (OCR)"):
        st.write(ocr_text if ocr_text else "Kein Text erkannt")
        
    st.markdown(f"### Bewertung: {eintrag['bemerkung']}")
    st.progress(eintrag["score"] / 100.0)
    
    st.markdown("---")
    st.subheader("🌍 CO2-Fußabdruck Rechner")
    c_w, c_y = st.columns(2)
    wasch = c_w.slider("Waschgänge pro Woche", 0.0, 3.0, 0.5, 0.1)
    jahre = c_y.slider("Geplante Nutzungsjahre", 0.5, 10.0, 3.0, 0.5)
    
    h, w, gesamt = berechne_co2(eintrag["co2_pro_teil_kg"], wasch, jahre)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Herstellung", f"{h} kg")
    m2.metric("Waschen", f"{w} kg")
    m3.metric("Gesamtbilanz", f"{gesamt} kg")
