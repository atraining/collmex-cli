"""Tests für collmex.booking: CMXLRN/CMXUMS-basierte Buchungslogik."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from collmex.api import CollmexError
from collmex.booking import (
    BookingEngine,
    BookingResult,
    format_betrag,
    format_datum,
    parse_betrag,
)
from collmex.models import (
    CollmexAusgangsrechnung,
    CollmexEingangsrechnung,
    CollmexKunde,
    CollmexLieferant,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HEUTE = date.today().strftime("%Y%m%d")


def _make_engine(success=True, new_ids=None) -> BookingEngine:
    """Erzeugt eine BookingEngine mit gemocktem API-Client."""
    client = MagicMock()
    response = MagicMock()
    response.success = success
    response.new_ids = new_ids or (["12345"] if success else [])
    response.messages = []
    response.raw = ""
    if not success:
        msg = MagicMock()
        msg.type = MagicMock()
        msg.type.value = "E"
        msg.text = "Testfehler"
        response.messages = [msg]
    client.request.return_value = response

    # post_booking: für post_stammdaten()
    booking_result = MagicMock()
    booking_result.success = success
    booking_result.booking_id = (new_ids[0] if new_ids else "12345") if success else None
    booking_result.first_error = "Testfehler" if not success else None
    booking_result.messages = response.messages
    client.post_booking.return_value = booking_result

    return BookingEngine(api_client=client)


# ---------------------------------------------------------------------------
# format_betrag
# ---------------------------------------------------------------------------


class TestFormatBetrag:
    """Tests für format_betrag()."""

    def test_ganzzahl(self):
        """500 -> '500,00'"""
        assert format_betrag(Decimal("500")) == "500,00"

    def test_zwei_stellen(self):
        """500.00 -> '500,00'"""
        assert format_betrag(Decimal("500.00")) == "500,00"

    def test_eine_stelle(self):
        """500.5 -> '500,50'"""
        assert format_betrag(Decimal("500.5")) == "500,50"

    def test_null(self):
        """0 -> '0,00'"""
        assert format_betrag(Decimal("0")) == "0,00"

    def test_großer_betrag(self):
        """12345.67 -> '12345,67'"""
        assert format_betrag(Decimal("12345.67")) == "12345,67"

    def test_cent_betrag(self):
        """0.99 -> '0,99'"""
        assert format_betrag(Decimal("0.99")) == "0,99"


# ---------------------------------------------------------------------------
# parse_betrag
# ---------------------------------------------------------------------------


class TestParseBetrag:
    """Tests für parse_betrag()."""

    def test_einfach(self):
        """'500,00' -> Decimal('500.00')"""
        assert parse_betrag("500,00") == Decimal("500.00")

    def test_tausendertrenner(self):
        """'1.234,56' -> Decimal('1234.56')"""
        assert parse_betrag("1.234,56") == Decimal("1234.56")

    def test_ohne_komma(self):
        """'500' -> Decimal('500')"""
        assert parse_betrag("500") == Decimal("500")

    def test_mit_leerzeichen(self):
        """' 500,00 ' -> Decimal('500.00')"""
        assert parse_betrag(" 500,00 ") == Decimal("500.00")

    def test_ungültig(self):
        """Ungültiger String wirft ValueError."""
        with pytest.raises(ValueError, match="Kann.*nicht.*parsen"):
            parse_betrag("abc")


# ---------------------------------------------------------------------------
# format_datum
# ---------------------------------------------------------------------------


class TestFormatDatum:
    """Tests für format_datum()."""

    def test_bereits_yyyymmdd(self):
        """'20260303' -> '20260303'"""
        assert format_datum("20260303") == "20260303"

    def test_iso_format(self):
        """'2026-03-03' -> '20260303'"""
        assert format_datum("2026-03-03") == "20260303"

    def test_deutsches_format(self):
        """'03.03.2026' -> '20260303'"""
        assert format_datum("03.03.2026") == "20260303"

    def test_mit_leerzeichen(self):
        """' 20260303 ' -> '20260303'"""
        assert format_datum(" 20260303 ") == "20260303"

    def test_ungültig(self):
        """Ungültiges Format wirft ValueError."""
        with pytest.raises(ValueError, match="nicht erkannt"):
            format_datum("March 3, 2026")


# ---------------------------------------------------------------------------
# BookingEngine.create_eingangsrechnung
# ---------------------------------------------------------------------------


class TestCreateEingangsrechnung:
    """Tests für BookingEngine.create_eingangsrechnung() -> CMXLRN."""

    def test_erzeugt_cmxlrn(self):
        """Eingangsrechnung erzeugt ein CollmexEingangsrechnung-Objekt."""
        engine = _make_engine()
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("500.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Büromaterial",
            belegdatum=HEUTE,
        )
        assert isinstance(rechnung, CollmexEingangsrechnung)

    def test_19_prozent_felder(self):
        """19%-Rechnung setzt netto_voll und konto_voll."""
        engine = _make_engine()
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("500.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Büromaterial",
            belegdatum=HEUTE,
        )
        assert rechnung.netto_voll == Decimal("500.00")
        assert rechnung.steuer_voll == Decimal("95.00")
        assert rechnung.konto_voll == 4400
        assert rechnung.netto_erm == Decimal("0")
        assert rechnung.sonstige_betrag == Decimal("0")

    def test_7_prozent_felder(self):
        """7%-Rechnung setzt netto_erm und konto_erm."""
        engine = _make_engine()
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("100.00"),
            ust_satz=7,
            aufwandskonto=4400,
            buchungstext="Lebensmittel",
            belegdatum=HEUTE,
        )
        assert rechnung.netto_erm == Decimal("100.00")
        assert rechnung.steuer_erm == Decimal("7.00")
        assert rechnung.konto_erm == 4400
        assert rechnung.netto_voll == Decimal("0")

    def test_0_prozent_felder(self):
        """0%-Rechnung setzt sonstige_konto und sonstige_betrag."""
        engine = _make_engine()
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("100.00"),
            ust_satz=0,
            aufwandskonto=4360,
            buchungstext="Versicherung",
            belegdatum=HEUTE,
        )
        assert rechnung.sonstige_konto == 4360
        assert rechnung.sonstige_betrag == Decimal("100.00")
        assert rechnung.netto_voll == Decimal("0")
        assert rechnung.netto_erm == Decimal("0")

    def test_gegenkonto_default_none(self):
        """Ohne Lieferant und ohne Gegenkonto ist gegenkonto None."""
        engine = _make_engine()
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("50.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Test",
            belegdatum=HEUTE,
        )
        assert rechnung.gegenkonto is None
        assert rechnung.lieferant_nr is None

    def test_gegenkonto_explizit_bank(self):
        """Explizites Gegenkonto 1200 wird gesetzt."""
        engine = _make_engine()
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("50.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Test",
            belegdatum=HEUTE,
            gegenkonto=1200,
        )
        assert rechnung.gegenkonto == 1200

    def test_mit_lieferant(self):
        """Mit Lieferant wird Gegenkonto nicht gesetzt."""
        engine = _make_engine()
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("50.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Test",
            belegdatum=HEUTE,
            lieferant_nr=70000,
        )
        assert rechnung.lieferant_nr == 70000
        assert rechnung.gegenkonto is None

    def test_csv_line_format(self):
        """to_csv_line() erzeugt gültige CMXLRN-Zeile."""
        engine = _make_engine()
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("500.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Büromaterial",
            belegdatum=HEUTE,
        )
        csv = rechnung.to_csv_line()
        assert csv.startswith("CMXLRN;")
        felder = csv.split(";")
        assert len(felder) == 20
        assert felder[0] == "CMXLRN"

    def test_datum_format_konvertierung(self):
        """Verschiedene Datumsformate werden akzeptiert."""
        engine = _make_engine()
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("100.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Test",
            belegdatum="03.03.2026",  # Deutsches Format
        )
        assert rechnung.datum == "20260303"


# ---------------------------------------------------------------------------
# BookingEngine.create_ausgangsrechnung
# ---------------------------------------------------------------------------


class TestCreateAusgangsrechnung:
    """Tests für BookingEngine.create_ausgangsrechnung() -> CMXUMS."""

    def test_erzeugt_cmxums(self):
        """Ausgangsrechnung erzeugt ein CollmexAusgangsrechnung-Objekt."""
        engine = _make_engine()
        rechnung = engine.create_ausgangsrechnung(
            betrag_netto=Decimal("1000.00"),
            ust_satz=19,
            ertragskonto=8400,
            buchungstext="Beratung",
            belegdatum=HEUTE,
        )
        assert isinstance(rechnung, CollmexAusgangsrechnung)

    def test_19_prozent_felder(self):
        """19%-Rechnung setzt netto_voll und konto_voll."""
        engine = _make_engine()
        rechnung = engine.create_ausgangsrechnung(
            betrag_netto=Decimal("1000.00"),
            ust_satz=19,
            ertragskonto=8400,
            buchungstext="Beratung",
            belegdatum=HEUTE,
        )
        assert rechnung.netto_voll == Decimal("1000.00")
        assert rechnung.steuer_voll == Decimal("190.00")
        assert rechnung.konto_voll == 8400

    def test_7_prozent_felder(self):
        """7%-Rechnung setzt netto_erm und konto_erm."""
        engine = _make_engine()
        rechnung = engine.create_ausgangsrechnung(
            betrag_netto=Decimal("200.00"),
            ust_satz=7,
            ertragskonto=8300,
            buchungstext="Ermäßigter Erlös",
            belegdatum=HEUTE,
        )
        assert rechnung.netto_erm == Decimal("200.00")
        assert rechnung.steuer_erm == Decimal("14.00")
        assert rechnung.konto_erm == 8300

    def test_0_prozent_steuerfrei(self):
        """0%-Rechnung setzt steuerfrei-Felder."""
        engine = _make_engine()
        rechnung = engine.create_ausgangsrechnung(
            betrag_netto=Decimal("5000.00"),
            ust_satz=0,
            ertragskonto=8120,
            buchungstext="Innergemeinschaftliche Lieferung",
            belegdatum=HEUTE,
        )
        assert rechnung.steuerfrei_konto == 8120
        assert rechnung.steuerfrei_betrag == Decimal("5000.00")

    def test_mit_kunde(self):
        """Mit Kundennummer wird Gegenkonto nicht gesetzt."""
        engine = _make_engine()
        rechnung = engine.create_ausgangsrechnung(
            betrag_netto=Decimal("1000.00"),
            ust_satz=19,
            ertragskonto=8400,
            buchungstext="Beratung",
            belegdatum=HEUTE,
            kunde_nr=10000,
        )
        assert rechnung.kunde_nr == 10000
        assert rechnung.gegenkonto is None

    def test_csv_line_format(self):
        """to_csv_line() erzeugt gültige CMXUMS-Zeile."""
        engine = _make_engine()
        rechnung = engine.create_ausgangsrechnung(
            betrag_netto=Decimal("1000.00"),
            ust_satz=19,
            ertragskonto=8400,
            buchungstext="Beratung",
            belegdatum=HEUTE,
            kunde_nr=10000,
        )
        csv = rechnung.to_csv_line()
        assert csv.startswith("CMXUMS;")
        felder = csv.split(";")
        assert len(felder) == 31
        assert felder[0] == "CMXUMS"


# ---------------------------------------------------------------------------
# Storno
# ---------------------------------------------------------------------------


class TestCreateStorno:
    """Tests für Storno-Rechnungen."""

    def test_storno_eingang(self):
        """Storno setzt Flag und ändert Buchungstext."""
        engine = _make_engine()
        original = engine.create_eingangsrechnung(
            betrag_netto=Decimal("500.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Büromaterial",
            belegdatum=HEUTE,
        )
        storno = engine.create_storno_eingang(original)
        assert storno.storno is True
        assert "STORNO" in storno.buchungstext
        assert storno.netto_voll == original.netto_voll

    def test_storno_ausgang(self):
        """Storno-Ausgangsrechnung setzt Flag."""
        engine = _make_engine()
        original = engine.create_ausgangsrechnung(
            betrag_netto=Decimal("1000.00"),
            ust_satz=19,
            ertragskonto=8400,
            buchungstext="Beratung",
            belegdatum=HEUTE,
        )
        storno = engine.create_storno_ausgang(original)
        assert storno.storno is True
        assert "STORNO" in storno.buchungstext

    def test_storno_csv_hat_flag(self):
        """Storno-CSV-Zeile hat Storno-Feld gesetzt."""
        engine = _make_engine()
        original = engine.create_eingangsrechnung(
            betrag_netto=Decimal("100.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Test",
            belegdatum=HEUTE,
        )
        storno = engine.create_storno_eingang(original)
        csv = storno.to_csv_line()
        felder = csv.split(";")
        # CMXLRN Feld 19 = Storno
        assert felder[18] == "1"

    def test_storno_original_unveraendert(self):
        """Storno ändert das Original nicht."""
        engine = _make_engine()
        original = engine.create_eingangsrechnung(
            betrag_netto=Decimal("500.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Büromaterial",
            belegdatum=HEUTE,
        )
        engine.create_storno_eingang(original)
        assert original.storno is False
        assert "STORNO" not in original.buchungstext


# ---------------------------------------------------------------------------
# BookingEngine.suggest_booking
# ---------------------------------------------------------------------------


class TestSuggestBooking:
    """Tests für BookingEngine.suggest_booking()."""

    @patch("collmex.booking.suggest_account", return_value=4400)
    def test_keyword_büromaterial(self, mock_suggest):
        """'Büromaterial' schlaegt Konto 4400 vor."""
        engine = _make_engine()
        rechnung = engine.suggest_booking(
            beschreibung="Büromaterial Druckerpapier",
            betrag=Decimal("100.00"),
            datum=HEUTE,
        )
        mock_suggest.assert_called_once_with("Büromaterial Druckerpapier")
        assert isinstance(rechnung, CollmexEingangsrechnung)
        assert rechnung.konto_voll == 4400

    @patch("collmex.booking.suggest_account", return_value=4900)
    def test_keyword_sonstiges(self, mock_suggest):
        """Unbekannter Begriff schlaegt 4900 vor."""
        engine = _make_engine()
        rechnung = engine.suggest_booking(
            beschreibung="Sonstige Ausgabe",
            betrag=Decimal("50.00"),
            datum=HEUTE,
        )
        assert rechnung.konto_voll == 4900


# ---------------------------------------------------------------------------
# BookingEngine.post_and_validate
# ---------------------------------------------------------------------------


class TestPostAndValidate:
    """Tests für BookingEngine.post_and_validate()."""

    def test_erfolgreiche_buchung(self):
        """Erfolgreiche Buchung liefert success=True."""
        engine = _make_engine(success=True)
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("100.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Test",
            belegdatum=HEUTE,
            lieferant_nr=70001,
        )
        result = engine.post_and_validate(rechnung)
        assert result.success is True
        assert result.beleg_nr == 12345

    def test_validierung_schlaegt_fehl(self):
        """Bei Validierungsfehler wird nicht gesendet."""
        engine = _make_engine()
        rechnung = CollmexEingangsrechnung(
            datum="UNGÜLTIG",
            buchungstext="",
        )
        result = engine.post_and_validate(rechnung)
        assert result.success is False
        assert len(result.fehler) > 0
        engine.api_client.request.assert_not_called()

    def test_api_fehler(self):
        """API-Exception führt zu success=False."""
        engine = _make_engine()
        engine.api_client.request.side_effect = ConnectionError("Timeout")
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("100.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Test",
            belegdatum=HEUTE,
            lieferant_nr=70001,
        )
        result = engine.post_and_validate(rechnung)
        assert result.success is False
        assert any("API-Fehler" in f for f in result.fehler)

    def test_api_error_message(self):
        """API-Fehlermeldung wird korrekt extrahiert."""
        engine = _make_engine(success=False)
        rechnung = engine.create_eingangsrechnung(
            betrag_netto=Decimal("100.00"),
            ust_satz=19,
            aufwandskonto=4400,
            buchungstext="Test",
            belegdatum=HEUTE,
            lieferant_nr=70001,
        )
        result = engine.post_and_validate(rechnung)
        assert result.success is False
        assert any("Testfehler" in f for f in result.fehler)


# ---------------------------------------------------------------------------
# BookingResult
# ---------------------------------------------------------------------------


class TestBookingResult:
    """Tests für BookingResult."""

    def test_ok_property_true(self):
        """ok ist True wenn success und keine Fehler."""
        result = BookingResult(success=True, beleg_nr=1, rechnung=None, fehler=[])
        assert result.ok is True

    def test_ok_property_false_fehler(self):
        """ok ist False wenn Fehler vorhanden."""
        result = BookingResult(
            success=True,
            beleg_nr=1,
            rechnung=None,
            fehler=["Gegenlesen fehlgeschlagen"],
        )
        assert result.ok is False


# ---------------------------------------------------------------------------
# CollmexLieferant / CollmexKunde: to_csv_line
# ---------------------------------------------------------------------------


class TestCollmexLieferant:
    """Tests für CollmexLieferant.to_csv_line()."""

    def test_csv_starts_with_cmxlif(self):
        lif = CollmexLieferant(name="Test GmbH", ort="Berlin")
        csv = lif.to_csv_line()
        assert csv.startswith("CMXLIF;")

    def test_csv_hat_41_felder(self):
        lif = CollmexLieferant(name="Test GmbH")
        felder = lif.to_csv_line().split(";")
        assert len(felder) == 41

    def test_csv_name_an_idx_7(self):
        lif = CollmexLieferant(name="Muster GmbH")
        felder = lif.to_csv_line().split(";")
        assert felder[7] == "Muster GmbH"

    def test_csv_aufwandskonto(self):
        lif = CollmexLieferant(name="Test", aufwandskonto=4900)
        felder = lif.to_csv_line().split(";")
        assert felder[35] == "4900"

    def test_csv_lieferant_nr_leer_bei_auto(self):
        lif = CollmexLieferant(name="Auto-Nr")
        felder = lif.to_csv_line().split(";")
        assert felder[1] == ""  # auto-Vergabe

    def test_csv_lieferant_nr_explizit(self):
        lif = CollmexLieferant(name="Explizit", lieferant_nr=70042)
        felder = lif.to_csv_line().split(";")
        assert felder[1] == "70042"


class TestCollmexKunde:
    """Tests für CollmexKunde.to_csv_line()."""

    def test_csv_starts_with_cmxknd(self):
        knd = CollmexKunde(name="Testkunde AG")
        csv = knd.to_csv_line()
        assert csv.startswith("CMXKND;")

    def test_csv_hat_35_felder(self):
        knd = CollmexKunde(name="Test")
        felder = knd.to_csv_line().split(";")
        assert len(felder) == 35

    def test_csv_name_an_idx_7(self):
        knd = CollmexKunde(name="Kunde GmbH")
        felder = knd.to_csv_line().split(";")
        assert felder[7] == "Kunde GmbH"

    def test_csv_kunde_nr_leer_bei_auto(self):
        knd = CollmexKunde(name="Auto-Nr")
        felder = knd.to_csv_line().split(";")
        assert felder[1] == ""

    def test_csv_kunde_nr_explizit(self):
        knd = CollmexKunde(name="Explizit", kunde_nr=10042)
        felder = knd.to_csv_line().split(";")
        assert felder[1] == "10042"


# ---------------------------------------------------------------------------
# BookingEngine.post_stammdaten
# ---------------------------------------------------------------------------


class TestPostStammdaten:
    """Tests für BookingEngine.post_stammdaten()."""

    def test_lieferant_auto_nr(self):
        """Auto-Vergabe: ID kommt aus API-Response."""
        engine = _make_engine(success=True, new_ids=["70001"])
        lif = CollmexLieferant(name="Neu GmbH", ort="Berlin")
        nr = engine.post_stammdaten(lif)
        assert nr == 70001

    def test_lieferant_explizite_nr(self):
        """Explizite Nr wird direkt zurückgegeben."""
        engine = _make_engine(success=True)
        lif = CollmexLieferant(name="Explizit", lieferant_nr=70042)
        nr = engine.post_stammdaten(lif)
        assert nr == 70042

    def test_kunde_auto_nr(self):
        """Auto-Vergabe für Kunden."""
        engine = _make_engine(success=True, new_ids=["10001"])
        knd = CollmexKunde(name="Neukunde AG")
        nr = engine.post_stammdaten(knd)
        assert nr == 10001

    def test_fehler_bei_api_fehler(self):
        """API-Fehler wirft CollmexError."""
        engine = _make_engine(success=False)
        lif = CollmexLieferant(name="Fehler GmbH")
        with pytest.raises(CollmexError):
            engine.post_stammdaten(lif)

    def test_sendet_csv_line(self):
        """post_stammdaten sendet die CSV-Zeile an post_booking."""
        engine = _make_engine(success=True, new_ids=["70001"])
        lif = CollmexLieferant(name="CSV-Test", ort="Berlin")
        engine.post_stammdaten(lif)
        call_args = engine.api_client.post_booking.call_args
        csv_lines = call_args[0][0]
        assert len(csv_lines) == 1
        assert csv_lines[0].startswith("CMXLIF;")
