# collmex-cli — Buchhaltung aus dem Terminal

**Für Buchhalter und Collmex-Nutzer, die die Klickerei in der Weboberfläche satt haben.**

`collmex-cli` ersetzt die verschachtelten Collmex-Menüs durch kurze
Kommandos. Eine Eingangsrechnung buchst du in einer Zeile statt in sieben
Klicks. Und weil jeder Befehl dokumentiert ist, kann ein LLM-Agent (z.B.
Claude Code) die Buchhaltung autonom führen — Beleg lesen, richtig
kontieren, Soll=Haben prüfen, buchen, protokollieren.

```console
$ collmex buchen "Büromaterial Papier + Toner" \
    --betrag 89,90 --lieferant 70012 \
    --konto 4400 --ust 19 --rechnungsnr RE-2026-042

✓ Eingangsrechnung gebucht
  4400 S   89,90   Büromaterial
  1576 S   17,08   Abziehbare Vorsteuer 19%
  70012 H 106,98   Verbindlichkeit
  Beleg: RE-2026-042   Periode: 04/2026
```

```console
$ collmex ustva --monat 04 --jahr 2026

USt-Voranmeldung 04/2026
  Steuerpflichtige Umsätze 19%    12.450,00    → USt  2.365,50
  Steuerpflichtige Umsätze 7%        880,00    → USt     61,60
  Vorsteuer abziehbar                           -1.742,80
  ────────────────────────────────────────────────────────
  Zahllast                                         684,30
  Abgabefrist: 10.05.2026 (Dauerfristverl.: 10.06.2026)
```

**Status:** Alpha — produktiv bei einer deutschen GmbH (SKR03).
SKR04 ist nur gemappt, nicht live getestet. Tests: 583 grün.

---

## Für wen ist das?

