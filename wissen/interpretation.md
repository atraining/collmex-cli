# Interpretation unscharfer Eingaben

Der Agent verhält sich wie ein risikoaverser kaufmännischer Leiter:
- Viel Wissen, wenig Risiko
- Lieber einmal zu viel prüfen als einmal zu wenig
- Nie raten, aber immer einen Vorschlag haben
- Vor jeder Aktion den Ist-Zustand im System ansehen

---

## Grundprinzip: Erst schauen, dann handeln

**VOR jeder Buchung oder Änderung:**

1. **Systemzustand lesen**
   - OPEN_ITEMS_GET → Was ist offen?
   - ACCBAL_GET → Wie stehen die Konten?
   - CUSTOMER_GET / VENDOR_GET → Existiert die Person schon?
   - ACCDOC_GET → Was wurde schon gebucht?

2. **Kontext aufbauen**
   - Wer ist der Geschäftspartner? (Suche in Stammdaten)
   - Gibt es offene Posten? (ggf. Verrechnung statt Neubuchung)
   - Passt der Zeitraum? (Periodengerecht?)
   - Gibt es ähnliche frühere Buchungen? (Muster erkennen)

3. **Vorschlag machen mit Begründung**
   - "Ich würde Konto X nehmen, weil..."
   - "Es gibt bereits eine offene Rechnung von diesem Lieferanten..."
   - "Achtung: USt-IdNr fehlt beim Kunden, §13b prüfen"

4. **Nur buchen wenn sicher** — im Zweifel nachfragen

---

## Szenarien: Vage Eingabe → Konkreter Vorschlag

### "Buch die Rechnung vom Designbüro"

```
1. Lieferant suchen:
   → VENDOR_GET durchsuchen nach "Design"
   → 1 Treffer: verwenden
   → 0 Treffer: "Kein Lieferant mit 'Design' gefunden. Meinst du...?"
   → 2+ Treffer: "Ich habe mehrere Lieferanten gefunden: [Liste]. Welcher?"

2. Aufwandskonto ableiten:
   → Lieferantenstamm prüfen (CMXLIF Idx 35)
   → Wenn gesetzt: verwenden + bestätigen
   → Wenn leer: "Welches Aufwandskonto? Vorschlag: 4900 (Fremdleistungen)"
   → NIEMALS Default 3200 blind verwenden!

3. Betrag:
   → "Wie hoch ist der Nettobetrag?"
   → NIEMALS einen Betrag raten

4. USt prüfen:
   → Lieferant DE → 19% VSt (Standard)
   → Lieferant EU mit USt-IdNr → §13b Reverse Charge
   → Lieferant Drittland → keine VSt, Einfuhrumsatzsteuer
   → Im Zweifel: OHNE VSt buchen und nachfragen

5. Vor dem Buchen:
   → "Eingangsrechnung: Lieferant 70001 (Kreativbüro), 2.800 EUR netto,
      Konto 4900, 19% VSt. Rechnungsnummer?"
   → Belegnummer ist PFLICHT (GoBD)
```

### "Schreib eine Rechnung an den Bäcker"

```
1. Kunde suchen:
   → CUSTOMER_GET durchsuchen nach "Bäck"
   → Treffer: Kunde 10003 (Bäckerei Sonnenkorn GmbH)

2. Offene Aufträge prüfen:
   → SALES_ORDER_GET für Kunde 10003
   → Wenn offener Auftrag vorhanden: "Es gibt Auftrag #8 mit 3 Positionen.
     Soll die Rechnung daraus erstellt werden?"
   → Wenn kein Auftrag: "Welche Leistung soll berechnet werden?"

3. Produkte vorschlagen:
   → PRODUCT_GET — bekannte Produkte auflisten
   → "Unsere Produkte: WEB-DESIGN (3500), SEO-SETUP (1200), CONTENT-PKT (800)"

4. Vor dem Erstellen:
   → "Rechnung für Bäckerei Sonnenkorn GmbH:
      Pos 1: WEB-DESIGN 1x 3.500,00
      Pos 2: SEO-SETUP 1x 1.200,00
      Netto: 4.700,00 + 893,00 USt = 5.593,00 brutto
      Aus Auftrag #8. Korrekt?"
```

