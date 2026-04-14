"""Pytest Fixtures für collmex-Tests.

Stellt Mock-Objekte bereit, damit keine echte Collmex-API benötigt wird.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

from collmex.api import (
    BookingResult,
    CollmexClient,
    CollmexMessage,
    CollmexResponse,
    MessageType,
)
from collmex.models import Booking, BookingLine, CollmexKunde


@pytest.fixture(autouse=True)
def _fake_collmex_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setzt Dummy-Credentials, damit CollmexClient() in Tests instanziiert
    werden kann, ohne dass eine echte .env-Datei vorhanden sein muss (CI)."""
    monkeypatch.setenv("COLLMEX_URL", "https://example.invalid/cgi-bin/cgi.exe?0,0,data_exchange")
    monkeypatch.setenv("COLLMEX_USER", "testuser")
    monkeypatch.setenv("COLLMEX_PASSWORD", "testpass")
    monkeypatch.setenv("COLLMEX_CUSTOMER", "999999")


# ---------------------------------------------------------------------------
# Mock API Client
# ---------------------------------------------------------------------------


def _success_message(
    text: str = "Datenimport erfolgreich. 1 Sätze verarbeitet.",
) -> CollmexMessage:
    return CollmexMessage(type=MessageType.SUCCESS, code="0", text=text)


def _success_response(**kwargs: Any) -> CollmexResponse:
    """Erzeugt eine erfolgreiche CollmexResponse mit optionalen Übersteuerungen."""
    defaults: dict[str, Any] = {
        "rows": [["MESSAGE", "S", "0", "Datenimport erfolgreich. 1 Sätze verarbeitet."]],
        "messages": [_success_message()],
        "new_ids": [],
        "raw": "MESSAGE;S;0;Datenimport erfolgreich. 1 Sätze verarbeitet.\n",
    }
    defaults.update(kwargs)
    return CollmexResponse(**defaults)


@pytest.fixture
def mock_api_client() -> MagicMock:
    """Mock CollmexClient der vordefinierte Responses liefert.

    Alle Methoden geben Erfolgs-Responses zurück. Einzelne Methoden
    können im Test überschrieben werden:

        def test_fehler(mock_api_client):
            mock_api_client.post_booking.return_value = BookingResult(
                success=False,
                messages=[CollmexMessage(type=MessageType.ERROR, code="1", text="Fehler")],
            )
    """
    client = MagicMock(spec=CollmexClient)

    # Attribut-Defaults
    client.url = "https://www.collmex.de/cgi-bin/cgi.exe?999999,0,data_exchange"
    client.user = "test_user"
    client.password = "test_pass"
    client.customer = "999999"
    client.company = 1

    # request(): generischer Erfolg
    client.request.return_value = _success_response()

    # status(): Verbindung OK
    client.status.return_value = True

    # post_booking(): Buchung erfolgreich mit neuer ID
    client.post_booking.return_value = BookingResult(
        success=True,
        booking_id="100001",
        messages=[_success_message()],
        raw_response="MESSAGE;S;0;Datenimport erfolgreich. 1 Sätze verarbeitet.\nNEW_OBJECT_ID;100001\n",
    )

    # get_balances(): Beispielsalden
    client.get_balances.return_value = [
        ["ACCBAL", "1", "2026", "1", "1200", "Bank", "10000,00", "0,00", "10000,00"],
        ["ACCBAL", "1", "2026", "1", "4400", "Bürobedarf", "500,00", "0,00", "500,00"],
    ]

    # get_bookings(): Beispielbuchung
    client.get_bookings.return_value = [
        [
            "ACCDOC",
            "1",
            "100001",
            "1",
            "4400",
            "Bürobedarf",
            "S",
            "500,00",
            "EUR",
            "",
            "20260303",
            "Büromaterial",
            "",
            "",
        ],
        [
            "ACCDOC",
            "1",
            "100001",
            "2",
            "1576",
            "Vorsteuer 19%",
            "S",
            "95,00",
            "EUR",
            "",
            "20260303",
            "Vorsteuer",
            "",
            "",
        ],
        [
            "ACCDOC",
            "1",
            "100001",
            "3",
            "1200",
            "Bank",
            "H",
            "595,00",
            "EUR",
            "",
            "20260303",
            "Bank",
            "",
            "",
        ],
    ]

    # query(): generische Abfrage (default: leere Liste)
    client.query.return_value = []

    # get_open_items(): Beispiel-OP
    client.get_open_items.return_value = [
        [
            "OPEN_ITEM",
            "1",
            "200001",
            "debitor",
            "10001",
            "Musterfirma GmbH",
            "1190,00",
            "EUR",
            "20260215",
            "20260317",
        ],
    ]

    return client


# ---------------------------------------------------------------------------
# Beispiel-Buchungsdaten
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_booking() -> Booking:
    """Standard-Eingangsrechnung: 500 EUR netto, 19% USt, Konto 4400.

    Buchungssatz:
      Soll 4400 (Bürobedarf)        500,00 EUR
      Soll 1576 (Vorsteuer 19%)       95,00 EUR
      Haben 1200 (Bank)              595,00 EUR
    """
    return Booking(
        beleg_nr=None,
        belegdatum="20260303",
        referenz="RE-2026-001",
        firma_nr=1,
        positionen=[
            BookingLine(
                positions_nr=1,
                konto=4400,
                bezeichnung="Bürobedarf",
                soll_haben="S",
                betrag=Decimal("500.00"),
                währung="EUR",
                steuersatz="",
                buchungstext="Büromaterial Lieferant X",
            ),
            BookingLine(
                positions_nr=2,
                konto=1576,
                bezeichnung="Vorsteuer 19%",
                soll_haben="S",
                betrag=Decimal("95.00"),
                währung="EUR",
                steuersatz="",
                buchungstext="Vorsteuer 19%",
            ),
            BookingLine(
                positions_nr=3,
                konto=1200,
                bezeichnung="Bank",
                soll_haben="H",
                betrag=Decimal("595.00"),
                währung="EUR",
                steuersatz="",
                buchungstext="Bank",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Beispiel-Kunde
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_customer() -> CollmexKunde:
    """Testkunde: Musterfirma GmbH, Berlin."""
    return CollmexKunde(
        kunde_nr=10001,
        name="Musterfirma GmbH",
        straße="Musterstr. 1",
        plz="12345",
        ort="Berlin",
        land="DE",
        ust_id="DE123456789",
        email="info@musterfirma.de",
    )


# ---------------------------------------------------------------------------
# Temporäres .collmex Verzeichnis (GoBD-Tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_collmex_dir(tmp_path: Any) -> Any:
    """Erzeugt ein temporäres .collmex Verzeichnis mit Unterordnern.

    Struktur:
        tmp_path/.collmex/
            logs/
            belege/
            export/

    Setzt COLLMEX_HOME auf das temporäre Verzeichnis und stellt
    den Originalwert nach dem Test wieder her.
    """
    collmex_home = tmp_path / ".collmex"
    collmex_home.mkdir()
    (collmex_home / "logs").mkdir()
    (collmex_home / "belege").mkdir()
    (collmex_home / "export").mkdir()

    original_home = os.environ.get("COLLMEX_HOME")
    os.environ["COLLMEX_HOME"] = str(collmex_home)

    yield collmex_home

    # Aufraumen: Umgebungsvariable wiederherstellen
    if original_home is None:
        os.environ.pop("COLLMEX_HOME", None)
    else:
        os.environ["COLLMEX_HOME"] = original_home
