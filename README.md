# WiBer – Webtool zur Bewertung von Kältemaschinen

WiBer ist ein Streamlit-basiertes Tool zur Analyse von Kälteleistung, Energieeinsparung und wetterabhängigen Betriebsbedingungen.

## 🔧 Funktionen

- Eingabe von Kühlbedarf, Lastprofil und Temperaturdifferenz
- Automatischer Abruf von Außentemperaturdaten (DWD, über wetterdienst)
- Zählung von Stunden in Temperaturbereichen
- Vergleich mit Effizienzgrenzen
- Diagramm + Auswertung
- Sprachauswahl und Übersetzungsdateien Englisch, Französisch und Spanisch hinzugefügt
- Fehler in Sprachdateien behoben
- Übersetzung vervollständigt
- Kälteleistung und COP nach Temperaturtripel berechnen
- überarbeitetes Layout
- Jahresdauerlinie mit Temperaturbereichen

## 🚀 Start

```bash
pip install -r requirements.txt
streamlit run streamlit_app_v0-11a.py

## 📦 Abhängigkeiten

Dieses Projekt basiert auf folgenden zentralen Bibliotheken (min Version):

# Core
streamlit>=1.30
pandas>=2.0
numpy>=1.24.0
# Plotting
altair>=5.0.0
# Daten & Verarbeitung
polars>=0.20
sqlite3  # in Python enthalten, keine Installation nötig
openpyxl>=3.1.0  # für Excel (.xlsx)
# PDF-Export
fpdf>=1.7.2
# Verschlüsselung
cryptography>=42.0.0
# Wetterdaten
wetterdienst>=0.107.0
# Geodaten
geopy>=2.3.0
# JSON mit Kommentaren
json5>=0.9.14
# Interpolation
scipy>=1.10.0
matplotlib>=3.7

Die vollständige Liste ist in `requirements.txt` enthalten.
