"""Validierung von Buchungsdaten fuer das collmex-Projekt.

Stellt sicher, dass Buchungssaetze den Regeln der doppelten Buchfuehrung
und den Anforderungen der Collmex-API entsprechen, bevor sie gesendet werden.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from collmex.accounts import is_valid_account
from collmex.models import BookingLine, ValidationError

if TYPE_CHECKING:
    from collmex.models import Booking

# Erlaubte USt-Saetze in Deutschland
_GUELTIGE_UST_SAETZE: frozenset[int] = frozenset({0, 7, 19})


# ---------------------------------------------------------------------------
# Oeffentliche Funktionen
# ---------------------------------------------------------------------------


def validate_booking(booking: Booking) -> list[str]:
    """Prueft einen Buchungsbeleg auf formale Korrektheit.

    Gibt eine Liste von Fehlermeldungen zurueck.
    Eine leere Liste bedeutet: alles OK.

    Pruefungen:
    1. Summe Soll == Summe Haben (auf 2 Dezimalstellen gerundet)
    2. Alle Kontonummern existieren im Kontenrahmen (SKR03)
    3. Mindestens 2 Positionen
    4. Alle Betraege > 0
    5. Belegdatum im Format YYYYMMDD und nicht in der Zukunft
    6. Buchungstext nicht leer (mindestens eine Position muss Text haben)
    """
    fehler: list[str] = []

    # 1. Mindestens 2 Positionen
    if len(booking.positionen) < 2:
        fehler.append(f"Mindestens 2 Positionen erforderlich, erhalten: {len(booking.positionen)}")

    # 2. Alle Betraege > 0
    for pos in booking.positionen:
        if pos.betrag <= Decimal("0"):
            fehler.append(
                f"Position {pos.positions_nr}: Betrag muss groesser 0 sein, erhalten: {pos.betrag}"
            )

    # 3. Alle Kontonummern existieren im SKR03
    for pos in booking.positionen:
        if not is_valid_account(pos.konto):
            fehler.append(
                f"Position {pos.positions_nr}: Konto {pos.konto} existiert nicht im Kontenrahmen."
            )

    # 4. Soll == Haben (auf 2 Dezimalstellen)
    if not check_soll_haben(booking.positionen):
        fehler.append(
            f"Summe Soll ({booking.summe_soll}) != "
            f"Summe Haben ({booking.summe_haben}). "
            f"Differenz: {abs(booking.summe_soll - booking.summe_haben)}"
        )

    # 5. Belegdatum pruefen
    datum_fehler = _validate_datum(booking.belegdatum)
    if datum_fehler:
        fehler.append(datum_fehler)

    # 6. Buchungstext nicht leer — mindestens eine Position muss Text haben
    hat_buchungstext = any(pos.buchungstext.strip() for pos in booking.positionen)
    if not hat_buchungstext:
        fehler.append("Buchungstext darf nicht leer sein.")

    return fehler


def validate_ust(betrag_netto: Decimal, ust_satz: int) -> Decimal:
    """Berechnet den USt-Betrag und prueft ob der Steuersatz gueltig ist.

    Parameters
    ----------
    betrag_netto:
        Nettobetrag (muss positiv sein).
    ust_satz:
        Steuersatz in Prozent (0, 7 oder 19).

    Returns
    -------
    Decimal
        Der gerundete USt-Betrag auf 2 Dezimalstellen.

    Raises
    ------
    ValidationError
        Falls der Steuersatz nicht 0, 7 oder 19 ist.
    """
    if ust_satz not in _GUELTIGE_UST_SAETZE:
        raise ValidationError(
            f"Ungueltiger USt-Satz: {ust_satz}%. Erlaubt sind: {sorted(_GUELTIGE_UST_SAETZE)}",
            {"ust_satz": ust_satz},
        )

    if not isinstance(betrag_netto, Decimal):
        betrag_netto = Decimal(str(betrag_netto))

    ust_betrag = (betrag_netto * Decimal(ust_satz) / Decimal("100")).quantize(Decimal("0.01"))

    return ust_betrag


def check_soll_haben(positionen: list[BookingLine]) -> bool:
    """Prueft ob Summe Soll == Summe Haben (auf 2 Dezimalstellen).

    Parameters
    ----------
    positionen:
        Liste der Buchungspositionen.

    Returns
    -------
    bool
        True wenn Soll und Haben uebereinstimmen.
    """
    summe_soll = sum(
        (p.betrag for p in positionen if p.soll_haben == "S"),
        Decimal("0"),
    ).quantize(Decimal("0.01"))

    summe_haben = sum(
        (p.betrag for p in positionen if p.soll_haben == "H"),
        Decimal("0"),
    ).quantize(Decimal("0.01"))

    return summe_soll == summe_haben


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------


def _validate_datum(datum: str) -> str | None:
    """Prueft ob ein Datum im Format YYYYMMDD gueltig ist und nicht in der Zukunft liegt.

    Returns None wenn alles OK, sonst einen Fehlerstring.
    """
    # Format-Check
    if len(datum) != 8 or not datum.isdigit():
        return f"Belegdatum '{datum}' ist nicht im Format YYYYMMDD."

    # Semantische Gueltigkeit
    try:
        jahr = int(datum[:4])
        monat = int(datum[4:6])
        tag = int(datum[6:8])
        parsed = date(jahr, monat, tag)
    except ValueError:
        return f"Belegdatum '{datum}' ist kein gueltiges Datum."

    # Zukunfts-Check
    if parsed > date.today():
        return (
            f"Belegdatum {datum} liegt in der Zukunft (heute: {date.today().strftime('%Y%m%d')})."
        )

    return None