### "Ist alles bezahlt?"

```
1. Offene Posten komplett abrufen:
   → OPEN_ITEMS_GET für aktuelles Jahr

2. Aufteilen in:
   → Debitoren (positive Beträge): "X Kunden schulden uns Y EUR"
   → Kreditoren (negative Beträge): "Wir schulden Z Lieferanten W EUR"
   → Überfällige separat markieren

3. Bericht:
   → "3 offene Debitoren-Posten (12.400 EUR), davon 1 überfällig seit 14 Tagen:
      - Kunde 10001: RE #3, 11.900 EUR, fällig 03.04.2026
      - Kunde 10003: RE #5, 6.545 EUR, fällig 11.04.2026 [noch nicht fällig]
      2 offene Kreditoren-Posten (-3.570 EUR):
      - Lieferant 70001: PC-2026-002, -3.332 EUR, fällig 31.03.2026"
```

### "Stimmen die Konten?"

```
1. Kontenabstimmung durchführen (→ Routine M3):
   → Bank (1200) vs. erwarteter Saldo
   → Debitorensumme (OPEN_ITEMS positiv) vs. Konto 1400
   → Kreditorensumme (OPEN_ITEMS negativ) vs. Konto 1600
   → Verrechnungskonten (1590, 1360) auf Null prüfen
   → USt-Konten gegenseitig abstimmen

2. Abweichungen melden:
   → "Kontenabstimmung März 2026:
      Bank 1200: 12.345,00 EUR [Kontoauszug prüfen]
      Debitoren: OP-Summe 18.445 EUR, Konto 1400: 18.445 EUR ✓
      Kreditoren: OP-Summe -3.332 EUR, Konto 1600: -3.570 EUR ✗ DIFFERENZ 238 EUR
      Verrechnungskonto 1590: 0,00 EUR ✓
      → Differenz Kreditoren: Vermutlich alte Buchung TEST-ER-002 (238 EUR) ohne OP-Zuordnung"
```

### "Mach mal die USt fertig"

```
1. Zeitraum bestimmen:
   → Aktueller Monat oder letzter Monat?
   → "USt-Voranmeldung für welchen Monat? Vorschlag: Februar 2026
      (Frist: 10.03.2026 bzw. 10.04. mit Dauerfrist)"

2. Konten auslesen:
   → ACCBAL_GET für 1775 (USt 19%), 1770 (USt 7%)
   → ACCBAL_GET für 1576 (VSt 19%), 1571 (VSt 7%)
   → ACCBAL_GET für 1577/1787 (§13b)

3. Berechnung:
   → "USt-Voranmeldung Februar 2026:
      USt 19%: 1.900,00 EUR (Konto 1775)
      USt 7%: 0,00 EUR (Konto 1770)
      VSt 19%: -532,00 EUR (Konto 1576)
      VSt 7%: 0,00 EUR (Konto 1571)
      ─────────────────
      Zahllast: 1.368,00 EUR"

4. Plausibilitäts-Check:
   → Zahllast vs. Vormonat vergleichen
   → Große Abweichungen erklären
   → "Zahllast 30% höher als Vormonat — Ursache: Rechnung #5 (5.500 netto)"
```

### "Wir haben was bei Amazon bestellt, 50 Euro"

```
1. Kategorie bestimmen:
   → "Was wurde bestellt? Büromaterial, Software, Hardware?"
   → Konto ableiten:
     - Büromaterial → 4930 (Büro-/Schreibwaren)
     - Software-Abo → 4964 (EDV-Kosten, Nutzungsentgelte)
     - Hardware <800 netto → 4855 (GWG sofort) oder 4830 (Aufwand)
     - Hardware >800 netto → Anlage 0027/0200ff + AfA

2. Lieferant:
   → Amazon existiert als Lieferant?
   → Wenn nicht: anlegen oder auf Sammelkonto 1600 buchen
   → "Amazon als Lieferant anlegen? Oder Direktbuchung ohne Personenkonto?"

3. USt:
   → Amazon DE → 19% VSt Standard
   → Amazon EU (Luxemburg-Rechnung) → USt-IdNr prüfen
   → "Rechnung von Amazon EU Services (LU)? Dann §13b prüfen!"

4. Betrag:
   → "50 EUR — brutto oder netto?"
   → Bei brutto: 50 / 1.19 = 42,02 netto + 7,98 USt
   → "Eingangsrechnung: Amazon, 42,02 netto, Konto 4930 (Büromaterial),
      7,98 VSt. Rechnungsnummer von Amazon?"
```

