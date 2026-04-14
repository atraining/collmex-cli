# Kaufmaennische Routinen — Checklisten fuer den Agenten

Dieses Dokument beschreibt die Pruef-Routinen eines kaufmaennischen Leiters.
Der Agent arbeitet diese Checklisten periodisch ab, dokumentiert Ergebnisse
in `mandant/berichte/` und meldet Widersprueche.

---

## Taeglich

### T1: Bankabgleich

- **Pruefung:** Alle Kontobewegungen mit offenen Posten abgleichen
- **Konten:** 1200 (Bank), 1210 (Bank 2), 1360 (Geldtransit)
- **Collmex:** ACCBAL_GET fuer Bankkonten, OPEN_ITEMS_GET
- **Typische Fehler:**
  - Zahlungseingang falschem Debitor zugeordnet
  - Bankgebuehren nicht gebucht (→ 4970 Nebenkosten Geldverkehr)
  - Lastschriftrueckgaben uebersehen
- **Aktion:** Fehlbuchung stornieren. Ungeklaerte Zahlungen auf 1590 parken, innerhalb 10 Tagen klaeren.

### T2: Eingangsrechnungen erfassen

- **Pruefung:** Eingegangene Rechnungen auf Pflichtangaben (§14 UStG) pruefen, kontieren, erfassen
- **Konten:** Aufwandskonten (typ-abhaengig), 1576 (VSt 19%), 1571 (VSt 7%), Kreditoren 70000+
- **Collmex:** CMXLRN — Aufwandskonto IMMER explizit in Feld 16!
- **Typische Fehler:**
  - Pflichtangaben fehlen (USt-IdNr, Leistungszeitraum, fortlaufende Nr)
  - VSt abgezogen obwohl Rechnung formell fehlerhaft
  - §13b (Reverse Charge) bei auslaendischen Rechnungen nicht erkannt
  - Falsches Aufwandskonto (Default 3200 statt korrekt z.B. 4900)
- **Aktion:** Korrigierte Rechnung anfordern. §13b: USt auf 1787, VSt auf 1577. Fehlkontierung stornieren.

### T3: Zahlungseingaenge zuordnen

- **Pruefung:** Eingegangene Zahlungen offenen Debitoren-Rechnungen zuordnen
- **Konten:** 1200 (Bank), Debitoren 10000-69999
- **Collmex:** OPEN_ITEMS_GET, Zahlungszuordnung
- **Typische Fehler:**
  - Zahlung falschem Kunden zugeordnet
  - Skonto gewaehrt obwohl Frist abgelaufen (→ 8736)
  - Teilzahlungen als Vollzahlung verbucht
- **Aktion:** OP-Zuordnung korrigieren. Ungeklaerte Zahlungen auf 1590 parken.

---

## Woechentlich

### W1: Offene Posten Debitoren (OPOS)

- **Pruefung:** Alle ueberfaelligen Forderungen identifizieren (0-14d, 15-30d, 31-60d, 60d+)
- **Konten:** Debitoren 10000-69999
- **Collmex:** OPEN_ITEMS_GET — positive Betraege = Debitoren
- **Typische Fehler:**
  - Bereits bezahlte Rechnungen noch offen (Zuordnungsfehler)
  - Gutschriften nicht verrechnet
  - Mahnungen an Kunden die schon bezahlt haben
- **Aktion:** Falsche Zuordnungen korrigieren. Gutschriften verrechnen. Mahnstufe eskalieren.

### W2: Mahnlauf

- **Pruefung:** Automatischer Mahnlauf. 3 Stufen: Zahlungserinnerung → Mahnung → Letzte Mahnung
- **Konten:** Debitoren, 8101 (Mahngebuehren), 2400 (Forderungsverluste)
- **Collmex:** `collmex mahnlauf`
- **Typische Fehler:**
  - Mahnung an gesperrte Kunden (Zahlungsvereinbarung, Reklamation)
  - Verjaehrung droht (3 Jahre, §195 BGB)
