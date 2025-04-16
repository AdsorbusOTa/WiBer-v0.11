# -*- coding: utf-8 -*-
VERSION = "v0-11b"
RELEASE_DATE = "16.04.2025"  # manuell gepflegt
AUTHOR = "Adsorbus OTamm"
# author: otamm
# --------------------------------------------------------------------------------------------------------------------------------------------------
#  Bibliotheken
# region -------------------------------------------------------------------------------------------------------------------------------------------
import streamlit as st
import pandas as pd
import sqlite3
import os
import wetterdienst
import polars as pl
import altair as alt
import streamlit.components.v1 as components
import json5 # 🌐 Sprache auswählen und Übersetzung laden
from datetime import date
from fpdf import FPDF
from cryptography.fernet import Fernet # 🔐 für Verschlüsselung
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 🔑 Zugriff und Vorbereitung
# Hier wird geprüft, ob Secrets geladen werden müssen
# (z. B. für API-Zugriffe oder Passwörter).
# Außerdem erfolgt ggf. die Initialisierung wichtiger Parameter.
# --------------------------------------------------------------------------------------------------------------------------------------------------

ADMIN_PASSWORT = st.secrets["admin_passwort"]
key = st.secrets["aes_key"].encode()
fernet = Fernet(key)

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 🌐 Spracheinstellungen laden
# Ermittelt die gewählte Sprache aus der Session oder setzt einen Standardwert.
# Lädt das passende Übersetzungswörterbuch aus den JSON-Dateien.
# --------------------------------------------------------------------------------------------------------------------------------------------------
sprachoptionen = {
    "de": "🇩🇪 Deutsch",
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
    "es": "🇪🇸 Español"
}

sichtbare_labels = list(sprachoptionen.values())
sprache_auswahl = st.selectbox("🌐 Sprache / Language / Langue / Idioma", options=sichtbare_labels, index=0)
lang = [code for code, label in sprachoptionen.items() if label == sprache_auswahl][0]

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 🔧 Hilfsfunktionen
# Gültigkeitsprüfung für Werte
# Automatisches ausfüllen
# Überschriften
# Benutzerdefinierte Infobox
# Sprachauswahl
# Verschlüsselung
# Formatierung Dezimal- und Tausender- Trennzeichen
# Funktion, um das Kennfeld zu laden
# interpolieren aus dem Kennfeld
#  region ------------------------------------------------------------------------------------------------------------------------------------------

# Gültigkeitsprüfung
def valid_value(x):
    return x is not None and isinstance(x, (int, float)) and x > 0

# automatisches Ausfüllen
def beispiel_checkbox():
    st.session_state["mit_beispieldaten"] = st.checkbox(
        t["example_data"], 
        value=st.session_state["mit_beispieldaten"]
    )

def beispielwert(beispiel, original):
    return beispiel if st.session_state["mit_beispieldaten"] else original

# Initialisierung Autoausfüllen
if "mit_beispieldaten" not in st.session_state:
    st.session_state["mit_beispieldaten"] = False
if "beispieldaten_wurden_gesetzt" not in st.session_state:
    st.session_state["beispieldaten_wurden_gesetzt"] = False

# Überschriften
def header_1(text: str):
    st.markdown(
        f"""
        <style>
        .custom-header-1 {{
            font-size: 36px;
            font-weight: bold;
            /* color: #444; */   /* Heller Text in Light-Theme */
            text-align: justify;
            margin-bottom: 0.3em;
        }}
        </style>
        <div class='custom-header-1'>
            {'<br>'.join(text.splitlines())}
        </div>
        """,
        unsafe_allow_html=True
    )

def header_2(text: str):
    st.markdown(
        f"""
        <style>
        .custom-header-2 {{
            font-size: 30px;
            font-weight: bold;
            /* color: #444; */   /* Heller Text in Light-Theme */
            text-align: justify;
            margin-bottom: 0.2em;
        }}
        </style>
        <div class='custom-header-2'>
            {'<br>'.join(text.splitlines())}
        </div>
        """,
        unsafe_allow_html=True
    )

def header_3(text: str):
    st.markdown(
        f"""
        <style>
        .custom-header-3 {{
            font-size: 24px;
            font-weight: normal;
            /* color: #444; */   /* Heller Text in Light-Theme */
            text-align: justify;
            margin-bottom: 0.2em;
        }}
        </style>
        <div class='custom-header-3'>
            {'<br>'.join(text.splitlines())}
        </div>
        """,
        unsafe_allow_html=True
    )

def header_4(text: str):
    st.markdown(
        f"""
        <style>
        .custom-header-4 {{
            font-size: 20px;
            font-weight: normal;
            font-style: italic;
            /* color: #444; */   /* Heller Text in Light-Theme */
            text-align: justify;
            margin-bottom: 0.2em;
        }}
        </style>
        <div class='custom-header-4'>
            {'<br>'.join(text.splitlines())}
        </div>
        """,
        unsafe_allow_html=True
    )