### "Der Kunde hat zu viel bezahlt"

```
1. Kunde identifizieren:
   → "Welcher Kunde?"
   → Oder aus Kontext ableiten (letzter besprochener Kunde)

2. Ist-Zustand prüfen:
   → OPEN_ITEMS_GET für diesen Kunden
   → Haben-Saldo bei Debitor = Überzahlung

3. Optionen vorschlagen:
   → "Kunde 10001 hat 200 EUR zu viel bezahlt. Optionen:
      a) Rückerstattung: Bank 1200 an Debitor 10001 (200 EUR)
      b) Verrechnung mit nächster Rechnung (Guthaben stehen lassen)
      c) Gutschrift erstellen
      Was bevorzugst du?"
```

---

## Risikovermeidung: Was der Agent NIEMALS tut

1. **Nie einen Betrag raten** — immer nachfragen
2. **Nie ohne Belegnummer buchen** — GoBD-Pflicht
3. **Nie USt-Satz raten** — bei Unsicherheit OHNE VSt und nachfragen
4. **Nie löschen** — nur Stornobuchungen (GoBD)
5. **Nie auf ein Konto buchen das er nicht kennt** — erst prüfen ob es existiert (ACCBAL_GET)
6. **Nie eine Buchung ändern** — nur Storno + Neubuchung
7. **Nie Personenkonten als Gegenkonto in CMXLRN** — nur Sachkonten (1600)
8. **Nie Default-Konten blind akzeptieren** — CMXLRN Default 3200 ist fast immer falsch
9. **Nie Produkt/Leistung raten** — wenn der User nicht sagt WAS verkauft/bestellt
   wurde: NACHFRAGEN! Nicht einfach ein vorhandenes Produkt nehmen.
   "Was wurde bestellt/geliefert?" ist immer die erste Frage.

## Risikobewertung vor jeder Aktion

| Aktion | Risiko | Verhalten |
|--------|--------|-----------|
| Stammdaten lesen | Kein | Frei ausführen |
| Salden/OP abfragen | Kein | Frei ausführen |
| Kunde/Lieferant anlegen | Niedrig | Vorschlag zeigen, dann ausführen |
| Eingangsrechnung buchen | Mittel | Vorschlag mit Konten zeigen, Bestätigung |
| Ausgangsrechnung erstellen | Mittel | Positionen + Beträge bestätigen lassen |
| Rechnung versenden | Hoch | Immer explizite Freigabe |
| Stornobuchung | Hoch | Grund dokumentieren, Bestätigung |
| Zahlungslauf | Hoch | Immer explizite Freigabe |

---

## Selbstprüfung nach jeder Buchung

Nach jeder Buchung führt der Agent automatisch durch:

```
1. ACCDOC_GET → Buchung vorhanden?
2. Soll = Haben? (Beträge prüfen)
3. Richtiges Konto? (vs. Erwartung)
4. Richtiger Zeitraum? (Periode prüfen)
5. OPEN_ITEMS_GET → OP korrekt angelegt/aufgelöst?
```

Wenn etwas nicht stimmt: SOFORT melden, nicht ignorieren.

---

## Kontextgedächtnis innerhalb einer Session

Der Agent merkt sich während einer Session:
- Welche Kunden/Lieferanten besprochen wurden
- Welche Buchungen gemacht wurden
- Welche offenen Fragen noch bestehen
- Welche Widersprüche aufgefallen sind

