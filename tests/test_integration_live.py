"""Integrationstests gegen die echte Collmex-API.

Simuliert typische Geschaeftsvorfaelle per CMXLRN (Eingangsrechnungen)
und CMXUMS (Ausgangsrechnungen) und prueft anschliessend ob Collmex
die doppelte Buchfuehrung korrekt erzeugt.

Ausfuehren mit: pytest tests/test_integration_live.py -m live -v
"""

from decimal import Decimal

import pytest

from collmex.api import CollmexClient
from collmex.booking import BookingEngine

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def client():
    """Echter Collmex API Client."""
    c = CollmexClient()
    assert c.status(), "Collmex API nicht erreichbar"
    return c


@pytest.fixture(scope="module")
def engine(client):
    """BookingEngine mit echtem Client."""
    return BookingEngine(api_client=client)


# ---------------------------------------------------------------------------
# Geschaeftsvorfaelle buchen
# ---------------------------------------------------------------------------


class TestEingangsrechnungen:
    """Eingangsrechnungen (CMXLRN) gegen echte API."""

    def test_bueromaterial_19_mit_gegenkonto(self, engine, client):
        """Eingangsrechnung Bueromaterial, 19% USt, direkt Bank."""
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("500.00"),
            ust_satz=19,
            aufwandskonto=4830,  # 4400 existiert nicht in diesem Collmex
            buchungstext="Live-Test Bueromaterial",
            belegdatum="20260303",
            rechnungs_nr="LIVE-ER-001",
        )
        result = engine.post_and_validate(rechnung)
        assert result.success, f"Bueromaterial fehlgeschlagen: {result.fehler}"

    def test_software_lizenz_19_mit_lieferant(self, engine, client):
        """Eingangsrechnung mit Lieferant -> Verbindlichkeiten."""
        # Erst Lieferant sicherstellen
        client.request(["CMXLIF;70000;1;Test-Lieferant GmbH"])

        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("200.00"),
            ust_satz=19,
            aufwandskonto=4830,
            buchungstext="Live-Test Software-Lizenz",
            belegdatum="20260303",
            lieferant_nr=70000,
            rechnungs_nr="LIVE-ER-002",
        )
        result = engine.post_and_validate(rechnung)
        assert result.success, f"Software fehlgeschlagen: {result.fehler}"

    def test_versicherung_steuerfrei(self, engine, client):
        """Eingangsrechnung steuerfrei (0%), z.B. Versicherung."""
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("150.00"),
            ust_satz=0,
            aufwandskonto=4830,
            buchungstext="Live-Test Versicherung steuerfrei",
            belegdatum="20260303",
            rechnungs_nr="LIVE-ER-003",
        )
        result = engine.post_and_validate(rechnung)
        assert result.success, f"Versicherung fehlgeschlagen: {result.fehler}"


class TestAusgangsrechnungen:
    """Ausgangsrechnungen (CMXUMS) gegen echte API."""

    def test_beratung_19_mit_kunde(self, engine, client):
        """Ausgangsrechnung Beratung, 19% USt, mit Kunde."""
        # Erst Kunde sicherstellen
        client.request(["CMXKND;10000;1;Testkunde GmbH"])

        rechnung = engine.create_ausgangsrechnung(
            betrag_netto=Decimal("1000.00"),
            ust_satz=19,
            ertragskonto=8400,
            buchungstext="Live-Test Beratung",
            belegdatum="20260303",
            kunde_nr=10000,
            rechnungs_nr="LIVE-AR-001",
        )
        result = engine.post_and_validate(rechnung)
        assert result.success, f"Beratung fehlgeschlagen: {result.fehler}"

    def test_barverkauf_19_mit_gegenkonto(self, engine, client):
        """Ausgangsrechnung Barverkauf direkt an Bank."""
        rechnung = engine.create_ausgangsrechnung(
            betrag_netto=Decimal("500.00"),
            ust_satz=19,
            ertragskonto=8400,
            buchungstext="Live-Test Barverkauf",
            belegdatum="20260303",
            gegenkonto=1200,
            rechnungs_nr="LIVE-AR-002",
        )
        result = engine.post_and_validate(rechnung)
        assert result.success, f"Barverkauf fehlgeschlagen: {result.fehler}"


class TestStorno:
    """Storno-Rechnungen gegen echte API."""

    def test_storno_eingangsrechnung(self, engine, client):
        """Storno einer Eingangsrechnung."""
        # Erst Original buchen
        original = engine.create_eingangsrechnung(
            betrag_netto=Decimal("100.00"),
            ust_satz=19,
            aufwandskonto=4830,
            buchungstext="Live-Test Storno-Original",
            belegdatum="20260303",
            rechnungs_nr="LIVE-STORNO-001",
        )
        orig_result = engine.post_and_validate(original)
        assert orig_result.success, f"Original fehlgeschlagen: {orig_result.fehler}"

        # Dann stornieren
        storno = engine.create_storno_eingang(original)
        storno.rechnungs_nr = "LIVE-STORNO-001-S"
        storno_result = engine.post_and_validate(storno)
        assert storno_result.success, f"Storno fehlgeschlagen: {storno_result.fehler}"


class TestValidierung:
    """Validierung der erzeugten Buchungen."""

    def test_buchungen_existieren(self, client):
        """ACCDOC_GET liefert Buchungspositionen."""
        bookings = client.get_bookings()
        assert len(bookings) > 0, "Keine Buchungen gefunden"

    def test_kontensalden_plausibel(self, client):
        """Kontensalden nach allen Buchungen pruefen."""
        # Periode 0 = kumuliert ueber alle Monate
        salden = client.get_balances(2026, 0)

        # Mindestens einige Konten sollten Salden haben
        # ACC_BAL-Zeilen: [ACC_BAL, Kontonr, Kontoname, Saldo, ...]
        konten = {row[1]: row for row in salden if len(row) > 1}
        assert len(konten) > 0, "Keine Kontensalden gefunden"

    def test_ustva_konten_vorhanden(self, client):
        """USt-relevante Konten sollten Salden haben."""
        salden = client.get_balances(2026, 0)  # kumuliert
        # ACC_BAL-Zeilen: [ACC_BAL, Kontonr, Kontoname, Saldo, ...]
        konten_nummern = {row[1] for row in salden if len(row) > 1}

        # Nach unseren Buchungen sollten 1576 (VSt) und/oder 1776 (USt) belegt sein
        assert "1576" in konten_nummern or "1776" in konten_nummern, (
            f"Keine USt-Konten gefunden. Vorhandene Konten: {konten_nummern}"
        )
