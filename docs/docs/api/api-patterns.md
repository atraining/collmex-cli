# Collmex API Patterns & Gotchas (Verified 2026-03)

## Goldene Regel: Lerne und dokumentiere

Wenn du durch Trial & Error etwas Neues über die Collmex-API lernst:
1. Trage es in `api-fields.md` ein (Feldstrukturen)
2. Trage es hier ein (Patterns, Gotchas, Workflows)
3. Update `api_reference.py` falls neue Satzarten entdeckt werden

## Pattern: NEW_OBJECT_ID Format (live-verifiziert 2026-03-04)

**Format:** `NEW_OBJECT_ID;ID;0;2` (4 Felder, Semikolon-getrennt)

- `row[1]` = Die neue ID (z.B. 70004 für Lieferant, 10005 für Kunde)
- `row[2]` und `row[3]` = interne Collmex-Felder (ignorieren)

**Getestet mit:** CMXLIF (Lieferant), CMXKND (Kunde)

**ACHTUNG:** CMXLRN und CMXUMS liefern KEIN NEW_OBJECT_ID zurück!
Diese Satzarten verwenden die Rechnungsnummer als Identifikator.

## Pattern: Beleg mit mehreren Positionen anlegen

**Problem:** Bei leerem Belegnummer-Feld erstellt Collmex pro CSV-Zeile
einen NEUEN Beleg. Zwei Zeilen ohne Nr = zwei separate Belege.

**Lösung (2-Schritt-Verfahren):**

```python
# Schritt 1: Position 1 anlegen, Belegnummer zurückbekommen
r1 = client.request([build_pos('', 1, 'Pos A', 5, '100,00')])
beleg_nr = r1.new_ids[0]

# Schritt 2: ALLE Positionen mit gleicher Belegnummer senden
r2 = client.request([
    build_pos(beleg_nr, 1, 'Pos A', 5, '100,00'),
    build_pos(beleg_nr, 2, 'Pos B', 10, '50,00'),
])
```

**WICHTIG:** Schritt 2 ERSETZT alle Positionen, nicht ergänzt sie!
Immer ALLE Positionen mitsenden, auch die bestehenden.

Gilt für: CMXORD-2, CMXINV, CMXQTN, CMXDLV (alle Belege mit Positionen).

## Pattern: Split-Buchung (mehrere Aufwandskonten pro Rechnung)

**Verifiziert 2026-03-04** gegen Live-API (Beleg 72, dann storniert).

Aufeinanderfolgende CMXLRN-Zeilen mit identischer Rechnungsnummer werden
von Collmex automatisch zu EINEM Buchungsbeleg zusammengefasst.

```
CMXLRN;;1;20260304;SPLIT-001;70,00;;;;;;EUR;1200;;Bewirtung 70%;;;4650;;
CMXLRN;;1;20260304;SPLIT-001;30,00;;;;;;EUR;1200;;Bewirtung 30% n.a.;;;4654;;
```

Collmex erzeugt daraus:
```
Soll 4650 (Bewirtung abzugsf.)    70,00
Soll 1576 (VSt 19% auf 70)        13,30
Soll 4654 (Bewirtung n.a.)        30,00
Soll 1576 (VSt 19% auf 30)         5,70
Haben 1200 (Bank)                119,00
```

**Regeln:**
- Rechnungsnummer MUSS identisch sein (sonst 2 separate Belege)
- Zeilen müssen aufeinanderfolgen im selben Request
- Funktioniert auch mit CMXUMS (Ausgangsrechnungen)
- Storno: gleiche Zeilen mit Storno-Flag=1 (Feld 19)

**Anwendungsfälle:**
- Bewirtungsbeleg 70/30 (4650 + 4654)
- Gemischte Rechnung (Bürobedarf + Fremdleistung)
- Rechnung mit Positionen in verschiedenen Steuersätzen UND Konten

**In collmex:** `BookingEngine.create_split_eingangsrechnung()`

## Pattern: Beleg löschen (GoBD-konform)

Collmex löscht nicht physisch. Stattdessen Gelöscht-Flag setzen:
- CMXORD-2: Index 42 = '1'
- CMXINV: Index 40 = '1'

