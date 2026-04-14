# Collmex API Field Structures (Verified Against Live API 2026-03)

## ACC_BAL (ACCBAL_GET Response) - 4 Fields

```
Index 0: "ACC_BAL"
Index 1: Kontonummer (e.g. "1200")
Index 2: Bezeichnung (e.g. "Bank")
Index 3: Saldo (e.g. "306,00")
```

NO Firma field, NO Soll/Haben split, NO Anfangsbestand.

## OPEN_ITEM (OPEN_ITEMS_GET Response) - 20 Fields

```
Index  0: "OPEN_ITEM"
Index  1: Firma Nr ("1")
Index  2: Geschäftsjahr ("2026")
Index  3: Buchungsperiode ("30")
Index  4: Positionsnummer ("1")
Index  5: (leer)
Index  6: (leer)
Index  7: Personenkonto-Nr ("70001" Kreditor, "10000" Debitor)
Index  8: Name + Ort ("Kreativbüro Pixel und Code GmbH, Berlin")
Index  9: Belegnummer ("PC-2026-002")
Index 10: Belegdatum ("20260301")
Index 11: Zahlungsbedingung ("0 30 Tage ohne Abzug")
Index 12: Fälligkeitsdatum ("20260331")
Index 13-15: diverse (0)
Index 16: Bezahlt ("0,00")
Index 17: Ursprungsbetrag ("-3332,00" negativ=Kreditor, positiv=Debitor)
Index 18: Skonto ("0,00")
Index 19: Offener Betrag ("-3332,00")
```

Debitoren (Kunden) haben positive Beträge, Kreditoren (Lieferanten) negative.

## CMXLIF (Lieferant Import) - 41 Felder

```
Index  0: Satzart ("CMXLIF")
Index  1: Lieferantennummer (leer = auto, ab 70001)
Index  2: Firma Nr ("1")
Index  3: Anrede ("Firma")
Index  4: Titel
Index  5: Vorname
Index  6: Name (Nachname)
Index  7: Firma ("Kreativbüro Pixel und Code GmbH")
Index  8: Abteilung
Index  9: Straße
Index 10: PLZ
Index 11: Ort
Index 12: Bemerkung
Index 13: Inaktiv (0=aktiv, 1=inaktiv, 2=löschen, 3=löschen wenn unbenutzt)
Index 14: Land ("DE")
Index 15: Telefon
Index 16: Telefax
Index 17: E-Mail
Index 18-22: Bankdaten (KontoNr, BLZ, IBAN, BIC, Bankname)
Index 23: Steuernummer
Index 24: USt-IdNr
Index 25: Zahlungsbedingung
Index 26: Lieferbedingung
Index 28: Ausgabemedium (0=Druck, 1=E-Mail, 2=Fax, 3=Brief, 100=Keine)
Index 29: Kontoinhaber
Index 31: Kundennr beim Lieferanten
Index 32: Währung
Index 34: Ausgabesprache (0=Deutsch, 1=Englisch)
Index 35: Aufwandskonto (z.B. "4900" Fremdleistungen)
Index 36: Vorsteuer (0=voll 19%, 1=ermäßigt 7%, 2=steuerfrei)
Index 37: Buchungstext
Index 38: Kostenstelle
Index 39: Privatperson (1=ja)
Index 40: URL
```

ACHTUNG: Aufwandskonto (Idx 35) wird als Default im Stamm gespeichert,
muss aber bei CMXLRN TROTZDEM explizit in Feld 16 angegeben werden!

## VENDOR_GET (Lieferant Abfrage)

```
VENDOR_GET;LieferantNr;FirmaNr
```

Antwort als CMXLIF (42 Felder).

## CMXLRN (Eingangsrechnung Import) - 20 Fields

```
CMXLRN;LieferantNr;FirmaNr;Datum;RechnungsNr;
NettoVoll;SteuerVoll;NettoErm;SteuerErm;
SonstigeKonto;SonstigeBetrag;Waehrung;Gegenkonto;
Gutschrift;Buchungstext;Zahlungsbedingung;
KontoVoll;KontoErm;Storno;Kostenstelle
```

## CMXUMS (Ausgangsrechnung Import) - 31 Felder