# infobox
def info_box(text: str, title: str = None):
    header = f"<h4>{title}</h4><hr>" if title else ""
    st.markdown(
        f"""
        <style>
        .custom-info-box {{
            padding: 1em;
            background-color: #172D43;
            color: #C7EBFF;
            border-radius: 5px;
            font-weight: normal;
            text-align: justify;
            margin-bottom: 0.5em;
        }}
        </style>

        <div class='custom-info-box'>
            {'<br>'.join(text.splitlines())}
        </div>
        """,
        unsafe_allow_html=True
    )

# Sprachauswahl
def load_translation(lang):
    with open(f"02_Hilfsfunktionen/translations/{lang}.json5", "r", encoding="utf-8") as f:
        return json5.load(f)
t = load_translation(lang)

# Verschlüsselung
def encrypt_database():
    key = st.secrets["aes_key"].encode()
    fernet = Fernet(key)

    with open("datenbank/betriebsdaten.db", "rb") as file:
        original = file.read()

    encrypted = fernet.encrypt(original)

    with open("datenbank/betriebsdaten_encrypted.db", "wb") as enc_file:
        enc_file.write(encrypted)

# Dezimal- und Tausender- Trennzeichen
def format_de(value, decimals=2, tausender="'"):
    if isinstance(value, (int, float)):
        s = f"{value:,.{decimals}f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", tausender)
        return s
    return str(value)

# Funktion, um das Kennfeld zu laden
def lade_kennfeld(pfad="02_Hilfsfunktionen/Kennfelder/kaeltemaschinen_kennfeld.csv"):
    try:
        df = pd.read_csv(pfad)
        return df
    except FileNotFoundError:
        st.error(f"Die Datei '{pfad}' wurde nicht gefunden.")
        return None

# interpolieren aus dem Kennfeld
from scipy.interpolate import LinearNDInterpolator
def erstelle_interpolatoren(df):
    punkte = df[["hwt", "rkt", "kwt_out"]].values
    cop = df["cop"].values
    kl = df["kl"].values
    interpolator_cop = LinearNDInterpolator(punkte, cop)
    interpolator_kl = LinearNDInterpolator(punkte, kl)
    return interpolator_cop, interpolator_kl
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 🧾 SQLITE-Datenbank erstellen
# Hier wird die Datenbak erstellt und die notwendigen Spalten für die Nutzerdaten generiert
# region -------------------------------------------------------------------------------------------------------------------------------------------
# Sicherstellen, dass der Speicherordner existiert
if not os.path.exists("datenbank"):
    os.makedirs("datenbank")
db_path = "datenbank/betriebsdaten.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
# Tabelle erstellen
cursor.execute('''
    CREATE TABLE IF NOT EXISTS betriebsdaten (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        standort TEXT,
        betreiber TEXT,
        kontaktperson TEXT,
        email TEXT,
        telefon TEXT,
        plz TEXT,
        ort TEXT,
        strasse TEXT,
        stromverbrauch REAL,
        betriebsstunden INTEGER,
        strompreis REAL,
        max_kälteleistung REAL,
        durchschn_kälteleistung REAL,
        wirkungsgrad REAL,
        volumenstrom REAL,
        temp_eintritt REAL,
        temp_austritt REAL,
        kosten REAL
    )
''')
conn.commit()

def generate_pdf(data):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Betriebsdaten-Bericht", ln=True, align="C")
    pdf.ln(10)
    for key, value in data.items():
        pdf.cell(200, 10, f"{key}: {value}", ln=True)
    pdf_path = "Betriebsbericht.pdf"
    pdf.output(pdf_path)
    return pdf_path

# Autocomplete für alle Formularfelder aktivieren
components.html("""
<script>
  // aktiviert autocomplete auf allen Input-Feldern
  document.querySelectorAll("input").forEach(el => el.setAttribute("autocomplete", "on"));
</script>
""", height=0)
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 🧩 Seitenlayout und App-Kopf
# region -------------------------------------------------------------------------------------------------------------------------------------------
# Zeigt Titel, Info-Box und Sprachabhängige Einführungstexte an.
# Hier beginnt die sichtbare Oberfläche für den Benutzer.

st.title(t["app_title"])
info_box(t["intro_box"])
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 📋 Benutzerformular zur Projekterfassung
# Hier gibt der Benutzer alle projektspezifischen Daten ein:
# Kontaktdaten, technische Eckwerte, Stromverbrauch, Temperaturdifferenzen usw.
# Die Eingaben werden später für die Berechnungen und Auswertungen verwendet.
# region -------------------------------------------------------------------------------------------------------------------------------------------

# Web-App UI
header_2(t["section_title_main"])
header_3(t["section_1"])


# 📌 Auswahl: Formular mit Beispieldaten füllen?
#mit_beispieldaten = st.checkbox(t["example_data"], value=False)

# Robuste Zuweisung mit Fallback-Werten
(
    id_val, standort_val, betreiber_val, kontaktperson_val, email_val, telefon_val,
    plz_val, ort_val, strasse_val,
    stromverbrauch_val, betriebsstunden_val, strompreis_val,
    max_kälteleistung_val, durchschn_kälteleistung_val, wirkungsgrad_val,
    volumenstrom_val, temp_eintritt_val, temp_austritt_val, kosten_val
) = (None,) * 19