- **Aktion:** Mahnsperren pruefen. Uneintreibbare Forderungen: Einzelwertberichtigung (2451).

### W3: Kreditoren-OPOS und Zahlungsplanung

- **Pruefung:** Faellige Lieferantenrechnungen, Skontofaehige priorisieren
- **Konten:** Kreditoren 70000+, 1200 (Bank), 3736 (Erhaltene Skonti 19%)
- **Collmex:** OPEN_ITEMS_GET — negative Betraege = Kreditoren
- **Typische Fehler:**
  - Skontofrist verpasst (2-3% Verlust)
  - Doppelzahlung
- **Aktion:** Skonto-Priorisierung. Doppelzahlung zurueckfordern.

### W4: Liquiditaetsvorschau

- **Pruefung:** Ein-/Auszahlungen naechste 2-4 Wochen, Kontostand-Prognose
- **Konten:** 1200 (Bank), 0630-0660 (Darlehen)
- **Collmex:** `collmex liquiditaet`
- **Typische Fehler:**
  - Grosse Zahlungen vergessen (USt, Loehne, Miete)
  - Kundenzahlungen zu optimistisch
- **Aktion:** Bei Unterdeckung: Zahlungen strecken, Kreditlinie nutzen.

### W5: Verrechnungskonten pruefen

- **Pruefung:** 1590, 1360, 1361 — muessen auf Null stehen. Posten >2 Wochen = Warnsignal.
- **Konten:** 1590 (Durchlaufende Posten), 1360 (Geldtransit), 1361 (Kreditkarten)
- **Collmex:** ACCBAL_GET fuer diese Konten
- **Typische Fehler:**
  - Verrechnungskonten als "Muellhalde" fuer ungeklaerte Posten
  - Posten seit Monaten nicht geklaert
- **Aktion:** Jeden Posten klaeren und umbuchen. Ziel: Saldo = 0.

---

## Monatlich

### M1: USt-Voranmeldung

- **Pruefung:** USt aus Ausgangsrechnungen minus VSt aus Eingangsrechnungen = Zahllast
- **Frist:** 10. des Folgemonats (mit Dauerfrist: 10. des uebernachsten)
- **Konten:** 1775 (USt 19%), 1770 (USt 7%), 1576 (VSt 19%), 1571 (VSt 7%), 1577 (VSt §13b), 1787 (USt §13b), 1780 (USt-Vorauszahlung)
- **Collmex:** `collmex ustva`
- **Typische Fehler:**
  - VSt aus nicht abzugsfaehiger Bewirtung zu 100% abgezogen (nur 70%!)
  - Innergemeinschaftliche Lieferungen falsch als steuerpflichtig
  - §13b-Faelle fehlen
  - Differenz USt-Konten vs. Voranmeldung
- **Aktion:** USt-Konten einzeln abstimmen. §13b nachbuchen. Korrekte Meldung via ELSTER.

### M2: BWA pruefen

- **Pruefung:** Erloese, Wareneinsatz, Personalkosten, EBIT — Monatsvergleich + vs. Vorjahr
- **Konten:** Erloese 8000-8999, Aufwand 4000-7999
- **Collmex:** `collmex soll-ist`
- **Typische Fehler:**
  - Einmaleffekte verzerren BWA (Jahresrechnung Versicherung)
  - Periodenfremd gebuchte Erloese
  - Abschreibungen fehlen → Gewinn zu hoch
- **Aktion:** Periodenabgrenzungen buchen (RAP). Abweichungen >10% im Detail pruefen.

### M3: Kontenabstimmung

- **Pruefung:** Alle wesentlichen Bilanzkonten auf Plausibilitaet
- **Checkliste:**
  - Bank (1200/1210): Saldo = Kontoauszug?
  - Kasse (1000): Saldo = physischer Bestand?
  - Debitoren-Summe (10000-69999) = Saldo 1400?
  - Kreditoren-Summe (70000+) = Saldo 1600?
  - USt-Konten gegenseitig stimmig?
  - Verrechnungskonten (1590/1360) = Null?
