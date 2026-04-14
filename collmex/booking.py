"""Buchungslogik für das collmex-Projekt.

Erzeugt Eingangs- und Ausgangsrechnungen als CMXLRN / CMXUMS-Sätze
und uebermittelt sie über den API-Client an Collmex.

WICHTIG: Collmex erlaubt KEINEN Import von allgemeinen Buchungen (ACCDOC).
Stattdessen werden Rechnungen über CMXLRN (Eingang) und CMXUMS (Ausgang)
importiert. Collmex erzeugt die doppelte Buchführung (Soll/Haben) intern.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from collmex.accounts import suggest_account
from collmex.api import CollmexError
from collmex.models import (
    Booking,
    CollmexAusgangsrechnung,
    CollmexEingangsrechnung,
    CollmexKunde,
    CollmexLieferant,
)
from collmex.validation import validate_ust

# SKR03-Standardkonten
_AUFWAND_KONTEN_VOLL = {19: None}  # Default: Collmex wählt
_ERLOES_KONTEN = {19: 8400, 7: 8300}
_BANK_KONTO = 1200


# ---------------------------------------------------------------------------
# Ergebnis-Datenklasse
# ---------------------------------------------------------------------------


@dataclass
class BookingResult:
    """Ergebnis einer Buchung inkl. Validierungsstatus."""

    success: bool
    beleg_nr: int | None
    rechnung: CollmexEingangsrechnung | CollmexAusgangsrechnung | Booking | None
    fehler: list[str]
    api_response: Any = None

    @property
    def ok(self) -> bool:
        return self.success and not self.fehler


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def format_betrag(betrag: Decimal) -> str:
    """Formatiert einen Decimal-Betrag im deutschen Format.

    Decimal("500.00") -> "500,00"
    """
    if not isinstance(betrag, Decimal):
        betrag = Decimal(str(betrag))
    # Auf 2 Stellen quantisieren und Punkt durch Komma ersetzen
    quantized = betrag.quantize(Decimal("0.01"))
    return str(quantized).replace(".", ",")


def parse_betrag(text: str) -> Decimal:
    """Parst einen Betrag im deutschen Format zu Decimal.

    "500,00" -> Decimal("500.00")
    "1.234,56" -> Decimal("1234.56")
    """
    if not isinstance(text, str):
        raise ValueError(f"Erwarte str, erhalten: {type(text).__name__}")

    # Tausenderpunkte entfernen, Komma durch Punkt ersetzen
    cleaned = text.strip().replace(".", "").replace(",", ".")

    try:
        result = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"Kann '{text}' nicht als Betrag parsen.")

    return result


def format_datum(datum: str) -> str:
    """Stellt sicher, dass ein Datum im YYYYMMDD-Format vorliegt.

    Unterstützt folgende Eingabeformate:
    - YYYYMMDD (wird direkt zurückgegeben)
    - YYYY-MM-DD
    - DD.MM.YYYY

    Raises ValueError bei ungültigem Format.
    """
    datum = datum.strip()

    # Bereits im Zielformat?
    if len(datum) == 8 and datum.isdigit():
        return datum

    # ISO-Format: YYYY-MM-DD
    if len(datum) == 10 and datum[4] == "-" and datum[7] == "-":
        teile = datum.split("-")
        if len(teile) == 3 and all(t.isdigit() for t in teile):
            return f"{teile[0]}{teile[1]}{teile[2]}"

    # Deutsches Format: DD.MM.YYYY
    if len(datum) == 10 and datum[2] == "." and datum[5] == ".":
        teile = datum.split(".")
        if len(teile) == 3 and all(t.isdigit() for t in teile):
            return f"{teile[2]}{teile[1]}{teile[0]}"

    raise ValueError(
        f"Datumsformat '{datum}' nicht erkannt. Erwartet: YYYYMMDD, YYYY-MM-DD oder DD.MM.YYYY"
    )


# ---------------------------------------------------------------------------
# BookingEngine
# ---------------------------------------------------------------------------


class BookingEngine:
    """Erzeugt und sendet Buchungssätze an Collmex.

    Verwendet CMXLRN für Eingangsrechnungen und CMXUMS für
    Ausgangsrechnungen.  Collmex erzeugt die doppelte Buchführung
    (Aufwand/Ertrag + Steuer + Gegenkonto) automatisch.
    """

    def __init__(self, api_client: Any) -> None:
        self.api_client = api_client

    # ------------------------------------------------------------------
    # Rechnungs-Erzeuger
    # ------------------------------------------------------------------

    def create_eingangsrechnung(
        self,
        betrag_netto: Decimal,
        ust_satz: int,
        aufwandskonto: int,
        buchungstext: str,
        belegdatum: str,
        lieferant_nr: int | None = None,
        gegenkonto: int | None = None,
        rechnungs_nr: str = "",
        kostenstelle: str = "",
    ) -> CollmexEingangsrechnung:
        """Erzeugt eine Eingangsrechnung (CMXLRN).

        Collmex kümmert sich um die doppelte Buchführung:
        - Aufwandskonto (Soll) -> aufwandskonto
        - Vorsteuer (Soll) -> automatisch
        - Verbindlichkeiten/Bank (Haben) -> lieferant_nr oder gegenkonto

        Parameters
        ----------
        betrag_netto: Nettobetrag der Rechnung
        ust_satz: USt-Satz (0, 7 oder 19)
        aufwandskonto: SKR03-Aufwandskonto (z.B. 4400 Bürobedarf)
        buchungstext: Beschreibung des Geschäftsvorfalls
        belegdatum: Datum (YYYYMMDD, YYYY-MM-DD oder DD.MM.YYYY)
        lieferant_nr: Collmex-Lieferanten-ID (optional)
        gegenkonto: Gegenkonto wenn kein Lieferant (Standard: 1200 Bank)
        rechnungs_nr: Externe Rechnungsnummer (leer = Collmex vergibt)
        kostenstelle: Kostenstelle (optional)
        """
        if not isinstance(betrag_netto, Decimal):
            betrag_netto = Decimal(str(betrag_netto))

        belegdatum = format_datum(belegdatum)
        ust_betrag = validate_ust(betrag_netto, ust_satz)

        rechnung = CollmexEingangsrechnung(
            lieferant_nr=lieferant_nr,
            datum=belegdatum,
            rechnungs_nr=rechnungs_nr,
            währung="EUR",
            gegenkonto=gegenkonto if not lieferant_nr else None,
            buchungstext=buchungstext,
            kostenstelle=kostenstelle,
        )

        if ust_satz == 19:
            rechnung.netto_voll = betrag_netto
            rechnung.steuer_voll = ust_betrag
            rechnung.konto_voll = aufwandskonto
        elif ust_satz == 7:
            rechnung.netto_erm = betrag_netto
            rechnung.steuer_erm = ust_betrag
            rechnung.konto_erm = aufwandskonto
        else:  # 0% — steuerfrei
            rechnung.sonstige_konto = aufwandskonto
            rechnung.sonstige_betrag = betrag_netto

        return rechnung

    def create_split_eingangsrechnung(
        self,
        positionen: list[tuple[Decimal, int, int]],
        buchungstext: str,
        belegdatum: str,
        lieferant_nr: int | None = None,
        gegenkonto: int | None = None,
        rechnungs_nr: str = "",
        kostenstelle: str = "",
    ) -> list[CollmexEingangsrechnung]:
        """Erzeugt eine Split-Eingangsrechnung (mehrere CMXLRN mit gleicher Rechnungsnr).

        Collmex mergt aufeinanderfolgende Zeilen mit identischer Rechnungsnummer
        zu einem Buchungsbeleg. Jede Position kann ein anderes Aufwandskonto haben.

        Parameters
        ----------
        positionen: Liste von (betrag_netto, aufwandskonto, ust_satz) Tupeln
        buchungstext: Beschreibung (wird für alle Positionen verwendet)
        belegdatum: Datum (YYYYMMDD, YYYY-MM-DD oder DD.MM.YYYY)
        lieferant_nr: Collmex-Lieferanten-ID (optional)
        gegenkonto: Gegenkonto wenn kein Lieferant (Standard: 1200 Bank)
        rechnungs_nr: Externe Rechnungsnummer (PFLICHT für Split!)
        kostenstelle: Kostenstelle (optional)
        """
        if not rechnungs_nr:
            raise ValueError(
                "Split-Buchung braucht eine Rechnungsnummer (Collmex mergt Zeilen mit gleicher Nr)."
            )
        if len(positionen) < 2:
            raise ValueError("Split-Buchung braucht mindestens 2 Positionen.")

        belegdatum = format_datum(belegdatum)
        rechnungen: list[CollmexEingangsrechnung] = []

        for i, (betrag_netto, aufwandskonto, ust_satz) in enumerate(positionen):
            if not isinstance(betrag_netto, Decimal):
                betrag_netto = Decimal(str(betrag_netto))
            ust_betrag = validate_ust(betrag_netto, ust_satz)

            pos_text = buchungstext if i == 0 else f"{buchungstext} (Pos {i + 1})"

            rechnung = CollmexEingangsrechnung(
                lieferant_nr=lieferant_nr,
                datum=belegdatum,
                rechnungs_nr=rechnungs_nr,
                währung="EUR",
                gegenkonto=gegenkonto if not lieferant_nr else None,
                buchungstext=pos_text,
                kostenstelle=kostenstelle,
            )

            if ust_satz == 19:
                rechnung.netto_voll = betrag_netto
                rechnung.steuer_voll = ust_betrag
                rechnung.konto_voll = aufwandskonto
            elif ust_satz == 7:
                rechnung.netto_erm = betrag_netto
                rechnung.steuer_erm = ust_betrag
                rechnung.konto_erm = aufwandskonto
            else:
                rechnung.sonstige_konto = aufwandskonto
                rechnung.sonstige_betrag = betrag_netto

            rechnungen.append(rechnung)

        return rechnungen

    def create_ausgangsrechnung(
        self,
        betrag_netto: Decimal,
        ust_satz: int,
        ertragskonto: int,
        buchungstext: str,
        belegdatum: str,
        kunde_nr: int | None = None,
        gegenkonto: int | None = None,
        rechnungs_nr: str = "",
        kostenstelle: str = "",
    ) -> CollmexAusgangsrechnung:
        """Erzeugt eine Ausgangsrechnung (CMXUMS).

        Collmex kümmert sich um die doppelte Buchführung:
        - Forderungen (Soll) -> kunde_nr oder gegenkonto
        - Erlöskonto (Haben) -> ertragskonto
        - Umsatzsteuer (Haben) -> automatisch

        Parameters
        ----------
        betrag_netto: Nettobetrag der Rechnung
        ust_satz: USt-Satz (0, 7 oder 19)
        ertragskonto: SKR03-Ertragskonto (z.B. 8400)
        buchungstext: Beschreibung
        belegdatum: Datum
        kunde_nr: Collmex-Kunden-ID (optional)
        gegenkonto: Gegenkonto wenn kein Kunde (z.B. 1200 Bank)
        rechnungs_nr: Externe Rechnungsnummer
        kostenstelle: Kostenstelle
        """
        if not isinstance(betrag_netto, Decimal):
            betrag_netto = Decimal(str(betrag_netto))

        belegdatum = format_datum(belegdatum)
        ust_betrag = validate_ust(betrag_netto, ust_satz)

        rechnung = CollmexAusgangsrechnung(
            kunde_nr=kunde_nr,
            datum=belegdatum,
            rechnungs_nr=rechnungs_nr,
            währung="EUR",
            gegenkonto=gegenkonto if not kunde_nr else None,
            buchungstext=buchungstext,
            kostenstelle=kostenstelle,
        )

        if ust_satz == 19:
            rechnung.netto_voll = betrag_netto
            rechnung.steuer_voll = ust_betrag
            rechnung.konto_voll = ertragskonto
        elif ust_satz == 7:
            rechnung.netto_erm = betrag_netto
            rechnung.steuer_erm = ust_betrag
            rechnung.konto_erm = ertragskonto
        else:  # 0% — steuerfrei (IG Lieferung, Export, etc.)
            rechnung.steuerfrei_konto = ertragskonto
            rechnung.steuerfrei_betrag = betrag_netto

        return rechnung

    def create_storno_eingang(
        self,
        original: CollmexEingangsrechnung,
    ) -> CollmexEingangsrechnung:
        """Erzeugt eine Storno-Eingangsrechnung.

        Setzt das Storno-Flag, Collmex kehrt die Buchung intern um.
        """
        from copy import deepcopy

        storno = deepcopy(original)
        storno.storno = True
        storno.buchungstext = f"STORNO: {original.buchungstext}"
        return storno

    def create_storno_ausgang(
        self,
        original: CollmexAusgangsrechnung,
    ) -> CollmexAusgangsrechnung:
        """Erzeugt eine Storno-Ausgangsrechnung.

        Setzt das Storno-Flag, Collmex kehrt die Buchung intern um.
        """
        from copy import deepcopy

        storno = deepcopy(original)
        storno.storno = True
        storno.buchungstext = f"STORNO: {original.buchungstext}"
        return storno

    # ------------------------------------------------------------------
    # Stammdaten (Kunden / Lieferanten)
    # ------------------------------------------------------------------

    def post_stammdaten(
        self,
        stammsatz: CollmexLieferant | CollmexKunde,
    ) -> int:
        """Sendet CMXKND/CMXLIF und gibt die neue ID zurück.

        Bei auto-Vergabe (Nr leer) kommt die ID aus NEW_OBJECT_ID.
        Bei expliziter Nr wird diese zurückgegeben.
        """
        csv_line = stammsatz.to_csv_line()
        api_response = self.api_client.post_booking([csv_line])

        if not api_response.success:
            raise CollmexError(api_response.first_error or "Stammdaten-Fehler")

        # Explizite Nummer? → direkt zurückgeben
        if isinstance(stammsatz, CollmexLieferant) and stammsatz.lieferant_nr:
            return stammsatz.lieferant_nr
        if isinstance(stammsatz, CollmexKunde) and stammsatz.kunde_nr:
            return stammsatz.kunde_nr

        # Auto-Vergabe → aus NEW_OBJECT_ID
        if api_response.booking_id:
            return int(api_response.booking_id)

        raise CollmexError("Keine ID zurückbekommen nach Stammdaten-Anlage")

    # ------------------------------------------------------------------
    # Post & Validate
    # ------------------------------------------------------------------

    def post_and_validate(
        self,
        rechnung: CollmexEingangsrechnung | CollmexAusgangsrechnung | list,
    ) -> BookingResult:
        """Validiert, sendet und liest eine Rechnung gegen.

        Akzeptiert eine einzelne Rechnung oder eine Liste (für Split-Buchungen).
        Bei Listen werden alle Zeilen in einem Request gesendet — Collmex mergt
        Zeilen mit identischer Rechnungsnummer zu einem Beleg.

        Ablauf:
        1. Grundvalidierung (Datum, Betrag, Text)
        2. CSV erzeugen und an Collmex senden
        3. Ergebnis prüfen
        """
        # Liste normalisieren
        if isinstance(rechnung, list):
            rechnungen = rechnung
        else:
            rechnungen = [rechnung]

        # 1. Validieren
        alle_fehler: list[str] = []
        for r in rechnungen:
            alle_fehler.extend(_validate_rechnung(r))
        if alle_fehler:
            return BookingResult(
                success=False,
                beleg_nr=None,
                rechnung=rechnungen[0] if len(rechnungen) == 1 else rechnungen,
                fehler=alle_fehler,
            )

        # 2. CSV erzeugen und senden
        csv_lines = [r.to_csv_line() for r in rechnungen]
        try:
            api_response = self.api_client.request(csv_lines)
        except Exception as exc:
            return BookingResult(
                success=False,
                beleg_nr=None,
                rechnung=rechnungen[0] if len(rechnungen) == 1 else rechnungen,
                fehler=[f"API-Fehler beim Senden: {exc}"],
            )

        # 3. Ergebnis prüfen
        api_fehler = _extract_api_fehler(api_response)

        first = rechnungen[0] if len(rechnungen) == 1 else rechnungen

        if api_fehler:
            return BookingResult(
                success=False,
                beleg_nr=None,
                rechnung=first,
                fehler=api_fehler,
                api_response=api_response,
            )

        # CMXLRN/CMXUMS liefern kein NEW_OBJECT_ID zurück.
        # Die Rechnungsnummer dient als Identifikator.
        beleg_nr = _extract_beleg_nr(api_response)

        return BookingResult(
            success=True,
            beleg_nr=beleg_nr,
            rechnung=first,
            fehler=[],
            api_response=api_response,
        )

    # ------------------------------------------------------------------
    # Vorschlag
    # ------------------------------------------------------------------

    def suggest_booking(
        self,
        beschreibung: str,
        betrag: Decimal,
        datum: str,
    ) -> CollmexEingangsrechnung:
        """Schlägt eine Eingangsrechnung basierend auf einer Beschreibung vor.

        Nutzt suggest_account() um das passende Aufwandskonto zu ermitteln.
        Nimmt 19% USt als Default.
        """
        if not isinstance(betrag, Decimal):
            betrag = Decimal(str(betrag))

        konto = suggest_account(beschreibung)
        datum = format_datum(datum)

        return self.create_eingangsrechnung(
            betrag_netto=betrag,
            ust_satz=19,
            aufwandskonto=konto,
            buchungstext=beschreibung,
            belegdatum=datum,
        )


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------


def _validate_rechnung(
    rechnung: CollmexEingangsrechnung | CollmexAusgangsrechnung,
) -> list[str]:
    """Validiert eine Rechnung vor dem Senden."""
    fehler: list[str] = []

    # Datum
    if not rechnung.datum or len(rechnung.datum) != 8 or not rechnung.datum.isdigit():
        fehler.append(f"Datum '{rechnung.datum}' ist nicht im Format YYYYMMDD.")

    # Buchungstext
    if not rechnung.buchungstext.strip():
        fehler.append("Buchungstext darf nicht leer sein.")

    # Mindestens ein Betrag > 0
    if isinstance(rechnung, CollmexEingangsrechnung):
        total = rechnung.netto_voll + rechnung.netto_erm + rechnung.sonstige_betrag
        if total <= 0:
            fehler.append("Mindestens ein Nettobetrag muss größer 0 sein.")
        # Lieferant oder Gegenkonto
        if not rechnung.lieferant_nr and not rechnung.gegenkonto:
            fehler.append("Lieferantennummer oder Gegenkonto erforderlich.")
    elif isinstance(rechnung, CollmexAusgangsrechnung):
        total = (
            rechnung.netto_voll
            + rechnung.netto_erm
            + rechnung.ig_lieferung
            + rechnung.export_umsätze
            + rechnung.steuerfrei_betrag
        )
        if total <= 0:
            fehler.append("Mindestens ein Nettobetrag muss größer 0 sein.")
        # Kunde oder Gegenkonto
        if not rechnung.kunde_nr and not rechnung.gegenkonto:
            fehler.append("Kundennummer oder Gegenkonto erforderlich.")

    return fehler


def _extract_beleg_nr(api_response: Any) -> int | None:
    """Extrahiert die Belegnummer aus der Collmex-API-Antwort."""
    if hasattr(api_response, "new_ids") and api_response.new_ids:
        try:
            return int(api_response.new_ids[0])
        except (ValueError, TypeError):
            pass

    # Fallback: rohe Liste
    if isinstance(api_response, list):
        for row in api_response:
            if isinstance(row, (list, tuple)) and row and row[0] == "NEW_OBJECT_ID":
                try:
                    return int(row[1])
                except (ValueError, TypeError, IndexError):
                    continue

    return None


def _extract_api_fehler(api_response: Any) -> list[str]:
    """Extrahiert Fehlermeldungen aus der Collmex-API-Antwort."""
    fehler: list[str] = []

    # CollmexResponse-Objekt
    if hasattr(api_response, "messages"):
        for msg in api_response.messages:
            if hasattr(msg, "type") and str(msg.type.value) == "E":
                fehler.append(msg.text)
        return fehler

    # Fallback: rohe Liste
    if isinstance(api_response, list):
        for row in api_response:
            if isinstance(row, (list, tuple)) and row:
                if row[0] == "MESSAGE" and len(row) > 1 and row[1] == "E":
                    msg = row[3] if len(row) > 3 else "Unbekannter Fehler"
                    fehler.append(msg)

    return fehler