```
Index  0: Satzart ("CMXUMS")
Index  1: Kunden-Nr (optional wenn Gegenkonto gesetzt)
Index  2: Firma Nr ("1")
Index  3: Rechnungsdatum YYYYMMDD (PFLICHT!)
Index  4: Rechnungsnummer (PFLICHT!)
Index  5: Netto voller Satz (8400 etc.)
Index  6: USt voller Satz (auto wenn leer)
Index  7: Netto ermäßigter Satz (8300 etc.)
Index  8: USt ermäßigter Satz (auto wenn leer)
Index  9: Innergemeinschaftliche Lieferung
Index 10: Export
Index 11: Steuerfreie Erlöse Konto (HABEN-Seite)
Index 12: Steuerfreie Erlöse Betrag
Index 13: Währung ("EUR")
Index 14: Gegenkonto (SOLL-Seite)
Index 15: Rechnungsart (0=Rechnung, 1=GUTSCHRIFT dreht Soll/Haben!)
Index 16: Buchungstext
Index 17: Zahlungsbedingung
Index 18: Konto voller Satz (default 8400)
Index 19: Konto ermäßigter Satz (default 8300)
Index 20: Zahlungsreferenz
Index 21: Auftragsnummer
Index 22: Storno (1=Storno, ACHTUNG: erzeugt KEINE ACCDOC-Einträge!)
Index 23: Schlussrechnung
Index 24: Erlösart
Index 25: Systemname
Index 26: Gegenrechnung
Index 27: Kostenstelle
Index 28: Lastschriftdatum
Index 29: Land
Index 30: Produktart
```

WICHTIG: Steuerfreie Felder (11/12/14) vs. Revenue-Felder (5/6/18):
- Steuerfreie Felder: Kein Auto-USt auf das Konto (f[11], Haben-Seite),
  ABER Auto-USt auf das Gegenkonto (f[14], Soll-Seite) wenn steuerpflichtig!
- Revenue-Felder: USt wird auf Basis des Erlöskontos (f[18]) berechnet
- Gutschrift (f[15]=1): Dreht Soll/Haben komplett, funktioniert zuverlässig
- Storno (f[22]=1): Wird akzeptiert, aber erzeugt KEINE Buchung in ACCDOC!

## CMXLRN (Lieferantenrechnung Import) - 21 Felder

```
Index  0: Satzart ("CMXLRN")
Index  1: Lieferant-Nr (PFLICHT wenn kein Gegenkonto)
Index  2: Firma Nr ("1")
Index  3: Rechnungsdatum YYYYMMDD
Index  4: Rechnungsnummer
Index  5: Netto voller Satz
Index  6: USt voller Satz (auto wenn leer)
Index  7: Netto ermäßigter Satz
Index  8: USt ermäßigter Satz
Index  9: Sonstige Umsätze Konto
Index 10: Sonstige Umsätze Betrag
Index 11: Währung ("EUR")
Index 12: Gegenkonto (NUR Sachkonten! Nicht 70001!)
Index 13: Gutschrift (1 = dreht Soll/Haben!)
Index 14: Buchungstext
Index 15: Zahlungsbedingung
Index 16: Konto voller Satz (Aufwandskonto, default 3200!)
Index 17: Konto ermäßigter Satz
Index 18: Storno (1 = Storno)
Index 19: Kostenstelle
Index 20: Internes Memo
```

WICHTIG: Feld 16 defaultet auf 3200 (Wareneingang), NICHT auf Lieferanten-Default!
Feld 13 (Gutschrift) dreht zuverlässig, für Stornos verwenden.

## CMXKND (Kunden Import) - Wichtige Felder

```
Index  0: Satzart ("CMXKND")
Index  1: Kundennummer (leer = auto)
Index  2: Firma Nr ("1")
Index  3: Anrede ("Firma")
Index  7: Firma/Name ("Testkunde GmbH")
Index  9: Straße
Index 10: PLZ
Index 11: Ort
Index 14: Land ("DE")
Index 15: Telefon
Index 17: E-Mail
Index 24: USt-IdNr ("DE123456789")
Index 25: Zahlungsbedingung
Index 29: Ausgabemedium (0=Drucken, 1=E-Mail, 2=Fax, 3=Brief, 100=Keine)
```

## CMXPRD (Produkt Import) - Wichtige Felder