Den Beleg mit allen Pflichtfeldern + Gelöscht=1 erneut senden.

## Pattern: Rechnung aus Kundenauftrag

CMXINV Feld 5 (Index 5) = Auftragsnummer verknüpft die Rechnung
mit dem Kundenauftrag. Die Positionen müssen trotzdem manuell
übernommen werden. Ein "konvertiere Auftrag zu Rechnung" gibt es nicht.

## Pattern: Rechnung per E-Mail versenden

Voraussetzungen (alle drei nötig!):
1. **Firma:** Steuernummer oder USt-IdNr in Firmenstammdaten
   (nur per Web-UI: Verwaltung → Firma)
2. **SMTP:** Postausgangs-Server in Collmex konfiguriert
   (nur per Web-UI: Verwaltung → E-Mail)
3. **Kunde:** E-Mail (Feld 17) + Ausgabemedium=1 (Feld 29)

```python
client.request(['INVOICE_OUTPUT;1;{re_nr};1'])
# Feld 4 = 1 = E-Mail
```

## Pattern: Kunde anlegen mit allen Versand-Feldern

```python
f = [''] * 35
f[0]  = 'CMXKND'
f[2]  = '1'                         # Firma Nr
f[7]  = 'Firmenname GmbH'           # Firma
f[9]  = 'Straße 1'                  # Straße
f[10] = '12345'                     # PLZ
f[11] = 'Berlin'                    # Ort
f[14] = 'DE'                        # Land
f[17] = 'kunde@example.com'         # E-Mail
f[24] = 'DE123456789'               # USt-IdNr
f[29] = '1'                         # Ausgabemedium: E-Mail
```

## Pattern: Produkt anlegen (CMXPRD)

```python
f = [''] * 15
f[0]  = 'CMXPRD'
f[1]  = 'WEB-DESIGN'              # Produktnummer (alphanumerisch!)
f[2]  = 'Website-Erstellung'      # Bezeichnung
f[4]  = 'PCE'                     # Mengeneinheit (ISO-Code!)
f[6]  = '1'                       # Firma Nr
f[7]  = '0'                       # Steuerklassifikation (0=voll)
f[11] = '1'                       # Produktart (1=Dienstleistung)
f[14] = '3500,00'                 # Verkaufs-Preis
```

**WICHTIG:** Mengeneinheiten müssen ISO-Codes sein!
`PCE` = Stück, NICHT "Stk", "Stck" oder "Stueck".

## Pattern: Angebot erstellen (CMXQTN)

Feldstruktur fast identisch zu CMXORD-2 (gleiche Positions-Indizes 68-79).

```python
f = [''] * 82
f[0]  = 'CMXQTN'
f[2]  = str(pos_nr)               # Position
f[4]  = '1'                       # Firma Nr
f[5]  = str(kunden_nr)            # Kunden-Nr
f[28] = datum                     # Angebotsdatum YYYYMMDD
f[47] = gueltig_bis               # Gültig-bis YYYYMMDD
f[68] = '0'                       # Positionstyp (0=Normal)
f[69] = produkt_nr                # Produktnummer
f[70] = beschreibung              # Produktbeschreibung
f[72] = str(menge)                # Menge
f[73] = preis                     # Einzelpreis (deutsch!)
f[77] = '1'                       # Produktart (1=DL)
f[78] = '0'                       # Steuerklassifikation
```

2-Schritt-Verfahren wie bei allen Belegen mit Positionen!

## Pattern: Lieferung erstellen (CMXDLV)

```python
f = [''] * 72
f[0]  = 'CMXDLV'
f[2]  = str(pos_nr)               # Position
f[4]  = '1'                       # Firma Nr
f[5]  = str(kunden_nr)            # Kunden-Nr
f[6]  = str(auftrags_nr)          # Auftrag Nr (Verknüpfung!)
f[30] = datum                     # Lieferungsdatum YYYYMMDD
f[60] = '0'                       # Positionstyp
f[61] = produkt_nr                # Produktnummer
f[62] = beschreibung              # Produktbeschreibung
f[64] = str(menge)                # Menge
f[65] = str(pos_nr)               # Kundenauftragsposition
```

