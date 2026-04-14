"""Tests fuer collmex.models — Dataclasses und Geschaeftslogik."""

from decimal import Decimal

import pytest

from collmex.models import (
    Account,
    Booking,
    BookingLine,
    CollmexAusgangsrechnung,
    CollmexEingangsrechnung,
    Customer,
    Invoice,
    OpenItem,
    Supplier,
    ValidationError,
)

# ===================================================================
# Hilfsfunktionen
# ===================================================================


def _make_booking(
    soll_betrag: Decimal = Decimal("500.00"),
    haben_betrag: Decimal = Decimal("500.00"),
    beleg_nr: int | None = None,
) -> Booking:
    """Erzeugt einen einfachen Buchungsbeleg mit einer Soll- und einer Haben-Position."""
    return Booking(
        beleg_nr=beleg_nr,
        belegdatum="20260303",
        positionen=[
            BookingLine(
                positions_nr=1,
                konto=4400,
                bezeichnung="Buerobedarf",
                soll_haben="S",
                betrag=soll_betrag,
            ),
            BookingLine(
                positions_nr=2,
                konto=1200,
                bezeichnung="Bank",
                soll_haben="H",
                betrag=haben_betrag,
            ),
        ],
    )


# ===================================================================
# BookingLine
# ===================================================================


class TestBookingLine:
    def test_decimal_betrag(self) -> None:
        """Betrag wird korrekt als Decimal gespeichert."""
        line = BookingLine(
            positions_nr=1,
            konto=4400,
            bezeichnung="Test",
            soll_haben="S",
            betrag=Decimal("123.45"),
        )
        assert line.betrag == Decimal("123.45")
        assert isinstance(line.betrag, Decimal)

    def test_betrag_wird_zu_decimal_konvertiert(self) -> None:
        """Nicht-Decimal-Betrag wird in __post_init__ konvertiert."""
        line = BookingLine(
            positions_nr=1,
            konto=4400,
            bezeichnung="Test",
            soll_haben="S",
            betrag=99.99,  # type: ignore[arg-type]
        )
        assert isinstance(line.betrag, Decimal)
        assert line.betrag == Decimal("99.99")

    def test_negativer_betrag_wirft_error(self) -> None:
        """Negative Betraege sind nicht erlaubt."""
        with pytest.raises(ValueError, match="nicht negativ"):
            BookingLine(
                positions_nr=1,
                konto=4400,
                bezeichnung="Test",
                soll_haben="S",
                betrag=Decimal("-10.00"),
            )

    def test_ungueltiges_soll_haben(self) -> None:
        """Nur 'S' und 'H' sind erlaubt."""
        with pytest.raises(ValueError, match="soll_haben"):
            BookingLine(
                positions_nr=1,
                konto=4400,
                bezeichnung="Test",
                soll_haben="X",
                betrag=Decimal("100.00"),
            )

    def test_defaults(self) -> None:
        """Standardwerte werden korrekt gesetzt."""
        line = BookingLine(
            positions_nr=1,
            konto=4400,
            bezeichnung="Test",
            soll_haben="S",
            betrag=Decimal("100.00"),
        )
        assert line.waehrung == "EUR"
        assert line.steuersatz == ""
        assert line.buchungstext == ""
        assert line.kostenstelle == ""

    def test_betrag_null_erlaubt(self) -> None:
        """Betrag 0 ist zulaessig (z.B. Storno-Gegenbuchung)."""
        line = BookingLine(
            positions_nr=1,
            konto=4400,
            bezeichnung="Test",
            soll_haben="S",
            betrag=Decimal("0.00"),
        )
        assert line.betrag == Decimal("0.00")


# ===================================================================
# Booking.validate()
# ===================================================================