```
Index  0: Satzart ("CMXPRD")
Index  1: Produktnummer (z.B. "WEB-DESIGN", alphanumerisch)
Index  2: Bezeichnung
Index  4: Basismengeneinheit (ISO-Code: "PCE"=Stück, NICHT "Stk"!)
Index  6: Firma Nr ("1")
Index  7: Steuerklassifikation (0=voll, 1=ermäßigt, 2=frei)
Index 11: Produktart (0=Ware, 1=Dienstleistung, 2=Mitgliedschaft)
Index 14: Verkaufs-Preis ("3500,00")
```

## PRODUCT_GET (Produkt Abfrage) - 10 Felder

```
PRODUCT_GET;FirmaNr;ProduktNr;Produktgruppe;Preisgruppe;
NurGeaenderte;Systemname;WebauftrittNr;NurMitPreis;Text
```

ACHTUNG: FirmaNr kommt ZUERST, dann ProduktNr!
Anders als CUSTOMER_GET/VENDOR_GET (dort ID zuerst, FirmaNr danach).
Nur FirmaNr nötig für alle Produkte. Antwort als CMXPRD.

## CMXQTN (Angebot Import) - 82 Felder

Struktur fast identisch zu CMXORD-2, gleiche Positions-Indizes!

```
Index  0: Satzart ("CMXQTN")
Index  1: Angebotsnummer (leer = neu)
Index  2: Position
Index  4: Firma Nr ("1")
Index  5: Kunden-Nr
Index 28: Angebotsdatum (YYYYMMDD)
Index 39: Gelöscht (0/1)
Index 47: Gültig bis (YYYYMMDD)
Index 68: Positionstyp (0=Normal)
Index 69: Produktnummer
Index 70: Produktbeschreibung
Index 72: Menge
Index 73: Einzelpreis
Index 77: Produktart (1=Dienstleistung)
Index 78: Steuerklassifikation (0=voll, 1=ermäßigt, 2=frei)
```

## QUOTATION_GET (Angebot Abfrage)

```
QUOTATION_GET;AngebotsNr;FirmaNr;KundeNr;DatumVon;DatumBis;
BriefpapierNicht;RueckgabeFormat;NurGeaenderte;Systemname
```

## CMXORD-2 (Kundenauftrag Import) - 99 Felder

```
Index  0: Satzart ("CMXORD-2")
Index  1: Auftragsnummer (leer = neu)
Index  2: Position
Index  4: Firma Nr ("1")
Index  5: Kunden-Nr
Index 29: Auftragsdatum (YYYYMMDD)
Index 42: Gelöscht (0/1)
Index 71: Positionstyp (0=Normal, 1=Summe, 2=Text, 3=Frei)
Index 72: Produktnummer
Index 73: Produktbeschreibung
Index 75: Menge
Index 76: Einzelpreis (deutsch: "1500,00")
Index 81: Produktart (0=Ware, 1=Dienstleistung, 2=Mitgliedschaft)
Index 82: Steuerklassifikation (0=voll 19%, 1=ermäßigt 7%, 2=steuerfrei)
Index 95: Angebot Nr (nur Export)
Index 98: Lieferrelevant (0=nein, 1=ja), WICHTIG für Dienstleistungen!
```

## SALES_ORDER_GET (Kundenauftrag Abfrage) - 12 Felder

```
SALES_ORDER_GET;AuftragsNr;FirmaNr;KundeNr;DatumVon;DatumBis;
AuftragsNrBeiKunde;RueckgabeFormat;NurGeaenderte;Systemname;
NurVomSystem;BriefpapierNicht
```

Rückgabe-Format: 0=CSV, 1=ZIP mit PDFs. Antwort kommt als CMXORD-2.

## CMXDLV (Lieferung Import) - 72 Felder

```
Index  0: Satzart ("CMXDLV")
Index  1: Lieferscheinnummer (leer = neu)
Index  2: Position
Index  4: Firma Nr ("1")
Index  5: Kunden-Nr
Index  6: Auftrag Nr (Verknüpfung zum Kundenauftrag)
Index 30: Lieferungsdatum (YYYYMMDD)
Index 60: Positionstyp (0=Normal)
Index 61: Produktnummer
Index 62: Produktbeschreibung
Index 64: Menge
Index 65: Kundenauftragsposition
```

