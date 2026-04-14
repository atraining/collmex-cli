"""Tests fuer collmex CLI (Click-basiert).

Nutzt click.testing.CliRunner und gemockte API-Clients.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from collmex import __version__
from collmex.cli import main


@pytest.fixture
def runner():
    """Click CliRunner fuer CLI-Tests."""
    return CliRunner()


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


def test_version_command(runner):
    """'collmex version' gibt die aktuelle Version aus."""
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_version_output_format(runner):
    """Version-Ausgabe beginnt mit 'collmex'."""
    result = runner.invoke(main, ["version"])
    assert result.output.strip().startswith("collmex")


# ---------------------------------------------------------------------------
# konten
# ---------------------------------------------------------------------------


def test_konten_command(runner):
    """'collmex konten' zeigt den Kontenrahmen an."""
    result = runner.invoke(main, ["konten"])
    assert result.exit_code == 0
    assert "SKR03" in result.output


def test_konten_enthaelt_bank(runner):
    """Kontenrahmen enthaelt Konto 1200 (Bank)."""
    result = runner.invoke(main, ["konten"])
    assert "1200" in result.output
    assert "Bank" in result.output


def test_konten_enthaelt_erloese(runner):
    """Kontenrahmen enthaelt Ertragskonten."""
    result = runner.invoke(main, ["konten"])
    assert "8400" in result.output


def test_konten_enthaelt_aufwand(runner):
    """Kontenrahmen enthaelt Aufwandskonten."""
    result = runner.invoke(main, ["konten"])
    assert "4400" in result.output


# ---------------------------------------------------------------------------
# konto
# ---------------------------------------------------------------------------


def test_konto_existiert(runner):
    """'collmex konto 1200' zeigt Konto-Details."""
    result = runner.invoke(main, ["konto", "1200"])
    assert result.exit_code == 0
    assert "1200" in result.output
    assert "Bank" in result.output


def test_konto_nicht_vorhanden(runner):
    """'collmex konto 9999' gibt Fehler aus."""
    result = runner.invoke(main, ["konto", "9999"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# status (gemockter Client)
# ---------------------------------------------------------------------------


def test_status_ok(runner):
    """'collmex status' zeigt 'Verbindung OK' bei erfolgreichem Login."""
    mock_client = MagicMock()
    mock_client.status.return_value = True
    mock_client.url = "https://test.collmex.de"
    mock_client.user = "testuser"
    mock_client.customer = "12345"
    mock_client.company = 1

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Verbindung OK" in result.output


def test_status_fehlgeschlagen(runner):
    """'collmex status' zeigt Fehler bei fehlgeschlagenem Login."""
    mock_client = MagicMock()
    mock_client.status.return_value = False

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(main, ["status"])
        assert result.exit_code != 0


def test_status_verbose(runner):
    """'collmex --verbose status' zeigt erweiterte Infos."""
    mock_client = MagicMock()
    mock_client.status.return_value = True
    mock_client.url = "https://test.collmex.de"
    mock_client.user = "testuser"
    mock_client.customer = "12345"
    mock_client.company = 1

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(main, ["--verbose", "status"])
        assert result.exit_code == 0
        assert "testuser" in result.output


# ---------------------------------------------------------------------------
# buchen --dry-run
# ---------------------------------------------------------------------------


def test_dry_run_keine_buchung(runner):
    """'--dry-run' fuehrt keine Buchung aus."""
    result = runner.invoke(
        main,
        [
            "buchen",
            "Bueromaterial Staples",
            "--betrag",
            "100.00",
            "--lieferant",
            "70001",
            "--ust",
            "19",
            "--datum",
            "20260303",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "dry-run" in result.output.lower() or "NICHT" in result.output


def test_dry_run_zeigt_buchungssatz(runner):
    """'--dry-run' zeigt den generierten Buchungssatz an."""
    result = runner.invoke(
        main,
        [
            "buchen",
            "Bueromaterial",
            "--betrag",
            "500.00",
            "--lieferant",
            "70001",
            "--konto",
            "4400",
            "--ust",
            "19",
            "--datum",
            "20260303",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "4400" in result.output
    assert "1576" in result.output  # Vorsteuer 19%
    assert "70001" in result.output  # Lieferant statt Bank


def test_dry_run_auto_konto(runner):
    """'--dry-run' ohne --konto erkennt automatisch das Aufwandskonto."""
    result = runner.invoke(
        main,
        [
            "buchen",
            "Bueromaterial Papier",
            "--betrag",
            "50.00",
            "--lieferant",
            "70001",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "4400" in result.output  # Buerobedarf


def test_dry_run_7_prozent_ust(runner):
    """'--dry-run' mit 7% USt zeigt Vorsteuer 7%."""
    result = runner.invoke(
        main,
        [
            "buchen",
            "Zeitschriften",
            "--betrag",
            "100.00",
            "--lieferant",
            "70001",
            "--konto",
            "4400",
            "--ust",
            "7",
            "--datum",
            "20260303",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "1571" in result.output  # Vorsteuer 7%


def test_buchen_ohne_lieferant_fehlt(runner):
    """'collmex buchen' ohne --lieferant gibt Fehler (Pflichtfeld)."""
    result = runner.invoke(
        main,
        [
            "buchen",
            "Test",
            "--betrag",
            "100.00",
        ],
    )
    assert result.exit_code != 0
    assert "lieferant" in result.output.lower()


# ---------------------------------------------------------------------------
# salden (gemockter Client)
# ---------------------------------------------------------------------------


def test_salden_leer(runner):
    """'collmex salden' zeigt Meldung bei leeren Daten."""
    mock_client = MagicMock()
    mock_client.get_balances.return_value = []

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(main, ["salden", "--monat", "1", "--jahr", "2026"])
        assert result.exit_code == 0
        assert "Keine" in result.output or "01/2026" in result.output


# ---------------------------------------------------------------------------
# Hilfe
# ---------------------------------------------------------------------------


def test_hauptgruppe_help(runner):
    """'collmex --help' zeigt Hilfemeldung."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "FiBu" in result.output or "Controlling" in result.output