- **Collmex:** ACCBAL_GET, OPEN_ITEMS_GET
- **Typische Fehler:**
  - Debitorensumme weicht von Sammelkonto 1400 ab
  - Banksalden stimmen nicht mit Auszuegen ueberein
- **Aktion:** Differenzanalyse. Fehlbuchungen stornieren und korrekt nachbuchen.

### M4: Debitoren-/Kreditoren-Abstimmung

- **Pruefung:** Personenkonten-Salden. Debitoren mit Haben-Saldo? Kreditoren mit Soll-Saldo?
- **Konten:** 10000-69999, 70000+, 1400, 1600
- **Collmex:** OPEN_ITEMS_GET
- **Typische Fehler:**
  - Doppelte Personenkonten fuer gleichen Kunden/Lieferanten
  - Skonto falsch verbucht (fehlende USt-Korrektur)
  - OP-Saldo ≠ Kontensaldo
- **Aktion:** Doppelte Konten zusammenfuehren. Skontobuchungen korrigieren.

### M5: Abschreibungen (AfA)

- **Pruefung:** Monatliche planmaessige AfA buchen. Neue Anschaffungen pruefen.
- **Konten:** 4830 (AfA Sachanlagen), 4855 (GWG bis 800 EUR netto), 0200-0480 (Sachanlagen)
- **Typische Fehler:**
  - AfA bei unterjahrigem Zugang nicht monatsgenau
  - GWG-Grenze (800 netto) mit Brutto verwechselt
  - Abgang nicht gebucht bei Verkauf/Verschrottung
- **Aktion:** AfA-Plan korrigieren. Fehlende Monate nachbuchen.

### M6: Rueckstellungen und Abgrenzungen

- **Pruefung:** Zeitliche Abgrenzung, Rueckstellungen fuer bekannte Verpflichtungen
- **Konten:** 0980 (aRAP), 0990 (pRAP), 0970 (Rueckstellungen), 0955 (Abschlusskosten)
- **Typische Fehler:**
  - Jahresvorauszahlungen nicht abgegrenzt → BWA verzerrt
  - Vorjahres-Rueckstellungen nicht aufgeloest (→ 2735)
- **Aktion:** RAP buchen. Rueckstellungen bilden/aufloesen.

---

## Quartalsweise

### Q1: Zusammenfassende Meldung (ZM)

- **Pruefung:** Alle innergemeinschaftlichen Lieferungen/Leistungen an EU-Unternehmen
- **Frist:** 25. des Folgemonats nach Quartalsende
- **Konten:** 8125 (steuerfreie igL), 8336 (Erloese sonstige Leistungen EU §13b)
- **Typische Fehler:**
  - USt-IdNr des Kunden falsch/fehlend
  - Nicht als steuerfrei gebucht
  - ZM-Summen ≠ USt-Voranmeldung
- **Aktion:** USt-IdNr ueber BZSt pruefen. Korrekturen nachmelden.

### Q2: Steuervorauszahlungen pruefen

- **Pruefung:** KSt + GewSt — stimmen Vorauszahlungen noch zum erwarteten Gewinn?
- **Fristen:** KSt: 10.03/06/09/12. GewSt: 15.02/05/08/11.
- **Konten:** 2200 (KSt), 2203 (KSt-VZ), 4320 (GewSt), 1550/1800 (FA-Forderungen/-Verbindl.)
- **Typische Fehler:**
  - VZ basiert auf veraltetem Gewinn
  - Saumniszuschlaege: 1% pro Monat bei verspaeteter Zahlung
- **Aktion:** Herabsetzungsantrag bei Gewinneinbruch. Ruecklage bei Mehrgewinn.

### Q3: Soll-Ist-Vergleich

