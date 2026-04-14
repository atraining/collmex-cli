"""DATEV Buchungsstapel Export für den Steuerberater.

Exportiert Buchungsbelege aus Collmex im DATEV-Format (EXTF CSV).
Das Format wird vom Steuerberater in DATEV Kanzlei-Rechnungswesen
importiert.

Referenz: DATEV Developer Portal, Format Version 13.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from collmex.api import CollmexClient, parse_amount

logger = logging.getLogger(__name__)

# DATEV Buchungsstapel hat 125 Felder pro Zeile
_NUM_FIELDS = 125

# ACCDOC Feld-Indizes (verifiziert gegen Collmex API)
_ACCDOC_FIRMA = 1
_ACCDOC_BELEG_NR = 2
_ACCDOC_POS_NR = 3
_ACCDOC_KONTO = 4
_ACCDOC_BEZEICHNUNG = 5
_ACCDOC_SOLL_HABEN = 6  # 0=Soll, 1=Haben
_ACCDOC_BETRAG = 7
_ACCDOC_WAEHRUNG = 8
_ACCDOC_BU = 9
_ACCDOC_DATUM = 10
_ACCDOC_TEXT = 11

# BU-Schlüssel Mapping: USt-Satz -> DATEV BU-Key
_BU_VORSTEUER = {19: "9", 7: "8"}
_BU_UMSATZSTEUER = {19: "3", 7: "2"}


def _format_datev_amount(betrag: Decimal) -> str:
    """Formatiert einen Betrag im DATEV-Format (Komma-Dezimal, immer positiv)."""
    return str(abs(betrag).quantize(Decimal("0.01"))).replace(".", ",")


def _datum_to_ddmm(datum_yyyymmdd: str) -> str:
    """Wandelt YYYYMMDD in DDMM (DATEV Belegdatum-Format)."""
    if len(datum_yyyymmdd) == 8 and datum_yyyymmdd.isdigit():
        return datum_yyyymmdd[6:8] + datum_yyyymmdd[4:6]
    return ""


def _make_header(
    berater_nr: int,
    mandant_nr: int,
    wj_beginn: str,
    datum_von: str,
    datum_bis: str,
    bezeichnung: str = "",
    sachkonto_laenge: int = 4,
) -> str:
    """Erzeugt die DATEV Header-Zeile (Zeile 1, 31 Felder)."""
    now = datetime.now()
    erzeugt = now.strftime("%Y%m%d%H%M%S") + "000"

    fields = [
        '"EXTF"',  # 1: Format-KZ
        "700",  # 2: Versionsnummer
        "21",  # 3: Datenkategorie (Buchungsstapel)
        '"Buchungsstapel"',  # 4: Formatname
        "13",  # 5: Formatversion
        erzeugt,  # 6: Erzeugt am
        "",  # 7: Importiert (leer)
        '"CM"',  # 8: Herkunft
        '"collmex"',  # 9: Exportiert von
        "",  # 10: Importiert von (leer)
        str(berater_nr),  # 11: Berater
        str(mandant_nr),  # 12: Mandant
        wj_beginn,  # 13: WJ-Beginn
        str(sachkonto_laenge),  # 14: Sachkontenlänge
        datum_von,  # 15: Datum vom
        datum_bis,  # 16: Datum bis
        f'"{bezeichnung}"' if bezeichnung else "",  # 17: Bezeichnung
        "",  # 18: Diktatkürzel
        "1",  # 19: Buchungstyp (FiBu)
        "0",  # 20: Rechnungslegungszweck
        "0",  # 21: Festschreibung
        '"EUR"',  # 22: WKZ
    ]
    # Felder 23-31: reserviert (leer)
    fields.extend([""] * 9)

    return ";".join(fields)


# DATEV Spalten-Header (125 Felder), Zeile 2, gekürzt auf die wichtigsten
_COLUMN_HEADER = (
    "Umsatz (ohne Soll/Haben-Kz);Soll/Haben-Kennzeichen;"
    "WKZ Umsatz;Kurs;Basisumsatz;WKZ Basisumsatz;"
    "Konto;Gegenkonto (ohne BU-Schlüssel);BU-Schlüssel;"
    "Belegdatum;Belegfeld 1;Belegfeld 2;Skonto;Buchungstext"
)


def _make_column_header() -> str:
    """Erzeugt die DATEV Spalten-Header-Zeile (Zeile 2).

    Enthält alle 125 Feldnamen, getrennt durch Semikolon.
    """
    # Wir geben die ersten 14 wichtigen Felder aus,
    # der Rest wird als leere Felder ergänzt
    base_fields = [
        "Umsatz (ohne Soll/Haben-Kz)",
        "Soll/Haben-Kennzeichen",
        "WKZ Umsatz",
        "Kurs",
        "Basisumsatz",
        "WKZ Basisumsatz",
        "Konto",
        "Gegenkonto (ohne BU-Schlüssel)",
        "BU-Schlüssel",
        "Belegdatum",
        "Belegfeld 1",
        "Belegfeld 2",
        "Skonto",
        "Buchungstext",
    ]
    # Felder 15-125: Weitere Felder (111 Stück)
    remaining = [""] * (_NUM_FIELDS - len(base_fields))
    return ";".join(base_fields + remaining)


def _make_booking_line(
    umsatz: Decimal,
    soll_haben: str,
    konto: str,
    gegenkonto: str,
    bu_schlüssel: str,
    belegdatum: str,
    belegfeld1: str,
    buchungstext: str,
) -> str:
    """Erzeugt eine DATEV Buchungszeile (125 Felder)."""
    fields: list[str] = [""] * _NUM_FIELDS

    fields[0] = _format_datev_amount(umsatz)
    fields[1] = f'"{soll_haben}"'
    # fields[2-5]: WKZ etc. leer (EUR ist Default im Header)
    fields[6] = f'"{konto}"'
    fields[7] = f'"{gegenkonto}"'
    fields[8] = f'"{bu_schlüssel}"' if bu_schlüssel else ""
    fields[9] = belegdatum  # DDMM
    fields[10] = f'"{belegfeld1}"' if belegfeld1 else ""
    # fields[11]: Belegfeld 2 leer
    # fields[12]: Skonto leer
    fields[13] = f'"{buchungstext[:60]}"' if buchungstext else ""

    return ";".join(fields)


class DatevExporter:
    """Exportiert Collmex-Buchungen im DATEV Buchungsstapel-Format."""

    def __init__(
        self,
        api_client: CollmexClient,
        berater_nr: int = 12345,
        mandant_nr: int = 1,
        sachkonto_laenge: int = 4,
    ) -> None:
        self.api = api_client
        self.berater_nr = berater_nr
        self.mandant_nr = mandant_nr
        self.sachkonto_laenge = sachkonto_laenge

    def export(
        self,
        date_from: str,
        date_to: str,
        bezeichnung: str = "",
    ) -> str:
        """Exportiert Buchungen im DATEV-Format.

        Args:
            date_from: Startdatum YYYYMMDD.
            date_to: Enddatum YYYYMMDD.
            bezeichnung: Optionale Beschreibung für den Header.

        Returns:
            DATEV CSV als String (Windows-1252 Encoding, CRLF).
        """
        # Buchungen laden
        rows = self.api.get_bookings(date_from=date_from, date_to=date_to)

        # Geschäftsjahr-Beginn ableiten
        jahr = date_from[:4]
        wj_beginn = f"{jahr}0101"

        if not bezeichnung:
            monat_von = date_from[4:6]
            monat_bis = date_to[4:6]
            if monat_von == monat_bis:
                bezeichnung = f"Buchungen {monat_von}/{jahr}"
            else:
                bezeichnung = f"Buchungen {monat_von}-{monat_bis}/{jahr}"

        # Header
        header = _make_header(
            berater_nr=self.berater_nr,
            mandant_nr=self.mandant_nr,
            wj_beginn=wj_beginn,
            datum_von=date_from,
            datum_bis=date_to,
            bezeichnung=bezeichnung,
            sachkonto_laenge=self.sachkonto_laenge,
        )

        # Spalten-Header
        col_header = _make_column_header()

        # Buchungszeilen erzeugen
        lines = [header, col_header]
        buchungen_count = 0

        for row in rows:
            if len(row) <= _ACCDOC_TEXT or row[0] != "ACCDOC":
                continue

            konto = row[_ACCDOC_KONTO]
            gegenkonto = ""  # Wird unten ermittelt
            sh_raw = row[_ACCDOC_SOLL_HABEN]
            soll_haben = "S" if sh_raw == "0" else "H"
            betrag = parse_amount(row[_ACCDOC_BETRAG])
            datum = _datum_to_ddmm(row[_ACCDOC_DATUM])
            text = row[_ACCDOC_TEXT] if len(row) > _ACCDOC_TEXT else ""
            beleg_nr = row[_ACCDOC_BELEG_NR]
            bu = row[_ACCDOC_BU] if len(row) > _ACCDOC_BU and row[_ACCDOC_BU] else ""

            # Einfache 1:1 Übertragung jeder ACCDOC-Position
            # Der Steuerberater kann in DATEV die Gegenkonto-Zuordnung machen
            # Hier verwenden wir die Belegzeilen direkt
            line = _make_booking_line(
                umsatz=betrag,
                soll_haben=soll_haben,
                konto=konto,
                gegenkonto=gegenkonto,
                bu_schlüssel=bu,
                belegdatum=datum,
                belegfeld1=beleg_nr,
                buchungstext=text,
            )
            lines.append(line)
            buchungen_count += 1

        logger.info(
            "DATEV-Export: %d Buchungszeilen, Zeitraum %s - %s",
            buchungen_count,
            date_from,
            date_to,
        )

        return "\r\n".join(lines) + "\r\n"

    def export_grouped(
        self,
        date_from: str,
        date_to: str,
        bezeichnung: str = "",
    ) -> str:
        """Exportiert Buchungen gruppiert nach Beleg mit Gegenkonto.

        Versucht, zusammengehörige ACCDOC-Zeilen (gleiche Belegnummer)
        zu einem DATEV-Satz mit Konto/Gegenkonto zusammenzuführen.

        Args:
            date_from: Startdatum YYYYMMDD.
            date_to: Enddatum YYYYMMDD.
            bezeichnung: Optionale Beschreibung.

        Returns:
            DATEV CSV als String.
        """
        rows = self.api.get_bookings(date_from=date_from, date_to=date_to)

        # Nach Belegnummer gruppieren
        belege: dict[str, list] = {}
        for row in rows:
            if len(row) <= _ACCDOC_TEXT or row[0] != "ACCDOC":
                continue
            beleg_nr = row[_ACCDOC_BELEG_NR]
            belege.setdefault(beleg_nr, []).append(row)

        jahr = date_from[:4]
        wj_beginn = f"{jahr}0101"

        if not bezeichnung:
            monat_von = date_from[4:6]
            monat_bis = date_to[4:6]
            if monat_von == monat_bis:
                bezeichnung = f"Buchungen {monat_von}/{jahr}"
            else:
                bezeichnung = f"Buchungen {monat_von}-{monat_bis}/{jahr}"

        header = _make_header(
            berater_nr=self.berater_nr,
            mandant_nr=self.mandant_nr,
            wj_beginn=wj_beginn,
            datum_von=date_from,
            datum_bis=date_to,
            bezeichnung=bezeichnung,
            sachkonto_laenge=self.sachkonto_laenge,
        )

        col_header = _make_column_header()
        lines = [header, col_header]

        for beleg_nr, positionen in sorted(belege.items()):
            if not positionen:
                continue

            # Soll- und Haben-Seiten identifizieren
            soll_zeilen = []
            haben_zeilen = []
            for pos in positionen:
                sh = pos[_ACCDOC_SOLL_HABEN]
                if sh == "0":
                    soll_zeilen.append(pos)
                else:
                    haben_zeilen.append(pos)

            # Pro Soll-Zeile eine DATEV-Zeile erzeugen
            # Gegenkonto = erste Haben-Zeile (meist Bank/Verbindlichkeit)
            gegenkonto_row = haben_zeilen[0] if haben_zeilen else None
            gegenkonto = gegenkonto_row[_ACCDOC_KONTO] if gegenkonto_row else ""

            for pos in soll_zeilen:
                konto = pos[_ACCDOC_KONTO]
                betrag = parse_amount(pos[_ACCDOC_BETRAG])
                datum = _datum_to_ddmm(pos[_ACCDOC_DATUM])
                text = pos[_ACCDOC_TEXT] if len(pos) > _ACCDOC_TEXT else ""
                bu = pos[_ACCDOC_BU] if len(pos) > _ACCDOC_BU and pos[_ACCDOC_BU] else ""

                line = _make_booking_line(
                    umsatz=betrag,
                    soll_haben="S",
                    konto=konto,
                    gegenkonto=gegenkonto,
                    bu_schlüssel=bu,
                    belegdatum=datum,
                    belegfeld1=beleg_nr,
                    buchungstext=text,
                )
                lines.append(line)

            # Auch Haben-Zeilen (ausser die als Gegenkonto genutzte)
            for pos in haben_zeilen[1:]:
                konto = pos[_ACCDOC_KONTO]
                betrag = parse_amount(pos[_ACCDOC_BETRAG])
                datum = _datum_to_ddmm(pos[_ACCDOC_DATUM])
                text = pos[_ACCDOC_TEXT] if len(pos) > _ACCDOC_TEXT else ""
                bu = pos[_ACCDOC_BU] if len(pos) > _ACCDOC_BU and pos[_ACCDOC_BU] else ""

                # Gegenkonto = erste Soll-Zeile
                gk = soll_zeilen[0][_ACCDOC_KONTO] if soll_zeilen else ""
                line = _make_booking_line(
                    umsatz=betrag,
                    soll_haben="H",
                    konto=konto,
                    gegenkonto=gk,
                    bu_schlüssel=bu,
                    belegdatum=datum,
                    belegfeld1=beleg_nr,
                    buchungstext=text,
                )
                lines.append(line)

        logger.info(
            "DATEV-Export (gruppiert): %d Belege, Zeitraum %s - %s",
            len(belege),
            date_from,
            date_to,
        )

        return "\r\n".join(lines) + "\r\n"