Am Ende einer Session mit Buchungen:
→ Zusammenfassung erstellen
→ Offene Punkte dokumentieren
→ Widersprüche in `mandant/berichte/widersprueche.md` schreiben
→ Committen

---

## Hinweis: Personenkonten vs. Kontenrahmen

Personenkonten (Debitoren 10000-69999, Kreditoren 70000+) sind NICHT Teil
von SKR03/SKR04 — sie sind eine Software-Konvention (Collmex, DATEV, etc.).
Beide Kontenrahmen nutzen denselben Personenkonten-Bereich.

SKR03 vs. SKR04 betrifft nur die Sachkonten (0000-9999).
Die Entscheidungsbäume unten verwenden SKR03-Konten.
Bei einem SKR04-Mandanten müssen die Kontonummern angepasst werden.

## Kontenrahmen-Erkennung (beim Forken / Onboarding)

Beim ersten Kontakt mit einem neuen Mandanten: Kontenrahmen erkennen!

**Schnelltest:** ACCBAL_GET für typische Konten:

| Konto | SKR03 | SKR04 |
|-------|-------|-------|
| 1200 | Bank | Bank (gleich!) |
| 1400 | Forderungen aus LuL | Forderungen aus LuL (gleich!) |
| 1600 | Verbindlichkeiten aus LuL | Verbindlichkeiten aus LuL (gleich!) |
| 4400 | **existiert nicht** | Erlöse |
| 8400 | Erlöse 19% | **existiert nicht** |
| 4900 | Sonstige betriebl. Aufwand | **existiert nicht** |
| 6300 | **existiert nicht** | Sonstige betriebl. Aufwand |

**Entscheidung:**
```
ACCBAL_GET;1;{jahr};0;8400
  → Konto existiert? → SKR03
ACCBAL_GET;1;{jahr};0;4400
  → Konto existiert? → SKR04
Beide existieren? → Individuell angepasst, NACHFRAGEN
Keines existiert? → Noch keine Buchungen, in Collmex-Einstellungen prüfen
```

**WICHTIG:** Kontenrahmen in `mandant/stammdaten.md` dokumentieren.
Alle Entscheidungsbäume in diesem Dokument verwenden SKR03.
Für SKR04 braucht es eine Mapping-Tabelle (→ `wissen/skr04.md`).

## Entscheidungsbaum: Welches Konto?

### Eingangsrechnung — Aufwandskonto bestimmen

```
Lieferantenstamm hat Aufwandskonto gesetzt?
  → JA: Verwenden (aber dem User zeigen)
  → NEIN:
    Was wurde geliefert/geleistet?
    ├── Büromaterial          → 4930
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
    ├── Buchführungskosten     → 4955
    ├── Werbekosten            → 4600
    ├── Geschenke (≤50 EUR)    → 4630
    ├── Geschenke (>50 EUR)    → 4635 (nicht abzugsfähig!)
    ├── Reparaturen            → 4800
    ├── Betriebsbedarf         → 4980
    └── Unklar                 → NACHFRAGEN, nicht raten
```

### Ausgangsrechnung — Erlöskonto bestimmen

```
Was wurde verkauft/geleistet?
├── Waren 19%               → 8400 (Erlöse 19% USt)
├── Waren 7%                → 8300 (Erlöse 7% USt)
├── Dienstleistungen 19%    → 8400
├── Steuerfreie Lieferung EU→ 8125 (igL steuerfrei)
├── Sonstige Leistung EU    → 8336 (§13b)
├── Export Drittland        → 8120 (steuerfreie Ausfuhr)
└── Unklar                  → NACHFRAGEN
```

### USt-Satz bestimmen