**Voraussetzung:** Auftragspositionen müssen `Lieferrelevant=1` haben
(CMXORD-2 Index 98). Ohne das: "Auftrag ist bereits komplett beliefert
oder enthält keine lieferrelevanten Positionen".

## Pattern: Kompletter Geschäftsvorfall (Workflow)

Getestet und verifiziert am 2026-03-04:

1. **Kunde anlegen** (CMXKND) → Kunden-Nr zurück
2. **Produkte anlegen** (CMXPRD): Mengeneinheit=PCE, Produktart=1 für DL
3. **Angebot erstellen** (CMXQTN): 2-Schritt, gleiche Indizes wie CMXORD-2
4. **Kundenauftrag** (CMXORD-2): 2-Schritt, Lieferrelevant=1 (Idx 98) für DL!
5. **Projekt** (CMXPRJ): Import geht, aber im Basic-Tarif nicht abrufbar
6. **Lieferung** (CMXDLV): 2-Schritt, verknüpft mit Auftrag (Idx 6)
7. **Rechnung** (CMXINV): 2-Schritt, Auftrag Nr in Idx 5
8. **Rechnungsversand** (INVOICE_OUTPUT): braucht Steuernr + SMTP

Jeder Schritt mit Positionen braucht das 2-Schritt-Verfahren!

## Pattern: Lieferant anlegen (CMXLIF)

```python
f = [''] * 41
f[0]  = 'CMXLIF'
f[2]  = '1'                        # Firma Nr
f[3]  = 'Firma'                    # Anrede
f[7]  = 'Kreativbüro GmbH'         # Firma
f[9]  = 'Straße 1'                 # Straße
f[10] = '10115'                    # PLZ
f[11] = 'Berlin'                   # Ort
f[14] = 'DE'                       # Land
f[17] = 'rechnung@beispiel.de'    # E-Mail
f[24] = 'DE987654321'             # USt-IdNr
f[35] = '4900'                    # Aufwandskonto (Fremdleistungen)
f[36] = '0'                        # Vorsteuer (0=voll 19%)
```

Lieferantennummer wird ab 70001 automatisch vergeben.

## Pattern: Eingangsrechnung buchen (CMXLRN)

```python
f = [''] * 21
f[0]  = 'CMXLRN'
f[1]  = '70001'                    # Lieferant Nr
f[2]  = '1'                        # Firma Nr
f[3]  = '20260301'                 # Rechnungsdatum
f[4]  = 'PC-2026-002'             # Belegnummer des Lieferanten
f[5]  = '2800,00'                  # Netto voller Satz (19%)
f[6]  = '532,00'                   # USt 19% (auto wenn leer)
f[11] = 'EUR'                      # Währung
f[14] = 'Logo + Corporate Design'  # Buchungstext
f[16] = '4900'                     # Aufwandskonto, IMMER explizit!
```

**Ergibt Buchung:**
- Soll 4900 (Fremdleistungen): 2.800,00 EUR
- Soll 1576 (Vorsteuer 19%): 532,00 EUR
- Haben 1600 (Verbindl. aus L+L): 3.332,00 EUR

**WICHTIG:** Feld 16 (Aufwandskonto) IMMER explizit setzen!
Default ist 3200 (Wareneingang), NICHT das Konto aus dem Lieferantenstamm.

## Pattern: Einkaufs-Workflow (Fremdleistungen)

Getestet und verifiziert am 2026-03-04:

1. **Lieferant anlegen** (CMXLIF) → Lieferant-Nr zurück (ab 70001)
2. **Eingangsrechnung** (CMXLRN): Aufwandskonto explizit setzen!
3. **Buchung verifizieren** (ACCDOC_GET): Soll=Haben prüfen
4. **Offene Posten** (OPEN_ITEMS_GET): Feld 7 = Personenkonto

Kein 2-Schritt-Verfahren nötig, da CMXLRN keine Positionen hat.

## Pattern: Personenkonten (Kreditoren/Debitoren)

Collmex bucht auf Sammelkonten (SKR03):
- **1400** Forderungen (Debitoren-Sammelkonto): für Ausgangsrechnungen
- **1600** Verbindlichkeiten (Kreditoren-Sammelkonto): für Eingangsrechnungen

