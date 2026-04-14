"""Tests fuer collmex.validation."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from collmex.models import Booking, BookingLine, ValidationError
from collmex.validation import check_soll_haben, validate_booking, validate_ust

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

HEUTE = date.today().strftime("%Y%m%d")
GESTERN = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
MORGEN = (date.today() + timedelta(days=1)).strftime("%Y%m%d")


def _make_booking(
    positionen: list[BookingLine] | None = None,
    belegdatum: str = HEUTE,
) -> Booking:
    """Hilfsfunktion: erzeugt einen gueltigen Buchungsbeleg."""
    if positionen is None:
        positionen = [
            BookingLine(
                1, 4400, "Buerobedarf", "S", Decimal("500.00"), buchungstext="Bueromaterial"
            ),
            BookingLine(
                2, 1576, "Vorsteuer 19%", "S", Decimal("95.00"), buchungstext="Bueromaterial"
            ),
            BookingLine(3, 1200, "Bank", "H", Decimal("595.00"), buchungstext="Bueromaterial"),
        ]
    return Booking(
        beleg_nr=None,
        belegdatum=belegdatum,
        positionen=positionen,
    )


# ---------------------------------------------------------------------------
# validate_booking
# ---------------------------------------------------------------------------


@patch("collmex.validation.is_valid_account", return_value=True)
class TestValidateBooking:
    """Tests fuer validate_booking()."""

    def test_gueltige_buchung_keine_fehler(self, mock_account):
        """Korrekte Buchung gibt leere Fehlerliste zurueck."""
        booking = _make_booking()
        fehler = validate_booking(booking)
        assert fehler == []

    def test_soll_ungleich_haben(self, mock_account):
        """Soll != Haben erzeugt einen Fehler."""
        positionen = [
            BookingLine(1, 4400, "", "S", Decimal("500.00"), buchungstext="Test"),
            BookingLine(2, 1200, "", "H", Decimal("400.00"), buchungstext="Test"),
        ]
        booking = _make_booking(positionen=positionen)
        fehler = validate_booking(booking)
        assert any("Summe Soll" in f for f in fehler)

    def test_weniger_als_zwei_positionen(self, mock_account):
        """Nur eine Position erzeugt einen Fehler."""
        positionen = [
            BookingLine(1, 4400, "", "S", Decimal("100.00"), buchungstext="Test"),
        ]
        booking = _make_booking(positionen=positionen)
        fehler = validate_booking(booking)
        assert any("Mindestens 2" in f for f in fehler)

    def test_belegdatum_in_zukunft(self, mock_account):
        """Datum in der Zukunft erzeugt einen Fehler."""
        booking = _make_booking(belegdatum=MORGEN)
        fehler = validate_booking(booking)
        assert any("Zukunft" in f for f in fehler)

    def test_belegdatum_heute_ok(self, mock_account):
        """Datum = heute ist gueltig."""
        booking = _make_booking(belegdatum=HEUTE)
        fehler = validate_booking(booking)
        assert not any("Zukunft" in f for f in fehler)

    def test_belegdatum_gestern_ok(self, mock_account):
        """Datum = gestern ist gueltig."""
        booking = _make_booking(belegdatum=GESTERN)
        fehler = validate_booking(booking)
        assert not any("Datum" in f or "Zukunft" in f for f in fehler)

    def test_leerer_buchungstext(self, mock_account):
        """Alle Positionen ohne Buchungstext erzeugt einen Fehler."""
        positionen = [
            BookingLine(1, 4400, "", "S", Decimal("100.00"), buchungstext=""),
            BookingLine(2, 1200, "", "H", Decimal("100.00"), buchungstext=""),
        ]
        booking = _make_booking(positionen=positionen)
        fehler = validate_booking(booking)
        assert any("Buchungstext" in f for f in fehler)

    def test_buchungstext_in_einer_position_reicht(self, mock_account):
        """Buchungstext in mindestens einer Position reicht."""
        positionen = [
            BookingLine(1, 4400, "", "S", Decimal("100.00"), buchungstext="Einkauf"),
            BookingLine(2, 1200, "", "H", Decimal("100.00"), buchungstext=""),
        ]
        booking = _make_booking(positionen=positionen)
        fehler = validate_booking(booking)
        assert not any("Buchungstext" in f for f in fehler)


@patch("collmex.validation.is_valid_account")
class TestValidateBookingKonten:
    """Tests fuer Kontovalidierung."""

    def test_ungueltiges_konto(self, mock_account):
        """Ungueltiges Konto erzeugt einen Fehler."""
        mock_account.return_value = False
        booking = _make_booking()
        fehler = validate_booking(booking)
        assert any("existiert nicht" in f for f in fehler)

    def test_alle_konten_gueltig(self, mock_account):
        """Alle gueltigen Konten erzeugen keinen Kontofehler."""
        mock_account.return_value = True
        booking = _make_booking()
        fehler = validate_booking(booking)
        assert not any("existiert nicht" in f for f in fehler)


# ---------------------------------------------------------------------------
# validate_ust
# ---------------------------------------------------------------------------


class TestValidateUst:
    """Tests fuer validate_ust()."""

    def test_ust_19_prozent(self):
        """19% auf 100 EUR = 19 EUR."""
        result = validate_ust(Decimal("100.00"), 19)
        assert result == Decimal("19.00")

    def test_ust_7_prozent(self):
        """7% auf 100 EUR = 7 EUR."""
        result = validate_ust(Decimal("100.00"), 7)
        assert result == Decimal("7.00")

    def test_ust_0_prozent(self):
        """0% = 0 EUR."""
        result = validate_ust(Decimal("100.00"), 0)
        assert result == Decimal("0.00")

    def test_ust_19_auf_500(self):
        """19% auf 500 EUR = 95 EUR."""
        result = validate_ust(Decimal("500.00"), 19)
        assert result == Decimal("95.00")

    def test_ust_rundung(self):
        """USt wird korrekt auf 2 Stellen gerundet."""
        # 19% von 33.33 = 6.3327 -> 6.33
        result = validate_ust(Decimal("33.33"), 19)
        assert result == Decimal("6.33")

    def test_ungueltiger_satz_5_prozent(self):
        """5% ist kein gueltiger USt-Satz."""
        with pytest.raises(ValidationError, match="Ungueltiger USt-Satz"):
            validate_ust(Decimal("100.00"), 5)

    def test_ungueltiger_satz_16_prozent(self):
        """16% ist kein gueltiger USt-Satz (alter Satz)."""
        with pytest.raises(ValidationError, match="Ungueltiger USt-Satz"):
            validate_ust(Decimal("100.00"), 16)

    def test_ungueltiger_satz_negativ(self):
        """Negativer Satz ist ungueltig."""
        with pytest.raises(ValidationError):
            validate_ust(Decimal("100.00"), -1)


# ---------------------------------------------------------------------------
# check_soll_haben
# ---------------------------------------------------------------------------


class TestCheckSollHaben:
    """Tests fuer check_soll_haben()."""

    def test_ausgeglichen(self):
        """Soll == Haben gibt True zurueck."""
        positionen = [
            BookingLine(1, 4400, "", "S", Decimal("500.00")),
            BookingLine(2, 1576, "", "S", Decimal("95.00")),
            BookingLine(3, 1200, "", "H", Decimal("595.00")),
        ]
        assert check_soll_haben(positionen) is True

    def test_nicht_ausgeglichen(self):
        """Soll != Haben gibt False zurueck."""
        positionen = [
            BookingLine(1, 4400, "", "S", Decimal("500.00")),
            BookingLine(2, 1200, "", "H", Decimal("499.00")),
        ]
        assert check_soll_haben(positionen) is False

    def test_leere_liste(self):
        """Leere Liste ist ausgeglichen (0 == 0)."""
        assert check_soll_haben([]) is True

    def test_rundungsdifferenz(self):
        """Identische Summen nach Rundung auf 2 Stellen."""
        positionen = [
            BookingLine(1, 4400, "", "S", Decimal("33.33")),
            BookingLine(2, 4400, "", "S", Decimal("33.33")),
            BookingLine(3, 4400, "", "S", Decimal("33.34")),
            BookingLine(4, 1200, "", "H", Decimal("100.00")),
        ]
        assert check_soll_haben(positionen) is True
