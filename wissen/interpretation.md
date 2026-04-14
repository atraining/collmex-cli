# Interpretation unscharfer Eingaben

Der Agent verhalt sich wie ein risikoaverser kaufmaennischer Leiter:
- Viel Wissen, wenig Risiko
- Lieber einmal zu viel pruefen als einmal zu wenig
- Nie raten, aber immer einen Vorschlag haben
- Vor jeder Aktion den Ist-Zustand im System ansehen

---

## Grundprinzip: Erst schauen, dann handeln

**VOR jeder Buchung oder Aenderung:**

1. **Systemzustand lesen**
   - OPEN_ITEMS_GET → Was ist offen?
   - ACCBAL_GET → Wie stehen die Konten?
   - CUSTOMER_GET / VENDOR_GET → Existiert die Person schon?
   - ACCDOC_GET → Was wurde schon gebucht?

2. **Kontext aufbauen**
   - Wer ist der Geschaeftspartner? (Suche in Stammdaten)
   - Gibt es offene Posten? (ggf. Verrechnung statt Neubuchung)
   - Passt der Zeitraum? (Periodengerecht?)
   - Gibt es aehnliche fruehe Buchungen? (Muster erkennen)

3. **Vorschlag machen mit Begruendung**
   - "Ich wuerde Konto X nehmen, weil..."
   - "Es gibt bereits eine offene Rechnung von diesem Lieferanten..."
   - "Achtung: USt-IdNr fehlt beim Kunden, §13b pruefen"

4. **Nur buchen wenn sicher** — im Zweifel nachfragen

---

## Szenarien: Vage Eingabe → Konkreter Vorschlag

### "Buch die Rechnung vom Designbuero"

```
1. Lieferant suchen:
   → VENDOR_GET durchsuchen nach "Design"
   → 1 Treffer: verwenden
   → 0 Treffer: "Kein Lieferant mit 'Design' gefunden. Meinst du...?"
   → 2+ Treffer: "Ich habe mehrere Lieferanten gefunden: [Liste]. Welcher?"

2. Aufwandskonto ableiten:
   → Lieferantenstamm pruefen (CMXLIF Idx 35)
   → Wenn gesetzt: verwenden + bestaetigen
   → Wenn leer: "Welches Aufwandskonto? Vorschlag: 4900 (Fremdleistungen)"
   → NIEMALS Default 3200 blind verwenden!

3. Betrag:
   → "Wie hoch ist der Nettobetrag?"
   → NIEMALS einen Betrag raten

4. USt pruefen:
   → Lieferant DE → 19% VSt (Standard)
   → Lieferant EU mit USt-IdNr → §13b Reverse Charge
   → Lieferant Drittland → keine VSt, Einfuhrumsatzsteuer
   → Im Zweifel: OHNE VSt buchen und nachfragen

5. Vor dem Buchen:
   → "Eingangsrechnung: Lieferant 70001 (Kreativbuero), 2.800 EUR netto,
      Konto 4900, 19% VSt. Rechnungsnummer?"
   → Belegnummer ist PFLICHT (GoBD)
```

### "Schreib eine Rechnung an den Baecker"

```
1. Kunde suchen:
   → CUSTOMER_GET durchsuchen nach "Baeck"
   → Treffer: Kunde 10003 (Baeckerei Sonnenkorn GmbH)

2. Offene Auftraege pruefen:
   → SALES_ORDER_GET fuer Kunde 10003
   → Wenn offener Auftrag vorhanden: "Es gibt Auftrag #8 mit 3 Positionen.
     Soll die Rechnung daraus erstellt werden?"
   → Wenn kein Auftrag: "Welche Leistung soll berechnet werden?"

3. Produkte vorschlagen:
   → PRODUCT_GET — bekannte Produkte auflisten
   → "Unsere Produkte: WEB-DESIGN (3500), SEO-SETUP (1200), CONTENT-PKT (800)"

4. Vor dem Erstellen:
   → "Rechnung fuer Baeckerei Sonnenkorn GmbH:
      Pos 1: WEB-DESIGN 1x 3.500,00
      Pos 2: SEO-SETUP 1x 1.200,00
      Netto: 4.700,00 + 893,00 USt = 5.593,00 brutto
      Aus Auftrag #8. Korrekt?"
```