# 📥 Autoausfüllung bei Bedarf
#standort_val = beispielwert("Werk Nord", standort_val)
#betreiber_val = beispielwert("Muster GmbH" , betreiber_val)
#kontaktperson_val = beispielwert("Martina Mustermann", kontaktperson_val)
#email_val = beispielwert("technik@mustergmbh.de", email_val)
#telefon_val = beispielwert("+49 123 12345678", telefon_val)
#plz_val = beispielwert("12345", plz_val)
#ort_val = beispielwert("Musterstadt", ort_val)
#strasse_val = beispielwert("Musterstraße 1", strasse_val)

stromverbrauch_val = beispielwert(200000.0, stromverbrauch_val)
betriebsstunden_val = beispielwert(6000, betriebsstunden_val)
strompreis_val = beispielwert(0.32, strompreis_val)
max_kälteleistung_val = beispielwert(120.0, max_kälteleistung_val)
durchschn_kälteleistung_val = beispielwert(100.0, durchschn_kälteleistung_val)
wirkungsgrad_val = beispielwert(3.0, wirkungsgrad_val)
volumenstrom_val = beispielwert(28.7, volumenstrom_val)
temp_eintritt_val = beispielwert(18.0, temp_eintritt_val)
temp_austritt_val = beispielwert(15.0, temp_austritt_val)


# Schrittweite definieren für bessere Nutzung mit Plus-/Minus-Schaltflächen
stromverbrauch_step = 50.0
betriebsstunden_step = 100
messung_step = 0.5
strompreis_step = 0.01
leistung_step = 5.0
eer_step = 0.1
temp_step = 0.5
volumen_step = 0.5

standort = st.text_input(t["site"], value=standort_val, help=t["tooltips"]["site"])
betreiber = st.text_input(t["operator"], value=betreiber_val, help=t["tooltips"]["operator"])
kontaktperson = st.text_input(t["contact"], value=kontaktperson_val, help=t["tooltips"]["contact"])
email = st.text_input(t["email"], value=email_val, help=t["tooltips"]["email"])
telefon = st.text_input(t["phone"], value=telefon_val, help=t["tooltips"]["phone"])
plz = st.text_input(t["postal_code"], value=plz_val, help=t["tooltips"]["postal_code"])
ort = st.text_input(t["city"], value=ort_val, help=t["tooltips"]["city"])
strasse = st.text_input(t["street"], value=strasse_val, help=t["tooltips"]["street"])

# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 📋 Daten Bestandskältemaschine
# region -------------------------------------------------------------------------------------------------------------------------------------------
header_3(t["section_2"])
# st.info(t["max_cooling_power"])
max_kälteleistung = st.number_input(
    t["nom_cooling_capa"], 
    min_value=0.0, 
    #value=max_kälteleistung_val, 
    step=leistung_step, 
    format="%0.1f", 
    help=t["tooltips"]["max_kälteleistung"]
    )
durchschn_kälteleistung = st.number_input(
    t["avg_cooling_capa"], 
    min_value=0.0, 
    #value=durchschn_kälteleistung_val, 
    step=leistung_step, 
    format="%0.1f", 
    help=t["tooltips"]["durchschn_kälteleistung"]
    )
wirkungsgrad = st.number_input(
    t["EER_nom"], 
    min_value=1.0, 
    max_value=10.0, 
    value=3.0, 
    step=eer_step, 
    format="%0.1f", 
    help=t["tooltips"]["wirkungsgrad"]
    )
volumenstrom = st.number_input(
    t["volumenstrom"], 
    min_value=0.0, 
    #value=5.0, 
    step=volumen_step, 
    format="%0.1f", 
    help=(t["tooltips"]["volumenstrom"])
    )
temp_eintritt = st.number_input(
    t["temp_eintritt"], 
    min_value=8.0, 
    max_value=30.0, 
    value=18.0, 
    step=temp_step, 
    format="%0.1f", 
    help=(t["tooltips"]["temp_eintritt"])
    )
temp_austritt = st.number_input(
    t["temp_austritt"], 
    min_value=4.0, 
    max_value=25.0, 
    value=15.0, 
    step=temp_step, 
    format="%0.1f", 
    help=(t["tooltips"]["temp_austritt"])
    )
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 📋 Betriebsdatenerfassung
# region -------------------------------------------------------------------------------------------------------------------------------------------
header_3(t["section_3"])
#beispiel_checkbox()

betriebsstunden = st.number_input(
    t["betriebsstunden"], 
    min_value=0, 
    max_value=8760, 
    #value=betriebsstunden_val, 
    step=betriebsstunden_step, 
    format="%d", 
    help=t["tooltips"]["betriebsstunden"])
strompreis = st.number_input(
    t["strompreis"], 
    min_value=0.0, 
    #value=strompreis_val, 
    step=strompreis_step, 
    format="%0.2f", 
    help=t["tooltips"]["strompreis"]
    )

verbrauch_bekannt = st.radio(
    t["verbrauch_bekannt"],
    (t["option_ja"], t["option_nein"]),
    index=0,
    horizontal=True
)

