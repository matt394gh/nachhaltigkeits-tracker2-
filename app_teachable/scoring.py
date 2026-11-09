import json
import difflib

WASCHGANG_KWH = 1.0
CO2_PRO_KWH = 0.38
TEILE_PRO_TROMMEL = 4.0

def lade_datenbank(pfad="sustainability_db.json"):
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"marken": []}

def finde_marke(db, suchtext):
    if not suchtext:
        return None
    text_clean = suchtext.strip().upper()
    marken = db.get("marken", [])
    for marke in marken:
        if marke["name"].upper() == text_clean:
            return marke
        for alias in marke.get("aliase", []):
            if alias.upper() == text_clean:
                return marke
    for marke in marken:
        names_to_check = [marke["name"].upper()] + [a.upper() for a in marke.get("aliase", [])]
        for name in names_to_check:
            if len(name) >= 3 and name in text_clean:
                return marke
    alle_namen = []
    name_zu_marke = {}
    for marke in marken:
        alle_namen.append(marke["name"].upper())
        name_zu_marke[marke["name"].upper()] = marke
        for alias in marke.get("aliase", []):
            alle_namen.append(alias.upper())
            name_zu_marke[alias.upper()] = marke
    matches = difflib.get_close_matches(text_clean, alle_namen, n=1, cutoff=0.8)
    if matches:
        return name_zu_marke[matches[0]]
    return None

def eintrag_fuer_kategorie(kategorie):
    kat = kategorie.lower()
    if "fast" in kat:
        return {"name": "Unbekannte Marke (Fast Fashion)", "kategorie": "fast_fashion", "score": 20, "co2_pro_teil_kg": 12.0, "bemerkung": "Hohe Umweltbelastung."}
    elif "nachhaltig" in kat or "fair" in kat:
        return {"name": "Unbekannte Marke (Nachhaltig)", "kategorie": "nachhaltig", "score": 85, "co2_pro_teil_kg": 5.5, "bemerkung": "Fokus auf Umweltfreundlichkeit."}
    else:
        return {"name": "Unbekannte Marke (Standard)", "kategorie": "mittel", "score": 45, "co2_pro_teil_kg": 9.0, "bemerkung": "Durchschnittliches Mittelfeld."}

def eintrag_fuer_ergebnis(db, sucht_label, kategorie=None):
    marke = finde_marke(db, sucht_label)
    if marke:
        return marke
    if kategorie:
        return eintrag_fuer_kategorie(kategorie)
    return eintrag_fuer_kategorie(sucht_label)

def material_erkennen(text):
    if not text:
        return []
    stoffe = [
        ("BIO-BAUMWOLLE", "Bio-Baumwolle (Nachhaltig)"),
        ("ORGANIC COTTON", "Bio-Baumwolle (Nachhaltig)"),
        ("POLYESTER", "Polyester (Synthetisch/Mikroplastik)"),
        ("BAUMWOLLE", "Baumwolle (Konventionell)"),
        ("COTTON", "Baumwolle (Konventionell)"),
        ("ELASTHAN", "Elasthan (Synthetisch)"),
        ("WOLLE", "Wolle (Naturfaser)")
    ]
    gefundene = []
    text_up = text.upper()
    for key, label in stoffe:
        if key in text_up and label not in gefundene:
            gefundene.append(label)
    return gefundene

def berechne_co2(herstellung, waschgaenge_woche, jahre):
    gesamt_wasch = waschgaenge_woche * 52 * jahre
    waschen = gesamt_wasch * (WASCHGANG_KWH * CO2_PRO_KWH / TEILE_PRO_TROMMEL)
    gesamt = herstellung + waschen
    return round(herstellung, 2), round(waschen, 2), round(gesamt, 2)