### "Ist alles bezahlt?"

```
1. Offene Posten komplett abrufen:
   → OPEN_ITEMS_GET fuer aktuelles Jahr

2. Aufteilen in:
   → Debitoren (positive Betraege): "X Kunden schulden uns Y EUR"
   → Kreditoren (negative Betraege): "Wir schulden Z Lieferanten W EUR"
   → Ueberfaellige separat markieren

3. Bericht:
   → "3 offene Debitoren-Posten (12.400 EUR), davon 1 ueberfaellig seit 14 Tagen:
      - Kunde 10001: RE #3, 11.900 EUR, faellig 03.04.2026
      - Kunde 10003: RE #5, 6.545 EUR, faellig 11.04.2026 [noch nicht faellig]
      2 offene Kreditoren-Posten (-3.570 EUR):
      - Lieferant 70001: PC-2026-002, -3.332 EUR, faellig 31.03.2026"
```

### "Stimmen die Konten?"

```
1. Kontenabstimmung durchfuehren (→ Routine M3):
   → Bank (1200) vs. erwarteter Saldo
   → Debitorensumme (OPEN_ITEMS positiv) vs. Konto 1400
   → Kreditorensumme (OPEN_ITEMS negativ) vs. Konto 1600
   → Verrechnungskonten (1590, 1360) auf Null pruefen
   → USt-Konten gegenseitig abstimmen

2. Abweichungen melden:
   → "Kontenabstimmung Maerz 2026:
      Bank 1200: 12.345,00 EUR [Kontoauszug pruefen]
      Debitoren: OP-Summe 18.445 EUR, Konto 1400: 18.445 EUR ✓
      Kreditoren: OP-Summe -3.332 EUR, Konto 1600: -3.570 EUR ✗ DIFFERENZ 238 EUR
      Verrechnungskonto 1590: 0,00 EUR ✓
      → Differenz Kreditoren: Vermutlich alte Buchung TEST-ER-002 (238 EUR) ohne OP-Zuordnung"
```

### "Mach mal die USt fertig"

```
1. Zeitraum bestimmen:
   → Aktueller Monat oder letzter Monat?
   → "USt-Voranmeldung fuer welchen Monat? Vorschlag: Februar 2026
      (Frist: 10.03.2026 bzw. 10.04. mit Dauerfrist)"

2. Konten auslesen:
   → ACCBAL_GET fuer 1775 (USt 19%), 1770 (USt 7%)
   → ACCBAL_GET fuer 1576 (VSt 19%), 1571 (VSt 7%)
   → ACCBAL_GET fuer 1577/1787 (§13b)

3. Berechnung:
   → "USt-Voranmeldung Februar 2026:
      USt 19%: 1.900,00 EUR (Konto 1775)
      USt 7%: 0,00 EUR (Konto 1770)
      VSt 19%: -532,00 EUR (Konto 1576)
      VSt 7%: 0,00 EUR (Konto 1571)
      ─────────────────
      Zahllast: 1.368,00 EUR"

4. Plausibilitaets-Check:
   → Zahllast vs. Vormonat vergleichen
   → Grosse Abweichungen erklaeren
   → "Zahllast 30% hoeher als Vormonat — Ursache: Rechnung #5 (5.500 netto)"
```

### "Wir haben was bei Amazon bestellt, 50 Euro"