Voraussetzung: Auftragspositionen müssen Lieferrelevant=1 haben (CMXORD-2 Index 98).

## DELIVERY_GET (Lieferung Abfrage)

```
DELIVERY_GET;LieferscheinNr;FirmaNr;...
```

## CMXINV (Rechnung Import) - 94 Felder

```
Index  0: Satzart ("CMXINV")
Index  1: Rechnungsnummer (leer = neu)
Index  2: Position
Index  3: Rechnungsart (0=Normal)
Index  4: Firma Nr ("1")
Index  5: Auftrag Nr (Verknüpfung zum Kundenauftrag!)
Index  6: Kunden-Nr
Index 21: Kunde-E-Mail
Index 28: Kunde-USt.IdNr
Index 29: Rechnungsdatum (YYYYMMDD)
Index 40: Gelöscht (0/1)
Index 45: Status (nur Export: 0=Neu, 100=Gelöscht)
Index 51: Liefer/Leistungsdatum (YYYYMMDD)
Index 68: Positionstyp (0=Normal)
Index 69: Produktnummer
Index 70: Produktbeschreibung
Index 72: Menge
Index 73: Einzelpreis
Index 77: Produktart (1=Dienstleistung)
Index 78: Steuerklassifikation (0=voll, 1=ermäßigt, 2=frei)
```

## INVOICE_GET (Rechnung Abfrage) - 12 Felder

```
INVOICE_GET;RechnungsNr;FirmaNr;KundeNr;DatumVon;DatumBis;...
RueckgabeFormat;NurGeaenderte;Systemname;NurVomSystem;
BriefpapierNicht;Rechnungsart
```

## INVOICE_OUTPUT (Rechnung Ausgabe/Versand) - 11 Felder

```
INVOICE_OUTPUT;FirmaNr;RechnungsNr;Ausgabemedium;AusgabeNoetig;
KundeNr;DatumVon;DatumBis;MaxAnzahl;InklGeloeschte;NichtBuchen
```

## INVOICE_OUTPUT_SET (Rechnung als ausgegeben markieren) - 3 Felder

```
INVOICE_OUTPUT_SET;RechnungsNr;Ausgabemedium
```

Ausgabemedium: 0=Drucken, 1=E-Mail, 2=Fax, 3=Brief, 100=Keine Ausgabe

## CMXPRJ (Projekt Import) - Wichtige Felder

```
Index  0: Satzart ("CMXPRJ")
Index  1: Projektnummer (NICHT auto, muss angegeben werden)
Index  2: Firma Nr ("1")
Index  3: Bezeichnung
Index  4: Kunden-Nr
Index  6: Abgeschlossen (0=nein, 1=ja, 2=abgerechnet)
Index  7: Budget
Index 10: Kundenauftrag Nr
```

ACHTUNG: Import wird akzeptiert, aber PROJECT_GET liefert im Tarif
"buchhaltung basic" keine Ergebnisse. Projekt-Modul ggf. nicht enthalten.

## PROJECT_GET (Projekt Abfrage) - 5 Felder

```
PROJECT_GET;ProjektNr;FirmaNr;KundeNr;Status
```

Status: 0/leer=alle, 1=nur aktive, 2=nur abgeschlossene.

## ACCDOC_GET (Abfrage) - 18 Felder

```
ACCDOC_GET;FirmaNr;Geschaeftsjahr;BelegNr;KontoNr;Kostenstelle;
KundenNr;LieferantNr;AnlagenNr;RechnungsNr;ReiseNr;
Text;BelegdatumVon;BelegdatumBis;Stornos;NurGeaenderte;
Systemname;ZahlungsNr
```

WICHTIG: Feld 3 = Geschäftsjahr (z.B. "2026"), NICHT Firma!
`ACCDOC_GET;1;2026` = Firma 1, GJ 2026.
`ACCDOC_GET;1;1` = Firma 1, GJ 1 (gibt 0 Ergebnisse!).

## ACCDOC (Response) - 31 Felder