class TestBookingValidate:
    def test_soll_gleich_haben_ok(self) -> None:
        """Buchung mit Soll = Haben validiert ohne Fehler."""
        booking = _make_booking(Decimal("595.00"), Decimal("595.00"))
        booking.validate()  # Kein Error

    def test_soll_ungleich_haben_wirft_error(self) -> None:
        """Buchung mit Soll != Haben wirft ValidationError."""
        booking = _make_booking(Decimal("500.00"), Decimal("400.00"))
        with pytest.raises(ValidationError) as exc_info:
            booking.validate()
        assert "Soll" in exc_info.value.message
        assert "Haben" in exc_info.value.message
        assert exc_info.value.details["differenz"] == "100.00"

    def test_validation_error_details(self) -> None:
        """ValidationError enthaelt strukturierte Details."""
        booking = _make_booking(Decimal("100.00"), Decimal("80.00"))
        with pytest.raises(ValidationError) as exc_info:
            booking.validate()
        details = exc_info.value.details
        assert "summe_soll" in details
        assert "summe_haben" in details
        assert details["summe_soll"] == "100.00"
        assert details["summe_haben"] == "80.00"

    def test_leere_positionen_wirft_error(self) -> None:
        """Buchung ohne Positionen wirft ValidationError."""
        booking = Booking(
            beleg_nr=None,
            belegdatum="20260303",
            positionen=[],
        )
        with pytest.raises(ValidationError, match="keine Positionen"):
            booking.validate()

    def test_drei_positionen_soll_gleich_haben(self) -> None:
        """Buchung mit 3 Positionen (2 Soll, 1 Haben) validiert korrekt."""
        booking = Booking(
            beleg_nr=None,
            belegdatum="20260303",
            positionen=[
                BookingLine(1, 4400, "Buerobedarf", "S", Decimal("500.00")),
                BookingLine(2, 1576, "Vorsteuer 19%", "S", Decimal("95.00")),
                BookingLine(3, 1200, "Bank", "H", Decimal("595.00")),
            ],
        )
        booking.validate()  # Kein Error


# ===================================================================
# Booking Properties
# ===================================================================


class TestBookingProperties:
    def test_summe_soll(self) -> None:
        """summe_soll addiert alle Soll-Positionen."""
        booking = Booking(
            beleg_nr=None,
            belegdatum="20260303",
            positionen=[
                BookingLine(1, 4400, "Buerobedarf", "S", Decimal("500.00")),
                BookingLine(2, 1576, "Vorsteuer", "S", Decimal("95.00")),
                BookingLine(3, 1200, "Bank", "H", Decimal("595.00")),
            ],
        )
        assert booking.summe_soll == Decimal("595.00")

    def test_summe_haben(self) -> None:
        """summe_haben addiert alle Haben-Positionen."""
        booking = Booking(
            beleg_nr=None,
            belegdatum="20260303",
            positionen=[
                BookingLine(1, 4400, "Buerobedarf", "S", Decimal("500.00")),
                BookingLine(2, 1576, "Vorsteuer", "S", Decimal("95.00")),
                BookingLine(3, 1200, "Bank", "H", Decimal("595.00")),
            ],
        )
        assert booking.summe_haben == Decimal("595.00")


# ===================================================================
# Booking.to_csv_lines()
# ===================================================================