```
Wer ist der Empfänger?
├── Inland (DE)
│   ├── Unternehmer          → 19% (Standard) oder 7% (ermäßigt)
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

## Spezialfälle und Gotchas

### §14 UStG — Pflichtangaben Rechnung

Jede Eingangsrechnung VOR dem VSt-Abzug prüfen:

1. Vollständiger Name + Anschrift Leistungserbringer
2. Vollständiger Name + Anschrift Leistungsempfänger
3. Steuernummer ODER USt-IdNr des Leistungserbringers
4. Fortlaufende Rechnungsnummer
5. Ausstellungsdatum
6. Leistungszeitpunkt oder -zeitraum
7. Menge + Art der Leistung
8. Nettobetrag + USt-Satz + USt-Betrag + Bruttobetrag
9. Bei Steuerbefreiung: Hinweis auf Befreiungsgrund

**Fehlende Angaben:** VSt-Abzug NICHT möglich → korrigierte Rechnung anfordern.
**Kleinbetragsrechnung (≤250 EUR brutto):** Nur Nr. 1, 5, 7, 8 erforderlich.

### Gutschrift vs. Stornorechnung

- **Stornorechnung (Rechnungskorrektur):** Korrigiert eine fehlerhafte Rechnung.
  → Negativer Betrag, Bezug auf Original-Rechnungsnummer.
  → In Collmex: `collmex storno`
- **Kaufmännische Gutschrift:** Nachlass, Bonus, Rückgabe.
  → Eigenes Dokument, aber Bezug auf Lieferung/Auftrag.
- **Gutschrift i.S.d. UStG (§14 Abs. 2 S. 2):** Rechnung durch Leistungsempfänger.
  → Selten, nur bei Vereinbarung. NICHT mit Stornorechnung verwechseln!

### GWG — Geringwertige Wirtschaftsgüter

```
Nettobetrag der Anschaffung:
├── ≤ 250 EUR      → Sofortaufwand, kein Anlagespiegel (4855 oder Sachkonto)
├── 250,01-800 EUR → GWG, Sofortabschreibung möglich (4855 + Anlage)
├── 800,01-1000 EUR→ Sammelposten (0485) 5 Jahre AfA ODER Einzelanlage
└── > 1000 EUR     → Anlage aktivieren, planmäßige AfA
```

**Achtung:** GWG-Grenze immer NETTO (ohne USt). 800 EUR netto = 952 EUR brutto bei 19%.

### Bewirtungsbeleg (§4 Abs. 5 Nr. 2 EStG)

```
Bewirtungsaufwand gesamt:
├── 70% betrieblich abzugsfähig → 4650 (Bewirtungskosten)
└── 30% nicht abzugsfähig       → 4654 (Nicht abzugsfähige Bewirtung)
VSt: Auf den GESAMTEN Betrag abziehbar (100%)!
```

Pflichtangaben auf dem Beleg:
- Ort, Datum, Teilnehmer, Anlass
- Eigenbeleg bei ausländischen Restaurants

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

**Häufiger Fehler:** Skonto als Nettobetrag buchen, USt-Korrektur vergessen.

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
→ Nachweis: Gelangensbestätigung

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
→ Nachweis: Ausfuhrbestätigung (ATLAS)
```

### Betriebsprüfungs-Hotspots

Was das Finanzamt besonders genau prüft:

1. **Bewirtungskosten:** 70/30-Aufteilung, Angaben auf Beleg
2. **Geschenke:** Grenze 50 EUR (Konto 4630 vs. 4635)
3. **Privatanteile:** Kfz (1% oder Fahrtenbuch), Telefon, Bewirtung
4. **Sachkonten vs. Personenkonten:** Forderungen/Verbindlichkeiten immer über Personenkonten
5. **Periodenabgrenzung:** Leistungsdatum = Buchungsdatum, nicht Rechnungsdatum
6. **Kassenbuchführung:** Lückenlos, keine negativen Kassenbestände
7. **GoBD:** Unveränderbarkeit, Nachvollziehbarkeit, Vollständigkeit

### Zusammenfassende Meldung (ZM)

```
Pflicht bei: igL + sonstige Leistungen an EU-Unternehmer (§13b)
Frist: 25. des Folgemonats nach Quartalsende
       (monatlich bei igL > 50.000 EUR/Quartal)
Inhalt: USt-IdNr des Empfängers + Bemessungsgrundlage
Sanktion: Bußgeld bis 5.000 EUR bei Versäumnis
```
