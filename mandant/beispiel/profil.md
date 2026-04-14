# Mandant: Beispiel GmbH

> Dies ist ein **Template**. Kopiere diesen Ordner nach
> `mandant/<dein-firmenkuerzel>/`, passe die Werte an und committe ihn
> **nicht** (das eigene Verzeichnis wird von `.gitignore` erfasst).

## Stammdaten

- Collmex-Kundennr: `123456`
- API-User: `apiuser` (Credentials in `.env`)
- Tarif: `buchhaltung basic` (voller API-Zugang, sonst keine Data-Exchange-Schnittstelle)
- Rechtsform: GmbH
- Handelsregister: HRB 00000 (Amtsgericht Musterstadt)
- Steuernr: `00/000/00000` (Finanzamt Musterstadt)
- USt-IdNr: `DE000000000`
- Geschäftsjahr: 01.01. - 31.12.

## Buchhaltung

- Kontenrahmen: **SKR03** (alternativ SKR04 — siehe `wissen/skr04.md`)
- Abweichende Konten: _(z.B. "Konto 4400 existiert nicht, stattdessen 4830")_
- Personenkonten:
  - Debitoren (Kunden): `10000 - 69999`
  - Kreditoren (Lieferanten): `70000 - 99999`
- Manuell angelegte Konten: _(Liste mit Begründung, z.B. "0868: Ausstehende Einlagen auf gez. Kapital")_

## Umsatzsteuer

- USt-Pflicht: Regelbesteuerung (alternativ: Kleinunternehmer §19 UStG)
- Voranmeldung: monatlich / vierteljährlich / jährlich
- Dauerfristverlängerung: ja / nein
- Relevante Sätze: 19% (Standard), 7% (ermäßigt), 0% (steuerfrei/igL)
- Besonderheiten: _(z.B. "Häufig §13b wegen EU-Lieferanten")_

## Steuerberater / DATEV

- Kanzlei: _(Name)_
- DATEV-Export: ja / nein
- Übergabe-Rhythmus: monatlich / quartalsweise

## Besonderheiten / Lessons Learned

- _(Freitext — Dinge, die der LLM-Agent bei diesem Mandanten wissen muss,
   z.B. wiederkehrende Buchungsmuster, Ausnahmen, Workarounds)_

## Web-UI

Bestimmte Felder (Firmenstammdaten, Steuernr, SMTP-Einstellungen) sind nur
über die Collmex-Weboberfläche änderbar. Dafür:

- Web-User: separater Benutzer, NICHT der API-User
- In `.env` setzen: `COLLMEX_WEB_USER` und `COLLMEX_WEB_PASSWORD`
- Aufruf: `collmex webui firma` / `collmex webui mengeneinheiten`
