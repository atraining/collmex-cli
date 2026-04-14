"""Tests für collmex.stammdaten — HTML-Parser und generischer Renderer."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch

from rich.console import Console

from collmex.stammdaten import (
    _strip_html,
    fetch_help_table,
    get_field_names,
    render_stammdaten,
)

# ---------------------------------------------------------------------------
# _strip_html
# ---------------------------------------------------------------------------


def test_strip_html_tags():
    assert _strip_html("<b>bold</b>") == "bold"


def test_strip_html_entities():
    assert _strip_html("A &amp; B") == "A & B"
    assert _strip_html("&nbsp;") == ""
    assert _strip_html("A &rarr; B") == "A -> B"


def test_strip_html_nested():
    assert _strip_html('<a href="x">link</a> text') == "link text"


# ---------------------------------------------------------------------------
# fetch_help_table
# ---------------------------------------------------------------------------

SAMPLE_HTML = """<!DOCTYPE HTML>
<head><title>Test</title></head>
<body>
<table class="help">
<tr><th class="help">Nr<th class="help">Feld<th class="help">Typ<th class="help">Max.Länge<th class="help">Bemerkung
<tr><td class="help">1<td class="help">Satzart<td class="help">C<td class="help">&nbsp;<td class="help">Festwert CMXKND
<tr><td class="help">2<td class="help">Kundennummer<td class="help">I<td class="help">8<td class="help">Eindeutige Nummer
<tr><td class="help">3<td class="help">Firma Nr<td class="help">I<td class="help">8<td class="help">Interne Nummer
</table>
</body>"""


@patch("collmex.stammdaten.requests.get")
def test_fetch_help_table_parses_rows(mock_get):
    mock_resp = MagicMock()
    mock_resp.content = SAMPLE_HTML.encode("iso-8859-1")
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = fetch_help_table("daten_importieren_kunde")

    assert len(result) == 3
    assert result[0] == ("1", "Satzart", "C", "", "Festwert CMXKND")
    assert result[1] == ("2", "Kundennummer", "I", "8", "Eindeutige Nummer")
    assert result[2][1] == "Firma Nr"


@patch("collmex.stammdaten.requests.get")
def test_fetch_help_table_network_error(mock_get):
    import requests as req

    mock_get.side_effect = req.ConnectionError("no network")
    result = fetch_help_table("daten_importieren_kunde")
    assert result == []


@patch("collmex.stammdaten.requests.get")
def test_fetch_help_table_no_table(mock_get):
    mock_resp = MagicMock()
    mock_resp.content = b"<html><body>No table here</body></html>"
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = fetch_help_table("nonexistent_page")
    assert result == []


# ---------------------------------------------------------------------------
# get_field_names
# ---------------------------------------------------------------------------


@patch("collmex.stammdaten.requests.get")
def test_get_field_names(mock_get):
    mock_resp = MagicMock()
    mock_resp.content = SAMPLE_HTML.encode("iso-8859-1")
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    names = get_field_names("daten_importieren_kunde")
    assert names[0] == "Satzart"
    assert names[1] == "Kundennummer"
    assert names[2] == "Firma Nr"


@patch("collmex.stammdaten.requests.get")
def test_get_field_names_network_error(mock_get):
    import requests as req

    mock_get.side_effect = req.ConnectionError("no network")
    names = get_field_names("anything")
    assert names == []


# ---------------------------------------------------------------------------
# render_stammdaten — mit query()
# ---------------------------------------------------------------------------


@patch("collmex.stammdaten.get_field_names")
def test_render_stammdaten_empty(mock_fields):
    """Keine Daten → Meldung 'Keine Daten'."""
    mock_fields.return_value = ["Satzart", "Nr"]

    ctx = MagicMock()
    ctx.client.query.return_value = []

    out = StringIO()
    con = Console(file=out, no_color=True, width=120)
    err = Console(file=StringIO(), no_color=True)

    render_stammdaten(ctx, "CUSTOMER_GET", console=con, error_console=err)
    assert "Keine" in out.getvalue()


@patch("collmex.stammdaten.get_field_names")
def test_render_stammdaten_shows_data(mock_fields):
    """Daten werden als Tabelle angezeigt."""
    mock_fields.return_value = ["Satzart", "Kundennummer", "Firma"]

    ctx = MagicMock()
    ctx.client.query.return_value = [
        ["CMXKND", "10001", "Testkunde GmbH"],
    ]

    out = StringIO()
    con = Console(file=out, no_color=True, width=120)
    err = Console(file=StringIO(), no_color=True)

    render_stammdaten(ctx, "CUSTOMER_GET", console=con, error_console=err)
    output = out.getvalue()
    assert "Testkunde" in output
    assert "1 Ergebnisse" in output


@patch("collmex.stammdaten.get_field_names")
def test_render_stammdaten_suche(mock_fields):
    """Suche filtert korrekt."""
    mock_fields.return_value = ["Satzart", "Nr", "Firma"]

    ctx = MagicMock()
    ctx.client.query.return_value = [
        ["CMXKND", "10001", "Alpha GmbH"],
        ["CMXKND", "10002", "Beta AG"],
    ]

    out = StringIO()
    con = Console(file=out, no_color=True, width=120)
    err = Console(file=StringIO(), no_color=True)

    render_stammdaten(ctx, "CUSTOMER_GET", suche="alpha", console=con, error_console=err)
    output = out.getvalue()
    assert "Alpha" in output
    assert "Beta" not in output
    assert "1 Ergebnisse" in output


@patch("collmex.stammdaten.get_field_names")
def test_render_stammdaten_fallback_field_names(mock_fields):
    """Wenn Doku-Fetch fehlschlaegt, Fallback auf 'Feld N'."""
    mock_fields.return_value = []

    ctx = MagicMock()
    ctx.client.query.return_value = [
        ["CMXKND", "10001", "Test"],
    ]

    out = StringIO()
    con = Console(file=out, no_color=True, width=120)
    err = Console(file=StringIO(), no_color=True)

    render_stammdaten(ctx, "CUSTOMER_GET", console=con, error_console=err)
    output = out.getvalue()
    assert "Feld" in output
    assert "Test" in output


@patch("collmex.stammdaten.get_field_names")
def test_render_stammdaten_skips_empty_columns(mock_fields):
    """Leere Spalten werden nicht angezeigt."""
    mock_fields.return_value = ["Satzart", "Nr", "Firma", "Leer1", "Leer2", "Ort"]

    ctx = MagicMock()
    ctx.client.query.return_value = [
        ["CMXKND", "10001", "Test", "", "", "Berlin"],
    ]

    out = StringIO()
    con = Console(file=out, no_color=True, width=120)
    err = Console(file=StringIO(), no_color=True)

    render_stammdaten(ctx, "CUSTOMER_GET", console=con, error_console=err)
    output = out.getvalue()
    assert "Berlin" in output
    # Leer1 and Leer2 headers should not appear
    assert "Leer1" not in output
    assert "Leer2" not in output


@patch("collmex.stammdaten.get_field_names")
def test_render_stammdaten_unknown_satzart(mock_fields):
    """Unbekannte Satzart ohne api_reference Eintrag: autodetect."""
    mock_fields.return_value = []

    ctx = MagicMock()
    ctx.client.query.return_value = [
        ["MYSTERY", "1", "Foo"],
        ["MYSTERY", "2", "Bar"],
    ]

    out = StringIO()
    con = Console(file=out, no_color=True, width=120)
    err = Console(file=StringIO(), no_color=True)

    render_stammdaten(ctx, "MYSTERY_GET", console=con, error_console=err)
    output = out.getvalue()
    assert "Foo" in output
    assert "Bar" in output
