"""Collmex API Client — CSV-Batch-Protokoll über HTTP POST.

Alle Kommunikation mit der Collmex-API läuft über dieses Modul.
Jeder Request besteht aus einer LOGIN-Zeile gefolgt von Datenzeilen,
Semikolon-getrennt, per POST an den Collmex-Endpunkt.
"""

from __future__ import annotations

import csv
import io
import logging
import os
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CollmexError(Exception):
    """Fehler aus der Collmex API oder dem Client."""

    def __init__(self, message: str, code: str = "", raw: str = ""):
        self.code = code
        self.raw = raw
        super().__init__(message)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class MessageType(str, Enum):
    SUCCESS = "S"
    WARNING = "W"
    ERROR = "E"


@dataclass
class CollmexMessage:
    """Eine einzelne MESSAGE-Zeile aus der Collmex-Antwort."""

    type: MessageType
    code: str
    text: str


@dataclass
class CollmexResponse:
    """Geparstes Ergebnis eines Collmex-API-Aufrufs."""

    rows: list[list[str]] = field(default_factory=list)
    messages: list[CollmexMessage] = field(default_factory=list)
    new_ids: list[str] = field(default_factory=list)
    raw: str = ""

    @property
    def success(self) -> bool:
        """True wenn kein ERROR in den Messages vorliegt."""
        return not any(m.type == MessageType.ERROR for m in self.messages)

    @property
    def errors(self) -> list[CollmexMessage]:
        return [m for m in self.messages if m.type == MessageType.ERROR]

    @property
    def warnings(self) -> list[CollmexMessage]:
        return [m for m in self.messages if m.type == MessageType.WARNING]

    @property
    def first_error(self) -> str | None:
        errs = self.errors
        return errs[0].text if errs else None

    @property
    def data_rows(self) -> list[list[str]]:
        """Alle Zeilen die keine MESSAGE und kein NEW_OBJECT_ID sind."""
        skip = {"MESSAGE", "NEW_OBJECT_ID"}
        return [r for r in self.rows if r and r[0] not in skip]


@dataclass
class BookingResult:
    """Ergebnis einer Buchungs-Operation (ACCDOC import)."""

    success: bool
    booking_id: str | None = None
    messages: list[CollmexMessage] = field(default_factory=list)
    raw_response: str = ""

    @property
    def first_error(self) -> str | None:
        errs = [m for m in self.messages if m.type == MessageType.ERROR]
        return errs[0].text if errs else None


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def format_amount(value: Decimal | float | int | str) -> str:
    """Formatiert einen Betrag im Collmex-Format: Komma als Dezimaltrenner.

    >>> format_amount(Decimal("500.00"))
    '500,00'
    >>> format_amount(1234.5)
    '1234,50'
    >>> format_amount(0)
    '0,00'
    """
    if isinstance(value, str):
        # Erlaube bereits formatierte Werte oder Punkt-Dezimalwerte
        value = value.replace(",", ".")
        try:
            value = Decimal(value)
        except InvalidOperation:
            raise CollmexError(f"Ungültiger Betrag: {value!r}")
    elif isinstance(value, (int, float)):
        value = Decimal(str(value))

    # Auf 2 Nachkommastellen formatieren, Punkt durch Komma ersetzen
    return f"{value:.2f}".replace(".", ",")


def parse_amount(text: str) -> Decimal:
    """Parst einen Collmex-Betrag (Komma als Dezimaltrenner) zu Decimal.

    >>> parse_amount("500,00")
    Decimal('500.00')
    >>> parse_amount("-1.234,56")
    Decimal('-1234.56')
    """
    if not text or not text.strip():
        return Decimal("0")
    # Tausenderpunkte entfernen, Komma durch Punkt ersetzen
    cleaned = text.strip().replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        raise CollmexError(f"Ungültiger Betrag: {text!r}")