Die Personenkontozuordnung läuft automatisch:
- Debitor 10001 → über Kundennummer in CMXINV/CMXUMS
- Kreditor 70001 → über Lieferantennummer in CMXLRN

Personenkonten sind KEIN Sachkonto im Kontenrahmen:
- ACCBAL_GET(70001) → Fehler "Konto nicht vorhanden"
- OPEN_ITEMS_GET → zeigt Personenkonto in Feld 7

## Gotchas

### request() erwartet list[str], nicht str
```python
# FALSCH: iteriert zeichenweise, "Datentyp C ist ungültig"
client.request(csv_string)

# RICHTIG
client.request([zeile1, zeile2])
```

### Abfrage-Feldfolge ≠ Import-Feldfolge
- SALES_ORDER_GET: `Satzart;AuftragsNr;FirmaNr;...`
- INVOICE_GET: `Satzart;RechnungsNr;FirmaNr;...`
- CUSTOMER_GET: `Satzart;KundenNr;FirmaNr`
- Immer in der Doku nachschlagen, die Reihenfolge ist NICHT konsistent!

### Firmenstammdaten nicht per API änderbar
Steuernummer, USt-IdNr, SMTP-Einstellungen → nur Web-UI.
URL: `https://www.collmex.de/c.cmx?{kundennr},1,coch,1`

### E-Rechnung seit 2025 Pflicht
Jede Rechnungsausgabe (auch Drucken!) validiert E-Rechnungs-Pflichtfelder.
Ohne Firma-Steuernummer geht NICHTS raus.

### Ausgabemedium-Werte (global verwendet)
| Wert | Medium |
|------|--------|
| 0 | Drucken |
| 1 | E-Mail |
| 2 | Fax |
| 3 | Brief |
| 100 | Keine Ausgabe |

### Beträge immer deutsches Format
`1500,00` nicht `1500.00`. Collmex erwartet Komma als Dezimaltrenner.

### Mengeneinheiten sind ISO-Codes
`PCE` (Stück), NICHT "Stk", "Stck" oder "Stueck".
Collmex akzeptiert nur ISO-konforme Einheiten.
Alle verfügbaren Einheiten: `collmex webui mengeneinheiten`

Häufigste Codes: PCE=Stück, HR=Stunden, DAY=Tage, MON=Monat, ANN=Jahr,
KGM=Kilogramm, LTR=Liter, MTR=Meter, P1=Prozent, WEE=Woche.

ACHTUNG: PCE hat ISO-Code H87 (nicht PCE). Collmex-interner Code ≠ ISO-Code!

### Dienstleistungen brauchen Lieferrelevant=1
CMXORD-2 Index 98 muss `1` sein, damit Lieferungen (CMXDLV) möglich sind.
Ohne das Flag: "Auftrag ist bereits komplett beliefert oder enthält keine
lieferrelevanten Positionen".

### Projekte im Basic-Tarif nicht abrufbar
CMXPRJ-Import wird ohne Fehler akzeptiert, aber PROJECT_GET liefert
0 Ergebnisse. Das Projekt-Modul ist im "buchhaltung basic"-Tarif
vermutlich nicht enthalten.

### CMXQTN ≈ CMXORD-2
Angebote (CMXQTN) haben fast identische Feldstruktur wie Kundenaufträge
(CMXORD-2). Gleiche Positions-Indizes (68-79). Nur Header-Felder
unterscheiden sich leicht (z.B. Idx 28 vs 29 für Datum, Idx 47 = Gültig-bis).

### CMXLRN Aufwandskonto ist NICHT der Lieferanten-Default
Feld 16 (KontoVoll) defaultet auf 3200 (Wareneingang), NICHT auf das
Aufwandskonto aus dem Lieferantenstamm (CMXLIF Idx 35). Immer explizit setzen!

### CMXLRN Gegenkonto muss Sachkonto sein
Feld 12 (Gegenkonto) akzeptiert NUR Sachkonten (z.B. 1600). Personenkonten
(70001) führen zu "Konto nicht vorhanden". Die Personenkontozuordnung
läuft automatisch über die Lieferantennummer (Feld 1).

### Personenkonten nicht in ACCBAL_GET
ACCBAL_GET funktioniert NUR für Sachkonten. Personenkonten (10000+, 70000+)
erzeugen "Konto nicht vorhanden". Stattdessen OPEN_ITEMS_GET nutzen.

