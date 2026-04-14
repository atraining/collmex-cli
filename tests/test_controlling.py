"""Tests fuer collmex.controlling — ControllingEngine.

Alle Tests mocken den API-Client, keine echten API-Calls.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from collmex.controlling import ControllingEngine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    """Erzeugt einen gemockten CollmexClient."""
    return MagicMock()


@pytest.fixture
def engine(mock_client):
    """Erzeugt eine ControllingEngine mit gemocktem Client."""
    return ControllingEngine(mock_client)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _make_accbal_row(konto: int, soll: str, haben: str) -> list[str]:
    """Erzeugt eine ACC_BAL-Zeile im echten Collmex-Format (4 Felder).

    Berechnet den Saldo aus soll - haben fuer Rueckwaertskompatibilitaet
    der bestehenden Testaufrufe.
    """
    from collmex.api import parse_amount

    soll_val = parse_amount(soll)
    haben_val = parse_amount(haben)
    saldo = soll_val - haben_val
    saldo_str = str(saldo).replace(".", ",")
    return ["ACC_BAL", str(konto), "Bezeichnung", saldo_str]


# ---------------------------------------------------------------------------
# Tests: _get_balance
# ---------------------------------------------------------------------------


class TestGetBalance:
    def test_balance_returns_soll_minus_haben(self, engine, mock_client):
        """Saldo = Soll - Haben."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(1200, "10000,00", "3000,00"),
        ]
        result = engine._get_balance(1200, 2026, 3)
        assert result == Decimal("7000.00")

    def test_balance_empty_rows(self, engine, mock_client):
        """Leere Antwort ergibt Saldo 0."""
        mock_client.get_balances.return_value = []
        result = engine._get_balance(1200, 2026, 3)
        assert result == Decimal("0")

    def test_balance_multiple_rows(self, engine, mock_client):
        """Mehrere Zeilen werden summiert."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(1200, "5000,00", "1000,00"),
            _make_accbal_row(1200, "3000,00", "500,00"),
        ]
        result = engine._get_balance(1200, 2026, 3)
        assert result == Decimal("6500.00")


# ---------------------------------------------------------------------------
# Tests: _get_account_range_total
# ---------------------------------------------------------------------------


class TestGetAccountRangeTotal:
    def test_range_filters_correctly(self, engine, mock_client):
        """Nur Konten im angegebenen Bereich werden summiert."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(4100, "5000,00", "0,00"),
            _make_accbal_row(4400, "800,00", "0,00"),
            _make_accbal_row(8400, "0,00", "10000,00"),  # ausserhalb
            _make_accbal_row(3999, "100,00", "0,00"),  # ausserhalb
        ]
        result = engine._get_account_range_total(4000, 4999, 2026, 3)
        assert result == Decimal("5800.00")

    def test_range_empty(self, engine, mock_client):
        """Keine Konten im Bereich ergibt 0."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(1200, "5000,00", "0,00"),
        ]
        result = engine._get_account_range_total(4000, 4999, 2026, 3)
        assert result == Decimal("0")


# ---------------------------------------------------------------------------
# Tests: dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    def _setup_dashboard_mocks(self, mock_client):
        """Konfiguriert die Mocks fuer einen vollstaendigen Dashboard-Aufruf."""

        def get_balances_side_effect(year, period, account=None):
            if account == 1200:
                return [_make_accbal_row(1200, "50000,00", "0,00")]
            if account == 1000:
                return [_make_accbal_row(1000, "2000,00", "0,00")]
            if account == 1400:
                return [_make_accbal_row(1400, "15000,00", "0,00")]
            if account == 1600:
                return [_make_accbal_row(1600, "0,00", "20000,00")]
            if account is None:
                # Fuer _get_account_range_total
                return [
                    _make_accbal_row(8400, "0,00", "30000,00"),
                    _make_accbal_row(8300, "0,00", "5000,00"),
                    _make_accbal_row(4100, "10000,00", "0,00"),
                    _make_accbal_row(4400, "2000,00", "0,00"),
                    _make_accbal_row(4800, "3000,00", "0,00"),
                ]
            return []

        mock_client.get_balances.side_effect = get_balances_side_effect

    def test_dashboard_returns_all_keys(self, engine, mock_client):
        """Dashboard-Dict enthaelt alle erwarteten Schluessel."""
        self._setup_dashboard_mocks(mock_client)
        result = engine.dashboard()
        expected_keys = {
            "kontostand",
            "offene_forderungen",
            "offene_verbindlichkeiten",
            "umsatz_monat",
            "kosten_monat",
            "ergebnis_monat",
            "liquiditaet_1",
            "dso",
        }
        assert set(result.keys()) == expected_keys

    def test_dashboard_kontostand(self, engine, mock_client):
        """Bank-Kontostand wird korrekt gelesen."""
        self._setup_dashboard_mocks(mock_client)
        result = engine.dashboard()
        assert result["kontostand"] == Decimal("50000.00")

    def test_dashboard_forderungen(self, engine, mock_client):
        """Offene Forderungen werden korrekt gelesen."""
        self._setup_dashboard_mocks(mock_client)
        result = engine.dashboard()
        assert result["offene_forderungen"] == Decimal("15000.00")

    def test_dashboard_verbindlichkeiten(self, engine, mock_client):
        """Verbindlichkeiten werden als positiver Betrag zurueckgegeben."""
        self._setup_dashboard_mocks(mock_client)
        result = engine.dashboard()
        assert result["offene_verbindlichkeiten"] == Decimal("20000.00")

    def test_dashboard_ergebnis(self, engine, mock_client):
        """Ergebnis = Umsatz - Kosten."""
        self._setup_dashboard_mocks(mock_client)
        result = engine.dashboard()
        # Umsatz: abs(-30000 + -5000) aus Bereich 8100-8700 = 35000
        # Kosten: 10000 + 2000 + 3000 aus Bereich 4000-4999 = 15000
        assert result["ergebnis_monat"] == result["umsatz_monat"] - result["kosten_monat"]

    def test_dashboard_liquiditaet_1(self, engine, mock_client):
        """Liquiditaet 1. Grades = (Bank + Kasse) / Verbindlichkeiten."""
        self._setup_dashboard_mocks(mock_client)
        result = engine.dashboard()
        # (50000 + 2000) / 20000 = 2.60
        assert result["liquiditaet_1"] == Decimal("2.60")

    def test_dashboard_liquiditaet_zero_verbindlichkeiten(self, engine, mock_client):
        """Bei 0 Verbindlichkeiten ist Liquiditaet 0."""

        def get_balances_side_effect(year, period, account=None):
            if account == 1200:
                return [_make_accbal_row(1200, "50000,00", "0,00")]
            if account == 1000:
                return [_make_accbal_row(1000, "2000,00", "0,00")]
            if account == 1400:
                return [_make_accbal_row(1400, "0,00", "0,00")]
            if account == 1600:
                return [_make_accbal_row(1600, "0,00", "0,00")]
            if account is None:
                return []
            return []

        mock_client.get_balances.side_effect = get_balances_side_effect
        result = engine.dashboard()
        assert result["liquiditaet_1"] == Decimal("0")

    def test_dashboard_dso_zero_umsatz(self, engine, mock_client):
        """Bei 0 Umsatz ist DSO 0."""

        def get_balances_side_effect(year, period, account=None):
            if account == 1200:
                return [_make_accbal_row(1200, "10000,00", "0,00")]
            if account == 1000:
                return []
            if account == 1400:
                return [_make_accbal_row(1400, "5000,00", "0,00")]
            if account == 1600:
                return []
            if account is None:
                return []
            return []

        mock_client.get_balances.side_effect = get_balances_side_effect
        result = engine.dashboard()
        assert result["dso"] == Decimal("0")

    def test_dashboard_all_values_are_decimal(self, engine, mock_client):
        """Alle Dashboard-Werte sind Decimal."""
        self._setup_dashboard_mocks(mock_client)
        result = engine.dashboard()
        for key, value in result.items():
            assert isinstance(value, Decimal), f"{key} ist {type(value)}, erwartet Decimal"


# ---------------------------------------------------------------------------
# Tests: liquiditaetsvorschau
# ---------------------------------------------------------------------------


class TestLiquiditaetsvorschau:
    def test_returns_correct_number_of_weeks(self, engine, mock_client):
        """Gibt die angeforderte Anzahl Wochen zurueck."""
        mock_client.get_open_items.return_value = []
        result = engine.liquiditaetsvorschau(wochen=8)
        assert len(result) == 8

    def test_default_13_weeks(self, engine, mock_client):
        """Standard sind 13 Wochen."""
        mock_client.get_open_items.return_value = []
        result = engine.liquiditaetsvorschau()
        assert len(result) == 13

    def test_week_dict_has_correct_keys(self, engine, mock_client):
        """Jede Woche hat die erwarteten Schluessel."""
        mock_client.get_open_items.return_value = []
        result = engine.liquiditaetsvorschau(wochen=1)
        expected_keys = {
            "woche",
            "start",
            "erwartete_eingaenge",
            "erwartete_ausgaenge",
            "saldo",
        }
        assert set(result[0].keys()) == expected_keys

    def test_saldo_is_eingaenge_minus_ausgaenge(self, engine, mock_client):
        """Saldo = Eingaenge - Ausgaenge (auch bei leeren Daten)."""
        mock_client.get_open_items.return_value = []
        result = engine.liquiditaetsvorschau(wochen=1)
        w = result[0]
        assert w["saldo"] == w["erwartete_eingaenge"] - w["erwartete_ausgaenge"]

    def test_open_items_assigned_to_correct_week(self, engine, mock_client):
        """Offene Posten werden der richtigen Woche zugeordnet."""
        heute = date.today()
        montag = heute - timedelta(days=heute.weekday())
        # Faelligkeit in der zweiten Woche (Mittwoch)
        target_date = montag + timedelta(days=9)
        faellig_str = target_date.strftime("%Y%m%d")

        mock_client.get_open_items.return_value = [
            # Debitor-Posten (Personenkonto 10000 = Eingang)
            [
                "OPEN_ITEM",
                "1",
                "2026",
                "3",
                "1",
                "10000",
                "Kunde A",
                "",
                "",
                "R001",
                "20260101",
                "",
                faellig_str,
                "0",
                "0",
                "",
                "0,00",
                "5000,00",
                "0,00",
                "5000,00",
            ],
        ]
        result = engine.liquiditaetsvorschau(wochen=4)
        # Woche 1 (Index 1) sollte den Eingang haben
        assert result[1]["erwartete_eingaenge"] == Decimal("5000.00")
        assert result[0]["erwartete_eingaenge"] == Decimal("0")


# ---------------------------------------------------------------------------
# Tests: soll_ist
# ---------------------------------------------------------------------------


class TestSollIst:
    def test_basic_comparison(self, engine, mock_client):
        """Grundlegender Soll-Ist-Vergleich."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(4400, "800,00", "0,00"),
        ]
        budget = {4400: Decimal("1000.00")}
        result = engine.soll_ist(3, 2026, budget)
        assert len(result) == 1
        assert result[0]["konto"] == 4400
        assert result[0]["budget"] == Decimal("1000.00")
        assert result[0]["ist"] == Decimal("800.00")
        assert result[0]["abweichung"] == Decimal("-200.00")

    def test_ampel_gruen(self, engine, mock_client):
        """Ampel ist gruen bei <= 100%."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(4400, "900,00", "0,00"),
        ]
        budget = {4400: Decimal("1000.00")}
        result = engine.soll_ist(3, 2026, budget)
        assert result[0]["ampel"] == "gruen"

    def test_ampel_gelb(self, engine, mock_client):
        """Ampel ist gelb bei 101-120%."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(4400, "1100,00", "0,00"),
        ]
        budget = {4400: Decimal("1000.00")}
        result = engine.soll_ist(3, 2026, budget)
        assert result[0]["ampel"] == "gelb"

    def test_ampel_rot(self, engine, mock_client):
        """Ampel ist rot bei > 120%."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(4400, "1500,00", "0,00"),
        ]
        budget = {4400: Decimal("1000.00")}
        result = engine.soll_ist(3, 2026, budget)
        assert result[0]["ampel"] == "rot"

    def test_zero_budget(self, engine, mock_client):
        """Bei Budget 0 ist Prozent 0."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(4400, "500,00", "0,00"),
        ]
        budget = {4400: Decimal("0")}
        result = engine.soll_ist(3, 2026, budget)
        assert result[0]["prozent"] == Decimal("0")

    def test_multiple_accounts(self, engine, mock_client):
        """Mehrere Konten werden korrekt verarbeitet."""

        def get_balances_side_effect(year, period, account=None):
            data = {
                4100: [_make_accbal_row(4100, "8000,00", "0,00")],
                4400: [_make_accbal_row(4400, "500,00", "0,00")],
                4800: [_make_accbal_row(4800, "2000,00", "0,00")],
            }
            return data.get(account, [])

        mock_client.get_balances.side_effect = get_balances_side_effect
        budget = {
            4100: Decimal("10000.00"),
            4400: Decimal("600.00"),
            4800: Decimal("1500.00"),
        }
        result = engine.soll_ist(3, 2026, budget)
        assert len(result) == 3
        # Sortiert nach Kontonummer
        assert result[0]["konto"] == 4100
        assert result[1]["konto"] == 4400
        assert result[2]["konto"] == 4800

    def test_result_dict_keys(self, engine, mock_client):
        """Jedes Ergebnis hat die erwarteten Schluessel."""
        mock_client.get_balances.return_value = [
            _make_accbal_row(4400, "500,00", "0,00"),
        ]
        budget = {4400: Decimal("1000.00")}
        result = engine.soll_ist(3, 2026, budget)
        expected_keys = {"konto", "budget", "ist", "abweichung", "prozent", "ampel"}
        assert set(result[0].keys()) == expected_keys