```
1. Kategorie bestimmen:
   → "Was wurde bestellt? Bueromaterial, Software, Hardware?"
   → Konto ableiten:
     - Bueromaterial → 4930 (Buero-/Schreibwaren)
     - Software-Abo → 4964 (EDV-Kosten, Nutzungsentgelte)
     - Hardware <800 netto → 4855 (GWG sofort) oder 4830 (Aufwand)
     - Hardware >800 netto → Anlage 0027/0200ff + AfA

2. Lieferant:
   → Amazon existiert als Lieferant?
   → Wenn nicht: anlegen oder auf Sammelkonto 1600 buchen
   → "Amazon als Lieferant anlegen? Oder Direktbuchung ohne Personenkonto?"

3. USt:
   → Amazon DE → 19% VSt Standard
   → Amazon EU (Luxemburg-Rechnung) → USt-IdNr pruefen
   → "Rechnung von Amazon EU Services (LU)? Dann §13b pruefen!"

4. Betrag:
   → "50 EUR — brutto oder netto?"
   → Bei brutto: 50 / 1.19 = 42,02 netto + 7,98 USt
   → "Eingangsrechnung: Amazon, 42,02 netto, Konto 4930 (Bueromaterial),
      7,98 VSt. Rechnungsnummer von Amazon?"
```

### "Der Kunde hat zu viel bezahlt"

```
1. Kunde identifizieren:
   → "Welcher Kunde?"
   → Oder aus Kontext ableiten (letzter besprochener Kunde)

2. Ist-Zustand pruefen:
   → OPEN_ITEMS_GET fuer diesen Kunden
   → Haben-Saldo bei Debitor = Ueberzahlung

3. Optionen vorschlagen:
   → "Kunde 10001 hat 200 EUR zu viel bezahlt. Optionen:
      a) Rueckerstattung: Bank 1200 an Debitor 10001 (200 EUR)
      b) Verrechnung mit naechster Rechnung (Guthaben stehen lassen)
      c) Gutschrift erstellen
      Was bevorzugst du?"
```

---

## Risikovermeidung: Was der Agent NIEMALS tut

1. **Nie einen Betrag raten** — immer nachfragen
2. **Nie ohne Belegnummer buchen** — GoBD-Pflicht
3. **Nie USt-Satz raten** — bei Unsicherheit OHNE VSt und nachfragen
4. **Nie loeschen** — nur Stornobuchungen (GoBD)
5. **Nie auf ein Konto buchen das er nicht kennt** — erst pruefen ob es existiert (ACCBAL_GET)
6. **Nie eine Buchung aendern** — nur Storno + Neubuchung
7. **Nie Personenkonten als Gegenkonto in CMXLRN** — nur Sachkonten (1600)
8. **Nie Default-Konten blind akzeptieren** — CMXLRN Default 3200 ist fast immer falsch
9. **Nie Produkt/Leistung raten** — wenn der User nicht sagt WAS verkauft/bestellt
   wurde: NACHFRAGEN! Nicht einfach ein vorhandenes Produkt nehmen.
   "Was wurde bestellt/geliefert?" ist immer die erste Frage.

## Risikobewertung vor jeder Aktion

| Aktion | Risiko | Verhalten |
|--------|--------|-----------|
| Stammdaten lesen | Kein | Frei ausfuehren |
| Salden/OP abfragen | Kein | Frei ausfuehren |
| Kunde/Lieferant anlegen | Niedrig | Vorschlag zeigen, dann ausfuehren |
| Eingangsrechnung buchen | Mittel | Vorschlag mit Konten zeigen, Bestaetigung |
| Ausgangsrechnung erstellen | Mittel | Positionen + Betraege bestaetigen lassen |
| Rechnung versenden | Hoch | Immer explizite Freigabe |
| Stornobuchung | Hoch | Grund dokumentieren, Bestaetigung |
| Zahlungslauf | Hoch | Immer explizite Freigabe |

---

## Selbstpruefung nach jeder Buchung

Nach jeder Buchung fuehrt der Agent automatisch durch:

```
1. ACCDOC_GET → Buchung vorhanden?
2. Soll = Haben? (Betraege pruefen)
3. Richtiges Konto? (vs. Erwartung)
4. Richtiger Zeitraum? (Periode pruefen)
5. OPEN_ITEMS_GET → OP korrekt angelegt/aufgeloest?
```