class TestBookingToCsvLines:
    def test_einfacher_buchungssatz(self) -> None:
        """Einfacher Buchungssatz erzeugt korrekte ACCDOC-Zeilen."""
        booking = _make_booking(Decimal("500.00"), Decimal("500.00"), beleg_nr=42)
        lines = booking.to_csv_lines()
        assert len(lines) == 2
        assert lines[0].startswith("ACCDOC;")
        assert lines[1].startswith("ACCDOC;")

    def test_felder_reihenfolge(self) -> None:
        """CSV-Felder erscheinen in der richtigen Reihenfolge."""
        booking = Booking(
            beleg_nr=99,
            belegdatum="20260303",
            positionen=[
                BookingLine(
                    positions_nr=1,
                    konto=4400,
                    bezeichnung="Buerobedarf",
                    soll_haben="S",
                    betrag=Decimal("500.00"),
                    waehrung="EUR",
                    steuersatz="",
                    buchungstext="Bueromaterial Lieferant X",
                    kostenstelle="KST01",
                ),
            ],
            referenz="RE-2026-001",
            firma_nr=1,
        )
        lines = booking.to_csv_lines()
        felder = lines[0].split(";")
        assert felder[0] == "ACCDOC"
        assert felder[1] == "1"  # firma_nr
        assert felder[2] == "99"  # beleg_nr
        assert felder[3] == "1"  # positions_nr
        assert felder[4] == "4400"  # konto
        assert felder[5] == "Buerobedarf"  # bezeichnung
        assert felder[6] == "S"  # soll_haben
        assert felder[7] == "500,00"  # betrag (deutsches Format)
        assert felder[8] == "EUR"  # waehrung
        assert felder[9] == ""  # steuersatz
        assert felder[10] == "20260303"  # belegdatum
        assert felder[11] == "Bueromaterial Lieferant X"  # buchungstext
        assert felder[12] == "RE-2026-001"  # referenz
        assert felder[13] == "KST01"  # kostenstelle

    def test_beleg_nr_none_erzeugt_leeres_feld(self) -> None:
        """Wenn beleg_nr None ist, bleibt das Feld leer (automatische Vergabe)."""
        booking = _make_booking(Decimal("100.00"), Decimal("100.00"), beleg_nr=None)
        lines = booking.to_csv_lines()
        felder = lines[0].split(";")
        assert felder[2] == ""  # beleg_nr leer

    def test_betrag_deutsches_komma_format(self) -> None:
        """Betraege werden mit Komma als Dezimaltrennzeichen ausgegeben."""
        booking = _make_booking(Decimal("1234.56"), Decimal("1234.56"))
        lines = booking.to_csv_lines()
        felder = lines[0].split(";")
        assert felder[7] == "1234,56"

    def test_drei_positionen_erzeugt_drei_zeilen(self) -> None:
        """Buchung mit 3 Positionen erzeugt 3 CSV-Zeilen."""
        booking = Booking(
            beleg_nr=None,
            belegdatum="20260303",
            positionen=[
                BookingLine(1, 4400, "Buerobedarf", "S", Decimal("500.00")),
                BookingLine(2, 1576, "Vorsteuer 19%", "S", Decimal("95.00")),
                BookingLine(3, 1200, "Bank", "H", Decimal("595.00")),
            ],
        )
        lines = booking.to_csv_lines()
        assert len(lines) == 3


# ===================================================================
# Booking Datum-Validierung
# ===================================================================


class TestBookingDatum:
    def test_ungueltiges_datum_format(self) -> None:
        """Datum im falschen Format wirft ValueError."""
        with pytest.raises(ValueError, match="YYYYMMDD"):
            Booking(
                beleg_nr=None,
                belegdatum="2026-03-03",
                positionen=[],
            )

    def test_datum_nicht_numerisch(self) -> None:
        """Nicht-numerisches Datum wirft ValueError."""
        with pytest.raises(ValueError, match="YYYYMMDD"):
            Booking(
                beleg_nr=None,
                belegdatum="ABCDEFGH",
                positionen=[],
            )


# ===================================================================
# Invoice
# ===================================================================