if verbrauch_bekannt == t["option_ja"]:
    stromverbrauch = st.number_input(
        t["labels"]["stromverbrauch"], #"Jahresstromverbrauch der Kältemaschine (kWh)",
        min_value=0.0,
        #value=stromverbrauch_val,
        step=stromverbrauch_step,
        format="%0.0f",
        help=t["tooltips"]["stromverbrauch"]
    )
else:
    stromverbrauch = 0.0  # oder None, je nach späterer Verarbeitung
    leistung_messung = 0.0  # oder None, je nach späterer Verarbeitung
    ermitteln = st.checkbox(t["ermitteln"])

    if ermitteln:
        header_4(t["header_ermitteln"])
        info_box(t["info_ermitteln"])

        messverbrauch = st.number_input(
            t["messverbrauch"], 
            min_value=0.0, 
            step=stromverbrauch_step, 
            format="%0.0f", 
            help=t["tooltips"]["messverbrauch"]
            )
        messdauer = st.number_input(
            t["messdauer"], 
            min_value=0.5, 
            step=messung_step, 
            format="%0.1f", 
            help=t["tooltips"]["messdauer"]
            )

        if valid_value(messdauer):
            leistung_messung = messverbrauch / messdauer
            st.write(t["leistung_messung"].format(value=format_de(leistung_messung, 0)))
            if valid_value(betriebsstunden):
                ber_stromverbrauch = leistung_messung * betriebsstunden
                st.write(
                    t["ber_stromverbrauch"].format(
                        value1=format_de(betriebsstunden, 0),
                        value2=format_de(ber_stromverbrauch, 0))
                    )
            if valid_value(wirkungsgrad_val):
                berechnete_kaelteleistung = leistung_messung * wirkungsgrad
                st.write(
                    t["berechnete_kaelteleistung"].format(
                    berechnete_kaelteleistung=format_de(berechnete_kaelteleistung, 1)))
            else:
                st.warning(t["EER_fehlt"])
        else:
            durchschn_leistung = None
            st.warning(t["messdauer_null"])

# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 📋 Berechnungen
# Berechnung: Durchschnittliche Kälteleistung aus Stromverbrauch und Wirkungsgrad
# region -------------------------------------------------------------------------------------------------------------------------------------------
# ➕ Absicherung gegen Division durch 0 bei Abweichungsberechnung
if all(x is not None and x > 0 for x in [wirkungsgrad, stromverbrauch, betriebsstunden]):
    berechnete_kälteleistung = stromverbrauch / betriebsstunden * wirkungsgrad
    #st.write(f"🔹 Berechnete durchschnittliche Kälteleistung aus Jahresstromverbrauch und Betriebsstunden: {format_de(berechnete_kälteleistung, 1)} kW")
    st.write(t["berechnete_kaelteleistung"].format(value=format_de(berechnete_kälteleistung, 1)))
    if durchschn_kälteleistung > 0:
        differenz = abs(durchschn_kälteleistung - berechnete_kälteleistung)
        if berechnete_kälteleistung != 0:
            prozent_diff = differenz / berechnete_kälteleistung
            if prozent_diff < 0.05:
                st.success(t["diff_success"].format(
                    wert=format_de(differenz, 1),
                    abweichung=round(prozent_diff * 100)
                ))
            elif prozent_diff < 0.20:
                st.warning(t["diff_warning"].format(
                    wert=format_de(differenz, 1),
                    abweichung=round(prozent_diff * 100)
                ))
            else:
                st.error(t["diff_error"].format(
                    wert=format_de(differenz, 1),
                    abweichung=round(prozent_diff * 100)
                ))
        else:
            st.warning(t["diff_zero"])
    else:
        st.info(t["calc_not_possible"])
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 🔄 Betriebspunkt/Auslegungspunkt der Anlage
# region -------------------------------------------------------------------------------------------------------------------------------------------
# st.subheader(t["section_4"])
# st.info("💡 Volumenstrom in m³/h und Temperaturen an Ein- und Austritt zur Berechnung der Leistung.")

delta_T = temp_eintritt - temp_austritt if temp_eintritt > temp_austritt else 0
leistung_temp = volumenstrom * 1.16 * delta_T if delta_T > 0 and volumenstrom > 0 else 0

if valid_value(betriebsstunden):
    if stromverbrauch is not None and strompreis is not None:
        kosten = stromverbrauch * strompreis
        st.write(t["kosten"].format(value=format_de(kosten, 0)))
    else:
        kosten = None
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 🔄 Abruf von DWD Wetterdaten
# region -------------------------------------------------------------------------------------------------------------------------------------------
header_3(t["weather_title"])

from wetterdienst.provider.dwd.observation import DwdObservationRequest
from geopy.geocoders import Nominatim
from datetime import datetime

@st.cache_data(show_spinner=False)
def get_coordinates_from_plz(plz_code):
    geolocator = Nominatim(user_agent="coolcalc")
    location = geolocator.geocode(f"{plz_code}, Germany")
    if location:
        return (location.latitude, location.longitude)
    return None

