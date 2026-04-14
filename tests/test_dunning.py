"""Tests fuer collmex.dunning — DunningEngine.

Alle Tests mocken den API-Client, keine echten API-Calls.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from collmex.dunning import DunningEngine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def engine(mock_client):
    return DunningEngine(mock_client)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _make_open_item(
    konto: int = 10000,
    kunde_name: str = "Musterkunde GmbH",
    beleg_nr: str = "R001",
    datum: str = "20260101",
    faellig: str = "20260131",
    betrag: str = "1000,00",
) -> list[str]:
    """Erzeugt eine OPEN_ITEM-Zeile im echten Collmex-Format (20 Felder)."""
    return [
        "OPEN_ITEM",
        "1",
        "2026",
        "3",
        "1",
        str(konto),
        kunde_name,
        "",
        "",
        beleg_nr,
        datum,
        "",
        faellig,
        "0",
        "0",
        "",
        "0,00",
        betrag,
        "0,00",
        betrag,
    ]


def _date_str(days_ago: int) -> str:
    """Gibt ein Datum als YYYYMMDD-String zurueck, X Tage vor heute."""
    d = date.today() - timedelta(days=days_ago)
    return d.strftime("%Y%m%d")


# ---------------------------------------------------------------------------
# Tests: _parse_date
# ---------------------------------------------------------------------------


class TestParseDate:
    def test_valid_date(self):
        result = DunningEngine._parse_date("20260303")
        assert result == date(2026, 3, 3)

    def test_invalid_date(self):
        assert DunningEngine._parse_date("20261301") is None

    def test_empty_string(self):
        assert DunningEngine._parse_date("") is None

    def test_wrong_length(self):
        assert DunningEngine._parse_date("2026030") is None


# ---------------------------------------------------------------------------
# Tests: _mahnstufe
# ---------------------------------------------------------------------------


class TestMahnstufe:
    def test_stufe_0_not_overdue(self):
        assert DunningEngine._mahnstufe(0) == 0

    def test_stufe_0_under_30(self):
        assert DunningEngine._mahnstufe(30) == 0

    def test_stufe_1(self):
        assert DunningEngine._mahnstufe(31) == 1
        assert DunningEngine._mahnstufe(60) == 1

    def test_stufe_2(self):
        assert DunningEngine._mahnstufe(61) == 2
        assert DunningEngine._mahnstufe(90) == 2

    def test_stufe_3(self):
        assert DunningEngine._mahnstufe(91) == 3
        assert DunningEngine._mahnstufe(365) == 3


# ---------------------------------------------------------------------------
# Tests: get_overdue_items
# ---------------------------------------------------------------------------


class TestGetOverdueItems:
    def test_returns_only_overdue(self, engine, mock_client):
        """Nur ueberfaellige Posten (> 0 Tage) werden zurueckgegeben."""
        mock_client.get_open_items.return_value = [
            # 45 Tage ueberfaellig
            _make_open_item(faellig=_date_str(45), betrag="1000,00"),
            # Noch nicht faellig (in der Zukunft)
            _make_open_item(
                beleg_nr="R002",
                faellig=(date.today() + timedelta(days=10)).strftime("%Y%m%d"),
                betrag="2000,00",
            ),
        ]
        result = engine.get_overdue_items()
        assert len(result) == 1
        assert result[0]["betrag"] == Decimal("1000.00")

    def test_sorted_by_days_overdue_desc(self, engine, mock_client):
        """Sortiert nach Tagen ueberfaellig, aelteste zuerst."""
        mock_client.get_open_items.return_value = [
            _make_open_item(beleg_nr="R001", faellig=_date_str(31), betrag="500,00"),
            _make_open_item(beleg_nr="R002", faellig=_date_str(91), betrag="800,00"),
            _make_open_item(beleg_nr="R003", faellig=_date_str(61), betrag="300,00"),
        ]
        result = engine.get_overdue_items()
        assert len(result) == 3
        assert result[0]["tage_ueberfaellig"] >= result[1]["tage_ueberfaellig"]
        assert result[1]["tage_ueberfaellig"] >= result[2]["tage_ueberfaellig"]

    def test_empty_when_no_overdue(self, engine, mock_client):
        """Leere Liste wenn keine ueberfaelligen Posten."""
        mock_client.get_open_items.return_value = [
            _make_open_item(
                faellig=(date.today() + timedelta(days=30)).strftime("%Y%m%d"),
            ),
        ]
        result = engine.get_overdue_items()
        assert result == []

    def test_filters_only_debitoren(self, engine, mock_client):
        """Nur Debitoren (Personenkonten 10000-69999) werden beruecksichtigt."""
        mock_client.get_open_items.return_value = [
            _make_open_item(konto=10000, faellig=_date_str(45)),
            _make_open_item(konto=70000, faellig=_date_str(45)),  # Kreditor
            _make_open_item(konto=1200, faellig=_date_str(45)),  # Sachkonto
        ]
        result = engine.get_overdue_items()
        assert len(result) == 1

    def test_result_dict_keys(self, engine, mock_client):
        """Jedes Ergebnis hat die erwarteten Schluessel."""
        mock_client.get_open_items.return_value = [
            _make_open_item(faellig=_date_str(45)),
        ]
        result = engine.get_overdue_items()
        expected_keys = {
            "kunde",
            "kunde_nr",
            "beleg_nr",
            "betrag",
            "datum",
            "faellig",
            "tage_ueberfaellig",
            "mahnstufe",
        }
        assert set(result[0].keys()) == expected_keys

    def test_mahnstufe_assigned_correctly(self, engine, mock_client):
        """Mahnstufe wird korrekt zugeordnet."""
        mock_client.get_open_items.return_value = [
            _make_open_item(beleg_nr="R001", faellig=_date_str(45)),
        ]
        result = engine.get_overdue_items()
        assert result[0]["mahnstufe"] == 1  # 45 Tage = Stufe 1


# ---------------------------------------------------------------------------
# Tests: altersstruktur
# ---------------------------------------------------------------------------


class TestAltersstruktur:
    def test_structure_has_all_keys(self, engine, mock_client):
        """Altersstruktur hat alle erwarteten Schluessel."""
        mock_client.get_open_items.return_value = []
        result = engine.altersstruktur()
        expected_keys = {"nicht_faellig", "stufe_1", "stufe_2", "stufe_3", "gesamt"}
        assert set(result.keys()) == expected_keys

    def test_empty_items(self, engine, mock_client):
        """Leere Posten ergeben ueberall 0."""
        mock_client.get_open_items.return_value = []
        result = engine.altersstruktur()
        assert result["gesamt"]["anzahl"] == 0
        assert result["gesamt"]["summe"] == Decimal("0")

    def test_classification_stufe_1(self, engine, mock_client):
        """Posten 31-60 Tage ueberfaellig -> stufe_1."""
        mock_client.get_open_items.return_value = [
            _make_open_item(faellig=_date_str(45), betrag="1000,00"),
        ]
        result = engine.altersstruktur()
        assert result["stufe_1"]["anzahl"] == 1
        assert result["stufe_1"]["summe"] == Decimal("1000.00")

    def test_classification_stufe_3(self, engine, mock_client):
        """Posten > 90 Tage ueberfaellig -> stufe_3."""
        mock_client.get_open_items.return_value = [
            _make_open_item(faellig=_date_str(120), betrag="5000,00"),
        ]
        result = engine.altersstruktur()
        assert result["stufe_3"]["anzahl"] == 1
        assert result["stufe_3"]["summe"] == Decimal("5000.00")

    def test_gesamt_summe(self, engine, mock_client):
        """Gesamt-Summe stimmt mit der Summe aller Stufen ueberein."""
        mock_client.get_open_items.return_value = [
            _make_open_item(beleg_nr="R001", faellig=_date_str(10), betrag="1000,00"),
            _make_open_item(beleg_nr="R002", faellig=_date_str(45), betrag="2000,00"),
            _make_open_item(beleg_nr="R003", faellig=_date_str(75), betrag="3000,00"),
            _make_open_item(beleg_nr="R004", faellig=_date_str(120), betrag="4000,00"),
        ]
        result = engine.altersstruktur()
        total = (
            result["nicht_faellig"]["summe"]
            + result["stufe_1"]["summe"]
            + result["stufe_2"]["summe"]
            + result["stufe_3"]["summe"]
        )
        assert total == result["gesamt"]["summe"]
        assert result["gesamt"]["anzahl"] == 4

    def test_nicht_faellig_category(self, engine, mock_client):
        """Posten 0-30 Tage ueberfaellig -> nicht_faellig."""
        mock_client.get_open_items.return_value = [
            _make_open_item(faellig=_date_str(15), betrag="500,00"),
        ]
        result = engine.altersstruktur()
        assert result["nicht_faellig"]["anzahl"] == 1
        assert result["nicht_faellig"]["summe"] == Decimal("500.00")


# ---------------------------------------------------------------------------
# Tests: mahnlauf
# ---------------------------------------------------------------------------


class TestMahnlauf:
    def test_returns_only_overdue(self, engine, mock_client):
        """Mahnlauf gibt nur Posten mit mahnstufe >= 1 zurueck."""
        mock_client.get_open_items.return_value = [
            _make_open_item(beleg_nr="R001", faellig=_date_str(10)),  # nicht faellig
            _make_open_item(beleg_nr="R002", faellig=_date_str(45)),  # stufe 1
        ]
        result = engine.mahnlauf()
        assert len(result) == 1
        assert result[0]["beleg_nr"] == "R002"

    def test_filter_by_stufe(self, engine, mock_client):
        """Mahnlauf kann nach Stufe gefiltert werden."""
        mock_client.get_open_items.return_value = [
            _make_open_item(beleg_nr="R001", faellig=_date_str(45)),  # stufe 1
            _make_open_item(beleg_nr="R002", faellig=_date_str(75)),  # stufe 2
            _make_open_item(beleg_nr="R003", faellig=_date_str(120)),  # stufe 3
        ]
        result = engine.mahnlauf(stufe=2)
        assert len(result) == 1
        assert result[0]["beleg_nr"] == "R002"

    def test_mahnaktion_stufe_1(self, engine, mock_client):
        """Stufe 1: Zahlungserinnerung."""
        mock_client.get_open_items.return_value = [
            _make_open_item(faellig=_date_str(45)),
        ]
        result = engine.mahnlauf()
        assert "Zahlungserinnerung" in result[0]["mahnaktion"]

    def test_mahnaktion_stufe_2(self, engine, mock_client):
        """Stufe 2: 2. Mahnung."""
        mock_client.get_open_items.return_value = [
            _make_open_item(faellig=_date_str(75)),
        ]
        result = engine.mahnlauf()
        assert "2. Mahnung" in result[0]["mahnaktion"]

    def test_mahnaktion_stufe_3(self, engine, mock_client):
        """Stufe 3: Letzte Mahnung / Inkasso."""
        mock_client.get_open_items.return_value = [
            _make_open_item(faellig=_date_str(120)),
        ]
        result = engine.mahnlauf()
        assert "Inkasso" in result[0]["mahnaktion"] or "Letzte" in result[0]["mahnaktion"]

    def test_sorted_by_stufe_then_betrag(self, engine, mock_client):
        """Sortiert nach Mahnstufe (absteigend), dann Betrag (absteigend)."""
        mock_client.get_open_items.return_value = [
            _make_open_item(beleg_nr="R001", faellig=_date_str(45), betrag="500,00"),
            _make_open_item(beleg_nr="R002", faellig=_date_str(120), betrag="2000,00"),
            _make_open_item(beleg_nr="R003", faellig=_date_str(120), betrag="3000,00"),
        ]
        result = engine.mahnlauf()
        assert result[0]["mahnstufe"] >= result[1]["mahnstufe"]
        # Die zwei Stufe-3-Posten sollten nach Betrag sortiert sein
        stufe_3 = [r for r in result if r["mahnstufe"] == 3]
        if len(stufe_3) == 2:
            assert stufe_3[0]["betrag"] >= stufe_3[1]["betrag"]

    def test_empty_mahnlauf(self, engine, mock_client):
        """Leeres Ergebnis wenn nichts ueberfaellig."""
        mock_client.get_open_items.return_value = [
            _make_open_item(faellig=_date_str(10)),  # nicht faellig
        ]
        result = engine.mahnlauf()
        assert result == []

    def test_mahnaktion_key_present(self, engine, mock_client):
        """Mahnvorschlag enthaelt Schluessel 'mahnaktion'."""
        mock_client.get_open_items.return_value = [
            _make_open_item(faellig=_date_str(45)),
        ]
        result = engine.mahnlauf()
        assert "mahnaktion" in result[0]