### ACCDOC Soll/Haben ist Text
ACCDOC_GET liefert "Soll" und "Haben" als Text (Idx 10), NICHT als 0/1.
Haben-Beträge (Idx 11) sind NEGATIV.

## Pattern: Beliebige Buchung per CMXUMS (ohne Rechnung)

**Problem:** ACCDOC ist NUR lesbar. CMXINV/CMXLRN erzeugen immer Rechnungen.
Wie bucht man Eröffnungsbilanz, Umbuchungen, Korrekturen etc.?

**Lösung:** CMXUMS mit "steuerfreie Erlöse"-Feldern missbrauchen:

```python
f = [''] * 16
f[0]  = 'CMXUMS'
f[1]  = str(kunden_nr)       # Kunden-Nr (kann 0 sein)
f[2]  = '1'                  # Firma Nr
f[5]  = datum                # YYYYMMDD
f[7]  = buchungstext         # z.B. 'EB-2026-001'
f[11] = str(haben_konto)     # Konto (HABEN-Seite!)
f[12] = betrag               # deutsches Format: '12500,00'
f[14] = str(soll_konto)      # Gegenkonto (SOLL-Seite!)
```

**Ergibt:** Soll {soll_konto} / Haben {haben_konto}: {betrag} EUR

**WICHTIG:**
- Feld 11 = Haben-Konto, Feld 14 = Soll-Konto (nicht intuitiv!)
- Negative Beträge werden ABGELEHNT
- Kunden-Nr kann '0' sein für reine Sachkontenbuchungen
- Steuerklassifikation (Feld 13) leer lassen = steuerfrei

**Beispiel Eröffnungsbilanz GmbH (SKR03):**
```python
# Soll 1200 Bank / Haben 0800 Stammkapital: 12.500 EUR
f[11] = '800'    # Haben: Gezeichnetes Kapital
f[12] = '12500,00'
f[14] = '1200'   # Soll: Bank

# Soll 0868 Ausstehende Einlagen / Haben 0800: 12.500 EUR
f[11] = '800'    # Haben: Gezeichnetes Kapital
f[12] = '12500,00'
f[14] = '868'    # Soll: Ausstehende Einlagen
```

## Pattern: Storno per CMXUMS

**Problem:** CMXUMS akzeptiert keine negativen Beträge. Storno-Flag
(f[22]='1') wird akzeptiert, erzeugt aber KEINE ACCDOC-Einträge!

**Lösung A: Steuerfreie Konten, Soll/Haben tauschen:**

```python
# Nur für Konten OHNE Steuerklassifikation (0xxx, 1200, etc.)!
# Original: Soll 0860 / Haben 0800: 12.500
f[11] = '800';  f[14] = '860';  f[12] = '12500,00'

# Storno: Soll 0800 / Haben 0860: 12.500 (umgekehrt!)
f[11] = '860';  f[14] = '800';  f[12] = '12500,00'
```

**Lösung B: Erlöskonto (8400) stornieren per CMXUMS Gutschrift:**

```python
# ACHTUNG: Steuerfreie Felder (f[11]/f[14]) mit 8400 als Gegenkonto
# lösen Auto-USt aus! 500 EUR wird zu 420,17 netto + 79,83 USt.
# Stattdessen: Reguläre Revenue-Felder + Rechnungsart=Gutschrift

f = [''] * 31
f[0]  = 'CMXUMS'
f[2]  = '1'              # Firma
f[3]  = '20260304'       # Datum
f[4]  = 'GS-001'         # Belegnummer
f[5]  = '1000,00'        # Netto voller Satz
f[14] = '1400'           # Gegenkonto (oder 1776)
f[15] = '1'              # Rechnungsart: GUTSCHRIFT!
f[16] = 'Storno Beratung'
f[18] = '8400'           # Konto voller Satz
```

Ergibt: Soll 8400 1000 / Soll 1776 190 / Haben Gegenkonto 1190
(exakt umgekehrt zum Original)

**Lösung C: Eingangsrechnung (CMXLRN) stornieren per Gutschrift-Flag:**

```python
f[13] = '1'  # Gutschrift, dreht Soll/Haben der Eingangsrechnung
```

