import streamlit as st
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForCausalLM

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="EcoLens - Nachhaltigkeits-Analyse",
    page_icon="🌿",
    layout="centered"
)

# --- EDLES NATURE-DESIGN (Angelehnt an dein Layout) ---
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #f9fbf9 0%, #edf4f0 100%);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
h1, h2, h3 {
    color: #23382d !important;
    font-weight: 600;
}
div.stAlert, div[data-testid="stVerticalBlock"] > div {
    border-radius: 16px;
}
.stButton>button {
    background-color: #2d4a3e;
    color: white;
    border-radius: 10px;
    border: none;
    font-weight: 600;
    padding: 0.6rem 1.2rem;
    box-shadow: 0 4px 12px rgba(45, 74, 62, 0.15);
    width: 100%;
}
.stButton>button:hover {
    background-color: #1f332a;
    color: white;
}
[data-testid="stMetricValue"] {
    color: #2d4a3e;
}
</style>
""", unsafe_allow_html=True)

# --- UMFANGREICHE MARKEN- & PRODUKT-DATENBANK ---
@st.cache_data
def lade_datenbank():
    return {
      "marken": [
        # Ultra Fast Fashion (Sehr niedrig)
        {"name": "Shein", "aliase": ["SHEIN", "shein"], "score": 8, "kategorie": "Sehr Kritisch", "begruendung": "Extrem hohes Überproduktionsvolumen, extrem niedrige Löhne und intransparente Synthetik-Lieferketten."},
        {"name": "Temu", "aliase": ["TEMU", "temu"], "score": 8, "kategorie": "Sehr Kritisch", "begruendung": "Massiver Einsatz von Luftfracht und extrem kurzlebige Einweg-Konsumgüter."},
        {"name": "AliExpress", "aliase": ["ALIEXPRESS"], "score": 10, "kategorie": "Sehr Kritisch", "begruendung": "Keinerlei ökologische Standards oder Nachverfolgbarkeit der Textilien."},
        
        # Fast Fashion (Niedrig)
        {"name": "Primark", "aliase": ["PRIMARK"], "score": 15, "kategorie": "Kritisch", "begruendung": "Billigproduktion fördert die Wegwerfkultur; unzureichende existenzsichernde Löhne."},
        {"name": "Zara", "aliase": ["ZARA", "zara", "INDITEX"], "score": 25, "kategorie": "Unter Durchschnitt", "begruendung": "Pionier der Fast-Fashion-Zyklen mit hohem Ressourcenverbrauch trotz kleiner Recycling-Kollektionen."},
        {"name": "Bershka", "aliase": ["BERSHKA"], "score": 25, "kategorie": "Unter Durchschnitt", "begruendung": "Tochtermarke von Inditex mit identisch schnellen Kollektionswechseln."},
        {"name": "H&M", "aliase": ["H&M", "HM", "HENNES & MAURITZ"], "score": 30, "kategorie": "Unter Durchschnitt", "begruendung": "Große grüne Marketing-Initiativen, aber das Kernvolumen basiert weiterhin auf Massenproduktion."},
        {"name": "Mango", "aliase": ["MANGO"], "score": 35, "kategorie": "Unter Durchschnitt", "begruendung": "Leichte Verbesserungen bei nachhaltigen Materialien, aber insgesamt konventionelle Fast Fashion."},

        # Mid-Range & Sport (Mittelfeld)
        {"name": "Uniqlo", "aliase": ["UNIQLO"], "score": 45, "kategorie": "Mittelfeld", "begruendung": "Fokus auf langlebigere Basics und recycelten Daunen, jedoch kaum Kreislaufwirtschaft."},
        {"name": "Nike", "aliase": ["NIKE"], "score": 42, "kategorie": "Mittelfeld", "begruendung": "Hoher Einsatz von recycelten Polyester-Fasern, aber enorme CO2-Emissionen in der globalen Sportartikel-Produktion."},
        {"name": "Adidas", "aliase": ["ADIDAS"], "score": 48, "kategorie": "Mittelfeld", "begruendung": "Starke Klimaziele und Plastik-Reduktionsprogramme, starkes Sponsoring treibt jedoch den Konsum."},
        {"name": "Levi's", "aliase": ["LEVI'S", "LEVIS"], "score": 50, "kategorie": "Mittelfeld", "begruendung": "Langlebiger Denim, Initiativen für Wassereinsparung (WaterLess), aber konventioneller Baumwollanbau."},
        {"name": "s.Oliver", "aliase": ["S.OLIVER"], "score": 45, "kategorie": "Mittelfeld", "begruendung": "Klassischer Anbieter im Mittelfeld mit moderaten Fortschritten bei Bio-Baumwolle."},

        # Eco & Nachhaltig (Sehr gut)
        {"name": "Patagonia", "aliase": ["PATAGONIA"], "score": 88, "kategorie": "Vorbildlich", "begruendung": "Branchenprimus: 100% Bio-Baumwolle/recycelte Stoffe, umfangreiche Reparaturversprechen und Spende von Gewinnen für den Umweltschutz."},
        {"name": "Armedangels", "aliase": ["ARMEDANGELS"], "score": 85, "kategorie": "Vorbildlich", "begruendung": "GOTS-zertifiziert, faire Arbeitsbedingungen, strenge Schadstoffprüfungen und transparenter CO2-Fußabdruck."},
        {"name": "Vaude", "aliase": ["VAUDE"], "score": 86, "kategorie": "Vorbildlich", "begruendung": "Strenge Umweltstandards (Green Shape), bluesign-zertifiziert und Vorreiter für faire Outdoor-Ausrüstung."},
        {"name": "hessnatur", "aliase": ["HESSNATUR"], "score": 90, "kategorie": "Vorbildlich", "begruendung": "Absoluter Pionier für Naturtextilien und strengste ökologische Richtlinien seit Jahrzehnten."},
        {"name": "Nudie Jeans", "aliase": ["NUDIE JEANS"], "score": 87, "kategorie": "Vorbildlich", "begruendung": "100% Bio-Denim, lebenslanger kostenloser Reparaturservice und transparente Lieferketten."},
        {"name": "Secondhand / Vintage", "aliase": ["SECONDHAND", "VINTAGE", "VINTED", "REUSE"], "score": 98, "kategorie": "Perfekt", "begruendung": "Die mit Abstand nachhaltigste Wahl: Keine Neuproduktion, keine zusätzlichen CO2-Emissionen, maximale Kreislaufwirtschaft."}
      ]
    }

def finde_marke_intelligent(db, text):
    if not text:
        return None
    text_up = text.upper()
    
    for marke in db["marken"]:
        if marke["name"].upper() in text_up:
            return marke
        for alias in marke.get("aliase", []):
            if alias.upper() in text_up:
                return marke
                
    if "BIO" in text_up or "ORGANIC" in text_up or "GOTS" in text_up:
        return {"name": "Zertifiziertes Bio-Textil", "score": 80, "kategorie": "Nachhaltig", "begruendung": "Das Etikett weist zertifizierte Bio-Fasern auf, was den ökologischen Fußabdruck drastisch senkt."}
    if "POLYESTER" in text_up or "ELASTHAN" in text_up:
        return {"name": "Synthetik-Mix", "score": 35, "kategorie": "Kritisch", "begruendung": "Synthetische Fasern auf Erdölbasis verursachen Mikroplastik beim Waschen."}
        
    return None

@st.cache_resource
def lade_ki_modell():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-base", torch_dtype=torch.float32, trust_remote_code=True).to(device)
    return processor, model, device

st.title("🌿 EcoLens")
st.markdown("#### Wie nachhaltig ist dein Artikel?")
st.caption("Lade ein Foto deines Kleidungsstücks oder Waschetiketts hoch, um die Umweltauswirkungen fundiert zu prüfen.")

db = lade_datenbank()

uploaded_file = st.file_uploader("Foto auswählen (JPG oder PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Hochgeladener Artikel", use_container_width=True)
    
    with st.spinner("Analysiere Bild und Etikett mit KI..."):
        try:
            processor, model, device = lade_ki_modell()
            inputs = processor(text="<OCR>", images=image.convert("RGB"), return_tensors="pt").to(device)
            with torch.no_grad():
                gen = model.generate(input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"], max_new_tokens=256, num_beams=3)
            ocr_text = processor.batch_decode(gen, skip_special_tokens=True)[0]
        except
