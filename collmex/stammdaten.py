"""Generischer Stammdaten-Renderer mit dynamischem Doku-Parser.

Parst Feldnamen direkt von Collmex-Hilfeseiten und rendert
Stammdaten-Tabellen dynamisch — keine hardcodierten Spalten-Indices.
"""

from __future__ import annotations

import logging
import re
import sys

import requests
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

DOKU_BASIS = "https://www.collmex.de/c.cmx?1005,1,help,"


# ---------------------------------------------------------------------------
# HTML-Parser für Collmex-Hilfeseiten
# ---------------------------------------------------------------------------


def _strip_html(text: str) -> str:
    """Entfernt HTML-Tags und dekodiert Entities."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ")
    text = text.replace("&rarr;", "->")
    text = text.replace("&raquo;", ">>")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    return text.strip()


def fetch_help_table(doku_page: str) -> list[tuple[str, str, str, str, str]]:
    """Parst <table class="help"> von einer Collmex-Doku-Seite.

    Returns:
        [(nr, feld, typ, max_len, bemerkung), ...]
    """
    url = f"{DOKU_BASIS}{doku_page}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        html = resp.content.decode("iso-8859-1")
    except (requests.RequestException, UnicodeDecodeError) as exc:
        logger.warning("Doku-Fetch fehlgeschlagen: %s", exc)
        return []

    # <table class="help"> ... </table> extrahieren
    match = re.search(r'<table class="help">(.*?)</table>', html, re.DOTALL)
    if not match:
        return []

    table_html = match.group(1)

    # Zeilen parsen: Collmex schliesst <tr> Tags oft nicht,
    # daher immer per split arbeiten
    rows = re.split(r"<tr>", table_html)

    result: list[tuple[str, str, str, str, str]] = []
    for row_html in rows:
        # <th> = Header, ueberspringen
        if "<th" in row_html:
            continue
        cells = re.findall(r'<td class="help">(.*?)(?=<td class="help">|$)', row_html, re.DOTALL)
        if not cells:
            # Fallback: einfach alle <td> nehmen
            cells = re.findall(r"<td[^>]*>(.*?)(?=<td|$)", row_html, re.DOTALL)
        if len(cells) >= 2:
            nr = _strip_html(cells[0])
            feld = _strip_html(cells[1])
            typ = _strip_html(cells[2]) if len(cells) > 2 else ""
            max_len = _strip_html(cells[3]) if len(cells) > 3 else ""
            bemerkung = _strip_html(cells[4]) if len(cells) > 4 else ""
            if nr and feld:
                result.append((nr, feld, typ, max_len, bemerkung))

    return result


def get_field_names(doku_page: str) -> list[str]:
    """Gibt Feldnamen als Liste zurück (Index 0 = Feld 1 der Doku).

    Bei Fehler: leere Liste.
    """
    fields = fetch_help_table(doku_page)
    if not fields:
        return []
    # Sortiert nach Feldnummer
    result: list[str] = []
    for nr_str, name, *_ in fields:
        try:
            nr = int(nr_str)
        except ValueError:
            continue
        # Liste auf Index nr-1 auffüllen
        while len(result) < nr:
            result.append(f"Feld {len(result) + 1}")
        result[nr - 1] = name
    return result


# ---------------------------------------------------------------------------
# Generischer Renderer
# ---------------------------------------------------------------------------


def render_stammdaten(
    ctx,
    get_satzart: str,
    suche: str | None = None,
    console: Console | None = None,
    error_console: Console | None = None,
    felder: tuple = (),
) -> None:
    """Generische Abfrage + Pretty-Print für beliebige GET-Satzarten.

    1. Satzart in api_reference.py nachschlagen → name, antwort, doku
    2. ctx.client.query(get_satzart) aufrufen
    3. Rows filtern auf Antwort-Satzart
    4. Feldnamen aus Doku holen (fetch_help_table)
    5. Interessante Spalten erkennen, Tabelle bauen
    6. --suche anwenden
    """
    from collmex.api import CollmexError
    from collmex.api_reference import get_satzart as lookup_satzart

    if console is None:
        console = Console()
    if error_console is None:
        error_console = Console(stderr=True)

    # 1. Satzart in api_reference nachschlagen
    ref = lookup_satzart(get_satzart)
    label = ref["name"] if ref else get_satzart
    antwort_satzart = ref.get("antwort") if ref else None

    # Doku-Seite: Wenn eine Antwort-Satzart bekannt ist, deren Import-Doku verwenden
    # (weil die Import-Satzart die Felddefinitionen hat)
    doku_page = None
    if antwort_satzart:
        antwort_ref = lookup_satzart(antwort_satzart)
        if antwort_ref and "doku" in antwort_ref:
            doku_page = antwort_ref["doku"]
    if not doku_page and ref:
        doku_page = ref.get("doku")

    # 2. API aufrufen
    try:
        all_rows = ctx.client.query(get_satzart, *felder)
    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    # 3. Rows filtern auf Antwort-Satzart
    if antwort_satzart:
        data_rows = [r for r in all_rows if r and r[0] == antwort_satzart]
    elif all_rows:
        # Autodetect: erste Datenzeile bestimmt den Satzart-Filter
        detected = all_rows[0][0] if all_rows[0] else None
        data_rows = [r for r in all_rows if r and r[0] == detected] if detected else all_rows
    else:
        data_rows = []

    if not data_rows:
        console.print(f"[yellow]Keine Daten für {get_satzart}.[/]")
        return

    # 4. Feldnamen aus Doku holen
    field_names = get_field_names(doku_page) if doku_page else []

    # 5. Interessante Spalten erkennen (Spalte 0 = Satzart immer skippen)
    max_cols = max(len(r) for r in data_rows)
    non_empty_cols: list[int] = []
    for col_idx in range(1, max_cols):
        values: set[str] = set()
        for row in data_rows:
            val = row[col_idx].strip() if col_idx < len(row) else ""
            values.add(val)
        non_empty = values - {""}
        if not non_empty:
            continue
        if len(non_empty) == 1 and len(data_rows) > 1:
            continue
        non_empty_cols.append(col_idx)

    MAX_COLS = 8
    if len(non_empty_cols) > MAX_COLS:
        non_empty_cols = non_empty_cols[:MAX_COLS]

    # 6. Suche anwenden
    if suche:
        suche_lower = suche.lower()
        filtered: list[list[str]] = []
        for row in data_rows:
            for col_idx in non_empty_cols:
                val = row[col_idx] if col_idx < len(row) else ""
                if suche_lower in val.lower():
                    filtered.append(row)
                    break
        data_rows = filtered

    if not data_rows:
        console.print(f"[yellow]Keine Daten für '{suche}' gefunden.[/]")
        return

    # 7. Tabelle bauen
    table = Table(title=label)
    for col_idx in non_empty_cols:
        if col_idx < len(field_names):
            header = field_names[col_idx]
        else:
            header = f"Feld {col_idx + 1}"
        style = "cyan" if col_idx == 1 else None
        table.add_column(header, style=style)

    for row in data_rows:
        values = []
        for col_idx in non_empty_cols:
            val = row[col_idx] if col_idx < len(row) else ""
            values.append(val)
        table.add_row(*values)

    console.print(table)
    console.print(f"\n[dim]{len(data_rows)} Ergebnisse[/]")


# ---------------------------------------------------------------------------
# Collmex Handbuch Parser
# ---------------------------------------------------------------------------

HANDBUCH_URL = "https://www.collmex.de/handbuch_pro.html"

# Kuratierte Sektionen für kaufmännischen Leiter
# Mapping: Kurzname → (Anker-ID, Titel)
HANDBUCH_SEKTIONEN: dict[str, tuple[str, str]] = {
    "buchen": ("buchen", "Buchen"),
    "fehler": ("fehlermeldungen", "Fehlermeldungen: Buchungen"),
    "jahresabschluss": ("jahresabschluss", "Jahresabschluss"),
    "buchung-stornieren": ("buchung_stornieren", "Buchung stornieren"),
    "op": ("op_verwalten", "Offene Posten verwalten"),
    "op-sonderfälle": ("op_sonderfälle", "OP Sonderfälle"),
    "reverse-charge": ("umgekehrte_steuerschuld", "Umgekehrte Steuerschuld (§13b)"),
    "mahnung": ("mahnung_allgemein", "Mahnung"),
    "mahnung-anlegen": ("mahnung_anlegen", "Mahnungen anlegen"),
    "mahnung-einstellungen": ("einstellungen_mahnung", "Einstellungen Mahnung"),
    "banking": ("online_banking", "Online-Banking"),
    "kontoauszug": ("kontoauszug", "Import von Kontoauszügen"),
    "bankumsatz": ("bankumsatz_buchen", "Bankumsatz buchen"),
    "zahlung": ("zahlung_allgemein", "Zahlungsverkehr"),
    "anlagen": ("anlagen_allgemein", "Anlagen"),
    "gwg": ("anlage_gwg", "Geringwertige Wirtschaftsgüter (GWG)"),
    "abschreibung": ("abschreibungslauf", "Abschreibungslauf"),
    "ust": ("umsatzsteuer_allgemein", "Umsatzsteuer"),
    "ustva": ("umsatzsteuer_voranmeldung_anlegen", "USt-Voranmeldung anlegen"),
    "zm": ("zusammenfassende_meldung", "Zusammenfassende Meldung (ZM)"),
    "guv": ("gewinn__und_verlustrechnung", "Gewinn und Verlust (GuV)"),
    "bilanz": ("bilanz", "Bilanz"),
    "bwa": ("bwa", "BWA"),
    "susa": ("summen_und_salden", "Summen und Salden"),
    "datev": ("datev_export", "Datev-Export"),
    "steuerprüfer": ("steuerprüfer_export", "Steuerprüfer-Export"),
    "rechnung": ("rechnung_allgemein", "Rechnungen und Gutschriften"),
    "rechnung-anlegen": ("rechnung_anlegen", "Rechnung anlegen"),
    "e-rechnung": ("rechnung_e_rechnung", "E-Rechnung"),
    "kunde": ("kunde_allgemein", "Kunden"),
    "lieferant": ("lieferant_allgemein", "Lieferanten"),
    "produkt": ("produkt_einführung", "Produkte"),
    "buchungsvorlagen": ("buchungsvorlagen_allgemein", "Buchungsvorlagen"),
    "beleg": ("beleg_allgemein", "Belegverwaltung"),
    "kassenbuch": ("kassenbuch_allgemein", "Kassenbuch"),
    "konto": ("konto_allgemein", "Kontenrahmen"),
    "api": ("api", "Collmex API"),
    "api-überblick": ("api_überblick", "API Überblick"),
    "daten-importieren": ("daten_importieren_allgemein", "Daten importieren"),
    "cmxlrn": ("daten_importieren_lieferantenrechnung", "Lieferantenrechnung (CMXLRN)"),
    "cmxums": ("daten_importieren_umsätze", "Erlöse (CMXUMS)"),
    "cmxinv": ("daten_importieren_rechnungen", "Rechnung (CMXINV)"),
}


def fetch_handbuch_section(anchor: str) -> str:
    """Holt eine Sektion aus dem Collmex-Handbuch per Anker-ID.

    Extrahiert Text zwischen dem Anker und dem nächsten <h2>.
    Gibt Plain-Text zurück (HTML-Tags entfernt).
    """
    try:
        resp = requests.get(HANDBUCH_URL, timeout=15)
        resp.raise_for_status()
        html = resp.content.decode("iso-8859-1")
    except (requests.RequestException, UnicodeDecodeError) as exc:
        return f"Fehler beim Laden des Handbuchs: {exc}"

    # Anker finden: <a name="anchor_id"></a> oder id="anchor_id"
    pattern = rf'(?:<a\s+name="{re.escape(anchor)}"[^>]*>|id="{re.escape(anchor)}")'
    match = re.search(pattern, html)
    if not match:
        return f"Sektion '{anchor}' nicht im Handbuch gefunden."

    # Ab Anker bis zum nächsten <a name= auf gleicher/uebergeordneter Ebene
    rest = html[match.end() :]
    # Nächste Sektion = nächstes <a name="..."> (Collmex benutzt <a name> für alle Sektionen)
    next_section = re.search(r'<a\s+name="[^"]+"\s*>', rest)
    if next_section:
        section_html = rest[: next_section.start()]
    else:
        section_html = rest[:5000]  # Fallback: max 5000 Zeichen

    # HTML zu lesbarem Text konvertieren
    # Block-Elemente → Zeilenumbrüche
    text = re.sub(r"<br\s*/?>", "\n", section_html)
    text = re.sub(r"</(?:p|div|tr|li|h[1-6])>", "\n", text)
    text = re.sub(r"<(?:p|div|tr|h[1-6])[^>]*>", "\n", text)
    text = re.sub(r"<li[^>]*>", "  - ", text)
    # Restliche Tags entfernen
    text = re.sub(r"<[^>]+>", "", text)
    # Entities dekodieren
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#042;", "*")
    text = text.replace("&rarr;", "→")
    text = text.replace("&raquo;", "»")
    # Mehrfache Leerzeilen reduzieren
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