def test_buchen_help(runner):
    """'collmex buchen --help' zeigt Optionen."""
    result = runner.invoke(main, ["buchen", "--help"])
    assert result.exit_code == 0
    assert "--betrag" in result.output
    assert "--dry-run" in result.output


# ---------------------------------------------------------------------------
# fristen
# ---------------------------------------------------------------------------


def test_fristen_command(runner):
    """'collmex fristen' zeigt anstehende Fristen."""
    result = runner.invoke(main, ["fristen"])
    assert result.exit_code == 0
    assert "Fristen" in result.output


def test_fristen_monat(runner):
    """'collmex fristen --monat 3' zeigt Fristen fuer Maerz."""
    result = runner.invoke(main, ["fristen", "--monat", "3", "--jahr", "2026"])
    assert result.exit_code == 0
    assert "03/2026" in result.output


def test_fristen_ueberfaellig(runner):
    """'collmex fristen --ueberfaellig' zeigt ueberfaellige Fristen."""
    result = runner.invoke(main, ["fristen", "--ueberfaellig"])
    assert result.exit_code == 0


def test_fristen_tage(runner):
    """'collmex fristen --tage 7' zeigt Fristen der naechsten 7 Tage."""
    result = runner.invoke(main, ["fristen", "--tage", "7"])
    assert result.exit_code == 0


def test_fristen_help(runner):
    """'collmex fristen --help' zeigt Optionen."""
    result = runner.invoke(main, ["fristen", "--help"])
    assert result.exit_code == 0
    assert "--monat" in result.output
    assert "--tage" in result.output
    assert "--ueberfaellig" in result.output


# ---------------------------------------------------------------------------
# ustva (gemockter Client)
# ---------------------------------------------------------------------------


def test_ustva_help(runner):
    """'collmex ustva --help' zeigt Optionen."""
    result = runner.invoke(main, ["ustva", "--help"])
    assert result.exit_code == 0
    assert "--monat" in result.output
    assert "--jahr" in result.output


def test_ustva_zeigt_kennzahlen(runner):
    """'collmex ustva' zeigt UStVA-Kennzahlen."""
    mock_client = MagicMock()
    mock_client.get_balances.return_value = []

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(main, ["ustva", "--monat", "2", "--jahr", "2026"])
        assert result.exit_code == 0
        assert "UStVA 02/2026" in result.output
        assert "KZ 81" in result.output
        assert "Vorauszahlung" in result.output


# ---------------------------------------------------------------------------
# liquiditaet (gemockter Client)
# ---------------------------------------------------------------------------