@st.cache_data(show_spinner=True)
def get_stationen_und_parameter(coords, entfernung_km, auto_jahrsuche=False, fixed_year=None):
    meldungen = []
    daten = {}
    gefundene_stationen = []
    lat, lon = coords
    current_year = date.today().year

    if auto_jahrsuche:
        jahr_liste = list(range(current_year - 1, 1999, -1))
    else:
        jahr_liste = [fixed_year]

    for year in jahr_liste:
        start_date = datetime.strptime(f"{year}-01-01", "%Y-%m-%d")
        end_date = datetime.strptime(f"{year}-12-31", "%Y-%m-%d")

        try:
            request = DwdObservationRequest(
                parameters="hourly/air_temperature",
                periods="historical"
            )
            stations = request.filter_by_distance(latlon=(lat, lon), distance=entfernung_km)
            stations_df = stations.df.to_pandas()

            for station in stations_df.itertuples():
                try:
                    values = request.filter_by_station_id(station.station_id).values
                    for measurement in values.query():
                        df = measurement.df
                        #df = df.to_pandas() if hasattr(df, "to_pandas") else df
                        if isinstance(df, pl.DataFrame):
                            df = df.to_pandas()

                        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

                        if "temperature_air_mean_2m" not in df["parameter"].unique():
                            continue

                        df = df[df["parameter"] == "temperature_air_mean_2m"]
                        df = df[(df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))]

                        if not df.empty:
                            daten[station.station_id] = {
                                "name": station.name,
                                "distance": station.distance,
                                "daten": df
                            }
                            eintrag = t["station_dropdown_entry"].format(
                                station_id=station.station_id,
                                name=station.name,
                                distance=round(station.distance, 1)
                            )
                            
                            gefundene_stationen.append(eintrag)
                            #gefundene_stationen.append(f"{station.station_id} – {station.name} – Entfernung: {round(station.distance, 1)} km")
                            break
                except Exception as e:
                    meldungen.append(
                        t["station_error"].format(
                            station_id=station.station_id,
                            error=e
                            )
                    )
                    #meldungen.append(f"⚠️ Fehler bei Station {station.station_id}: {e}")
                    continue

            if len(daten) > 0:
                break

        except Exception as e:
            meldungen.append(
                t["year_error"].format(
                    year=year,
                    error=e
                )
            )
            #meldungen.append(f"⚠️ Fehler in Jahr {year}: {e}")
            continue

    return daten, year, meldungen
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 🌡️ Temperaturauswertung aus Wetterdaten
# Abfrage der nächsten Wetterstation über die eingegebene PLZ,
# Ermittlung der Jahresdaten (z. B. Stundentemperatur),
# Darstellung als Tagesmittelwerte zur besseren Analyse.
# region ------------------------------------------------------------------------------------------------------------------------------------------

# Initialisierung Wetterdaten
if "wetter_daten" not in st.session_state:
    st.session_state["wetter_daten"] = None
    st.session_state["wetter_jahr"] = None
    st.session_state["wetter_meldungen"] = []