def _parse_csv_response(text: str) -> list[list[str]]:
    """Parst die Collmex-CSV-Antwort (Semikolon-getrennt) robust.

    Verwendet das Python csv-Modul für korrekte Behandlung von
    gequoteten Feldern und Semikolon-Trennern.
    """
    rows: list[list[str]] = []
    reader = csv.reader(
        io.StringIO(text),
        delimiter=";",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
    )
    for row in reader:
        if row:  # Leerzeilen ignorieren
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class CollmexClient:
    """Client für die Collmex CSV-Batch-API.

    Lädt Credentials aus Umgebungsvariablen (oder .env-Datei):
      - COLLMEX_URL:      Vollständiger Endpunkt inkl. Kundennummer
      - COLLMEX_USER:     API-Benutzername
      - COLLMEX_PASSWORD:  API-Passwort
      - COLLMEX_CUSTOMER:  Collmex-Kundennummer

    Beispiel::

        client = CollmexClient()
        if client.status():
            balances = client.get_balances(2026, 1)
    """

    def __init__(
        self,
        url: str | None = None,
        user: str | None = None,
        password: str | None = None,
        customer: str | None = None,
        company: int = 1,
        *,
        env_file: str | None = None,
    ):
        # .env laden (wenn vorhanden)
        load_dotenv(dotenv_path=env_file)

        self.url = url or os.getenv("COLLMEX_URL", "")
        self.user = user or os.getenv("COLLMEX_USER", "")
        self.password = password or os.getenv("COLLMEX_PASSWORD", "")
        self.customer = customer or os.getenv("COLLMEX_CUSTOMER", "")
        self.company = company

        if not self.url:
            raise CollmexError("COLLMEX_URL nicht konfiguriert")
        if not self.user:
            raise CollmexError("COLLMEX_USER nicht konfiguriert")
        if not self.password:
            raise CollmexError("COLLMEX_PASSWORD nicht konfiguriert")
        if not self.customer:
            raise CollmexError("COLLMEX_CUSTOMER nicht konfiguriert")

    # ------------------------------------------------------------------
    # Kern-Request
    # ------------------------------------------------------------------

    def _build_login_line(self) -> str:
        """Erzeugt die LOGIN-CSV-Zeile."""
        return f"LOGIN;{self.user};{self.password};{self.customer};1"

    def request(self, lines: list[str]) -> CollmexResponse:
        """Sendet CSV-Zeilen an Collmex und parst die Antwort.

        Args:
            lines: Liste der CSV-Datenzeilen (ohne LOGIN).

        Returns:
            CollmexResponse mit geparsten Zeilen und Messages.

        Raises:
            CollmexError: Bei Netzwerk-/HTTP-Fehlern.
        """
        login = self._build_login_line()
        payload = login + "\n" + "\n".join(lines)

        logger.debug(
            "Collmex Request: %d Datenzeilen an %s",
            len(lines),
            self.url,
        )
        # Login-Zeile NICHT loggen (enthält Passwort)
        for line in lines:
            logger.debug("  > %s", line)

        try:
            http_response = requests.post(
                self.url,
                data=payload.encode("utf-8"),
                headers={"Content-Type": "text/csv; charset=UTF-8"},
                timeout=30,
            )
        except requests.RequestException as exc:
            raise CollmexError(f"HTTP-Fehler: {exc}") from exc

        # Collmex liefert ISO-8859-1 — immer explizit dekodieren
        raw_text = http_response.content.decode("iso-8859-1")

        logger.debug("Collmex Response (HTTP %d):", http_response.status_code)
        logger.debug("  %s", raw_text[:500])

        http_response.raise_for_status()

        return self._parse_response(raw_text)

    def _parse_response(self, raw_text: str) -> CollmexResponse:
        """Parst den rohen Response-Text in ein CollmexResponse-Objekt."""
        rows = _parse_csv_response(raw_text)
        response = CollmexResponse(rows=rows, raw=raw_text)

        for row in rows:
            if not row:
                continue
            record_type = row[0]

            if record_type == "MESSAGE":
                msg_type_str = row[1] if len(row) > 1 else ""
                msg_code = row[2] if len(row) > 2 else ""
                msg_text = row[3] if len(row) > 3 else ""
                try:
                    msg_type = MessageType(msg_type_str)
                except ValueError:
                    msg_type = MessageType.ERROR
                response.messages.append(
                    CollmexMessage(type=msg_type, code=msg_code, text=msg_text)
                )
                if msg_type == MessageType.ERROR:
                    logger.error("Collmex FEHLER [%s]: %s", msg_code, msg_text)
                elif msg_type == MessageType.WARNING:
                    logger.warning("Collmex WARNUNG [%s]: %s", msg_code, msg_text)
                else:
                    logger.info("Collmex OK [%s]: %s", msg_code, msg_text)

            elif record_type == "NEW_OBJECT_ID":
                # Live-verifiziertes Format (CMXLIF/CMXKND):
                #   NEW_OBJECT_ID;70004;0;2
                # → row[1] = ID, row[2..] = interne Collmex-Felder
                new_id = row[1] if len(row) > 1 else ""
                response.new_ids.append(new_id)
                logger.info("Collmex neue ID: %s", new_id)

        return response

    # ------------------------------------------------------------------
    # Generische Abfrage
    # ------------------------------------------------------------------

    def query(self, satzart: str, *fields) -> list[list[str]]:
        """Generische Abfrage: sendet beliebige Satzart mit beliebigen Feldern.

        Baut CSV-Zeile: SATZART;feld1;feld2;...
        Jede GET-Satzart hat eigene Feld-Reihenfolge (siehe Collmex-Doku).
        """
        line = ";".join([satzart] + [str(f) for f in fields])
        resp = self.request([line])
        if not resp.success:
            raise CollmexError(resp.first_error or f"Fehler bei {satzart}", raw=resp.raw)
        return resp.data_rows

    # ------------------------------------------------------------------
    # Komfort-Wrapper (viele interne Aufrufer)
    # ------------------------------------------------------------------

    def get_balances(self, year, period, account=None, *, company=None):
        """Kontensalden abfragen (ACCBAL_GET)."""
        co = company or self.company
        return self.query("ACCBAL_GET", co, year, period, str(account) if account else "")

    def get_bookings(self, booking_id=None, date_from=None, date_to=None, *, company=None):
        """Buchungsbelege abrufen (ACCDOC_GET)."""
        co = company or self.company
        return self.query(
            "ACCDOC_GET",
            co,
            str(booking_id) if booking_id else "",
            "",
            date_from or "",
            date_to or "",
        )

    def get_open_items(self, *, company=None):
        """Offene Posten abrufen (OPEN_ITEMS_GET)."""
        co = company or self.company
        return self.query("OPEN_ITEMS_GET", co)

    # ------------------------------------------------------------------
    # Schreiben (Import-Satzarten)
    # ------------------------------------------------------------------

    def post_booking(self, lines: list[str]) -> BookingResult:
        """Rechnungen importieren (CMXLRN oder CMXUMS).

        HINWEIS: ACCDOC-Import ist bei Collmex NICHT möglich.
        Stattdessen CMXLRN (Eingangsrechnung) oder CMXUMS (Ausgangsrechnung)
        verwenden.  Collmex erzeugt die doppelte Buchführung intern.

        Args:
            lines: CSV-Zeilen (CMXLRN oder CMXUMS).

        Returns:
            BookingResult mit Erfolg/Fehler und ggf. neuer Beleg-ID.
        """
        valid_prefixes = ("CMXLRN;", "CMXUMS;", "CMXKND;", "CMXLIF;", "CMXINV;", "CMXPRD;")
        for line in lines:
            if not any(line.startswith(p) for p in valid_prefixes):
                raise CollmexError(
                    f"post_booking erwartet CMXLRN/CMXUMS-Zeilen, erhalten: {line[:40]!r}"
                )

        resp = self.request(lines)
        booking_id = resp.new_ids[0] if resp.new_ids else None

        result = BookingResult(
            success=resp.success,
            booking_id=booking_id,
            messages=resp.messages,
            raw_response=resp.raw,
        )

        if not resp.success:
            logger.error(
                "Buchung fehlgeschlagen: %s",
                resp.first_error or "Unbekannter Fehler",
            )
        else:
            logger.info("Buchung erfolgreich, ID: %s", booking_id)

        return result

    def post_eingangsrechnung(self, csv_line: str) -> BookingResult:
        """Eingangsrechnung importieren (CMXLRN).

        Args:
            csv_line: CMXLRN-CSV-Zeile (eine Zeile = eine Rechnung).

        Returns:
            BookingResult mit Erfolg/Fehler.
        """
        if not csv_line.startswith("CMXLRN;"):
            raise CollmexError(f"Erwartet CMXLRN-Zeile, erhalten: {csv_line[:40]!r}")
        return self.post_booking([csv_line])

    def post_ausgangsrechnung(self, csv_line: str) -> BookingResult:
        """Ausgangsrechnung importieren (CMXUMS).

        Args:
            csv_line: CMXUMS-CSV-Zeile (eine Zeile = eine Rechnung).

        Returns:
            BookingResult mit Erfolg/Fehler.
        """
        if not csv_line.startswith("CMXUMS;"):
            raise CollmexError(f"Erwartet CMXUMS-Zeile, erhalten: {csv_line[:40]!r}")
        return self.post_booking([csv_line])

    # ------------------------------------------------------------------
    # Komfort-Methoden
    # ------------------------------------------------------------------

    def status(self) -> bool:
        """Verbindungstest: Prüft ob Login und API-Zugang funktionieren.

        Führt eine minimale Abfrage (ACCBAL_GET für Konto 1200, aktuelles
        Jahr, Periode 1) durch und prüft ob kein Fehler zurückkommt.

        Returns:
            True bei erfolgreichem Login, False bei Fehler.
        """
        try:
            line = f"ACCBAL_GET;{self.company};2026;1;"
            resp = self.request([line])
            return resp.success
        except (CollmexError, requests.RequestException) as exc:
            logger.warning("Collmex status() fehlgeschlagen: %s", exc)
            return False

    def __repr__(self) -> str:
        return (
            f"CollmexClient(url={self.url!r}, user={self.user!r}, "
            f"customer={self.customer!r}, company={self.company})"
        )
