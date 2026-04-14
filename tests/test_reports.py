"""Tests für collmex Reports (BWA, SuSa, OP, Säumige Kunden).

Alle Tests nutzen gemockte API-Clients, keine echten API-Aufrufe.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from collmex.reports import BWA_BEREICHE, BWA_BEZEICHNUNGEN, ReportsEngine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    """Gemockter CollmexClient."""
    return MagicMock()


@pytest.fixture
def engine(mock_client):
    """ReportsEngine mit gemocktem Client."""
    return ReportsEngine(mock_client)


def _make_accbal_row(
    konto_nr: int,
    bezeichnung: str = "",
    soll_umsatz: str = "0,00",
    haben_umsatz: str = "0,00",
    saldo: str = "0,00",
    anfangsbestand: str = "0,00",
) -> list[str]:
    """Erzeugt eine ACC_BAL-Zeile im echten Collmex-Format (4 Felder).

    Verifiziert gegen echte API: ACC_BAL;Kontonummer;Bezeichnung;Saldo
    soll_umsatz/haben_umsatz/anfangsbestand werden ignoriert (für
    Rückwärtskompatibilität der Aufrufe behalten).
    """
    return [
        "ACC_BAL",  # 0: Satzart
        str(konto_nr),  # 1: Kontonummer
        bezeichnung,  # 2: Bezeichnung
        saldo,  # 3: Saldo
    ]


def _make_open_item_row(
    konto_nr: int,
    name: str,
    beleg_nr: str,
    datum: str,
    fällig: str,
    betrag: str,
    jahr: str = "2026",
    periode: str = "3",
) -> list[str]:
    """Erzeugt eine OPEN_ITEM-Zeile im echten Collmex-Format (20 Felder).

    Verifiziert gegen echte API-Antwort (2026-03).
    """
    return [
        "OPEN_ITEM",  # 0: Satzart
        "1",  # 1: Firma Nr
        jahr,  # 2: Geschäftsjahr
        periode,  # 3: Buchungsperiode
        "1",  # 4: Positionsnummer
        str(konto_nr),  # 5: Kontonummer
        name,  # 6: Name (Kunde/Lieferant)
        "",  # 7: (leer)
        "",  # 8: (leer)
        beleg_nr,  # 9: Belegnummer
        datum,  # 10: Belegdatum
        "",  # 11: Zahlungsbedingung
        fällig,  # 12: Fälligkeitsdatum
        "0",  # 13: (unbekannt)
        "0",  # 14: (unbekannt)
        "",  # 15: (leer)
        "0,00",  # 16: Bezahlt
        betrag,  # 17: Ursprungsbetrag
        "0,00",  # 18: Skonto
        betrag,  # 19: Offener Betrag
    ]


# ---------------------------------------------------------------------------
# BWA-Tests
# ---------------------------------------------------------------------------


def test_bwa_berechnung_erlöse_minus_kosten(engine, mock_client):
    """BWA: Erlöse minus Kosten = Betriebsergebnis."""
    mock_client.get_balances.return_value = [
        _make_accbal_row(8400, "Erlöse 19%", saldo="-10000,00"),
        _make_accbal_row(4100, "Löhne", saldo="3000,00"),
        _make_accbal_row(4210, "Miete", saldo="1000,00"),
        _make_accbal_row(4400, "Bürobedarf", saldo="500,00"),
    ]

    result = engine.bwa(2026, 3)

    assert result["umsatzerlöse"] == Decimal("10000.00")
    assert result["personalkosten"] == Decimal("3000.00")
    assert result["raumkosten"] == Decimal("1000.00")
    assert result["betriebskosten"] == Decimal("500.00")
    assert result["betriebsergebnis"] == Decimal("5500.00")


def test_bwa_ohne_erlöse(engine, mock_client):
    """BWA: Nur Kosten, keine Erlöse ergibt negatives Ergebnis."""
    mock_client.get_balances.return_value = [
        _make_accbal_row(4100, "Löhne", saldo="2000,00"),
        _make_accbal_row(4210, "Miete", saldo="800,00"),
    ]

    result = engine.bwa(2026, 3)

    assert result["umsatzerlöse"] == Decimal("0")
    assert result["betriebsergebnis"] == Decimal("-2800.00")


def test_bwa_leere_daten(engine, mock_client):
    """BWA: Leere Daten ergeben Nullwerte."""
    mock_client.get_balances.return_value = []

    result = engine.bwa(2026, 3)

    assert result["umsatzerlöse"] == Decimal("0")
    assert result["summe_kosten"] == Decimal("0")
    assert result["betriebsergebnis"] == Decimal("0")


def test_bwa_positionen_reihenfolge(engine, mock_client):
    """BWA: Positionen sind in der richtigen Reihenfolge."""
    mock_client.get_balances.return_value = [
        _make_accbal_row(8400, "Erlöse 19%", saldo="-5000,00"),
        _make_accbal_row(4100, "Löhne", saldo="1000,00"),
    ]

    result = engine.bwa(2026, 3)
    positionen = result["positionen"]

    assert positionen[0]["bezeichnung"] == "Umsatzerlöse"
    assert positionen[-1]["bezeichnung"] == "Betriebsergebnis"
    assert positionen[-2]["bezeichnung"] == "Summe Kosten"


def test_bwa_summe_kosten(engine, mock_client):
    """BWA: Summe Kosten ist Summe aller Kostenarten."""
    mock_client.get_balances.return_value = [
        _make_accbal_row(4100, "Löhne", saldo="1000,00"),
        _make_accbal_row(4210, "Miete", saldo="500,00"),
        _make_accbal_row(4400, "Bürobedarf", saldo="200,00"),
        _make_accbal_row(4510, "Kfz", saldo="300,00"),
        _make_accbal_row(4600, "Reise", saldo="150,00"),
        _make_accbal_row(4822, "AfA", saldo="100,00"),
        _make_accbal_row(4900, "Sonstige", saldo="50,00"),
    ]

    result = engine.bwa(2026, 3)

    erwartete_summe = Decimal("2300.00")
    assert result["summe_kosten"] == erwartete_summe


def test_bwa_alle_bereiche_vorhanden(engine, mock_client):
    """BWA-Ergebnis enthält alle definierten Bereiche."""
    mock_client.get_balances.return_value = []
    result = engine.bwa(2026, 3)

    for bereich in BWA_BEREICHE:
        if bereich == "umsatzerlöse":
            assert bereich in result
        else:
            assert bereich in result


# ---------------------------------------------------------------------------
# SuSa-Tests
# ---------------------------------------------------------------------------


def test_susa_sortierung(engine, mock_client):
    """SuSa: Konten sind nach Kontonummer sortiert."""
    mock_client.get_balances.return_value = [
        _make_accbal_row(4400, "Bürobedarf", saldo="100,00"),
        _make_accbal_row(1200, "Bank", saldo="5000,00"),
        _make_accbal_row(8400, "Erlöse", saldo="-8000,00"),
    ]

    result = engine.susa(2026, 3)

    konto_nummern = [r["konto_nr"] for r in result]
    assert konto_nummern == sorted(konto_nummern)


def test_susa_felder(engine, mock_client):
    """SuSa: Jeder Eintrag hat alle erforderlichen Felder."""
    mock_client.get_balances.return_value = [
        _make_accbal_row(1200, "Bank", saldo="5000,00"),
    ]

    result = engine.susa(2026, 3)
    assert len(result) == 1

    eintrag = result[0]
    assert eintrag["konto_nr"] == 1200
    assert eintrag["bezeichnung"] == "Bank"
    assert eintrag["saldo"] == Decimal("5000.00")
    # ACC_BAL liefert nur den Saldo, nicht Soll/Haben einzeln
    assert eintrag["soll_umsatz"] == Decimal("0")
    assert eintrag["haben_umsatz"] == Decimal("0")
    assert eintrag["anfangsbestand"] == Decimal("0")


def test_susa_leere_daten(engine, mock_client):
    """SuSa: Leere Daten ergeben leere Liste."""
    mock_client.get_balances.return_value = []
    result = engine.susa(2026, 3)
    assert result == []


# ---------------------------------------------------------------------------
# OP-Tests
# ---------------------------------------------------------------------------


def test_op_debitoren_kreditoren_getrennt(engine, mock_client):
    """OP-Liste: Debitoren und Kreditoren werden getrennt."""
    heute = date.today().strftime("%Y%m%d")
    gestern = (date.today() - timedelta(days=1)).strftime("%Y%m%d")

    mock_client.get_open_items.return_value = [
        _make_open_item_row(10000, "Kunde A", "R001", "20260101", gestern, "1000,00"),
        _make_open_item_row(70000, "Lieferant B", "E001", "20260101", heute, "500,00"),
    ]

    result = engine.op_liste()

    assert len(result["debitoren"]) == 1
    assert len(result["kreditoren"]) == 1
    assert result["debitoren"][0]["name"] == "Kunde A"
    assert result["kreditoren"][0]["name"] == "Lieferant B"


def test_op_summen(engine, mock_client):
    """OP-Liste: Summen werden korrekt berechnet."""
    heute = date.today().strftime("%Y%m%d")

    mock_client.get_open_items.return_value = [
        _make_open_item_row(10000, "Kunde A", "R001", "20260101", heute, "1000,00"),
        _make_open_item_row(10000, "Kunde B", "R002", "20260101", heute, "2000,00"),
        _make_open_item_row(70000, "Lieferant C", "E001", "20260101", heute, "750,00"),
    ]

    result = engine.op_liste()

    assert result["summe_debitoren"] == Decimal("3000.00")
    assert result["summe_kreditoren"] == Decimal("750.00")


def test_op_altersstruktur(engine, mock_client):
    """OP-Liste: Altersstruktur wird korrekt berechnet."""
    heute = date.today()
    tag_10 = (heute - timedelta(days=10)).strftime("%Y%m%d")
    tag_45 = (heute - timedelta(days=45)).strftime("%Y%m%d")
    tag_75 = (heute - timedelta(days=75)).strftime("%Y%m%d")
    tag_120 = (heute - timedelta(days=120)).strftime("%Y%m%d")

    mock_client.get_open_items.return_value = [
        _make_open_item_row(10000, "Kunde A", "R001", "20260101", tag_10, "100,00"),
        _make_open_item_row(10000, "Kunde B", "R002", "20260101", tag_45, "200,00"),
        _make_open_item_row(10000, "Kunde C", "R003", "20260101", tag_75, "300,00"),
        _make_open_item_row(10000, "Kunde D", "R004", "20260101", tag_120, "400,00"),
    ]

    result = engine.op_liste()
    alters = result["altersstruktur"]

    assert alters["aktuell"] == Decimal("100.00")
    assert alters["überfällig_30"] == Decimal("200.00")
    assert alters["überfällig_60"] == Decimal("300.00")
    assert alters["überfällig_90"] == Decimal("400.00")


def test_op_leere_daten(engine, mock_client):
    """OP-Liste: Leere Daten ergeben leere Listen."""
    mock_client.get_open_items.return_value = []

    result = engine.op_liste()

    assert result["debitoren"] == []
    assert result["kreditoren"] == []
    assert result["summe_debitoren"] == Decimal("0")
    assert result["summe_kreditoren"] == Decimal("0")


# ---------------------------------------------------------------------------
# Säumige Kunden
# ---------------------------------------------------------------------------


def test_säumige_korrekte_sortierung(engine, mock_client):
    """Säumige Kunden: Sortierung nach Tagen überfällig (absteigend)."""
    heute = date.today()
    tag_10 = (heute - timedelta(days=10)).strftime("%Y%m%d")
    tag_60 = (heute - timedelta(days=60)).strftime("%Y%m%d")
    tag_100 = (heute - timedelta(days=100)).strftime("%Y%m%d")

    mock_client.get_open_items.return_value = [
        _make_open_item_row(10000, "Kunde A", "R001", "20260101", tag_10, "100,00"),
        _make_open_item_row(10000, "Kunde B", "R002", "20260101", tag_60, "200,00"),
        _make_open_item_row(10000, "Kunde C", "R003", "20260101", tag_100, "300,00"),
    ]

    result = engine.säumige_kunden()

    assert len(result) == 3
    # Sortierung: meiste Tage zuerst
    assert result[0]["name"] == "Kunde C"
    assert result[1]["name"] == "Kunde B"
    assert result[2]["name"] == "Kunde A"
    assert result[0]["tage_ueberfällig"] >= result[1]["tage_ueberfällig"]
    assert result[1]["tage_ueberfällig"] >= result[2]["tage_ueberfällig"]


def test_säumige_mahnstufen(engine, mock_client):
    """Säumige Kunden: Mahnstufen sind korrekt."""
    heute = date.today()
    tag_10 = (heute - timedelta(days=10)).strftime("%Y%m%d")
    tag_45 = (heute - timedelta(days=45)).strftime("%Y%m%d")
    tag_75 = (heute - timedelta(days=75)).strftime("%Y%m%d")
    tag_120 = (heute - timedelta(days=120)).strftime("%Y%m%d")

    mock_client.get_open_items.return_value = [
        _make_open_item_row(10000, "Stufe 0", "R001", "20260101", tag_10, "100,00"),
        _make_open_item_row(10000, "Stufe 1", "R002", "20260101", tag_45, "200,00"),
        _make_open_item_row(10000, "Stufe 2", "R003", "20260101", tag_75, "300,00"),
        _make_open_item_row(10000, "Stufe 3", "R004", "20260101", tag_120, "400,00"),
    ]

    result = engine.säumige_kunden()

    mahnstufen = {r["name"]: r["mahnstufe"] for r in result}
    assert mahnstufen["Stufe 0"] == 0
    assert mahnstufen["Stufe 1"] == 1
    assert mahnstufen["Stufe 2"] == 2
    assert mahnstufen["Stufe 3"] == 3


def test_säumige_keine_ueberfälligen(engine, mock_client):
    """Säumige Kunden: Leere Liste wenn niemand überfällig."""
    morgen = (date.today() + timedelta(days=1)).strftime("%Y%m%d")

    mock_client.get_open_items.return_value = [
        _make_open_item_row(10000, "Kunde A", "R001", "20260101", morgen, "1000,00"),
    ]

    result = engine.säumige_kunden()
    assert result == []


def test_säumige_nur_debitoren(engine, mock_client):
    """Säumige Kunden: Kreditoren werden nicht als säumige Kunden gelistet."""
    gestern = (date.today() - timedelta(days=1)).strftime("%Y%m%d")

    mock_client.get_open_items.return_value = [
        _make_open_item_row(70000, "Lieferant X", "E001", "20260101", gestern, "500,00"),
    ]

    result = engine.säumige_kunden()
    assert result == []


# ---------------------------------------------------------------------------
# BWA Bezeichnungen
# ---------------------------------------------------------------------------


def test_bwa_bezeichnungen_vollständig():
    """Alle BWA-Bereiche haben eine Bezeichnung."""
    for bereich in BWA_BEREICHE:
        assert bereich in BWA_BEZEICHNUNGEN, f"Bereich '{bereich}' fehlt in BWA_BEZEICHNUNGEN"
