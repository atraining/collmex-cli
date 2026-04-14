# Collmex Web-UI Zugang (Fallback wenn API nicht reicht)

## Wann braucht man das?

Die Collmex-API deckt nicht alles ab. Folgende Daten gibt es NUR per Web-UI:

- **Mengeneinheiten** (Liste aller konfigurierten Einheiten)
- **Zahlungsbedingungen** (Skonto-Tage, Skonto-%, Netto-Tage)
- **Firmenstammdaten** (Steuernummer, USt-IdNr, Adresse)
- **SMTP/E-Mail-Einstellungen** (Postausgangsserver)
- **Nummernvergabe** (Start-Nummern für Rechnungen, Aufträge etc.)
- **Textbausteine** (Rechnungstexte, Mahnungstexte)
- **Mahnungseinstellungen** (Mahnstufen, Gebühren, Fristen)
- **Kontenrahmen-Einstellungen** (SKR03/SKR04, individuelle Konten)
- **Druck-/Mail-Vorlagen**

## Login-Technik (Python requests)

### Voraussetzungen

- **Web-Benutzer** (NICHT der API-User!). Der apiuser hat keinen Web-Zugang.
- Zugangsdaten: Benutzer-ID + Kennwort (aus Collmex Verwaltung → Benutzer)
- Python `requests` Bibliothek

### 2-Schritt-Login

```python
import requests

COLLMEX_KUNDENNR = '123456'
WEB_USER = 'YOUR_USER_ID'       # aus Collmex Verwaltung -> Benutzer
WEB_PASSWORD = 'YOUR_PASSWORD'  # nicht der API-Password!

session = requests.Session()

# Schritt 1: Login-Seite laden (initialisiert Session-Cookie)
r1 = session.get(
    f'https://www.collmex.de/c.cmx?{COLLMEX_KUNDENNR},0,login'
)
# → Setzt initiale Cookies

# Schritt 2: Login-POST mit Credentials
login_data = {
    'group_benutzerId': WEB_USER,
    'group_kennwort': WEB_PASSWORD,
}
r2 = session.post(
    f'https://www.collmex.de/c.cmx?{COLLMEX_KUNDENNR},1,login',
    data=login_data,
)
# → Setzt Session-Cookies: sid_{kundennr}, sid_{kundennr}_{userid}

# Schritt 3: Beliebige Seite abrufen
r3 = session.get(
    f'https://www.collmex.de/c.cmx?{COLLMEX_KUNDENNR},1,settings'
)
print(r3.text)  # HTML der Einstellungen-Seite
```

### Warum 2 Schritte?

Collmex initialisiert beim GET auf die Login-Seite Session-Cookies.
Ohne Schritt 1 wird der POST in Schritt 2 abgelehnt (kein gültiger Session-State).

### Cookies nach erfolgreichem Login

```
sid_123456          = <session-id>        # Haupt-Session
sid_123456_<user-id> = <user-session-id>  # User-spezifisch
```

### Wichtige URLs (nach Login)

URL-Format: `https://www.collmex.de/c.cmx?{kundennr},{parameter}`

| Parameter | Seite |
|-----------|-------|
| `1,settings` | Einstellungen-Übersicht |
| `1,coch,1` | Firmenstammdaten (Adresse, Steuernr, USt-IdNr) |
| `1,ac` | Kontenrahmen (alle Konten) |
| `1,uomch` | Mengeneinheiten |
| `1,zbli` | Zahlungsbedingungen (Liste) |
| `1,zbcr` | Zahlungsbedingung anlegen |
| `1,tbli` | Textbausteine (Liste) |
| `1,tbcr` | Textbaustein anlegen |
| `1,dnst` | Mahnungseinstellungen |
| `1,nr` | Nummernvergabe |
| `1,stpr` | Druckeinstellungen |
| `1,stmaildo` | E-Mail-Einstellungen |
| `1,us` | Benutzer (Liste) |
| `1,uscr` | Benutzer anlegen |
| `1,exp` | Datenexport |
| `1,imp` | Datenimport |
| `1,acc` | Buchhaltung (Hauptseite) |
| `1,crm` | Verkauf (Hauptseite) |
| `1,scm` | Warenwirtschaft (Hauptseite) |
| `0,login` | Login-Seite |

Beispiel: `https://www.collmex.de/c.cmx?123456,1,uomch` = Mengeneinheiten

### CLI-Zugang (empfohlen)

Statt manuell zu scrapen, nutze die CLI-Befehle:

```bash
collmex webui mengeneinheiten      # Alle Mengeneinheiten mit ISO-Codes
collmex webui zahlungsbedingungen  # Alle Zahlungsbedingungen
collmex webui firma                # Firmenstammdaten (Adresse, Steuernr, Kontenrahmen)
```

Code: `collmex/webui.py` (CollmexWebUI-Klasse mit Session-Login und HTML-Parsing).

### Encoding

Collmex liefert HTML als **ISO-8859-1** (wie bei der API).
```python
r3.encoding = 'iso-8859-1'
html = r3.text
```

### HTML parsen

Die Seiten enthalten Standard-HTML-Tabellen. Für einfaches Parsen:
```python
from html.parser import HTMLParser
# oder: pip install beautifulsoup4
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, 'html.parser')
tables = soup.find_all('table')
```

## Sicherheitshinweise

- Web-Credentials gehören in `.env`, NICHT in Code oder Git
- `.env` steht in `.gitignore` → wird nicht committed
- Session-Cookies sind temporär und verfallen nach Inaktivität
- Für Mandanten-Forks: `.env` pro Mandant individuell

## Sachkonto anlegen per Web-UI

Collmex SKR03 hat einen reduzierten Kontenrahmen. Fehlende Konten (z.B. 0868)
müssen per Web-UI angelegt werden.

```python
# WICHTIG: acch (ändern), NICHT accr (anlegen)!
session.post(
    f'https://www.collmex.de/c.cmx?{COLLMEX_KUNDENNR},1,acch',
    data={
        'group_kontoNr': '868',
        'group_kontoName': 'Ausstehende Einlagen auf gez. Kapital',
        'cx': 'Speichern',
    }
)
```

Die `accr`-Seite erwartet eine existierende Vorlage (group_vorlage) und
schlägt fehl wenn das Konto noch nicht existiert. `acch` funktioniert
auch für neue Konten.

## Wann API vs. Web-UI?

| Aufgabe | API | Web-UI |
|---------|-----|--------|
| Buchungen lesen/schreiben | ja | nein |
| Rechnungen erstellen | ja | nein |
| Kunden/Lieferanten pflegen | ja | nein |
| Salden/OP abfragen | ja | nein |
| Firmenstammdaten ändern | NEIN | ja |
| SMTP konfigurieren | NEIN | ja |
| Mengeneinheiten sehen | NEIN | ja |
| Zahlungsbedingungen sehen | NEIN | ja |
| Kontenrahmen komplett | NEIN | ja |
| Textbausteine pflegen | NEIN | ja |
