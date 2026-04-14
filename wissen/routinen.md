# Kaufmännische Routinen — Checklisten für den Agenten

Dieses Dokument beschreibt die Prüf-Routinen eines kaufmännischen Leiters.
Der Agent arbeitet diese Checklisten periodisch ab, dokumentiert Ergebnisse
in `mandant/berichte/` und meldet Widersprüche.

---

## Täglich

### T1: Bankabgleich

- **Prüfung:** Alle Kontobewegungen mit offenen Posten abgleichen
- **Konten:** 1200 (Bank), 1210 (Bank 2), 1360 (Geldtransit)
- **Collmex:** ACCBAL_GET für Bankkonten, OPEN_ITEMS_GET
- **Typische Fehler:**
  - Zahlungseingang falschem Debitor zugeordnet
  - Bankgebühren nicht gebucht (→ 4970 Nebenkosten Geldverkehr)
  - Lastschriftrückgaben übersehen
- **Aktion:** Fehlbuchung stornieren. Ungeklärte Zahlungen auf 1590 parken, innerhalb 10 Tagen klären.

### T2: Eingangsrechnungen erfassen

- **Prüfung:** Eingegangene Rechnungen auf Pflichtangaben (§14 UStG) prüfen, kontieren, erfassen
- **Konten:** Aufwandskonten (typ-abhängig), 1576 (VSt 19%), 1571 (VSt 7%), Kreditoren 70000+
- **Collmex:** CMXLRN — Aufwandskonto IMMER explizit in Feld 16!
- **Typische Fehler:**
  - Pflichtangaben fehlen (USt-IdNr, Leistungszeitraum, fortlaufende Nr)
  - VSt abgezogen obwohl Rechnung formell fehlerhaft
  - §13b (Reverse Charge) bei ausländischen Rechnungen nicht erkannt
  - Falsches Aufwandskonto (Default 3200 statt korrekt z.B. 4900)
- **Aktion:** Korrigierte Rechnung anfordern. §13b: USt auf 1787, VSt auf 1577. Fehlkontierung stornieren.

### T3: Zahlungseingänge zuordnen

- **Prüfung:** Eingegangene Zahlungen offenen Debitoren-Rechnungen zuordnen
- **Konten:** 1200 (Bank), Debitoren 10000-69999
- **Collmex:** OPEN_ITEMS_GET, Zahlungszuordnung
- **Typische Fehler:**
  - Zahlung falschem Kunden zugeordnet
  - Skonto gewährt obwohl Frist abgelaufen (→ 8736)
  - Teilzahlungen als Vollzahlung verbucht
- **Aktion:** OP-Zuordnung korrigieren. Ungeklärte Zahlungen auf 1590 parken.

---

## Wöchentlich

### W1: Offene Posten Debitoren (OPOS)

- **Prüfung:** Alle überfälligen Forderungen identifizieren (0-14d, 15-30d, 31-60d, 60d+)
- **Konten:** Debitoren 10000-69999
- **Collmex:** OPEN_ITEMS_GET — positive Beträge = Debitoren
- **Typische Fehler:**
  - Bereits bezahlte Rechnungen noch offen (Zuordnungsfehler)
  - Gutschriften nicht verrechnet
  - Mahnungen an Kunden die schon bezahlt haben
- **Aktion:** Falsche Zuordnungen korrigieren. Gutschriften verrechnen. Mahnstufe eskalieren.

### W2: Mahnlauf

- **Prüfung:** Automatischer Mahnlauf. 3 Stufen: Zahlungserinnerung → Mahnung → Letzte Mahnung
- **Konten:** Debitoren, 8101 (Mahngebühren), 2400 (Forderungsverluste)
- **Collmex:** `collmex mahnlauf`
- **Typische Fehler:**
  - Mahnung an gesperrte Kunden (Zahlungsvereinbarung, Reklamation)
  - Verjährung droht (3 Jahre, §195 BGB)
- **Aktion:** Mahnsperren prüfen. Uneintreibbare Forderungen: Einzelwertberichtigung (2451).

### W3: Kreditoren-OPOS und Zahlungsplanung

- **Prüfung:** Fällige Lieferantenrechnungen, Skontofähige priorisieren
- **Konten:** Kreditoren 70000+, 1200 (Bank), 3736 (Erhaltene Skonti 19%)
- **Collmex:** OPEN_ITEMS_GET — negative Beträge = Kreditoren
- **Typische Fehler:**
  - Skontofrist verpasst (2-3% Verlust)
  - Doppelzahlung
- **Aktion:** Skonto-Priorisierung. Doppelzahlung zurückfordern.

### W4: Liquiditätsvorschau

- **Prüfung:** Ein-/Auszahlungen nächste 2-4 Wochen, Kontostand-Prognose
- **Konten:** 1200 (Bank), 0630-0660 (Darlehen)
- **Collmex:** `collmex liquiditaet`
- **Typische Fehler:**
  - Große Zahlungen vergessen (USt, Löhne, Miete)
  - Kundenzahlungen zu optimistisch