class TestInvoice:
    def test_betrag_brutto_19_prozent(self) -> None:
        """Bruttobetrag bei 19% USt wird korrekt berechnet."""
        invoice = Invoice(
            id=1,
            kunde_id=100,
            datum="20260303",
            betrag_netto=Decimal("1000.00"),
            ust_satz=19,
            buchungstext="Beratung",
        )
        assert invoice.betrag_brutto == Decimal("1190.00")

    def test_ust_betrag_19_prozent(self) -> None:
        """USt-Betrag bei 19% wird korrekt berechnet."""
        invoice = Invoice(
            id=1,
            kunde_id=100,
            datum="20260303",
            betrag_netto=Decimal("1000.00"),
            ust_satz=19,
            buchungstext="Beratung",
        )
        assert invoice.ust_betrag == Decimal("190.00")

    def test_betrag_brutto_7_prozent(self) -> None:
        """Bruttobetrag bei 7% USt wird korrekt berechnet."""
        invoice = Invoice(
            id=2,
            kunde_id=200,
            datum="20260303",
            betrag_netto=Decimal("500.00"),
            ust_satz=7,
            buchungstext="Lebensmittel",
        )
        assert invoice.betrag_brutto == Decimal("535.00")

    def test_ust_betrag_7_prozent(self) -> None:
        """USt-Betrag bei 7% wird korrekt berechnet."""
        invoice = Invoice(
            id=2,
            kunde_id=200,
            datum="20260303",
            betrag_netto=Decimal("500.00"),
            ust_satz=7,
            buchungstext="Lebensmittel",
        )
        assert invoice.ust_betrag == Decimal("35.00")

    def test_ust_betrag_0_prozent(self) -> None:
        """USt-Betrag bei 0% ist 0."""
        invoice = Invoice(
            id=3,
            kunde_id=300,
            datum="20260303",
            betrag_netto=Decimal("800.00"),
            ust_satz=0,
            buchungstext="Innergemeinschaftliche Lieferung",
        )
        assert invoice.ust_betrag == Decimal("0.00")
        assert invoice.betrag_brutto == Decimal("800.00")

    def test_ust_betrag_rundung(self) -> None:
        """USt-Betrag wird auf 2 Nachkommastellen gerundet."""
        invoice = Invoice(
            id=4,
            kunde_id=400,
            datum="20260303",
            betrag_netto=Decimal("33.33"),
            ust_satz=19,
            buchungstext="Test Rundung",
        )
        # 33.33 * 0.19 = 6.3327 -> gerundet 6.33
        assert invoice.ust_betrag == Decimal("6.33")
        assert invoice.betrag_brutto == Decimal("39.66")

    def test_default_status(self) -> None:
        """Default-Status ist 'offen'."""
        invoice = Invoice(
            id=None,
            kunde_id=100,
            datum="20260303",
            betrag_netto=Decimal("100.00"),
            ust_satz=19,
            buchungstext="Test",
        )
        assert invoice.status == "offen"

    def test_betrag_netto_konvertierung(self) -> None:
        """Nicht-Decimal betrag_netto wird konvertiert."""
        invoice = Invoice(
            id=None,
            kunde_id=100,
            datum="20260303",
            betrag_netto=250,  # type: ignore[arg-type]
            ust_satz=19,
            buchungstext="Test",
        )
        assert isinstance(invoice.betrag_netto, Decimal)
        assert invoice.betrag_netto == Decimal("250")


# ===================================================================
# OpenItem
# ===================================================================


