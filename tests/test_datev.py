"""Tests fuer collmex.datev — DATEV Buchungsstapel Export."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from collmex.datev import (
    DatevExporter,
    _datum_to_ddmm,
    _format_datev_amount,
    _make_header,
)

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


class TestFormatDatevAmount:
    def test_positive(self):
        assert _format_datev_amount(Decimal("500.00")) == "500,00"

    def test_negative_becomes_positive(self):
        assert _format_datev_amount(Decimal("-500.00")) == "500,00"

    def test_rounding(self):
        assert _format_datev_amount(Decimal("1234.567")) == "1234,57"

    def test_zero(self):
        assert _format_datev_amount(Decimal("0")) == "0,00"


class TestDatumToDDMM:
    def test_normal(self):
        assert _datum_to_ddmm("20260303") == "0303"

    def test_december(self):
        assert _datum_to_ddmm("20261231") == "3112"

    def test_invalid(self):
        assert _datum_to_ddmm("invalid") == ""

    def test_empty(self):
        assert _datum_to_ddmm("") == ""


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


class TestMakeHeader:
    def test_contains_extf(self):
        h = _make_header(12345, 1, "20260101", "20260301", "20260331")
        assert '"EXTF"' in h

    def test_contains_berater(self):
        h = _make_header(99999, 42, "20260101", "20260301", "20260331")
        assert "99999" in h
        assert "42" in h

    def test_contains_datum(self):
        h = _make_header(12345, 1, "20260101", "20260301", "20260331")
        assert "20260301" in h
        assert "20260331" in h

    def test_contains_bezeichnung(self):
        h = _make_header(12345, 1, "20260101", "20260301", "20260331", bezeichnung="Testexport")
        assert "Testexport" in h

    def test_has_31_fields(self):
        h = _make_header(12345, 1, "20260101", "20260301", "20260331")
        assert h.count(";") == 30  # 31 Felder = 30 Trennzeichen


# ---------------------------------------------------------------------------
# Exporter
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    return MagicMock()


class TestDatevExporter:
    def test_empty_export(self, mock_client):
        """Export ohne Buchungen erzeugt Header + Spaltenheader."""
        mock_client.get_bookings.return_value = []
        exp = DatevExporter(mock_client)
        result = exp.export("20260301", "20260331")
        lines = result.strip().split("\r\n")
        assert len(lines) == 2  # Header + Spaltenheader
        assert '"EXTF"' in lines[0]

    def test_export_with_bookings(self, mock_client):
        """Export mit Buchungen erzeugt korrekte DATEV-Zeilen."""
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
                "Bueromaterial",
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
                "Vorsteuer 19%",
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
                "Bank",
            ],
        ]
        exp = DatevExporter(mock_client, berater_nr=54321, mandant_nr=7)
        result = exp.export("20260301", "20260331")
        lines = result.strip().split("\r\n")
        assert len(lines) == 5  # Header + ColHeader + 3 Buchungszeilen
        assert "54321" in lines[0]
        assert "500,00" in lines[2]
        assert '"S"' in lines[2]  # Soll
        assert '"H"' in lines[4]  # Haben

    def test_export_grouped(self, mock_client):
        """Gruppierter Export fasst Belege zusammen."""
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
                "Bueromaterial",
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
                "Vorsteuer 19%",
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
                "Bank",
            ],
        ]
        exp = DatevExporter(mock_client)
        result = exp.export_grouped("20260301", "20260331")
        lines = result.strip().split("\r\n")
        # Gruppiert: 2 Soll-Zeilen mit Gegenkonto 1200
        assert len(lines) >= 3  # Header + ColHeader + mind. 1 Buchung
        # Gegenkonto 1200 sollte in den gruppierten Zeilen auftauchen
        data_lines = lines[2:]
        assert any("1200" in line for line in data_lines)

    def test_crlf_line_endings(self, mock_client):
        """Export verwendet CRLF Zeilenenden."""
        mock_client.get_bookings.return_value = []
        exp = DatevExporter(mock_client)
        result = exp.export("20260301", "20260331")
        assert "\r\n" in result

    def test_belegdatum_ddmm(self, mock_client):
        """Belegdatum wird als DDMM formatiert."""
        mock_client.get_bookings.return_value = [
            [
                "ACCDOC",
                "1",
                "1",
                "1",
                "4830",
                "Sonstige",
                "0",
                "100,00",
                "EUR",
                "",
                "20260315",
                "Test",
            ],
        ]
        exp = DatevExporter(mock_client)
        result = exp.export("20260301", "20260331")
        assert "1503" in result  # 15. Maerz -> 1503

    def test_bezeichnung_auto(self, mock_client):
        """Bezeichnung wird automatisch generiert."""
        mock_client.get_bookings.return_value = []
        exp = DatevExporter(mock_client)
        result = exp.export("20260301", "20260331")
        assert "03/2026" in result

    def test_125_fields_per_line(self, mock_client):
        """Jede Buchungszeile hat 125 Felder."""
        mock_client.get_bookings.return_value = [
            [
                "ACCDOC",
                "1",
                "1",
                "1",
                "4830",
                "Sonstige",
                "0",
                "100,00",
                "EUR",
                "",
                "20260303",
                "Test",
            ],
        ]
        exp = DatevExporter(mock_client)
        result = exp.export("20260301", "20260331")
        lines = result.strip().split("\r\n")
        data_line = lines[2]
        # 125 Felder = 124 Semikolons
        assert data_line.count(";") == 124