- **Aktion:** Bei Unterdeckung: Zahlungen strecken, Kreditlinie nutzen.

### W5: Verrechnungskonten prüfen

- **Prüfung:** 1590, 1360, 1361 — müssen auf Null stehen. Posten >2 Wochen = Warnsignal.
- **Konten:** 1590 (Durchlaufende Posten), 1360 (Geldtransit), 1361 (Kreditkarten)
- **Collmex:** ACCBAL_GET für diese Konten
- **Typische Fehler:**
  - Verrechnungskonten als "Müllhalde" für ungeklärte Posten
  - Posten seit Monaten nicht geklärt
- **Aktion:** Jeden Posten klären und umbuchen. Ziel: Saldo = 0.

---

## Monatlich

### M1: USt-Voranmeldung

- **Prüfung:** USt aus Ausgangsrechnungen minus VSt aus Eingangsrechnungen = Zahllast
- **Frist:** 10. des Folgemonats (mit Dauerfrist: 10. des übernächsten)
- **Konten:** 1775 (USt 19%), 1770 (USt 7%), 1576 (VSt 19%), 1571 (VSt 7%), 1577 (VSt §13b), 1787 (USt §13b), 1780 (USt-Vorauszahlung)
- **Collmex:** `collmex ustva`
- **Typische Fehler:**
  - VSt aus nicht abzugsfähiger Bewirtung zu 100% abgezogen (nur 70%!)
  - Innergemeinschaftliche Lieferungen falsch als steuerpflichtig
  - §13b-Fälle fehlen
  - Differenz USt-Konten vs. Voranmeldung
- **Aktion:** USt-Konten einzeln abstimmen. §13b nachbuchen. Korrekte Meldung via ELSTER.

### M2: BWA prüfen

- **Prüfung:** Erlöse, Wareneinsatz, Personalkosten, EBIT — Monatsvergleich + vs. Vorjahr
- **Konten:** Erlöse 8000-8999, Aufwand 4000-7999
- **Collmex:** `collmex soll-ist`
- **Typische Fehler:**
  - Einmaleffekte verzerren BWA (Jahresrechnung Versicherung)
  - Periodenfremd gebuchte Erlöse
  - Abschreibungen fehlen → Gewinn zu hoch
- **Aktion:** Periodenabgrenzungen buchen (RAP). Abweichungen >10% im Detail prüfen.

### M3: Kontenabstimmung

- **Prüfung:** Alle wesentlichen Bilanzkonten auf Plausibilität
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
  - Banksalden stimmen nicht mit Auszügen überein
- **Aktion:** Differenzanalyse. Fehlbuchungen stornieren und korrekt nachbuchen.

### M4: Debitoren-/Kreditoren-Abstimmung

- **Prüfung:** Personenkonten-Salden. Debitoren mit Haben-Saldo? Kreditoren mit Soll-Saldo?
- **Konten:** 10000-69999, 70000+, 1400, 1600
- **Collmex:** OPEN_ITEMS_GET
- **Typische Fehler:**
  - Doppelte Personenkonten für gleichen Kunden/Lieferanten
  - Skonto falsch verbucht (fehlende USt-Korrektur)
  - OP-Saldo ≠ Kontensaldo
- **Aktion:** Doppelte Konten zusammenführen. Skontobuchungen korrigieren.

### M5: Abschreibungen (AfA)

- **Prüfung:** Monatliche planmäßige AfA buchen. Neue Anschaffungen prüfen.
- **Konten:** 4830 (AfA Sachanlagen), 4855 (GWG bis 800 EUR netto), 0200-0480 (Sachanlagen)
- **Typische Fehler:**
  - AfA bei unterjährigem Zugang nicht monatsgenau
  - GWG-Grenze (800 netto) mit Brutto verwechselt
  - Abgang nicht gebucht bei Verkauf/Verschrottung
- **Aktion:** AfA-Plan korrigieren. Fehlende Monate nachbuchen.

### M6: Rückstellungen und Abgrenzungen

- **Prüfung:** Zeitliche Abgrenzung, Rückstellungen für bekannte Verpflichtungen
- **Konten:** 0980 (aRAP), 0990 (pRAP), 0970 (Rückstellungen), 0955 (Abschlusskosten)
- **Typische Fehler:**
  - Jahresvorauszahlungen nicht abgegrenzt → BWA verzerrt
  - Vorjahres-Rückstellungen nicht aufgelöst (→ 2735)
- **Aktion:** RAP buchen. Rückstellungen bilden/auflösen.

---

## Quartalsweise

### Q1: Zusammenfassende Meldung (ZM)

- **Prüfung:** Alle innergemeinschaftlichen Lieferungen/Leistungen an EU-Unternehmen
- **Frist:** 25. des Folgemonats nach Quartalsende
- **Konten:** 8125 (steuerfreie igL), 8336 (Erlöse sonstige Leistungen EU §13b)
- **Typische Fehler:**
  - USt-IdNr des Kunden falsch/fehlend
  - Nicht als steuerfrei gebucht
  - ZM-Summen ≠ USt-Voranmeldung