if plz:
    coords = get_coordinates_from_plz(plz)
    if coords:
        entfernung = st.slider(
            t["weather_search_radius"], 
            min_value=10, 
            max_value=300, 
            value=30, 
            step=10
            )
        selected_year = st.number_input(
            t["manual_year"], 
            min_value=2019, 
            max_value=date.today().year - 1, 
            value=2023
            )
        auto = st.toggle(
            t["auto_year"], 
            value=False
            )
        
        # Bei Betätigung Button, werden die Daten abgerufen in nach SessionState übertragen:
        if st.button(t["start_search"]):
            #get_stationen_und_parameter(coords, entfernung, auto_jahrsuche=auto, fixed_year=selected_year)
            #daten = get_stationen_und_parameter(coords, entfernung, auto_jahrsuche=auto, fixed_year=selected_year)
            daten, jahr, meldungen = get_stationen_und_parameter(coords, entfernung, auto_jahrsuche=auto, fixed_year=selected_year)
            st.session_state["wetter_daten"] = daten
            st.session_state["wetter_jahr"] = jahr
            st.session_state["wetter_meldungen"] = meldungen
            # Ausgabe an den Benutzer z.B. „⚠️ Station XY hat keine Temperaturdaten für 2022.“
            if meldungen:
                for m in meldungen:
                    st.info(m)
        
        # Ohne Button werden Daten direkt aus dem Session-State verwendet:
        daten = st.session_state["wetter_daten"]
        jahr = st.session_state["wetter_jahr"]
        meldungen = st.session_state["wetter_meldungen"]

        if daten:
            stationen = list(daten.keys())
            station_labels = [
                t["station_dropdown_entry"].format(
                    station_id=sid,
                    name=daten[sid]["name"],
                    distance=round(daten[sid]["distance"], 1)
                )
                for sid in daten
            ]
            #station_labels = [f"📍 {sid} – {daten[sid]['name']} – Entfernung: {round(daten[sid]['distance'], 1)} km" for sid in daten]
            station_ids = list(daten.keys())
            selected_index = st.selectbox(
                t["weather_select_station"], 
                range(len(station_ids)), 
                format_func=lambda i: station_labels[i]
                )
            station_id = station_ids[selected_index]

            # 🌡️ Temperaturgrenzen
            st.markdown(t["weather_temp_limits"])
            temp_grenze_1 = st.number_input(
                t["weather_limit_1"], 
                min_value=-50.0, 
                max_value=60.0, 
                value=12.0, 
                step=0.5,
                help=t["tooltips"]["weather_limit_1"]
                )
            temp_grenze_2 = st.number_input(
                t["weather_limit_2"], 
                min_value=temp_grenze_1, 
                max_value=60.0, 
                value=21.0, 
                step=0.5,
                help=t["tooltips"]["weather_limit_2"]
                )
            temp_grenze_3 = st.number_input(
                t["weather_limit_3"], 
                min_value=temp_grenze_2, 
                max_value=60.0, 
                value=30.0, 
                step=0.5,
                help=t["tooltips"]["weather_limit_3"]
                )

            # 📈 Diagramm & Auswertung im Expander
            with st.expander(f"{t['weather_expander_title']} {jahr}", expanded=False):
                with st.spinner(t["loading_stations_and_parameters"]):
                    try:
                        df_temp = daten[station_id]["daten"]
                        # ✅ HIER sicherstellen, dass df_temp ein Pandas-DataFrame ist:
                        if isinstance(df_temp, pl.DataFrame):
                            df_temp = df_temp.to_pandas()
                        #df_temp = df_temp.filter(pl.col("parameter") == "temperature_air_mean_2m")
                        df_temp = df_temp[df_temp["parameter"] == "temperature_air_mean_2m"]

                        # 🌡️ Temperaturverteilung berechnen
                        anzahl_1 = (df_temp["value"] < temp_grenze_1).sum()
                        anzahl_2 = ((df_temp["value"] >= temp_grenze_1) & (df_temp["value"] < temp_grenze_2)).sum()
                        anzahl_3 = ((df_temp["value"] >= temp_grenze_2) & (df_temp["value"] < temp_grenze_3)).sum()
                        anzahl_4 = (df_temp["value"] >= temp_grenze_3).sum()

                        bereich_labels = [
                            t["temp_range_labels"]["range_1"],
                            t["temp_range_labels"]["range_2"],
                            t["temp_range_labels"]["range_3"],
                            t["temp_range_labels"]["range_4"]
                        ]

                        ausgabe_zeilen = [
                            t["weather_hours_ranges"]["range_1"].format(
                                label=bereich_labels[0],
                                g1=temp_grenze_1,
                                h=anzahl_1,
                                stunden=t["stunden"]
                            ),
                            t["weather_hours_ranges"]["range_2"].format(
                                label=bereich_labels[1],
                                g1=temp_grenze_1,
                                g2=temp_grenze_2,
                                h=anzahl_2,
                                stunden=t["stunden"]
                            ),
                            t["weather_hours_ranges"]["range_3"].format(
                                label=bereich_labels[2],
                                g2=temp_grenze_2,
                                g3=temp_grenze_3,
                                h=anzahl_3,
                                stunden=t["stunden"]
                            ),
                            t["weather_hours_ranges"]["range_4"].format(
                                label=bereich_labels[3],
                                g3=temp_grenze_3,
                                h=anzahl_4,
                                stunden=t["stunden"]
                            )
                        ]

                        #st.write(t["weather_distribution_title"])
                        for zeile in ausgabe_zeilen:
                            st.markdown(f"- {zeile}")

                        # Umbenennen und Index setzen
                        df_plot = df_temp.rename(columns={"date": "index"}).set_index("index")
                        df_plot["Stunde"] = range(len(df_plot))
                        # Diagramm anzeigen
                        #st.line_chart(df_plot["value"])
                        chart_verlauf = alt.Chart(df_plot.reset_index()).mark_line().encode(
                            x=alt.X("index:T", title=t["chart_month_axis_title"]),  # T für Zeitachse
                            y=alt.Y("value:Q", title=t["chart_temperature_axis_title"]),
                            tooltip=[
                                alt.Tooltip("index:T", title=t["tooltips"]["date"]),
                                alt.Tooltip("value:Q", title=t["tooltips"]["temperature"])
                            ]
                        ).properties(
                            width=700,
                            height=400,
                            title=t["chart_title_verlauf"]
                        )
                        st.altair_chart(chart_verlauf, use_container_width=True)

                        # 🔢 Temperaturdaten sortieren
                        df_sorted = df_temp.sort_values(by="value").copy().reset_index(drop=True)
                        df_sorted["Stunde"] = df_sorted.index  # künstliche Zeitachse: Stunde 0–n
                        # 🏷️ Temperaturbereich benennen
                        bereich_labels = [
                            t["temp_range_labels"]["range_1"],
                            t["temp_range_labels"]["range_2"],
                            t["temp_range_labels"]["range_3"],
                            t["temp_range_labels"]["range_4"]
                        ]

                        df_sorted["Temperaturbereich"] = pd.cut(
                            df_sorted["value"],
                            bins=[-float("inf"), temp_grenze_1, temp_grenze_2, temp_grenze_3, float("inf")],
                            labels=bereich_labels
                        )
                        # Farbzuordnung manuell festlegen
                        farbskala = alt.Scale(
                            domain=bereich_labels,
                            range=[
                                "#1f77b4", # Dunkelblau
                                "#aec7e8", # Hellblau
                                "#ff7f0e", # Orange
                                "#d62728" # Rot
                                ]
                        )

                        # 🌡️ Minimalwert für y-Achse bestimmen
                        min_temp = df_sorted["value"].min()

                        # 🎨 Altair-Flächendiagramm
                        chart = alt.Chart(df_sorted).mark_area(
                            #line={"color": "black"},
                            strokeWidth=0.5,
                            interpolate="monotone"
                        ).encode(
                            x=alt.X("Stunde:Q",
                                    title=t["chart_hour_axis_title"],
                                    scale=alt.Scale(domain=[0, 8760]),
                                    axis=alt.Axis(values=list(range(0, 8761, 730)))),
                            y=alt.Y("value:Q",
                                    title=t["chart_temperature_axis_title"],
                                    scale=alt.Scale(domain=[min_temp - 1, df_sorted["value"].max() + 1])),
                            # color=alt.Color(
                            #     "Temperaturbereich:N", 
                            #     title="Temperaturbereich",
                            #     scale=farbskala,
                            #     legend=alt.Legend(orient="bottom")),
                            fill=alt.Fill("Temperaturbereich:N",
                                scale=farbskala,
                                legend=alt.Legend(
                                    orient="bottom",
                                    title=t["temp_area"],
                                    direction="horizontal",
                                    columns=2,
                                    labelFontSize=11,     # kleinerer Text
                                    titleFontSize=12,
                                    labelLimit=200
                                    ),
                                title=t["temp_area"]),
                            detail="Temperaturbereich:N",  # Gruppierung ohne Linie
                            tooltip=[
                                alt.Tooltip("Stunde:Q", title=t["tooltips"]["hour"]),
                                alt.Tooltip("value:Q", title=t["tooltips"]["value"]),
                                alt.Tooltip("Temperaturbereich:N", title=t["tooltips"]["area"])
                            ]
                        ).properties(
                            width=700,
                            height=400,
                            title=t["title_jdl"]
                        )
                        st.altair_chart(chart, use_container_width=True)

                        #st.line_chart(df_temp.rename({"date": "index"}).set_index("index")["value"])
                    except Exception as e:
                        st.error(
                            t["data_error"].format(
                                error=e
                            )
                        )
    else:
        st.warning(t["weather_no_data"])
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 🎯 Designpunkt der Adsorptionskältemaschine
# Interpoliert aus dem Maschinen-Kennfeld die erwartete Kälteleistung (kl)
# und den COP, basierend auf den drei Design-Temperaturen:
# Hochtemperatur (HT), Mitteltemperatur (MT) und Austritt Niedertemperatur (NT).
# region -------------------------------------------------------------------------------------------------------------------------------------------

