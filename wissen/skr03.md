# SKR03 Kontenrahmen — Wissensgrundlage

Der SKR03 (Prozessgliederungsprinzip) ordnet Konten nach dem Ablauf
betrieblicher Prozesse. Klassen 0-2 Bilanz, Klasse 3 Wareneingang,
Klasse 4 Aufwand, Klassen 5+6 **leer**, Klasse 7 Bestände, Klasse 8
Erlöse, Klasse 9 Vortrag.

> **Quelle der kuratierten Liste:** `collmex/accounts.py` (Modul
> `SKR03`). Dieses Markdown ist die lesbare Fassung derselben Konten
> und dient als Nachschlagewerk für den LLM-Agenten. Der Python-Code
> ist die kanonische Quelle — wenn sich etwas ändert, dort ändern.

## Kontenklassen-Übersicht

| Klasse | Inhalt | Bilanz/GuV |
|--------|--------|------------|
| 0 | Anlagevermögen, gezeichnetes Kapital | Bilanz |
| 1 | Umlaufvermögen, Finanzmittel, Verbindlichkeiten, USt | Bilanz |
| 2 | Neutrale Aufwendungen/Erträge, Steuern | GuV |
| 3 | Wareneingang, Bestände, Fremdleistungen | GuV (Aufwand) |
| 4 | Betriebliche Aufwendungen | GuV (Aufwand) |
| 5 | — (leer im Standard-SKR03) | - |
| 6 | — (leer im Standard-SKR03) | - |
| 7 | Bestände Erzeugnisse, unfertige Leistungen | Bilanz |
| 8 | Erlöse | GuV (Ertrag) |
| 9 | Vortrags-/statistische Konten | Sonstiges |

## Erkennungsmerkmale SKR03 vs. SKR04

Kurztest beim Erstkontakt mit einem Mandanten:

- Konto **8400** existiert und enthält Erlöse? → **SKR03**
- Konto **4400** existiert und enthält Erlöse? → **SKR04**
- Klassen 5 und 6 leer? → SKR03. Belegt? → SKR04.

## Bestandskonten Aktiv (Klasse 0-1)

| Konto | Bezeichnung |
|-------|-------------|
| 400  | Technische Anlagen und Maschinen |
| 600  | Betriebs- und Geschäftsausstattung |
| 1000 | Kasse |
| 1200 | Bank |
| 1300 | Weitere Bankkonten |
| 1400 | Forderungen aus Lieferungen und Leistungen |
| 1500 | Sonstige Forderungen |
| 1570 | Abziehbare Vorsteuer |
| 1571 | Abziehbare Vorsteuer 7% |
| 1576 | Abziehbare Vorsteuer 19% |
| 1580 | Vorsteuer nach §13b UStG |
| 1780 | Umsatzsteuer-Vorauszahlung |

## Bestandskonten Passiv (Klasse 0-1)

| Konto | Bezeichnung |
|-------|-------------|
| 970  | Sonstige Rückstellungen |
| 1600 | Verbindlichkeiten aus Lieferungen und Leistungen |
| 1700 | Sonstige Verbindlichkeiten |
| 1770 | Umsatzsteuer |
| 1771 | Umsatzsteuer 7% |
| 1776 | Umsatzsteuer 19% |
| 1790 | Umsatzsteuer Vorjahr |
| 1800 | Gezeichnetes Kapital |
| 1810 | Kapitalrücklage |
| 1820 | Gesellschafter-Darlehen |
| 1860 | Gewinnvortrag |

## Aufwandskonten (Klasse 4)

| Konto | Bezeichnung | Keyword-Hinweis |
|-------|-------------|------------------|
| 4100 | Löhne und Gehälter | |
| 4110 | Gesetzliche Sozialaufwendungen | |
| 4120 | Freiwillige Sozialaufwendungen | |
| 4200 | Raumkosten | |
| 4210 | Miete | miete, pacht |
| 4220 | Nebenkosten | strom, heizung, gas, wasser |
| 4300 | Instandhaltung und Reparatur | |
| 4400 | Bürobedarf | büromaterial, büro, papier, toner |
| 4410 | Porto | porto, versand, dhl |
| 4420 | Telefon und Internet | telefon, internet, mobilfunk |
| 4430 | Versicherungen | versicherung, haftpflicht |
| 4440 | Beiträge und Mitgliedschaften | ihk, beitrag, mitgliedschaft |
| 4510 | Kfz-Kosten | benzin, tanken, kfz |
| 4600 | Reisekosten | hotel, flug, bahn, taxi, reise |
| 4630 | Bewirtungskosten (70% abziehbar) | essen, bewirtung, restaurant |
| 4700 | Kosten der Warenabgabe | |
| 4730 | Werbekosten | werbung, google_ads, anzeige |
| 4800 | Rechts- und Beratungskosten | beratung, steuerberater, anwalt |
| 4810 | Bankgebühren | bank, kontoführung |
| 4822 | Abschreibungen auf Sachanlagen | |
| 4830 | Abschreibungen auf immat. VG (auch Software/Lizenzen) | software, lizenz, saas, cloud |
| 4900 | Sonstige betriebliche Aufwendungen (**Fallback**) | |
| 4910 | Forderungsverluste | |

## Ertragskonten (Klasse 8)

| Konto | Bezeichnung |
|-------|-------------|
| 8100 | Steuerfreie Umsätze |
| 8200 | Erlöse 0% |
| 8300 | Erlöse 7% |
| 8400 | Erlöse 19% |
| 8500 | Sonstige betriebliche Erträge |
| 8700 | Erträge aus dem Abgang von Anlagevermögen |

## Kontierungsregeln (Entscheidungshilfen)

### Bewirtung — 70/30-Split
Geschäftliche Bewirtung ist nur zu 70% steuerlich abziehbar, die VSt
dagegen zu 100%. Split auf zwei Konten:
- **4650** (70% — abzugsfähig)
- **4654** (30% — nicht abzugsfähig)

VSt wird auf den **gesamten** Netto-Betrag gezogen (1576 bei 19%).
Siehe auch Flow *Split-Buchung* in `CLAUDE.md`.

### Reverse Charge §13b UStG
EU-Lieferant mit gültiger USt-IdNr:
- Aufwand auf normales Aufwandskonto (z.B. 4830 für SaaS)
- USt: Konto **1580** (Vorsteuer §13b) auf der Soll-Seite
- Gegenbuchung: **1787** (USt §13b) auf der Haben-Seite
- Netto-Effekt auf USt: null — aber BZSt-meldepflichtig.

### Bank, Kasse, Verrechnung
- Nie direkt auf **1200** (Bank) buchen — IMMER über Personenkonto
  (Debitor/Kreditor). Siehe Regel 9 in `CLAUDE.md`.
- **1590** Durchlaufende Posten / Verrechnungskonto: maximal 10 Tage
  offene Salden, dann klären.
- **1361** Geldtransit: für Überweisungen zwischen eigenen Konten.

### Anlagevermögen
- Anschaffungskosten **netto > 800 Euro** → Anlagevermögen (Klasse 0)
  + planmäßige AfA über Nutzungsdauer
- Bis 800 Euro netto → GWG, sofort voll abschreibbar (Konto 4855 oder
  direkt als Aufwand)
- Sammelposten 250-1000 Euro: 5 Jahre linear (Konto 0485)

## Mapping zu SKR04

Die wichtigsten Umschlüsselungen siehe `wissen/skr04.md` (Kapitel
*Mapping SKR04 → SKR03*). Die Richtung SKR03 → SKR04 ist spiegelbildlich.
