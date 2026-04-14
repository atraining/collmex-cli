"""Tests für collmex.taxes: TaxEngine.

Alle Tests mocken den API-Client, keine echten API-Calls.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from collmex.taxes import TaxEngine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def engine(mock_client):
    return TaxEngine(mock_client)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _make_accbal_row(konto: int, soll: str, haben: str) -> list[str]:
    """Erzeugt eine ACC_BAL-Zeile im echten Collmex-Format (4 Felder).

    Berechnet den Saldo aus soll - haben für Rückwärtskompatibilität.
    """
    from collmex.api import parse_amount

    soll_val = parse_amount(soll)
    haben_val = parse_amount(haben)
    saldo = soll_val - haben_val
    saldo_str = str(saldo).replace(".", ",")
    return ["ACC_BAL", str(konto), "Bezeichnung", saldo_str]


def _setup_standard_ustva_mocks(mock_client):
    """Konfiguriert Mocks für einen Standard-UStVA-Fall.

    Szenario:
    - Erlöse 19% (8400): 10.000 EUR (Haben)
    - Erlöse 7% (8300): 2.000 EUR (Haben)
    - USt 19% (1776): 1.900 EUR (Haben)
    - USt 7% (1771): 140 EUR (Haben)
    - VSt 19% (1576): 500 EUR (Soll)
    - VSt 7% (1571): 70 EUR (Soll)
    - VSt §13b (1580): 0 EUR
    """

    def get_balances_side_effect(year, period, account=None):
        data = {
            8400: [_make_accbal_row(8400, "0,00", "10000,00")],
            8300: [_make_accbal_row(8300, "0,00", "2000,00")],
            1776: [_make_accbal_row(1776, "0,00", "1900,00")],
            1771: [_make_accbal_row(1771, "0,00", "140,00")],
            1576: [_make_accbal_row(1576, "500,00", "0,00")],
            1571: [_make_accbal_row(1571, "70,00", "0,00")],
            1580: [_make_accbal_row(1580, "0,00", "0,00")],
        }
        return data.get(account, [])

    mock_client.get_balances.side_effect = get_balances_side_effect


# ---------------------------------------------------------------------------
# Tests: _get_saldo
# ---------------------------------------------------------------------------


class TestGetSaldo:
    def test_saldo_soll_konto(self, engine, mock_client):
        """Saldo eines Aktivkontos (Soll - Haben)."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(1576, "500,00", "0,00"),
        ]
        result = engine._get_saldo(1576, 2026, 3)
        assert result == Decimal("500.00")

    def test_saldo_haben_konto(self, engine, mock_client):
        """Saldo eines Passivkontos (Soll - Haben = negativ)."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(1776, "0,00", "1900,00"),
        ]
        result = engine._get_saldo(1776, 2026, 3)
        assert result == Decimal("-1900.00")

    def test_saldo_empty(self, engine, mock_client):
        """Leere Antwort ergibt 0."""
        mock_client.get_balances.return_value = []
        result = engine._get_saldo(9999, 2026, 3)
        assert result == Decimal("0")


# ---------------------------------------------------------------------------
# Tests: ustva
# ---------------------------------------------------------------------------


class TestUstva:
    def test_returns_all_keys(self, engine, mock_client):
        """UStVA-Dict enthält alle erwarteten Kennzahlen."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        expected_keys = {
            "kz81",
            "kz86",
            "ust_19",
            "ust_7",
            "ust_zahllast",
            "kz66",
            "kz61",
            "kz67",
            "vst_abzug",
            "vorauszahlung",
            "kz83",
            "jahr",
            "monat",
        }
        assert set(result.keys()) == expected_keys

    def test_kz81_umsätze_19(self, engine, mock_client):
        """KZ81: Steuerpflichtige Umsätze 19% (Netto)."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        assert result["kz81"] == Decimal("10000.00")

    def test_kz86_umsätze_7(self, engine, mock_client):
        """KZ86: Steuerpflichtige Umsätze 7% (Netto)."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        assert result["kz86"] == Decimal("2000.00")

    def test_ust_zahllast(self, engine, mock_client):
        """USt-Zahllast = USt 19% + USt 7%."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        assert result["ust_zahllast"] == Decimal("2040.00")
        assert result["ust_zahllast"] == result["ust_19"] + result["ust_7"]

    def test_kz66_vorsteuer_19(self, engine, mock_client):
        """KZ66: Vorsteuer 19%."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        assert result["kz66"] == Decimal("500.00")

    def test_kz61_vorsteuer_7(self, engine, mock_client):
        """KZ61: Vorsteuer 7%."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        assert result["kz61"] == Decimal("70.00")

    def test_kz67_vorsteuer_13b(self, engine, mock_client):
        """KZ67: Vorsteuer §13b."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        assert result["kz67"] == Decimal("0")

    def test_vst_abzug(self, engine, mock_client):
        """Vorsteuerabzug = VSt 19% + VSt 7% + VSt §13b."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        assert result["vst_abzug"] == Decimal("570.00")
        assert result["vst_abzug"] == result["kz66"] + result["kz61"] + result["kz67"]

    def test_vorauszahlung(self, engine, mock_client):
        """Vorauszahlung = Zahllast - Vorsteuerabzug."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        assert result["vorauszahlung"] == Decimal("1470.00")
        assert result["vorauszahlung"] == result["ust_zahllast"] - result["vst_abzug"]

    def test_kz83_equals_vorauszahlung(self, engine, mock_client):
        """KZ83 = Vorauszahlung."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        assert result["kz83"] == result["vorauszahlung"]

    def test_jahr_and_monat(self, engine, mock_client):
        """Jahr und Monat werden im Ergebnis zurückgegeben."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        assert result["jahr"] == 2026
        assert result["monat"] == 3

    def test_negative_vorauszahlung(self, engine, mock_client):
        """Vorauszahlung kann negativ sein (Vorsteuererstattung)."""

        def get_balances_side_effect(year, period, account=None):
            data = {
                8400: [_make_accbal_row(8400, "0,00", "1000,00")],
                8300: [],
                1776: [_make_accbal_row(1776, "0,00", "190,00")],
                1771: [],
                1576: [_make_accbal_row(1576, "5000,00", "0,00")],
                1571: [],
                1580: [],
            }
            return data.get(account, [])

        mock_client.get_balances.side_effect = get_balances_side_effect
        result = engine.ustva(2026, 3)
        assert result["vorauszahlung"] < Decimal("0")

    def test_all_values_decimal_or_int(self, engine, mock_client):
        """Alle Geldbeträge sind Decimal, Jahr/Monat sind int."""
        _setup_standard_ustva_mocks(mock_client)
        result = engine.ustva(2026, 3)
        decimal_keys = {
            "kz81",
            "kz86",
            "ust_19",
            "ust_7",
            "ust_zahllast",
            "kz66",
            "kz61",
            "kz67",
            "vst_abzug",
            "vorauszahlung",
            "kz83",
        }
        for key in decimal_keys:
            assert isinstance(result[key], Decimal), f"{key} ist {type(result[key])}"
        assert isinstance(result["jahr"], int)
        assert isinstance(result["monat"], int)

    def test_zero_activity_month(self, engine, mock_client):
        """Monat ohne Buchungen ergibt ueberall 0."""
        mock_client.get_balances.return_value = []
        result = engine.ustva(2026, 1)
        assert result["kz81"] == Decimal("0")
        assert result["kz86"] == Decimal("0")
        assert result["ust_zahllast"] == Decimal("0")
        assert result["vst_abzug"] == Decimal("0")
        assert result["vorauszahlung"] == Decimal("0")
