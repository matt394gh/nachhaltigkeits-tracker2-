import streamlit as st
from PIL import Image
import scoring
import model_b

st.set_page_config(page_title="EcoLens - Florence-2 OCR", page_icon="🌿", layout="centered")

# --- ECO-NATURE DESIGN (Waldgrün & sanftes Natur-Weiß) ---
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

st.title("🌿 EcoLens: Florence-2 (Version B)")
st.markdown("### Wie nachhaltig ist dein Artikel? (OCR & Etiketten-Analyse)")

with st.sidebar:
    st.info("ℹ️ **Version B:** Nutzt Microsoft Florence-2 für lokale Texterkennung auf Waschetiketten.")
    st.success("✅ Modell: `microsoft/Florence-2-base`")

db = scoring.lade_datenbank("sustainability_db.json")
uploaded_file = st.file_uploader("Etikett-Foto hochladen (JPG oder PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Hochgeladenes Etikett", use_container_width=True)
    
    with st.spinner("Analysiere Etikett per OCR (Lokale Ausführung)..."):
        res = model_b.analysiere_etikett(image)
        ocr_text = res["ocr"]
            
    eintrag = scoring.eintrag_fuer_ergebnis(db, ocr_text)
    stoffe = scoring.material_erkennen(ocr_text)
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    c1.metric("Erkannte Marke / Text", eintrag["name"])
    c2.metric("Kategorie", eintrag["kategorie"].upper())
    
    with st.expander("🔍 Technische OCR-Rohdaten"):
        st.write(ocr_text if ocr_text else "Kein Text erkannt")
        if stoffe:
            st.write("Erkannte Materialien:", ", ".join(stoffe))
            
    score = eintrag["score"]
    st.markdown(f"### Eco Score: {score} / 100")
    st.progress(score / 100.0)
    st.info(eintrag["bemerkung"])
    
    st.markdown("---")
    st.subheader("🌍 CO2-Fußabdruck Rechner")
    w_col, y_col = st.columns(2)
    wasch = w_col.slider("Waschgänge pro Woche", 0.0, 3.0, 0.5, 0.1)
    jahre = y_col.slider("Nutzungsjahre", 0.5, 10.0, 3.0, 0.5)
    
    h_co2, w_co2, g_co2 = scoring.berechne_co2(eintrag["co2_pro_teil_kg"], wasch, jahre)
    
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Herstellung", f"{h_co2} kg")
    sc2.metric("Waschen", f"{w_co2} kg")
    sc3.metric("Gesamtbilanz", f"{g_co2} kg")