Wenn etwas nicht stimmt: SOFORT melden, nicht ignorieren.

---

## Kontextgedaechtnis innerhalb einer Session

Der Agent merkt sich waehrend einer Session:
- Welche Kunden/Lieferanten besprochen wurden
- Welche Buchungen gemacht wurden
- Welche offenen Fragen noch bestehen
- Welche Widersprueche aufgefallen sind

Am Ende einer Session mit Buchungen:
→ Zusammenfassung erstellen
→ Offene Punkte dokumentieren
→ Widersprueche in `mandant/berichte/widersprueche.md` schreiben
→ Committen

---

## Hinweis: Personenkonten vs. Kontenrahmen

Personenkonten (Debitoren 10000-69999, Kreditoren 70000+) sind NICHT Teil
von SKR03/SKR04 — sie sind eine Software-Konvention (Collmex, DATEV, etc.).
Beide Kontenrahmen nutzen denselben Personenkonten-Bereich.

SKR03 vs. SKR04 betrifft nur die Sachkonten (0000-9999).
Die Entscheidungsbaeume unten verwenden SKR03-Konten.
Bei einem SKR04-Mandanten muessen die Kontonummern angepasst werden.

## Kontenrahmen-Erkennung (beim Forken / Onboarding)

Beim ersten Kontakt mit einem neuen Mandanten: Kontenrahmen erkennen!

**Schnelltest:** ACCBAL_GET fuer typische Konten:

| Konto | SKR03 | SKR04 |
|-------|-------|-------|
| 1200 | Bank | Bank (gleich!) |
| 1400 | Forderungen aus LuL | Forderungen aus LuL (gleich!) |
| 1600 | Verbindlichkeiten aus LuL | Verbindlichkeiten aus LuL (gleich!) |
| 4400 | **existiert nicht** | Erloese |
| 8400 | Erloese 19% | **existiert nicht** |
| 4900 | Sonstige betriebl. Aufwand | **existiert nicht** |
| 6300 | **existiert nicht** | Sonstige betriebl. Aufwand |

**Entscheidung:**
```
ACCBAL_GET;1;{jahr};0;8400
  → Konto existiert? → SKR03
ACCBAL_GET;1;{jahr};0;4400
  → Konto existiert? → SKR04
Beide existieren? → Individuell angepasst, NACHFRAGEN
Keines existiert? → Noch keine Buchungen, in Collmex-Einstellungen pruefen
```

**WICHTIG:** Kontenrahmen in `mandant/stammdaten.md` dokumentieren.
Alle Entscheidungsbaeume in diesem Dokument verwenden SKR03.
Fuer SKR04 braucht es eine Mapping-Tabelle (→ `wissen/skr04.md`).

## Entscheidungsbaum: Welches Konto?

### Eingangsrechnung — Aufwandskonto bestimmen

```
Lieferantenstamm hat Aufwandskonto gesetzt?
  → JA: Verwenden (aber dem User zeigen)
  → NEIN:
    Was wurde geliefert/geleistet?
    ├── Bueromaterial          → 4930
    ├── Porto/Versand          → 4910
    ├── Telefon/Internet       → 4920
    ├── Software-Abo           → 4964
    ├── Fremdleistungen/Agentur→ 4900
    ├── Miete                  → 4210
    ├── Versicherungen         → 4360
    ├── Fahrzeugkosten         → 4500-4580
    ├── Reisekosten            → 4660-4670
    ├── Bewirtung (70%)        → 4650 + 4654 (30% nicht abzugsf.)
    ├── Fortbildung            → 4945
    ├── Rechts-/Beratungskosten→ 4950
    ├── Buchfuehrungskosten    → 4955
    ├── Werbekosten            → 4600
    ├── Geschenke (≤50 EUR)    → 4630
    ├── Geschenke (>50 EUR)    → 4635 (nicht abzugsfaehig!)
    ├── Reparaturen            → 4800
    ├── Betriebsbedarf         → 4980
    └── Unklar                 → NACHFRAGEN, nicht raten
```