```
Index  0: "ACCDOC"
Index  1: Firma Nr ("1")
Index  2: Geschäftsjahr ("2026")
Index  3: Belegnummer ("31")
Index  4: Belegdatum ("01.01.2026")
Index  5: Buchungsdatum ("04.03.2026")
Index  6: Buchungstext ("Rechnung Nr EB-2026-001 vom 01.01.2026")
Index  7: Positionsnummer ("1", "2")
Index  8: Kontonummer ("800", "1200", "4900")
Index  9: Kontobezeichnung ("Gezeichnetes Kapital", "Bank")
Index 10: Soll/Haben ("Soll" / "Haben"), Text, nicht 0/1!
Index 11: Betrag ("12500,00" / "-12500,00", negativ bei Haben)
Index 12: Kunden-Nr
Index 13: Kundenname
Index 14: Lieferant-Nr
Index 15: Lieferantname
Index 16: Anlagen-Nr
Index 17: Anlagenname
Index 18: Stornierte Belegnummer
Index 19: Kostenstelle
Index 20: Rechnungsnummer
Index 21: Kundenauftrags-Nr
Index 22: Reise-Nr
Index 23-25: Gegenkonto-Zuordnung
Index 26: Belegnummer (nochmal)
Index 27-28: Datumswerte (YYYYMMDD)
Index 29: Internes Memo
Index 30: Benutzer ("apiuser")
```

WICHTIG: Soll/Haben ist als Text ("Soll"/"Haben"), NICHT als 0/1!
Haben-Beträge sind NEGATIV. Feld 3 = Belegnummer (Response), nicht Periode!

## Key API Findings

1. ACCDOC is READ-ONLY (no import possible)
2. Soll/Haben in ACCDOC_GET: Text "Soll"/"Haben", NICHT 0/1! Haben-Beträge negativ.
3. No NEW_OBJECT_ID returned for CMXLRN/CMXUMS
4. Account 4400 doesn't exist in this instance; 4830 works
5. Collmex "buchhaltung basic" (11.95 EUR) has full API access
6. Konto 1580 (VSt §13b) may not exist, handle gracefully
7. Period 0 = cumulated for ACCBAL_GET
8. Firmenstammdaten (Steuernr, USt-IdNr) sind NICHT per API änderbar
9. E-Rechnungsversand (INVOICE_OUTPUT) braucht: Firma-Steuernr + SMTP-Config in Collmex
10. Mengeneinheiten müssen ISO-Codes sein: PCE (Stück), nicht "Stk"
11. Dienstleistungen brauchen Lieferrelevant=1 (CMXORD-2 Idx 98) für Lieferungen
12. CMXPRJ Import geht ohne Fehler, aber Projekte nicht abrufbar im Basic-Tarif
13. CMXQTN hat fast identische Feldstruktur wie CMXORD-2 (gleiche Positions-Indizes 68-79)
14. CMXUMS kann für beliebige Sachkontenbuchungen genutzt werden (EB, Umbuchungen): Feld 11=Haben, 14=Soll
15. CMXUMS Storno: Konten tauschen (steuerfrei), Gutschrift f[15]='1' (mit USt), oder CMXLRN f[13]='1'
15a. CMXUMS Storno-Flag f[22]='1' wird akzeptiert, erzeugt aber KEINE ACCDOC-Einträge!
15b. CMXUMS steuerfreie Felder (f[11]/f[14]) mit 8400 als Gegenkonto → Auto-USt! Betrag wird als brutto gesplittet
16. ACCDOC_GET Feld 3 = Geschäftsjahr (z.B. "2026"), NICHT Firma (häufige Fehlerquelle!)
17. Sachkonten-Anlage nur per Web-UI möglich (POST an acch-Seite)
14. CMXLRN Gegenkonto (Feld 12) muss Sachkonto sein (1600), NICHT Personenkonto (70001)
15. CMXLRN Aufwandskonto (Feld 16): Default 3200, NICHT aus Lieferantenstamm! Immer explizit setzen.
16. ACCBAL_GET funktioniert NICHT für Personenkonten (70001), nur für Sachkonten
17. OPEN_ITEM Feld 7 = Personenkonto-Nr (Kreditor/Debitor), Feld 8 = Name + Ort
18. Kreditoren starten bei 70001 (auto-vergeben bei CMXLIF mit leerem Feld 1)
19. Lieferanten-Nr = Personenkonto-Nr (70001 = Kreditor 70001)