def test_liquiditaet_help(runner):
    """'collmex liquiditaet --help' zeigt Optionen."""
    result = runner.invoke(main, ["liquiditaet", "--help"])
    assert result.exit_code == 0
    assert "--wochen" in result.output


def test_liquiditaet_zeigt_vorschau(runner):
    """'collmex liquiditaet' zeigt Liquiditaetsvorschau."""
    mock_client = MagicMock()
    mock_client.get_open_items.return_value = []
    mock_client.get_balances.return_value = []

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(main, ["liquiditaet", "--wochen", "4"])
        assert result.exit_code == 0
        assert "Liquiditaetsvorschau" in result.output


# ---------------------------------------------------------------------------
# soll-ist (gemockter Client)
# ---------------------------------------------------------------------------


def test_soll_ist_help(runner):
    """'collmex soll-ist --help' zeigt Optionen."""
    result = runner.invoke(main, ["soll-ist", "--help"])
    assert result.exit_code == 0
    assert "--monat" in result.output
    assert "--budget-file" in result.output


def test_soll_ist_mit_standard_budget(runner):
    """'collmex soll-ist' mit Standard-Budget zeigt Vergleich."""
    mock_client = MagicMock()
    mock_client.get_balances.return_value = []

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(main, ["soll-ist", "--monat", "3", "--jahr", "2026"])
        assert result.exit_code == 0
        assert "Soll-Ist" in result.output
        assert "Ampel" in result.output


# ---------------------------------------------------------------------------
# storno
# ---------------------------------------------------------------------------


def test_storno_help(runner):
    """'collmex storno --help' zeigt Optionen."""
    result = runner.invoke(main, ["storno", "--help"])
    assert result.exit_code == 0
    assert "--betrag" in result.output
    assert "--konto" in result.output
    assert "--dry-run" in result.output