### Ausgangsrechnung — Erloeskonto bestimmen

```
Was wurde verkauft/geleistet?
├── Waren 19%               → 8400 (Erloese 19% USt)
├── Waren 7%                → 8300 (Erloese 7% USt)
├── Dienstleistungen 19%    → 8400
├── Steuerfreie Lieferung EU→ 8125 (igL steuerfrei)
├── Sonstige Leistung EU    → 8336 (§13b)
├── Export Drittland        → 8120 (steuerfreie Ausfuhr)
└── Unklar                  → NACHFRAGEN
```

### USt-Satz bestimmen

```
Wer ist der Empfaenger?
├── Inland (DE)
│   ├── Unternehmer          → 19% (Standard) oder 7% (ermaessigt)
│   ├── Privatperson         → 19% / 7%
│   └── Kleinunternehmer §19 → 0% (wenn WIR Kleinunternehmer sind)
├── EU (mit USt-IdNr)
│   ├── Ware                 → 0% (igL, §4 Nr. 1b UStG)
│   └── Dienstleistung       → 0% (§13b, Reverse Charge)
├── EU (ohne USt-IdNr / Privatperson)
│   ├── Ware                 → DE-Steuersatz (19%/7%)
│   └── Dienstleistung       → DE-Steuersatz (Ausnahmen: §3a UStG)
└── Drittland
    ├── Ware                 → 0% (Ausfuhrlieferung, Nachweis!)
    └── Dienstleistung       → 0% (§3a Abs. 2, B2B) oder DE-USt (B2C)
```

---

## Spezialfaelle und Gotchas

### §14 UStG — Pflichtangaben Rechnung

Jede Eingangsrechnung VOR dem VSt-Abzug pruefen:

1. Vollstaendiger Name + Anschrift Leistungserbringer
2. Vollstaendiger Name + Anschrift Leistungsempfaenger
3. Steuernummer ODER USt-IdNr des Leistungserbringers
4. Fortlaufende Rechnungsnummer
5. Ausstellungsdatum
6. Leistungszeitpunkt oder -zeitraum
7. Menge + Art der Leistung
8. Nettobetrag + USt-Satz + USt-Betrag + Bruttobetrag
9. Bei Steuerbefreiung: Hinweis auf Befreiungsgrund

**Fehlende Angaben:** VSt-Abzug NICHT moeglich → korrigierte Rechnung anfordern.
**Kleinbetragsrechnung (≤250 EUR brutto):** Nur Nr. 1, 5, 7, 8 erforderlich.

### Gutschrift vs. Stornorechnung

- **Stornorechnung (Rechnungskorrektur):** Korrigiert eine fehlerhafte Rechnung.
  → Negativer Betrag, Bezug auf Original-Rechnungsnummer.
  → In Collmex: `collmex storno`
- **Kaufmaennische Gutschrift:** Nachlass, Bonus, Rueckgabe.
  → Eigenes Dokument, aber Bezug auf Lieferung/Auftrag.
- **Gutschrift i.S.d. UStG (§14 Abs. 2 S. 2):** Rechnung durch Leistungsempfaenger.
  → Selten, nur bei Vereinbarung. NICHT mit Stornorechnung verwechseln!

### GWG — Geringwertige Wirtschaftsgueter

```
Nettobetrag der Anschaffung:
├── ≤ 250 EUR      → Sofortaufwand, kein Anlagespiegel (4855 oder Sachkonto)
├── 250,01-800 EUR → GWG, Sofortabschreibung moeglich (4855 + Anlage)
├── 800,01-1000 EUR→ Sammelposten (0485) 5 Jahre AfA ODER Einzelanlage
└── > 1000 EUR     → Anlage aktivieren, planmaessige AfA
```

**Achtung:** GWG-Grenze immer NETTO (ohne USt). 800 EUR netto = 952 EUR brutto bei 19%.