class TestOpenItem:
    def test_mahnstufe_0_nicht_faellig(self) -> None:
        """Mahnstufe 0: nicht faellig (0 Tage ueberfaellig)."""
        item = OpenItem(
            beleg_nr=1,
            kunde_oder_lieferant="Kunde A",
            typ="debitor",
            betrag=Decimal("100.00"),
            datum="20260201",
            faellig_am="20260303",
            tage_ueberfaellig=0,
        )
        assert item.mahnstufe == 0

    def test_mahnstufe_0_unter_30_tage(self) -> None:
        """Mahnstufe 0: bis 30 Tage ueberfaellig."""
        item = OpenItem(
            beleg_nr=2,
            kunde_oder_lieferant="Kunde B",
            typ="debitor",
            betrag=Decimal("200.00"),
            datum="20260101",
            faellig_am="20260201",
            tage_ueberfaellig=30,
        )
        assert item.mahnstufe == 0

    def test_mahnstufe_1_31_tage(self) -> None:
        """Mahnstufe 1: 31 Tage ueberfaellig."""
        item = OpenItem(
            beleg_nr=3,
            kunde_oder_lieferant="Kunde C",
            typ="debitor",
            betrag=Decimal("300.00"),
            datum="20260101",
            faellig_am="20260115",
            tage_ueberfaellig=31,
        )
        assert item.mahnstufe == 1

    def test_mahnstufe_1_60_tage(self) -> None:
        """Mahnstufe 1: genau 60 Tage ueberfaellig."""
        item = OpenItem(
            beleg_nr=4,
            kunde_oder_lieferant="Kunde D",
            typ="debitor",
            betrag=Decimal("400.00"),
            datum="20251201",
            faellig_am="20260101",
            tage_ueberfaellig=60,
        )
        assert item.mahnstufe == 1

    def test_mahnstufe_2_61_tage(self) -> None:
        """Mahnstufe 2: 61 Tage ueberfaellig."""
        item = OpenItem(
            beleg_nr=5,
            kunde_oder_lieferant="Kunde E",
            typ="debitor",
            betrag=Decimal("500.00"),
            datum="20251201",
            faellig_am="20260101",
            tage_ueberfaellig=61,
        )
        assert item.mahnstufe == 2

    def test_mahnstufe_2_90_tage(self) -> None:
        """Mahnstufe 2: genau 90 Tage ueberfaellig."""
        item = OpenItem(
            beleg_nr=6,
            kunde_oder_lieferant="Kunde F",
            typ="debitor",
            betrag=Decimal("600.00"),
            datum="20251101",
            faellig_am="20251201",
            tage_ueberfaellig=90,
        )
        assert item.mahnstufe == 2

    def test_mahnstufe_3_91_tage(self) -> None:
        """Mahnstufe 3: 91 Tage ueberfaellig."""
        item = OpenItem(
            beleg_nr=7,
            kunde_oder_lieferant="Kunde G",
            typ="debitor",
            betrag=Decimal("700.00"),
            datum="20251001",
            faellig_am="20251101",
            tage_ueberfaellig=91,
        )
        assert item.mahnstufe == 3

    def test_mahnstufe_3_180_tage(self) -> None:
        """Mahnstufe 3: weit ueberfaellig (180 Tage)."""
        item = OpenItem(
            beleg_nr=8,
            kunde_oder_lieferant="Kunde H",
            typ="debitor",
            betrag=Decimal("800.00"),
            datum="20250601",
            faellig_am="20250901",
            tage_ueberfaellig=180,
        )
        assert item.mahnstufe == 3

    def test_kreditor_typ(self) -> None:
        """OpenItem mit Typ 'kreditor' funktioniert korrekt."""
        item = OpenItem(
            beleg_nr=10,
            kunde_oder_lieferant="Lieferant X",
            typ="kreditor",
            betrag=Decimal("1500.00"),
            datum="20260201",
            faellig_am="20260303",
            tage_ueberfaellig=0,
        )
        assert item.typ == "kreditor"
        assert item.mahnstufe == 0

    def test_ungueltiger_typ(self) -> None:
        """Ungueltiger Typ wirft ValueError."""
        with pytest.raises(ValueError, match="debitor.*kreditor"):
            OpenItem(
                beleg_nr=11,
                kunde_oder_lieferant="Test",
                typ="unbekannt",
                betrag=Decimal("100.00"),
                datum="20260101",
                faellig_am="20260201",
                tage_ueberfaellig=0,
            )


# ===================================================================
# Account
# ===================================================================


class TestAccount:
    def test_erstellen(self) -> None:
        """Account wird korrekt erstellt."""
        konto = Account(
            konto_nr=4400,
            bezeichnung="Buerobedarf",
            konto_typ="aufwand",
            ust_relevant=True,
        )
        assert konto.konto_nr == 4400
        assert konto.bezeichnung == "Buerobedarf"
        assert konto.konto_typ == "aufwand"
        assert konto.ust_relevant is True

    def test_ungueltiger_konto_typ(self) -> None:
        """Ungueltiger konto_typ wirft ValueError."""
        with pytest.raises(ValueError, match="konto_typ"):
            Account(
                konto_nr=9999,
                bezeichnung="Test",
                konto_typ="ungueltig",
                ust_relevant=False,
            )


# ===================================================================
# Customer / Supplier
# ===================================================================