**WICHTIG: Steuerfreie Felder + steuerpflichtige Gegenkonten:**
Die "steuerfreien Erlöse"-Felder (f[11]/f[12]/f[14]) sind NICHT wirklich
steuerfrei wenn das Gegenkonto (f[14]) eine Steuerklassifikation hat!
8400 als Gegenkonto → Betrag wird als brutto behandelt und in netto+USt
aufgespalten. Nur verwenden mit Konten OHNE Steuerklassifikation
(Bilanzkonten 0xxx, 1200 Bank, etc.).

## Pattern: Sachkonto anlegen per Web-UI

Collmex SKR03 hat einen reduzierten Kontenrahmen. Viele Standard-Konten
(z.B. 0868 Ausstehende Einlagen) fehlen und müssen manuell erstellt werden.

```python
# POST an die Konto-Ändern-Seite (acch), NICHT Konto-Anlegen (accr)!
session.post(
    f'https://www.collmex.de/c.cmx?{kundennr},1,acch',
    data={
        'group_kontoNr': '868',
        'group_kontoName': 'Ausstehende Einlagen auf gez. Kapital',
        'cx': 'Speichern',
    }
)
```

**WICHTIG:** Die `accr`-Seite (Konto anlegen) funktioniert nur mit
existierender Vorlage. Für neue Konten `acch` (Konto ändern) verwenden!

### ACCDOC_GET Datumsfilter unzuverlässig
ACCDOC_GET mit date_from/date_to liefert manchmal 0 Ergebnisse, obwohl
Buchungen existieren. Workaround: Ohne Datumsfilter abfragen und
client-seitig filtern.

---

## Kritisches Collmex-Wissen (verifiziert/recherchiert 2026-03)

### Re-Import ist idempotent

Gleiche Rechnungsnummer nochmal importieren:
- **Daten unverändert** → kein neuer Beleg, stille Akzeptanz
- **Daten geändert** → alte Buchung automatisch storniert + neue Buchung

Das gilt für CMXLRN und CMXUMS. Extrem nützlich für Fehlerkorrektur:
einfach nochmal mit korrekten Daten senden statt manuell stornieren.

### All-or-Nothing Transaktionen

Alle Zeilen in einem API-Request = eine DB-Transaktion. Wenn EINE Zeile
einen Fehler hat, wird ALLES zurückgerollt. Keine Teilimporte.

**Konsequenz:** Bei Split-Buchungen (mehrere CMXLRN-Zeilen) ist das gut:
Entweder geht der ganze Split durch oder gar nichts.

### Steuer wird automatisch berechnet

- CMXLRN Feld 6 (Steuer voll) leer → Collmex berechnet aus Feld 5 (Netto)
- CMXLRN Feld 8 (Steuer erm.) leer → Collmex berechnet aus Feld 7
- CMXUMS identisch für Felder 6/8

**ACHTUNG Rundungsfalle:** Wenn du BEIDES angibst (Netto + Steuer) und die
Beträge nicht exakt zum erwarteten Steuersatz passen, wählt Collmex
möglicherweise das FALSCHE Erlöskonto. Besser: Steuer leer lassen.

### Gegenkonto muss Finanzkonto sein

CMXLRN Feld 12 (Gegenkonto) akzeptiert NUR Konten der Gruppe "Finanzkonto"
(Bank 1200, Kasse 1000, etc.). NICHT: 1600 (Verbindlichkeiten), NICHT
Personenkonten (70001). Personenkontozuordnung geht NUR über
Lieferantennummer (Feld 1).

**Korrektur** zu früherer Doku: "Sachkonto" war zu ungenau, es muss ein
Finanzkonto sein. Wenn Lieferantennummer gesetzt ist, wird 1600 automatisch
verwendet und Gegenkonto kann leer bleiben.

### CMXUMS Rechnungsart-Falle

| Wert | Bedeutung | Erzeugt Buchung? |
|------|-----------|-----------------|
| 0 | Normal | Ja |
| 1 | Gutschrift | Ja (Soll/Haben umgekehrt) |
| 2 | Abschlagsrechnung | **NEIN!** Kein ACCDOC-Eintrag |