- **Pruefung:** Plan vs. Ist ueber Quartal. Hochrechnung Gesamtjahr (Forecast).
- **Konten:** Erloese 8000-8999, Aufwand 4000-7999
- **Collmex:** `collmex soll-ist`
- **Aktion:** Plan aktualisieren. Massnahmen bei negativer Abweichung. Management-Report.

---

## Jaehrlich

### J1: Jahresabschluss vorbereiten

- **Pruefung:** Inventur aller Bilanzpositionen. Bilanz + GuV erstellen.
- **Checkliste:**
  - Anlagevermoegen: Anlagespiegel vollstaendig, AfA korrekt
  - Forderungen: Einzelwertberichtigung (2451), Pauschalwertberichtigung (2450)
  - Bank/Kasse: Saldenbestaetigung einholen
  - Verbindlichkeiten: Alle ER zum 31.12. erfasst?
  - Rueckstellungen: Abschlusskosten (0955), Urlaubsrueckstellungen, Gewaehrleistungen
  - RAP: Alle periodenuebergreifenden Buchungen abgegrenzt
  - Eigenkapital: Gesellschafterbeschluesse beruecksichtigt

### J2: USt-Jahreserklaerung

- **Frist:** 31.07. (mit Steuerberater: 28.02. uebernachstes Jahr)
- **Konten:** Alle USt-Konten (1770, 1775, 1776, 1571, 1576, 1577, 1780, 1787, 1789, 1790)
- **Pruefung:** Summe Voranmeldungen = Jahreserklaerung?
- **Aktion:** Konten 1789/1790 sauber abschliessen. Differenz auf 1780.

### J3: KSt-/GewSt-Erklaerung

- **Konten:** 2200 (KSt), 4320 (GewSt), 0963 (Steuer-RS)
- **Typische Fehler:**
  - Nicht abzugsfaehige BA abgezogen (Geschenke >50 EUR → 4630)
  - GewSt-Hinzurechnungen (Zinsen, Mieten, Lizenzen) fehlen
  - Verlustvortrag falsch

### J4: DATEV-Export und E-Bilanz

- **Collmex:** `collmex datev`
- **Pruefung:** Export DATEV-Format, E-Bilanz taxonomie-konform
- **Typische Fehler:** Kontenmapping auf Taxonomie fehlerhaft, Zeichensatz-Probleme

### J5: Offenlegung Bundesanzeiger

- **Frist:** 12 Monate nach Bilanzstichtag
- **Pruefung:** Bilanz + Anhang einreichen (kleine GmbH: Bilanz reicht)
- **Groessenkriterien kleine GmbH:** Bilanzsumme ≤6 Mio, Umsatz ≤12 Mio, ≤50 MA
- **Ordnungsgeld bei Verspaetung:** 2.500-25.000 EUR

### J6: Budgetplanung Folgejahr

- **Daten:** BWA Vorjahr, Auftragsbestand, Investitionen, Personal
- **Aktion:** 3 Szenarien (Best/Base/Worst). Monatliche Granularitaet.

---

## Fristenkalender (Zusammenfassung)

| Termin | Was | An wen |
|--------|-----|--------|
| 10. Folgemonat | USt-Voranmeldung + Zahlung | Finanzamt (ELSTER) |
| 10. Folgemonat | Lohnsteuer-Anmeldung | Finanzamt |
| Drittletzter Bankarbeitstag | SV-Beitraege | Krankenkasse |
| 25. nach Quartalsende | Zusammenfassende Meldung | BZSt |
| 10.03/06/09/12 | KSt-Vorauszahlung | Finanzamt |
| 15.02/05/08/11 | GewSt-Vorauszahlung | Gemeinde |
| 15.02. | SV-Jahresmeldung | Krankenkasse |
| 28.02. | Lohnsteuer-Bescheinigungen | Finanzamt + AN |
| 31.07. (bzw. 28.02. m. StB) | USt-/KSt-/GewSt-Jahreserklaerung | Finanzamt |
| 12 Mon. nach Stichtag | Offenlegung Jahresabschluss | Unternehmensregister |