header_3(t["design_title"])
df_kennfeld = lade_kennfeld()
if df_kennfeld is not None:
    from scipy.interpolate import LinearNDInterpolator

    def erstelle_interpolatoren(df):
        punkte = df[["hwt", "rkt", "kwt_out"]].values
        cop = df["cop"].values
        kl = df["kl"].values
        interpolator_cop = LinearNDInterpolator(punkte, cop)
        interpolator_kl = LinearNDInterpolator(punkte, kl)
        return interpolator_cop, interpolator_kl

    interpolator_cop, interpolator_kl = erstelle_interpolatoren(df_kennfeld)

    st.info(t["design_info"])

    hwt_input = st.number_input(
        t["design_input_ht"], 
        min_value=40.0, 
        max_value=100.0, 
        value=85.0, 
        step=1.0
        )
    rkt_input = st.number_input(
        t["design_input_mt"], 
        min_value=15.0, 
        max_value=45.0, 
        value=27.0, 
        step=1.0
        )
    kwt_out_input = st.number_input(
        t["design_input_nt"], 
        min_value=5.0, 
        max_value=20.0, 
        value=15.0, 
        step=0.5
        )

    if st.button(t["design_calculate"]):
        cop_wert = interpolator_cop(hwt_input, rkt_input, kwt_out_input)
        kl_wert = interpolator_kl(hwt_input, rkt_input, kwt_out_input)

        if cop_wert is not None and not pd.isna(cop_wert):
            st.success(t["design_result_cop"].format(cop=f"{cop_wert:.3f}"))
            st.success(t["design_result_kl"].format(kl=f"{kl_wert:.1f}"))
        else:
            st.warning(t["design_warning"])
else:
    st.error(t["design_error_load"])
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------------------------------------------------------------
# 💾 Eingabedaten speichern und anzeigen                                                                                                           
# # Speichert die vom Benutzer eingegebenen Werte in der SQLite-Datenbank.
# Danach wird die Datenbank verschlüsselt. Zusätzlich können die Daten
# aus der Session wieder angezeigt werden.
# region -------------------------------------------------------------------------------------------------------------------------------------------