- **Aktion:** USt-IdNr über BZSt prüfen. Korrekturen nachmelden.

### Q2: Steuervorauszahlungen prüfen

- **Prüfung:** KSt + GewSt — stimmen Vorauszahlungen noch zum erwarteten Gewinn?
- **Fristen:** KSt: 10.03/06/09/12. GewSt: 15.02/05/08/11.
- **Konten:** 2200 (KSt), 2203 (KSt-VZ), 4320 (GewSt), 1550/1800 (FA-Forderungen/-Verbindl.)
- **Typische Fehler:**
  - VZ basiert auf veraltetem Gewinn
  - Säumniszuschläge: 1% pro Monat bei verspäteter Zahlung
- **Aktion:** Herabsetzungsantrag bei Gewinneinbruch. Rücklage bei Mehrgewinn.

### Q3: Soll-Ist-Vergleich

- **Prüfung:** Plan vs. Ist über Quartal. Hochrechnung Gesamtjahr (Forecast).
- **Konten:** Erlöse 8000-8999, Aufwand 4000-7999
- **Collmex:** `collmex soll-ist`
- **Aktion:** Plan aktualisieren. Maßnahmen bei negativer Abweichung. Management-Report.

---

## Jährlich

### J1: Jahresabschluss vorbereiten

- **Prüfung:** Inventur aller Bilanzpositionen. Bilanz + GuV erstellen.
- **Checkliste:**
  - Anlagevermögen: Anlagespiegel vollständig, AfA korrekt
  - Forderungen: Einzelwertberichtigung (2451), Pauschalwertberichtigung (2450)
  - Bank/Kasse: Saldenbestätigung einholen
  - Verbindlichkeiten: Alle ER zum 31.12. erfasst?
  - Rückstellungen: Abschlusskosten (0955), Urlaubsrückstellungen, Gewährleistungen
  - RAP: Alle periodenübergreifenden Buchungen abgegrenzt
  - Eigenkapital: Gesellschafterbeschlüsse berücksichtigt

### J2: USt-Jahreserklärung

- **Frist:** 31.07. (mit Steuerberater: 28.02. übernächstes Jahr)
- **Konten:** Alle USt-Konten (1770, 1775, 1776, 1571, 1576, 1577, 1780, 1787, 1789, 1790)
- **Prüfung:** Summe Voranmeldungen = Jahreserklärung?
- **Aktion:** Konten 1789/1790 sauber abschließen. Differenz auf 1780.

### J3: KSt-/GewSt-Erklärung

- **Konten:** 2200 (KSt), 4320 (GewSt), 0963 (Steuer-RS)
- **Typische Fehler:**
  - Nicht abzugsfähige BA abgezogen (Geschenke >50 EUR → 4630)
  - GewSt-Hinzurechnungen (Zinsen, Mieten, Lizenzen) fehlen
  - Verlustvortrag falsch

### J4: DATEV-Export und E-Bilanz

- **Collmex:** `collmex datev`
- **Prüfung:** Export DATEV-Format, E-Bilanz taxonomie-konform
- **Typische Fehler:** Kontenmapping auf Taxonomie fehlerhaft, Zeichensatz-Probleme

### J5: Offenlegung Bundesanzeiger

- **Frist:** 12 Monate nach Bilanzstichtag
- **Prüfung:** Bilanz + Anhang einreichen (kleine GmbH: Bilanz reicht)
- **Größenkriterien kleine GmbH:** Bilanzsumme ≤6 Mio, Umsatz ≤12 Mio, ≤50 MA
- **Ordnungsgeld bei Verspätung:** 2.500-25.000 EUR

### J6: Budgetplanung Folgejahr

- **Daten:** BWA Vorjahr, Auftragsbestand, Investitionen, Personal
- **Aktion:** 3 Szenarien (Best/Base/Worst). Monatliche Granularität.

---

## Fristenkalender (Zusammenfassung)

| Termin | Was | An wen |
|--------|-----|--------|
| 10. Folgemonat | USt-Voranmeldung + Zahlung | Finanzamt (ELSTER) |
| 10. Folgemonat | Lohnsteuer-Anmeldung | Finanzamt |
| Drittletzter Bankarbeitstag | SV-Beiträge | Krankenkasse |
| 25. nach Quartalsende | Zusammenfassende Meldung | BZSt |
| 10.03/06/09/12 | KSt-Vorauszahlung | Finanzamt |
| 15.02/05/08/11 | GewSt-Vorauszahlung | Gemeinde |
| 15.02. | SV-Jahresmeldung | Krankenkasse |
| 28.02. | Lohnsteuer-Bescheinigungen | Finanzamt + AN |
| 31.07. (bzw. 28.02. m. StB) | USt-/KSt-/GewSt-Jahreserklärung | Finanzamt |
| 12 Mon. nach Stichtag | Offenlegung Jahresabschluss | Unternehmensregister |