class TestCustomer:
    def test_erstellen_mit_defaults(self) -> None:
        """CollmexKunde wird mit Standardwerten erstellt."""
        kunde = Customer(kunde_nr=1, name="Musterfirma GmbH")
        assert kunde.kunde_nr == 1
        assert kunde.name == "Musterfirma GmbH"
        assert kunde.land == "DE"
        assert kunde.strasse == ""
        assert kunde.email == ""

    def test_to_csv_line(self) -> None:
        """to_csv_line() erzeugt gueltige CMXKND-Zeile."""
        kunde = Customer(kunde_nr=10001, name="Test GmbH")
        csv = kunde.to_csv_line()
        assert csv.startswith("CMXKND;")
        assert "Test GmbH" in csv


class TestSupplier:
    def test_erstellen_mit_allen_feldern(self) -> None:
        """CollmexLieferant mit allen Feldern."""
        lieferant = Supplier(
            lieferant_nr=70042,
            name="Lieferant AG",
            strasse="Hauptstr. 1",
            plz="50667",
            ort="Koeln",
            land="DE",
            ust_id="DE123456789",
            email="info@lieferant.de",
        )
        assert lieferant.lieferant_nr == 70042
        assert lieferant.ust_id == "DE123456789"
        assert lieferant.ort == "Koeln"

    def test_to_csv_line(self) -> None:
        """to_csv_line() erzeugt gueltige CMXLIF-Zeile."""
        lieferant = Supplier(lieferant_nr=70001, name="Test AG")
        csv = lieferant.to_csv_line()
        assert csv.startswith("CMXLIF;")
        assert "Test AG" in csv


# ===================================================================
# ValidationError
# ===================================================================


class TestValidationError:
    def test_ist_exception(self) -> None:
        """ValidationError ist eine Exception."""
        err = ValidationError("Test-Fehler", {"key": "value"})
        assert isinstance(err, Exception)
        assert str(err) == "Test-Fehler"
        assert err.message == "Test-Fehler"
        assert err.details == {"key": "value"}

    def test_details_default_leer(self) -> None:
        """Ohne details-Argument wird ein leeres dict verwendet."""
        err = ValidationError("Fehler ohne Details")
        assert err.details == {}


# ===================================================================
# CollmexEingangsrechnung (CMXLRN)
# ===================================================================


class TestCollmexEingangsrechnung:
    def test_erstellen_19_prozent(self) -> None:
        """CMXLRN mit 19% USt."""
        rechnung = CollmexEingangsrechnung(
            lieferant_nr=70000,
            datum="20260303",
            netto_voll=Decimal("500.00"),
            steuer_voll=Decimal("95.00"),
            konto_voll=4400,
            buchungstext="Bueromaterial",
        )
        assert rechnung.betrag_netto == Decimal("500.00")
        assert rechnung.betrag_brutto == Decimal("595.00")

    def test_erstellen_7_prozent(self) -> None:
        """CMXLRN mit 7% USt."""
        rechnung = CollmexEingangsrechnung(
            gegenkonto=1200,
            datum="20260303",
            netto_erm=Decimal("100.00"),
            steuer_erm=Decimal("7.00"),
            konto_erm=4400,
            buchungstext="Lebensmittel",
        )
        assert rechnung.betrag_netto == Decimal("100.00")
        assert rechnung.betrag_brutto == Decimal("107.00")

    def test_erstellen_steuerfrei(self) -> None:
        """CMXLRN steuerfrei (0%)."""
        rechnung = CollmexEingangsrechnung(
            gegenkonto=1200,
            datum="20260303",
            sonstige_konto=4360,
            sonstige_betrag=Decimal("800.00"),
            buchungstext="Versicherung",
        )
        assert rechnung.betrag_netto == Decimal("800.00")
        assert rechnung.betrag_brutto == Decimal("800.00")

    def test_to_csv_line_20_felder(self) -> None:
        """CSV-Zeile hat exakt 20 Felder."""
        rechnung = CollmexEingangsrechnung(
            lieferant_nr=70000,
            datum="20260303",
            netto_voll=Decimal("500.00"),
            buchungstext="Test",
        )
        felder = rechnung.to_csv_line().split(";")
        assert len(felder) == 20
        assert felder[0] == "CMXLRN"
        assert felder[1] == "70000"  # Lieferantennummer
        assert felder[3] == "20260303"  # Datum
        assert felder[5] == "500,00"  # Nettobetrag voll

    def test_to_csv_line_gegenkonto(self) -> None:
        """Mit Gegenkonto statt Lieferant."""
        rechnung = CollmexEingangsrechnung(
            gegenkonto=1200,
            datum="20260303",
            netto_voll=Decimal("100.00"),
            buchungstext="Bankgebuehren",
        )
        felder = rechnung.to_csv_line().split(";")
        assert felder[1] == ""  # Kein Lieferant
        assert felder[12] == "1200"  # Gegenkonto

    def test_storno_flag(self) -> None:
        """Storno-Flag in CSV."""
        rechnung = CollmexEingangsrechnung(
            gegenkonto=1200,
            datum="20260303",
            netto_voll=Decimal("100.00"),
            buchungstext="Storno",
            storno=True,
        )
        felder = rechnung.to_csv_line().split(";")
        assert felder[18] == "1"  # Storno-Feld

    def test_decimal_konvertierung(self) -> None:
        """Nicht-Decimal-Werte werden konvertiert."""
        rechnung = CollmexEingangsrechnung(
            gegenkonto=1200,
            datum="20260303",
            netto_voll=500,  # type: ignore[arg-type]
            buchungstext="Test",
        )
        assert isinstance(rechnung.netto_voll, Decimal)
        assert rechnung.netto_voll == Decimal("500")