if st.button(t["submit"]):
    cursor.execute('''
        INSERT INTO betriebsdaten (
            standort, betreiber, kontaktperson, email, telefon, plz, ort, strasse,
            stromverbrauch, betriebsstunden, strompreis,
            max_kälteleistung, durchschn_kälteleistung, wirkungsgrad,
            volumenstrom, temp_eintritt, temp_austritt,
            kosten
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        standort, betreiber, kontaktperson, email, telefon, plz, ort, strasse,
        stromverbrauch, betriebsstunden, strompreis,
        max_kälteleistung, durchschn_kälteleistung, wirkungsgrad,
        volumenstrom, temp_eintritt, temp_austritt,
        kosten
    ))
    conn.commit()
    st.session_state['eigene_id'] = cursor.lastrowid
    encrypt_database()  # 🔐 automatische Verschlüsselung
    # Unverschlüsselte Datei nach dem Verschlüsseln löschen
    if os.path.exists("datenbank/betriebsdaten.db"):
        os.remove("datenbank/betriebsdaten.db")
    st.success(t["encryption_suc"])

if st.button(t["but_show_sav"]):
    if 'eigene_id' in st.session_state:
        cursor.execute("SELECT * FROM betriebsdaten WHERE id = ?", (st.session_state['eigene_id'],))
        daten = cursor.fetchall()
        df = pd.DataFrame(daten, columns=[
            "ID", "Standort", "Betreiber", "Kontaktperson", "E-Mail", "Telefon", "PLZ", "Ort", "Strasse",
            "Stromverbrauch", "Betriebsstunden", "Strompreis", "Max. Kälteleistung",
            "Durchschn. Kälteleistung", "Wirkungsgrad", "Volumenstrom",
            "T Eintritt", "T Austritt", "Kosten"
            ])
        st.dataframe(df)
    else:
        st.info(t["inf_not_saved"])
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------------------------------------------
#🧾 PDF-Bericht erstellen                                                                                                                          
# Aus den eingegebenen und berechneten Werten wird ein PDF-Bericht erzeugt.                                                                        
# Der Bericht kann heruntergeladen oder weiterverwendet werden – z. B. für Angebotszwecke.                                                          
# region -------------------------------------------------------------------------------------------------------------------------------------------
if st.button(t["create_pdf"]):
    data = {
        "Standort": standort,
        "Betreiber": betreiber,
        "Kontaktperson": kontaktperson,
        "E-Mail": email,
        "Telefon": telefon,
        "PLZ": plz,
        "Ort": ort,
        "Strasse": strasse,
        "Stromverbrauch (kWh)": format_de(stromverbrauch, 0),
        "Betriebsstunden": format_de(betriebsstunden, 0),
        "Strompreis (EUR/kWh)": format_de(strompreis, 2),
        "Max. Kälteleistung (kW)": format_de(max_kälteleistung, 0),
        "Durchschn. Kälteleistung (kW)": format_de(durchschn_kälteleistung, 0),
        "Wirkungsgrad (EER)": format_de(wirkungsgrad, 1),
        "Volumenstrom (m³/h)": format_de(volumenstrom, 1),
        "Temperatur Eintritt (°C)": format_de(temp_eintritt, 1),
        "Temperatur Austritt (°C)": format_de(temp_austritt, 1),
        "Jährliche Kosten (EUR)": format_de(kosten, 0) if kosten is not None else "N/A",
    }
    pdf_path = generate_pdf(data)
    st.success(t["pdf_suc"])
    with open(pdf_path, "rb") as file:
        st.download_button(t["download_pdf"], file, file_name="Betriebsbericht.pdf")
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------------------------------------------
# 🔒 Entwicklerzugang: Gesicherter Datenbank-Download
# region -------------------------------------------------------------------------------------------------------------------------------------------
query_params = st.query_params
# st.write("Query Params:", query_params)
admin_access = query_params.get("zugang", "") == "6T8wA7v9zQp1"   # sicherer Parameter

if admin_access:
    st.markdown("---")
    st.subheader(t["admin_title"])

    password = st.text_input(t["admin_password"], type="password")

    if password == ADMIN_PASSWORT:
        encrypted_path = "datenbank/betriebsdaten_encrypted.db"
        if os.path.exists(encrypted_path):
            with open(encrypted_path, "rb") as f:
                st.download_button(t["admin_download"], f, file_name="betriebsdaten_encrypted.db")
        else:
            st.warning(t["no_encr_data"])
    elif password != "":
        st.error(t["wrong_password"])
# endregion ----------------------------------------------------------------------------------------------------------------------------------------

#---------------------------------------------------------------------------------------------------------------------------------------------------
# 🔒 Disclaimer, Versionsinformationen, author
# region -------------------------------------------------------------------------------------------------------------------------------------------

from datetime import datetime
release_date = datetime.today().strftime("%d.%m.%Y")
version_info = t["disclaimer_version"].format(version=VERSION, date=RELEASE_DATE, author=AUTHOR)

st.markdown("---")
st.markdown(
    f"<div style='font-size: 0.85em; color: gray; text-align: center;'>"
    f"{t['disclaimer_footer']}<br>" 
    f"{version_info}"
    "</div>",
    unsafe_allow_html=True
)
# endregion ----------------------------------------------------------------------------------------------------------------------------------------