def test_storno_dry_run(runner):
    """'collmex storno --dry-run' zeigt Storno-Details ohne Ausfuehrung."""
    result = runner.invoke(
        main,
        [
            "storno",
            "ER-001",
            "--betrag",
            "500",
            "--konto",
            "4830",
            "--ust",
            "19",
            "--lieferant",
            "70001",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "ER-001" in result.output
    assert "dry-run" in result.output.lower() or "NICHT" in result.output


def test_storno_ohne_lieferant_fehlt(runner):
    """Storno eingang ohne --lieferant gibt Fehler."""
    result = runner.invoke(
        main,
        [
            "storno",
            "ER-001",
            "--typ",
            "eingang",
            "--betrag",
            "100",
            "--konto",
            "4900",
        ],
    )
    assert result.exit_code != 0
    assert "lieferant" in result.output.lower()


def test_storno_ausgang_ohne_kunde_fehlt(runner):
    """Storno ausgang ohne --kunde gibt Fehler."""
    result = runner.invoke(
        main,
        [
            "storno",
            "AR-001",
            "--typ",
            "ausgang",
            "--betrag",
            "100",
            "--konto",
            "8400",
        ],
    )
    assert result.exit_code != 0
    assert "kunde" in result.output.lower()


# ---------------------------------------------------------------------------
# datev-export
# ---------------------------------------------------------------------------


def test_datev_export_help(runner):
    """'collmex datev-export --help' zeigt Optionen."""
    result = runner.invoke(main, ["datev-export", "--help"])
    assert result.exit_code == 0
    assert "--monat" in result.output
    assert "--berater" in result.output
    assert "--mandant" in result.output
    assert "--gruppiert" in result.output


# ---------------------------------------------------------------------------
# mahnlauf (gemockter Client)
# ---------------------------------------------------------------------------


def test_mahnlauf_help(runner):
    """'collmex mahnlauf --help' zeigt Optionen."""
    result = runner.invoke(main, ["mahnlauf", "--help"])
    assert result.exit_code == 0
    assert "--stufe" in result.output


def test_mahnlauf_leer(runner):
    """'collmex mahnlauf' zeigt Meldung bei keinen Mahnungen."""
    mock_client = MagicMock()
    mock_client.get_open_items.return_value = []

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(main, ["mahnlauf"])
        assert result.exit_code == 0
        assert "Keine" in result.output


# ---------------------------------------------------------------------------
# ausgang
# ---------------------------------------------------------------------------


def test_ausgang_help(runner):
    """'collmex ausgang --help' zeigt Optionen."""
    result = runner.invoke(main, ["ausgang", "--help"])
    assert result.exit_code == 0
    assert "--betrag" in result.output
    assert "--konto" in result.output
    assert "--kunde" in result.output
    assert "--dry-run" in result.output


def test_ausgang_dry_run(runner):
    """'collmex ausgang --dry-run' zeigt Ausgangsrechnung ohne Ausfuehrung."""
    result = runner.invoke(
        main,
        [
            "ausgang",
            "Beratungsleistung",
            "--betrag",
            "1000.00",
            "--kunde",
            "10001",
            "--konto",
            "8400",
            "--ust",
            "19",
            "--datum",
            "20260303",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "8400" in result.output
    assert "1776" in result.output  # USt 19%
    assert "10001" in result.output  # Kunde statt Bank
    assert "dry-run" in result.output.lower() or "NICHT" in result.output


def test_ausgang_auto_konto(runner):
    """'collmex ausgang --dry-run' ohne --konto waehlt Ertragskonto automatisch."""
    result = runner.invoke(
        main,
        [
            "ausgang",
            "Dienstleistung",
            "--betrag",
            "500.00",
            "--kunde",
            "10001",
            "--ust",
            "19",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "8400" in result.output  # Default bei 19%


def test_ausgang_7_prozent_auto_konto(runner):
    """'collmex ausgang --dry-run' mit 7% waehlt 8300 automatisch."""
    result = runner.invoke(
        main,
        [
            "ausgang",
            "Buch",
            "--betrag",
            "100.00",
            "--kunde",
            "10001",
            "--ust",
            "7",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "8300" in result.output  # Erloese 7%


def test_ausgang_ohne_kunde_fehlt(runner):
    """'collmex ausgang' ohne --kunde gibt Fehler (Pflichtfeld)."""
    result = runner.invoke(
        main,
        [
            "ausgang",
            "Test",
            "--betrag",
            "100.00",
        ],
    )
    assert result.exit_code != 0
    assert "kunde" in result.output.lower()


# ---------------------------------------------------------------------------
# lieferant-anlegen
# ---------------------------------------------------------------------------


def test_lieferant_anlegen_help(runner):
    """'collmex lieferant-anlegen --help' zeigt Optionen."""
    result = runner.invoke(main, ["lieferant-anlegen", "--help"])
    assert result.exit_code == 0
    assert "--name" in result.output
    assert "--ort" in result.output
    assert "--aufwandskonto" in result.output
    assert "--dry-run" in result.output


def test_lieferant_anlegen_dry_run(runner):
    """'collmex lieferant-anlegen --dry-run' zeigt Vorschau ohne Anlage."""
    result = runner.invoke(
        main,
        [
            "lieferant-anlegen",
            "--name",
            "Test-Lieferant GmbH",
            "--ort",
            "Berlin",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "Test-Lieferant GmbH" in result.output
    assert "Berlin" in result.output
    assert "CMXLIF" in result.output
    assert "dry-run" in result.output.lower() or "NICHT" in result.output


def test_lieferant_anlegen_ohne_name_fehlt(runner):
    """'collmex lieferant-anlegen' ohne --name gibt Fehler."""
    result = runner.invoke(main, ["lieferant-anlegen"])
    assert result.exit_code != 0
    assert "name" in result.output.lower()


def test_lieferant_anlegen_mit_api(runner):
    """'collmex lieferant-anlegen' sendet CMXLIF an API."""
    from collmex.api import BookingResult, CollmexMessage, MessageType

    mock_client = MagicMock()
    mock_booking_result = BookingResult(
        success=True,
        booking_id="70001",
        messages=[CollmexMessage(type=MessageType.SUCCESS, code="0", text="OK")],
        raw_response="",
    )
    mock_client.post_booking.return_value = mock_booking_result

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(
            main,
            [
                "lieferant-anlegen",
                "--name",
                "API-Test GmbH",
                "--ort",
                "Hamburg",
            ],
        )
        assert result.exit_code == 0
        assert "angelegt" in result.output
        assert "70001" in result.output


# ---------------------------------------------------------------------------
# kunde-anlegen
# ---------------------------------------------------------------------------


def test_kunde_anlegen_help(runner):
    """'collmex kunde-anlegen --help' zeigt Optionen."""
    result = runner.invoke(main, ["kunde-anlegen", "--help"])
    assert result.exit_code == 0
    assert "--name" in result.output
    assert "--ort" in result.output
    assert "--dry-run" in result.output


def test_kunde_anlegen_dry_run(runner):
    """'collmex kunde-anlegen --dry-run' zeigt Vorschau ohne Anlage."""
    result = runner.invoke(
        main,
        [
            "kunde-anlegen",
            "--name",
            "Test-Kunde AG",
            "--ort",
            "Muenchen",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "Test-Kunde AG" in result.output
    assert "Muenchen" in result.output
    assert "CMXKND" in result.output
    assert "dry-run" in result.output.lower() or "NICHT" in result.output


def test_kunde_anlegen_ohne_name_fehlt(runner):
    """'collmex kunde-anlegen' ohne --name gibt Fehler."""
    result = runner.invoke(main, ["kunde-anlegen"])
    assert result.exit_code != 0
    assert "name" in result.output.lower()


def test_kunde_anlegen_mit_api(runner):
    """'collmex kunde-anlegen' sendet CMXKND an API."""
    from collmex.api import BookingResult, CollmexMessage, MessageType

    mock_client = MagicMock()
    mock_booking_result = BookingResult(
        success=True,
        booking_id="10001",
        messages=[CollmexMessage(type=MessageType.SUCCESS, code="0", text="OK")],
        raw_response="",
    )
    mock_client.post_booking.return_value = mock_booking_result

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(
            main,
            [
                "kunde-anlegen",
                "--name",
                "API-Testkunde GmbH",
                "--ort",
                "Frankfurt",
            ],
        )
        assert result.exit_code == 0
        assert "angelegt" in result.output
        assert "10001" in result.output


# ---------------------------------------------------------------------------
# buchungen (gemockter Client)
# ---------------------------------------------------------------------------


def test_buchungen_help(runner):
    """'collmex buchungen --help' zeigt Optionen."""
    result = runner.invoke(main, ["buchungen", "--help"])
    assert result.exit_code == 0
    assert "--beleg-nr" in result.output
    assert "--von" in result.output
    assert "--bis" in result.output


def test_buchungen_leer(runner):
    """'collmex buchungen' zeigt Meldung bei leeren Daten."""
    mock_client = MagicMock()
    mock_client.get_bookings.return_value = []

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(main, ["buchungen"])
        assert result.exit_code == 0
        assert "Keine" in result.output


def test_buchungen_zeigt_belege(runner):
    """'collmex buchungen' zeigt vorhandene Buchungsbelege."""
    mock_client = MagicMock()
    mock_client.get_bookings.return_value = [
        [
            "ACCDOC",
            "1",
            "42",
            "1",
            "4830",
            "Sonstige",
            "0",
            "500,00",
            "EUR",
            "",
            "20260303",
            "Test",
            "",
        ],
        [
            "ACCDOC",
            "1",
            "42",
            "2",
            "1576",
            "Vorsteuer",
            "0",
            "95,00",
            "EUR",
            "",
            "20260303",
            "Test",
            "",
        ],
        [
            "ACCDOC",
            "1",
            "42",
            "3",
            "1200",
            "Bank",
            "1",
            "595,00",
            "EUR",
            "",
            "20260303",
            "Test",
            "",
        ],
    ]

    with patch("collmex.cli.CollmexClient", return_value=mock_client):
        result = runner.invoke(main, ["buchungen"])
        assert result.exit_code == 0
        assert "42" in result.output
        assert "4830" in result.output
        assert "1200" in result.output


# ---------------------------------------------------------------------------
# abfrage (generisch)
# ---------------------------------------------------------------------------


def test_abfrage_help(runner):
    """'collmex abfrage --help' zeigt Optionen."""
    result = runner.invoke(main, ["abfrage", "--help"])
    assert result.exit_code == 0
    assert "--suche" in result.output


def test_abfrage_kunden_leer(runner):
    """'collmex abfrage CUSTOMER_GET' zeigt Meldung bei leerer Kundenliste."""
    mock_client = MagicMock()
    mock_client.query.return_value = []

    with (
        patch("collmex.cli.CollmexClient", return_value=mock_client),
        patch("collmex.stammdaten.get_field_names", return_value=[]),
    ):
        result = runner.invoke(main, ["abfrage", "CUSTOMER_GET"])
        assert result.exit_code == 0
        assert "Keine" in result.output


# ---------------------------------------------------------------------------
# hilfe
# ---------------------------------------------------------------------------


def test_hilfe_uebersicht(runner):
    """'collmex hilfe' zeigt Kategorien und Satzarten."""
    result = runner.invoke(main, ["hilfe"])
    assert result.exit_code == 0
    assert "Datenimport" in result.output
    assert "Abfragen" in result.output
    assert "Aktionen" in result.output
    assert "CMXINV" in result.output


def test_hilfe_suche(runner):
    """'collmex hilfe --suche rechnung' filtert korrekt."""
    result = runner.invoke(main, ["hilfe", "--suche", "rechnung"])
    assert result.exit_code == 0
    assert "CMXINV" in result.output
    assert "Treffer" in result.output


def test_hilfe_suche_keine_treffer(runner):
    """'collmex hilfe --suche xyzgarbage' zeigt Keine Treffer."""
    result = runner.invoke(main, ["hilfe", "--suche", "xyzgarbage"])
    assert result.exit_code == 0
    assert "Keine Treffer" in result.output


def test_hilfe_detail(runner):
    """'collmex hilfe CMXINV' zeigt Detail-Infos."""
    result = runner.invoke(main, ["hilfe", "CMXINV"])
    assert result.exit_code == 0
    assert "CMXINV" in result.output
    assert "Rechnungen" in result.output
    assert "94" in result.output
    assert "collmex.de" in result.output


def test_hilfe_detail_case_insensitive(runner):
    """'collmex hilfe cmxinv' funktioniert auch kleingeschrieben."""
    result = runner.invoke(main, ["hilfe", "cmxinv"])
    assert result.exit_code == 0
    assert "CMXINV" in result.output


def test_hilfe_nicht_gefunden(runner):
    """'collmex hilfe NONSENSE' gibt Fehler."""
    result = runner.invoke(main, ["hilfe", "NONSENSE"])
    assert result.exit_code != 0
    assert "nicht gefunden" in result.output


def test_hilfe_help(runner):
    """'collmex hilfe --help' zeigt Optionen."""
    result = runner.invoke(main, ["hilfe", "--help"])
    assert result.exit_code == 0
    assert "--suche" in result.output


def test_abfrage_kunden_zeigt_liste(runner):
    """'collmex abfrage CUSTOMER_GET' zeigt vorhandene Kunden."""
    mock_client = MagicMock()
    mock_client.query.return_value = [
        [
            "CMXKND",
            "10001",
            "Testkunde GmbH",
            "Firma",
            "",
            "",
            "",
            "",
            "",
            "12345",
            "Berlin",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "DE123456789",
        ],
    ]

    with (
        patch("collmex.cli.CollmexClient", return_value=mock_client),
        patch(
            "collmex.stammdaten.get_field_names",
            return_value=[
                "Satzart",
                "Kundennummer",
                "Firma",
                "Anrede",
                "Titel",
                "Vorname",
                "Name",
                "Firma2",
                "Abteilung",
                "PLZ",
                "Ort",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "USt.IdNr",
            ],
        ),
    ):
        result = runner.invoke(main, ["abfrage", "CUSTOMER_GET"])
        assert result.exit_code == 0
        assert "Testkunde" in result.output
        assert "1 Ergebnisse" in result.output


def test_abfrage_produkte_zeigt_liste(runner):
    """'collmex abfrage PRODUCT_GET' zeigt vorhandene Produkte."""
    mock_client = MagicMock()
    mock_client.query.return_value = [
        [
            "CMXPRD",
            "WEB-DESIGN",
            "Website-Erstellung",
            "",
            "PCE",
            "",
            "1",
            "0",
            "",
            "",
            "",
            "1",
            "",
            "",
            "3500,00",
        ],
    ]

    with (
        patch("collmex.cli.CollmexClient", return_value=mock_client),
        patch(
            "collmex.stammdaten.get_field_names",
            return_value=[
                "Satzart",
                "Produktnummer",
                "Bezeichnung",
                "Bezeichnung2",
                "Mengeneinheit",
            ],
        ),
    ):
        result = runner.invoke(main, ["abfrage", "PRODUCT_GET"])
        assert result.exit_code == 0
        assert "WEB-DESIGN" in result.output
        assert "1 Ergebnisse" in result.output


def test_abfrage_case_insensitive(runner):
    """'collmex abfrage customer_get' funktioniert auch kleingeschrieben."""
    mock_client = MagicMock()
    mock_client.query.return_value = [
        ["CMXKND", "10001", "Test GmbH"],
    ]

    with (
        patch("collmex.cli.CollmexClient", return_value=mock_client),
        patch("collmex.stammdaten.get_field_names", return_value=[]),
    ):
        result = runner.invoke(main, ["abfrage", "customer_get"])
        assert result.exit_code == 0
        assert "Test GmbH" in result.output


def test_abfrage_mit_suche(runner):
    """'collmex abfrage CUSTOMER_GET --suche helm' filtert korrekt."""
    mock_client = MagicMock()
    mock_client.query.return_value = [
        ["CMXKND", "10001", "Helm GmbH"],
        ["CMXKND", "10002", "Nagel AG"],
    ]

    with (
        patch("collmex.cli.CollmexClient", return_value=mock_client),
        patch("collmex.stammdaten.get_field_names", return_value=["Satzart", "Nr", "Firma"]),
    ):
        result = runner.invoke(main, ["abfrage", "CUSTOMER_GET", "--suche", "helm"])
        assert result.exit_code == 0
        assert "Helm" in result.output
        assert "Nagel" not in result.output


# ---------------------------------------------------------------------------
# webui (gemockter CollmexWebUI)
# ---------------------------------------------------------------------------


def test_webui_help(runner):
    """'collmex webui --help' zeigt Subcommands."""
    result = runner.invoke(main, ["webui", "--help"])
    assert result.exit_code == 0
    assert "mengeneinheiten" in result.output
    assert "zahlungsbedingungen" in result.output
    assert "firma" in result.output


def test_webui_mengeneinheiten(runner):
    """'collmex webui mengeneinheiten' zeigt Mengeneinheiten-Tabelle."""
    from collmex.webui import Mengeneinheit

    mock_einheiten = [
        Mengeneinheit("PCE", "St", "pcs", 0, "Stueck", "H87"),
        Mengeneinheit("HR", "h", "h", 2, "Stunden", "HUR"),
    ]

    with patch("collmex.webui.CollmexWebUI") as MockWUI:
        MockWUI.return_value.mengeneinheiten.return_value = mock_einheiten
        result = runner.invoke(main, ["webui", "mengeneinheiten"])
        assert result.exit_code == 0
        assert "PCE" in result.output
        assert "Stueck" in result.output
        assert "2 Mengeneinheiten" in result.output


def test_webui_zahlungsbedingungen(runner):
    """'collmex webui zahlungsbedingungen' zeigt Zahlungsbedingungen."""
    from collmex.webui import Zahlungsbedingung

    mock_zb = [
        Zahlungsbedingung(0, "30 Tage ohne Abzug"),
        Zahlungsbedingung(1, "Sofort ohne Abzug"),
    ]

    with patch("collmex.webui.CollmexWebUI") as MockWUI:
        MockWUI.return_value.zahlungsbedingungen.return_value = mock_zb
        result = runner.invoke(main, ["webui", "zahlungsbedingungen"])
        assert result.exit_code == 0
        assert "30 Tage" in result.output
        assert "2 Zahlungsbedingungen" in result.output


def test_webui_firma(runner):
    """'collmex webui firma' zeigt Firmenstammdaten."""
    from collmex.webui import Firmenstammdaten

    mock_firma = Firmenstammdaten(
        firma="Test GmbH",
        strasse="Teststr. 1",
        plz="12345",
        ort="Berlin",
        land="DE",
        email="test@test.de",
        ust_idnr="DE123456789",
        steuernummer="12/345/67890",
        bankkonto="1200",
        kontenrahmen="DATEV SKR 03",
    )

    with patch("collmex.webui.CollmexWebUI") as MockWUI:
        MockWUI.return_value.firmenstammdaten.return_value = mock_firma
        result = runner.invoke(main, ["webui", "firma"])
        assert result.exit_code == 0
        assert "Test GmbH" in result.output
        assert "DE123456789" in result.output
        assert "SKR 03" in result.output


def test_webui_ohne_credentials(runner):
    """'collmex webui firma' ohne Credentials zeigt Fehler."""
    with patch("collmex.webui.load_dotenv"):
        with patch.dict(
            "os.environ",
            {
                "COLLMEX_CUSTOMER": "123456",
                "COLLMEX_WEB_USER": "",
                "COLLMEX_WEB_PASSWORD": "",
            },
            clear=False,
        ):
            result = runner.invoke(main, ["webui", "firma"])
            assert result.exit_code != 0
            assert "Web-UI" in result.output or "WEB_USER" in result.output
