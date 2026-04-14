# collmex-cli — FiBu & Controlling CLI fuer Collmex

Python-CLI das [Collmex](https://www.collmex.de) (deutsche Buchhaltungssoftware) per API steuert.
Designed fuer autonomen Betrieb durch einen LLM-Agenten als CFO/Head of Finance.

**Status:** Alpha — produktiv im Einsatz bei einer deutschen GmbH (SKR03). SKR04 ist nur gemappt, nicht live getestet.

## Voraussetzungen

- Python **>= 3.11**
- Collmex-Account mit **API-Zugang** — nicht jeder Tarif beinhaltet die Data-Exchange-Schnittstelle. Minimum ist aktuell "buchhaltung basic". Details: [Collmex Tarife](https://www.collmex.de/buchhaltung.html).
- Schreibender API-Zugriff benoetigt einen separaten **API-User** (in Collmex Verwaltung -> Benutzer anlegen).
- Fuer das Web-UI-Scraping (`collmex webui`): separater **Web-User** mit Kennwort (NICHT der API-User).

## Setup

```bash
pip install -e ".[dev]"             # CLI + Dev-Abhaengigkeiten
cp .env.example .env                # Credentials eintragen
cp -r mandant/beispiel mandant/<kuerzel>   # eigenes Mandant-Profil anlegen
collmex status                      # Verbindungstest
collmex onboarding                  # Mandant einrichten
```

Credentials in `.env`:
```
COLLMEX_CUSTOMER=123456
COLLMEX_USER=apiuser
COLLMEX_PASSWORD=...
COLLMEX_WEB_USER=...       # optional, fuer Web-UI
COLLMEX_WEB_PASSWORD=...
```

### Mandant-Profil

Jeder Mandant braucht ein eigenes Profil unter `mandant/<kuerzel>/profil.md`.
Das Verzeichnis `mandant/` ist bis auf die committete Vorlage
(`mandant/beispiel/`) via `.gitignore` aus dem Repo ausgeschlossen — deine
eigenen Mandantendaten bleiben also **lokal** und werden nicht versehentlich
gepusht. Schema: siehe `mandant/beispiel/profil.md` oder `CLAUDE.md`
Abschnitt *Multi-Mandant*.

## CLI-Befehle

```
Buchen:
  buchen         Eingangsrechnung buchen (CMXLRN)
  ausgang        Ausgangsrechnung buchen (CMXUMS)
  storno         Stornobuchung erstellen

Auswertungen:
  salden         Kontensalden (ACCBAL_GET)
  buchungen      Buchungsbelege (ACCDOC_GET)
  op             Offene Posten
  bwa            Betriebswirtschaftliche Auswertung
  soll-ist       Budget vs. Ist
  dashboard      KPI-Uebersicht

Controlling & Steuern:
  ustva          USt-Voranmeldung berechnen
  liquiditaet    13-Wochen-Liquiditaetsprognose
  mahnlauf       Mahnlauf (ueberfaellige Debitoren)
  saeumige       Saeumige Kunden anzeigen
  fristen        Steuerliche Fristen
  datev-export   DATEV-Buchungsstapel exportieren

Stammdaten & API:
  abfrage        Generische Abfrage (alle ~30 GET-Satzarten)
  hilfe          API-Referenz (75 Satzarten)
  konten         SKR03 Kontenrahmen
  konto          Einzelnes Konto

System:
  status         API-Verbindungstest
  onboarding     Mandant einrichten (Kontenrahmen, Stammdaten)
  handbuch       Collmex-Handbuch nachschlagen
  version        Version anzeigen
  webui          Web-UI Daten (Mengeneinheiten, Zahlungsbedingungen, Firma)
```

## Module

```
collmex/
  api.py              Collmex API Client (CSV-over-HTTPS)
  api_reference.py    75 Satzarten mit Doku-URLs
  cli.py              CLI Entry Point (Click)
  booking.py          Buchungslogik (CMXLRN/CMXUMS)
  accounts.py         Kontenrahmen SKR03
  models.py           Dataclasses (Booking, Customer, etc.)
  validation.py       Buchungsvalidierung (Soll=Haben)
  gobd.py             GoBD-Compliance (Audit Trail)
  reports.py          Auswertungen (BWA, SuSa, OP)
  controlling.py      Controlling (Soll/Ist, Liquiditaet, KPIs)
  taxes.py            USt-Logik (UStVA)
  dunning.py          Mahnwesen
  datev.py            DATEV-Export
  deadlines.py        Steuerliche Fristen
  stammdaten.py       Generischer Stammdaten-Renderer + Handbuch-Parser
  webui.py            Web-UI Scraping
```

## Wissen

| Datei | Inhalt |
|-------|--------|
| `CLAUDE.md` | Bot-Protokoll: Rolle, Regeln, Flows, Commands |
| `wissen/routinen.md` | Taeglich/woechentlich/monatlich/jaehrlich Checklisten |
| `wissen/interpretation.md` | Entscheidungsbaeume, Spezialfaelle, Risiko |
| `wissen/skr03.md` | SKR03-Konten + Kontierungsregeln |
| `wissen/skr04.md` | SKR04-Konten + Mapping zu SKR03 |
| `wissen/collmex-webui.md` | Web-UI Scraping Details |
| `docs/docs/api/api-fields.md` | Verifizierte API-Feldstrukturen |
| `docs/docs/api/api-patterns.md` | API Gotchas und Workarounds |

## Collmex API

- CSV-over-HTTPS, Semikolon-getrennt, ISO-8859-1
- Ein Endpunkt, alles per CSV-Zeilen
- Schreiben: CMXLRN (Eingang), CMXUMS (Ausgang), CMXINV (Rechnung), CMXKND (Kunde), CMXLIF (Lieferant)
- Lesen: `collmex abfrage SATZART` — alle ~30 GET-Satzarten
- Doku: https://www.collmex.de/c.cmx?1005,1,help,api

## Tests

```bash
python -m pytest tests/ -v           # Unit-Tests (Mock-API)
python -m pytest tests/ -v -m live   # Live-Tests (echte API, braucht .env)
```

Siehe [CONTRIBUTING.md](CONTRIBUTING.md) fuer Details zum Setup einer eigenen Test-Umgebung.

## Autopilot-Prinzip

Dieses Repo ist fuer autonomen LLM-Betrieb gebaut:
1. Agent liest CLAUDE.md → kennt Rolle, Regeln, Flows
2. Arbeitet Aufgaben ab (Buchungen, Auswertungen, Checks)
3. Lernt etwas Neues → dokumentiert in `wissen/` oder `docs/`
4. Committed ins Repo → naechste Session profitiert

## Disclaimer

**Keine Steuerberatung.** Dieses Tool ist ein Automatisierungs-Werkzeug fuer Buchhalter und steuerlich Vorgebildete. Es ersetzt **keine** Steuerberatung und **keinen** Steuerberater. Die Interpretation von Belegen, USt-Saetzen, Kontierungen und Fristen liegt in der Verantwortung des Nutzers.

**GoBD / Haftung.** Der Betrieb eines FiBu-Tools unterliegt in Deutschland den GoBD-Regeln (Grundsaetze zur ordnungsmaessigen Fuehrung und Aufbewahrung von Buechern). Wer dieses Tool gegen eine produktive Collmex-Instanz einsetzt, traegt die alleinige Verantwortung fuer die Richtigkeit und Vollstaendigkeit der erzeugten Buchungen. Der Autor uebernimmt **keine Gewaehr** und **keine Haftung** fuer Fehlbuchungen, verpasste Fristen, USt-Fehler, Datenverlust oder sonstige Schaeden.

**Use at your own risk.** Erst mit einem **Test-Mandanten** gegenpruefen, bevor echte Buchungen laufen.

## Lizenz

Copyright © 2026 Christopher Helm. Alle Rechte vorbehalten.

Der Code ist zur Einsichtnahme und Evaluation einsehbar. Jede weitergehende Nutzung (kommerziell, Redistribution, Derivate) braucht eine schriftliche Genehmigung. Bei Interesse: **me@christopher-helm.com**.

Siehe [LICENSE](LICENSE) fuer den vollstaendigen Text.