### CMXUMS Erlösart (Feld 25): Kontenmapping

| Code | Bedeutung | SKR03 | SKR04 |
|------|-----------|-------|-------|
| 10 | Export | 8120 | 4120 |
| 11 | Innergemeinschaftliche Lieferung | 8125 | 4125 |
| 12 | Nicht steuerbare EU | 8336 | 4336 |
| 13 | Generell steuerfrei | aus GJ-Einstellungen | aus GJ-Einstellungen |
| 14 | Reverse Charge (§13b) | 8337 | 4337 |
| 15 | Nicht steuerbar Drittland | 8338 | 4338 |

### USt-Satz-Automatik bei Datumsänderungen

Bei Steuersatzänderungen (z.B. COVID 2020: 19%→16%) wählt Collmex
anhand des Belegdatums automatisch andere Konten:
- 8400 → 8410 (wenn berechneter Satz ≠ Standard-Satz am Belegdatum)
- 8300 → 8334

### Geschäftsjahr = Kalenderjahr (immer)

Collmex erlaubt NUR kalenderjahrgleiche Geschäftsjahre. Kein Rumpf-GJ,
kein abweichendes GJ (z.B. April-März). Das ist eine harte Einschränkung.

### Automatischer Saldenvortrag

Bilanzkonten (0xxx, 1xxx) werden automatisch ins Folgejahr vorgetragen.
Erfolgskonten (4xxx, 8xxx) starten bei Null. Keine Eröffnungsbuchungen nötig.

### UTF-8 seit Mai 2023 optional

LOGIN-Feld 4 = `1` aktiviert UTF-8 für die gesamte Session.
Ohne dieses Flag: ISO-8859-1 (Default). Zeichen außerhalb ISO-8859-1
werden mit `?` ersetzt.

### Rate Limits

| Limit | Wert |
|-------|------|
| API-Calls pro Tag | max 10.000 pro Kundennummer |
| Gleichzeitige Requests | max 5 pro User |
| Wartungsfenster | täglich 03:30 - 05:00 Uhr |
| Retry nach Fehler 200005 | min. 1 Minute warten |

### ACCDOC_GET Delta-Abfragen

Feld 15 = `1` + Feld 16 = Systemname → liefert nur Buchungen die sich
seit der letzten Abfrage mit diesem Systemnamen geändert haben.
Nützlich für inkrementelle Syncs.

### INVOICE_PAYMENT_GET nur für CMXUMS

Zahlungseingänge per API abfragen geht NUR für Rechnungen die per
CMXUMS importiert wurden. CMXINV-Rechnungen oder Web-UI-Rechnungen
werden NICHT geliefert.

### Buchungstext wird auto-generiert

Wenn CMXLRN Feld 14 oder CMXUMS Feld 16 (Buchungstext) leer ist,
erzeugt Collmex automatisch einen Text aus Rechnungsnummer + Datum.

### Zahlungsbedingung aus Stammdaten

Wenn CMXLRN Feld 15 oder CMXUMS Feld 17 leer: Collmex übernimmt die
Zahlungsbedingung aus dem Lieferanten-/Kundenstamm. Default: 0 = 30 Tage.

### Anzahlungen (Vorkasse)

CMXUMS mit Zahlungsbedingung 9 (Vorkasse) oder 14 (PayPal):
Collmex sucht automatisch nach offener Anzahlung mit identischem Betrag
für diesen Kunden. Bei Betragsdifferenz: manuelle Zuordnung nötig.

SKR03-Konten für erhaltene Anzahlungen:
- 1718 (19%), 1717 (16%), 1711 (7%), 1712 (5%)

### Sonstige Umsätze sind IMMER steuerfrei

CMXLRN Felder 9/10 (Sonstige Umsätze) werden IMMER ohne Steuer gebucht.
Das ist der richtige Weg für steuerfreie Anteile einer Lieferantenrechnung.

### CMXINV Schreibschutz

CMXINV Feld 94 (Schreibgeschützt):
- `0` setzen = Schutz entfernen (wird VOR anderen Feldern verarbeitet)
- `1` setzen = nur mit leeren Feldern (außer Rechnungsnr + Feld 94)
- Wird automatisch gesetzt beim E-Mail-Versand (seit 2024)