- Buchhalter, Steuerfachangestellte und GmbH-Inhaber, die **Collmex schon nutzen**
- Menschen, die **FiBu-Grundlagen** beherrschen (Soll/Haben, SKR03/04, USt-Sätze, §13b, periodengerecht)
- Alle, die die Web-UI von Collmex — wie [viele Reviews](https://www.capterra.com.de/software/205535/collmex) beschreiben — **altmodisch und klickintensiv** finden
- Devs und Agents, die Collmex als Buchhaltungs-Backend für ein eigenes Tool / einen LLM-Agenten verwenden wollen

**Für wen ist das nicht?**

- Wer keine Buchhaltungs-Grundlagen hat — das Tool bucht, was du ihm sagst, nicht was richtig ist
- Wer lieber klickt als tippt
- Wer ein GUI braucht (gibt es nicht und wird es auch nicht geben)
- Wer garantierten Support erwartet — es gibt keinen (siehe *Lizenz*)

## Was es besser macht als die Web-UI

| Schmerzpunkt in Collmex | Was `collmex-cli` anders macht |
|------------------------|-------------------------------|
| Menüdschungel, unklare Optionen | Ein Befehl pro Aktion, `collmex hilfe SATZART` zeigt dokumentiert alle Felder |
| Nicht mobiloptimiert | Läuft in jedem Terminal — inkl. SSH vom Handy |
| Hoher manueller Aufwand | Buchungen werden validiert (Soll=Haben, Konto existiert, USt-Satz gültig), bevor sie rausgehen |
| Mehrere Mandanten = Nutzer wechseln | `.env` umschalten, fertig |
| CSV-API existiert, aber du musst die Skripte selbst schreiben | Genau diese Skripte liegen hier fertig — Rechnung, Storno, Mahnung, USt-Voranmeldung, DATEV-Export |
| Keine Audit-Historie pro Aktion | Eingebauter GoBD-konformer Audit-Trail (`gobd.py`) |

Das Tool **löst nicht**:
- Collmex' schwache OCR — Belegdaten tippst du selbst (oder ein LLM liest sie für dich)
- Collmex' Tarif-Beschränkungen — manche API-Satzarten sind erst ab "buchhaltung pro" freigeschaltet
- Steuerliche Entscheidungen — siehe Disclaimer

## Was es kann (im Überblick)

**Buchen.** Eingangs-/Ausgangsrechnungen, Stornos, Split-Buchungen (z.B. Bewirtung 70/30), §13b Reverse Charge. Immer über Personenkonten (Debitor/Kreditor) — nie direkt auf Bank.

**Auswertungen.** Kontensalden, offene Posten, BWA, SuSa, Soll-Ist-Vergleich, KPI-Dashboard.

**Controlling & Steuern.** USt-Voranmeldung, 13-Wochen-Liquiditätsprognose, Mahnlauf, Fälligkeiten, DATEV-Buchungsstapel-Export für den Steuerberater.

**Stammdaten.** Kunden/Lieferanten anlegen und suchen, generische Abfrage für alle ~30 Lese-Satzarten der Collmex-API, SKR03-Kontenrahmen eingebaut, Handbuch-Lookup.

**LLM-Autopilot.** `CLAUDE.md` und `wissen/*.md` sind so geschrieben, dass Claude Code oder ein vergleichbarer Agent ohne Einarbeitung loslegen kann. Rollen, Regeln, Flows (Eingang / Ausgang / Storno / Zahlungseingang / Monatsabschluss), Entscheidungsbäume für Kontierung und USt.

---

## Voraussetzungen

- **Python >= 3.11**
- **Collmex-Account mit API-Zugang** — nicht jeder Tarif hat die
  Data-Exchange-Schnittstelle. Minimum aktuell `buchhaltung basic`. Siehe
  [Collmex-Tarife](https://www.collmex.de/buchhaltung.html).
- **Separater API-User** in Collmex (Verwaltung → Benutzer). Nicht der
  normale Web-Login — der API-User ist ein eigener technischer Account.
- **Optional für Web-UI-Scraping** (`collmex webui`): separater Web-User,
  nicht der API-User.

## Setup

```bash
pip install -e ".[dev]"                     # CLI + Dev-Abhängigkeiten
cp .env.example .env                        # Credentials eintragen
cp -r mandant/beispiel mandant/<kuerzel>    # eigenes Mandant-Profil anlegen
collmex status                              # Verbindungstest
collmex onboarding                          # Mandant einrichten
```

`.env` enthält:

```
COLLMEX_CUSTOMER=123456
COLLMEX_USER=apiuser
COLLMEX_PASSWORD=...
COLLMEX_WEB_USER=...       # optional, für Web-UI
COLLMEX_WEB_PASSWORD=...
```

### Mandant-Profil

Jeder Mandant braucht ein eigenes Profil unter `mandant/<kuerzel>/profil.md`.
Das Verzeichnis `mandant/` ist bis auf die committete Vorlage
(`mandant/beispiel/`) via `.gitignore` aus dem Repo ausgeschlossen — deine
eigenen Mandantendaten bleiben **lokal** und werden nicht versehentlich
gepusht. Schema: siehe `mandant/beispiel/profil.md` oder `CLAUDE.md` →
*Multi-Mandant*.

## Typische Workflows

### Eingangsrechnung buchen

```bash
# 1. Lieferant suchen
collmex abfrage VENDOR_GET --suche "Deutsche Telekom"

# 2. Buchen (Lieferant ist Pflicht — nie direkt auf Bank)
collmex buchen "Telefon Q2" --betrag 85,00 \
    --lieferant 70034 --konto 4420 --ust 19 --rechnungsnr 2026-04-0815

# 3. Offene Posten prüfen
collmex op
```

### USt-Voranmeldung erstellen

```bash
collmex ustva --monat 04 --jahr 2026
collmex fristen             # nächste Abgabetermine
```

### Monatsabschluss

```bash
collmex salden --monat 04
collmex bwa --monat 04
collmex soll-ist --monat 04
collmex datev-export --monat 04   # Stapel für den StB
```

### Komplette Befehlsliste

```
Buchen:        buchen | ausgang | storno
Auswertungen:  salden | buchungen | op | bwa | soll-ist | dashboard
Steuern:       ustva | liquiditaet | mahnlauf | saeumige | fristen | datev-export
Stammdaten:    abfrage | hilfe | konten | konto
System:        status | onboarding | handbuch | version | webui
```

`collmex --help` zeigt Details zu jedem Befehl, `collmex hilfe SATZART` zu jeder API-Satzart.

---

## LLM-Autopilot

Dieses Repo ist für autonomen LLM-Betrieb gebaut:

1. **Agent liest `CLAUDE.md`** → kennt Rolle (CFO / Head of Accounting), Regeln (Soll=Haben, keine Löschungen, immer Personenkonten, nie raten) und Flows (Eingang, Ausgang, Storno, Zahlungseingang, Monatsabschluss)
2. **Arbeitet Aufgaben ab** — Buchungen, Auswertungen, Monatsabschluss, Mahnlauf
3. **Lernt Neues** und dokumentiert es in `wissen/` oder `docs/`
4. **Committet** ins Repo → die nächste Session profitiert

In Kombination mit Claude Code läuft das so: du sagst „Buch die Telekom-Rechnung, 85 Euro netto", und der Agent prüft, ob der Lieferant schon existiert, sucht das Konto raus, fragt bei Unklarheit nach, bucht, prüft Soll=Haben und zeigt dir die Buchung zur Freigabe.

## Projektstruktur

```
collmex/
  api.py              Collmex API Client (CSV-over-HTTPS)
  api_reference.py    75 Satzarten mit Doku-URLs
  cli.py              CLI Entry Point (Click)
  booking.py          Buchungslogik (CMXLRN/CMXUMS)
  accounts.py         SKR03 Kontenrahmen (kuratiert)
  models.py           Dataclasses (Booking, Customer, etc.)
  validation.py       Buchungsvalidierung (Soll=Haben)
  gobd.py             GoBD-Audit-Trail
  reports.py          Auswertungen (BWA, SuSa, OP)
  controlling.py      Soll/Ist, Liquidität, KPIs
  taxes.py            USt-Logik (UStVA)
  dunning.py          Mahnwesen
  datev.py            DATEV-Export
  deadlines.py        Steuerliche Fristen
  stammdaten.py       Stammdaten-Renderer + Handbuch-Parser
  webui.py            Web-UI Scraping
```

## Wissensbasis

Das Repo bringt nicht nur Code mit, sondern auch das FiBu-Wissen, das der LLM-Agent braucht:

| Datei | Inhalt |
|-------|--------|
| `CLAUDE.md` | Bot-Protokoll: Rolle, Regeln, Flows, Commands |
| `wissen/routinen.md` | Checklisten Tag/Woche/Monat/Jahr mit Konten |
| `wissen/interpretation.md` | Entscheidungsbäume für Konto, USt, Risiko |
| `wissen/skr03.md` | SKR03-Konten + Kontierungsregeln (Bewirtung, §13b, GWG) |
| `wissen/skr04.md` | SKR04-Konten + Mapping zu SKR03 |
| `wissen/collmex-webui.md` | Web-UI Scraping Details |
| `docs/docs/api/api-fields.md` | Verifizierte Collmex-API-Feldstrukturen |
| `docs/docs/api/api-patterns.md` | API-Gotchas und Workarounds |

## Collmex API — Fakten

- CSV-over-HTTPS, Semikolon-getrennt, ISO-8859-1
- Ein einziger Endpunkt, alle Aktionen als CSV-Zeilen
- Schreiben: `CMXLRN` (Eingang), `CMXUMS` (Ausgang), `CMXINV` (Rechnung), `CMXKND` (Kunde), `CMXLIF` (Lieferant)
- Lesen: `collmex abfrage SATZART` — alle ~30 GET-Satzarten
- Offizielle Doku: <https://www.collmex.de/c.cmx?1005,1,help,api>

## Tests

```bash
python -m pytest tests/ -v           # Unit-Tests (Mock-API)
python -m pytest tests/ -v -m live   # Live-Tests (echte API, braucht .env)
```

Siehe [CONTRIBUTING.md](CONTRIBUTING.md) für Details zum Setup einer eigenen Test-Umgebung, inkl. wie man bei Collmex einen Test-Mandanten anlegt.

## Disclaimer

**Keine Steuerberatung.** Dieses Tool ist ein Automatisierungs-Werkzeug für Buchhalter und steuerlich Vorgebildete. Es ersetzt **keine** Steuerberatung und **keinen** Steuerberater. Die Interpretation von Belegen, USt-Sätzen, Kontierungen und Fristen liegt in der Verantwortung des Nutzers.

**GoBD / Haftung.** Der Betrieb eines FiBu-Tools unterliegt in Deutschland den GoBD. Wer dieses Tool gegen eine produktive Collmex-Instanz einsetzt, trägt die alleinige Verantwortung für die Richtigkeit und Vollständigkeit der erzeugten Buchungen. Der Autor übernimmt **keine Gewähr** und **keine Haftung** für Fehlbuchungen, verpasste Fristen, USt-Fehler, Datenverlust oder sonstige Schäden.

**Use at your own risk.** Erst mit einem **Test-Mandanten** gegenprüfen, bevor echte Buchungen laufen.

## Lizenz

Copyright © 2026 Christopher Helm. Alle Rechte vorbehalten.

Der Code ist zur Einsichtnahme und Evaluation einsehbar. Jede weitergehende Nutzung (kommerziell, Redistribution, Derivate) braucht eine schriftliche Genehmigung. Bei Interesse: **me@christopher-helm.com**.

Siehe [LICENSE](LICENSE) für den vollständigen Text.
