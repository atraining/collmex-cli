# SKR04 Kontenrahmen: Wissensgrundlage

Der SKR04 (Abschlussgliederungsprinzip) ordnet Konten nach Bilanz/GuV-Gliederung.
Klassen 0-3 = Bilanz, Klassen 4-7 = GuV.
Klassen 5 und 6 SIND belegt (anders als SKR03!).

## Kontenklassen-Übersicht

| Klasse | Inhalt | Bilanz/GuV |
|--------|--------|------------|
| 0 | Anlagevermögen | Bilanz (Aktiva) |
| 1 | Umlaufvermögen, Rechnungsabgrenzung | Bilanz (Aktiva) |
| 2 | Eigenkapital, Rückstellungen | Bilanz (Passiva) |
| 3 | Verbindlichkeiten, Rechnungsabgrenzung | Bilanz (Passiva) |
| 4 | Erlöse | GuV (Ertrag) |
| 5 | Material-/Wareneinsatz | GuV (Aufwand) |
| 6 | Personalkosten, Abschreibungen, sonstige Aufwand | GuV (Aufwand) |
| 7 | Sonstige Erträge, Zinsen | GuV (Ertrag/Aufwand) |
| 8 | (leer / nicht genutzt in Standard-SKR04) | - |
| 9 | Vortrags-/statistische Konten | Sonstiges |

## Mapping SKR04 → SKR03 (häufigste Konten)

### Bilanzkonten (Klasse 0-3)

| SKR04 | SKR03 | Bezeichnung |
|-------|-------|-------------|
| 0027 | 0027 | EDV-Software |
| 0200 | 0200 | Techn. Anlagen und Maschinen |
| 0320 | 0320 | Pkw |
| 0400 | 0400 | Betriebsausstattung |
| 0410 | 0410 | Geschäftsausstattung |
| 0420 | 0420 | Büroeinrichtung |
| 0480 | 0480 | GWG |
| 0630 | 0630 | Verbindl. ggü. Kreditinstituten |
| 0800 | 0800 | Gezeichnetes Kapital |
| 1000 | 1000 | Kasse |
| 1200 | 1400 | Forderungen aus LuL |
| 1400 | 1550 | Sonstige Vermögensgegenstände |
| 1406 | 1545 | Ford. aus USt-Vorauszahlungen |
| 1576 | 1576 | Abziehbare Vorsteuer 19% |
| 1571 | 1571 | Abziehbare Vorsteuer 7% |
| 1800 | 1200 | Bank |
| 1810 | 1210 | Bank 2 |
| 1890 | 1590 | Durchlaufende Posten |
| 2000 | 0800 | Gezeichnetes Kapital |
| 3272 | 1718 | Erhaltene Anzahlungen 19% USt |
| 3300 | 1600 | Verbindl. aus LuL |
| 3740 | 1741 | Verbindl. Lohnsteuer |
| 3741 | 1742 | Verbindl. Sozialversicherung |
| 3806 | 1776 | Umsatzsteuer 19% |
| 3801 | 1771 | Umsatzsteuer 7% |
| 3820 | 1780 | USt-Vorauszahlungen |

### GuV-Konten Erlöse (Klasse 4)

| SKR04 | SKR03 | Bezeichnung |
|-------|-------|-------------|
| 4400 | 8400 | Erlöse 19% USt |
| 4300 | 8300 | Erlöse 7% USt |
| 4200 | 8200 | Erlöse |
| 4125 | 8125 | Steuerfreie igL |
| 4336 | 8336 | Erlöse sonst. Leistungen EU §13b |
| 4700 | 8700 | Erlösschmälerungen |

### GuV-Konten Aufwand (Klasse 5-6)

| SKR04 | SKR03 | Bezeichnung |
|-------|-------|-------------|
| 5000 | 3000 | Roh-, Hilfs-, Betriebsstoffe |
| 5200 | 3200 | Wareneingang |
| 5900 | 3100 | Fremdleistungen |
| 6000 | 4100 | Löhne und Gehälter |
| 6010 | 4110 | Löhne |
| 6020 | 4120 | Gehälter |
| 6030 | 4124 | GF-Gehälter GmbH-Gesellschafter |
| 6040 | 4130 | Gesetzl. soziale Aufwendungen |
| 6100 | 4830 | AfA Sachanlagen |
| 6110 | 4831 | AfA Gebäude |
| 6120 | 4832 | AfA Kfz |
| 6160 | 4855 | Sofortabschreibung GWG |
| 6200 | 4200 | Raumkosten |
| 6210 | 4210 | Miete |
| 6230 | 4240 | Gas/Strom/Wasser |
| 6300 | 4900 | Sonstige betriebliche Aufwendungen |
| 6310 | 4910 | Porto |
| 6320 | 4920 | Telefon |
| 6325 | 4925 | Internet |
| 6330 | 4930 | Bürobedarf |
| 6400 | 4500 | Fahrzeugkosten |
| 6410 | 4510 | Kfz-Steuer |
| 6420 | 4520 | Kfz-Versicherungen |
| 6500 | 4600 | Werbekosten |
| 6610 | 4650 | Bewirtungskosten (70%) |
| 6620 | 4654 | Nicht abzugsf. Bewirtung (30%) |
| 6630 | 4660 | Reisekosten AN |
| 6640 | 4670 | Reisekosten Unternehmer |
| 6700 | 4950 | Rechts-/Beratungskosten |
| 6805 | 4970 | Nebenkosten Geldverkehr |
| 6815 | 4360 | Versicherungen |
| 6820 | 4380 | Beiträge |

### Zinsen und Steuern (Klasse 7)

| SKR04 | SKR03 | Bezeichnung |
|-------|-------|-------------|
| 7000 | 2700 | Sonstige Erträge |
| 7100 | 2650 | Zinserträge |
| 7300 | 2100 | Zinsaufwendungen |
| 7600 | 2200 | Körperschaftsteuer |
| 7610 | 4320 | Gewerbesteuer |

## Erkennungsmerkmale SKR04 vs. SKR03

| Merkmal | SKR03 | SKR04 |
|---------|-------|-------|
| Erlöse 19% | **8400** | **4400** |
| Bank | **1200** | **1800** |
| Forderungen LuL | **1400** | **1200** |
| Verbindl. LuL | **1600** | **3300** |
| Fremdleistungen | **4900** | **6300** |
| AfA Sachanlagen | **4830** | **6100** |
| Wareneingang | **3200** | **5200** |
| Klassen 5+6 | leer | belegt |
| Klasse 8 | Erlöse | leer |

Schnelltest: Existiert Konto 4400 mit Erlösen? → SKR04.
Existiert Konto 8400 mit Erlösen? → SKR03.

## Beispiel: Abo-Abrechnung (periodengerecht)

Typisches Muster aus einem SaaS-/Abo-Mandanten:
- **4400** Erlöse 19% USt → Ausgangsrechnungen
- **3272** Erhaltene Anzahlungen 19% USt → Abo-Vorauszahlungen
- Debitoren: durchnummeriert im Bereich `10100 - 11999` (Industrie/Endkunden)
- Buchungsmuster: Abo-Erlöse werden über 3272 (Erhaltene Anzahlungen)
  periodengerecht abgegrenzt und zum Leistungsbeginn auf 4400 umgebucht.