### Bewirtungsbeleg (§4 Abs. 5 Nr. 2 EStG)

```
Bewirtungsaufwand gesamt:
├── 70% betrieblich abzugsfaehig → 4650 (Bewirtungskosten)
└── 30% nicht abzugsfaehig       → 4654 (Nicht abzugsfaehige Bewirtung)
VSt: Auf den GESAMTEN Betrag abziehbar (100%)!
```

Pflichtangaben auf dem Beleg:
- Ort, Datum, Teilnehmer, Anlass
- Eigenbeleg bei auslaendischen Restaurants

### Skonto — USt-Korrektur nicht vergessen

```
Rechnung: 1.000 netto + 190 USt = 1.190 brutto
Skonto 2%: 23,80 EUR Abzug
→ Zahlung: 1.166,20 EUR

Buchung Zahlungseingang mit Skonto:
  Soll 1200 (Bank)          1.166,20
  Soll 8736 (Skonto)           20,00  (Netto-Skonto)
  Soll 1775 (USt-Korrektur)     3,80  (19% auf Skonto)
  Haben Debitor 10001       1.190,00
```

**Haeufiger Fehler:** Skonto als Nettobetrag buchen, USt-Korrektur vergessen.

### E-Rechnung (ab 01.01.2025)

```
Pflicht zur Annahme: Ab 01.01.2025 (alle B2B im Inland)
Pflicht zur Ausstellung:
├── Ab 01.01.2027: Umsatz Vorjahr > 800.000 EUR
└── Ab 01.01.2028: Alle Unternehmer

Formate: XRechnung, ZUGFeRD (ab Version 2.0.1)
```

Collmex kann E-Rechnungen erstellen: `collmex handbuch e-rechnung`

### Innergemeinschaftliche Lieferung (igL) vs. Erwerb (igE)

```
WIR liefern an EU-Unternehmer (mit USt-IdNr):
→ igL: Steuerfrei (§4 Nr. 1b UStG)
→ Konto 8125, Meldung in ZM Pflicht
→ Nachweis: Gelangensbestaetigung

WIR kaufen von EU-Unternehmer (mit USt-IdNr):
→ igE: Erwerbs-USt schulden WIR
→ USt auf 1774, VSt auf 1574
→ Nicht §13b! Eigener Mechanismus
```

### Drittland — Einfuhrumsatzsteuer

```
Import aus Drittland (z.B. USA, China):
→ Zoll + EUSt werden vom Zoll erhoben
→ EUSt ist als VSt abziehbar (Konto 1588)
→ Nachweis: Zollbescheid

Export in Drittland:
→ Steuerfrei (Ausfuhrlieferung)
→ Konto 8120
→ Nachweis: Ausfuhrbestaetigung (ATLAS)
```

### Betriebspruefungs-Hotspots

Was das Finanzamt besonders genau prueft:

1. **Bewirtungskosten:** 70/30-Aufteilung, Angaben auf Beleg
2. **Geschenke:** Grenze 50 EUR (Konto 4630 vs. 4635)
3. **Privatanteile:** Kfz (1% oder Fahrtenbuch), Telefon, Bewirtung
4. **Sachkonten vs. Personenkonten:** Forderungen/Verbindlichkeiten immer ueber Personenkonten
5. **Periodenabgrenzung:** Leistungsdatum = Buchungsdatum, nicht Rechnungsdatum
6. **Kassenbuchfuehrung:** Lueckenlos, keine negativen Kassenbestaende
7. **GoBD:** Unveraenderbarkeit, Nachvollziehbarkeit, Vollstaendigkeit

### Zusammenfassende Meldung (ZM)

```
Pflicht bei: igL + sonstige Leistungen an EU-Unternehmer (§13b)
Frist: 25. des Folgemonats nach Quartalsende
       (monatlich bei igL > 50.000 EUR/Quartal)
Inhalt: USt-IdNr des Empfaengers + Bemessungsgrundlage
Sanktion: Bußgeld bis 5.000 EUR bei Versaeumnis
```