# ===================================================================
# CollmexAusgangsrechnung (CMXUMS)
# ===================================================================


class TestCollmexAusgangsrechnung:
    def test_erstellen_19_prozent(self) -> None:
        """CMXUMS mit 19% USt."""
        rechnung = CollmexAusgangsrechnung(
            kunde_nr=10000,
            datum="20260303",
            netto_voll=Decimal("1000.00"),
            steuer_voll=Decimal("190.00"),
            konto_voll=8400,
            buchungstext="Beratung",
        )
        assert rechnung.betrag_netto == Decimal("1000.00")

    def test_erstellen_7_prozent(self) -> None:
        """CMXUMS mit 7% USt."""
        rechnung = CollmexAusgangsrechnung(
            kunde_nr=10000,
            datum="20260303",
            netto_erm=Decimal("200.00"),
            steuer_erm=Decimal("14.00"),
            konto_erm=8300,
            buchungstext="Ermaessigter Erloes",
        )
        assert rechnung.betrag_netto == Decimal("200.00")

    def test_to_csv_line_31_felder(self) -> None:
        """CSV-Zeile hat exakt 31 Felder."""
        rechnung = CollmexAusgangsrechnung(
            kunde_nr=10000,
            datum="20260303",
            netto_voll=Decimal("1000.00"),
            buchungstext="Test",
        )
        felder = rechnung.to_csv_line().split(";")
        assert len(felder) == 31
        assert felder[0] == "CMXUMS"
        assert felder[1] == "10000"  # Kundennummer

    def test_ig_lieferung(self) -> None:
        """Innergemeinschaftliche Lieferung."""
        rechnung = CollmexAusgangsrechnung(
            kunde_nr=10000,
            datum="20260303",
            ig_lieferung=Decimal("5000.00"),
            buchungstext="IG Lieferung",
        )
        assert rechnung.betrag_netto == Decimal("5000.00")
        felder = rechnung.to_csv_line().split(";")
        assert felder[9] == "5000,00"  # IG Lieferung

    def test_storno_flag(self) -> None:
        """Storno-Flag in CMXUMS-CSV."""
        rechnung = CollmexAusgangsrechnung(
            kunde_nr=10000,
            datum="20260303",
            netto_voll=Decimal("100.00"),
            buchungstext="Storno",
            storno=True,
        )
        felder = rechnung.to_csv_line().split(";")
        assert felder[22] == "1"  # Storno-Feld
