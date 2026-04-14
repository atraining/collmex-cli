"""Tests für collmex.api: Collmex API Client.

Unit Tests mocken requests.post, Live Tests (markiert mit @pytest.mark.live)
kommunizieren mit der echten Collmex-API.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from collmex.api import (
    BookingResult,
    CollmexClient,
    CollmexError,
    CollmexResponse,
    MessageType,
    _parse_csv_response,
    format_amount,
    parse_amount,
)

# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def client():
    """CollmexClient mit Dummy-Credentials (für Unit Tests)."""
    return CollmexClient(
        url="https://www.collmex.de/c.cmx?123456,0,data_exchange",
        user="testuser",
        password="testpass",
        customer="123456",
    )


@pytest.fixture
def live_client():
    """CollmexClient mit echten Credentials aus .env."""
    return CollmexClient()


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    """Erzeugt ein Mock-requests.Response-Objekt.

    Collmex liefert ISO-8859-1, daher encoden wir den Mock so.
    """
    mock = MagicMock()
    mock.text = text
    mock.content = text.encode("iso-8859-1")
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


# ===================================================================
# Login-Satz
# ===================================================================


class TestLoginLine:
    """Test: LOGIN-Zeile wird korrekt generiert."""

    def test_login_format(self, client):
        login = client._build_login_line()
        assert login == "LOGIN;testuser;testpass;123456;1"

    def test_login_contains_all_fields(self, client):
        login = client._build_login_line()
        parts = login.split(";")
        assert parts[0] == "LOGIN"
        assert parts[1] == "testuser"
        assert parts[2] == "testpass"
        assert parts[3] == "123456"
        assert parts[4] == "1"
        assert len(parts) == 5

    def test_login_with_special_chars_in_password(self):
        """Passwörter mit Sonderzeichen werden korrekt übernommen."""
        client = CollmexClient(
            url="https://example.com",
            user="user",
            password="P@ss w0rd!#$%&special",
            customer="123456",
        )
        login = client._build_login_line()
        assert "P@ss w0rd!#$%&special" in login


# ===================================================================
# Response Parsing
# ===================================================================


class TestResponseParsing:
    """Test: MESSAGE-Satzarten werden korrekt geparst (S/W/E)."""

    def test_success_response(self, client):
        raw = 'MESSAGE;S;0;"Datenimport erfolgreich. 1 Sätze verarbeitet."'
        resp = client._parse_response(raw)
        assert resp.success is True
        assert len(resp.messages) == 1
        assert resp.messages[0].type == MessageType.SUCCESS
        assert resp.messages[0].code == "0"
        assert "erfolgreich" in resp.messages[0].text

    def test_warning_response(self, client):
        raw = 'MESSAGE;W;100;"Hinweis: Konto existiert bereits."'
        resp = client._parse_response(raw)
        assert resp.success is True  # Warning ist kein Error
        assert len(resp.warnings) == 1
        assert resp.warnings[0].type == MessageType.WARNING

    def test_error_response(self, client):
        raw = 'MESSAGE;E;10001;"Ungültige Kontonummer"'
        resp = client._parse_response(raw)
        assert resp.success is False
        assert len(resp.errors) == 1
        assert resp.errors[0].code == "10001"
        assert resp.first_error == "Ungültige Kontonummer"

    def test_mixed_messages(self, client):
        raw = 'MESSAGE;W;50;"Warnung: Datum"\nMESSAGE;S;0;"OK"\n'
        resp = client._parse_response(raw)
        assert resp.success is True
        assert len(resp.messages) == 2
        assert len(resp.warnings) == 1

    def test_error_with_success_still_error(self, client):
        raw = 'MESSAGE;S;0;"Datenimport erfolgreich."\nMESSAGE;E;500;"Konto gesperrt"\n'
        resp = client._parse_response(raw)
        assert resp.success is False
        assert resp.first_error == "Konto gesperrt"

    def test_new_object_id(self, client):
        raw = 'NEW_OBJECT_ID;42\nMESSAGE;S;0;"OK"\n'
        resp = client._parse_response(raw)
        assert resp.success is True
        assert resp.new_ids == ["42"]

    def test_new_object_id_4_felder(self, client):
        """Live-Format: NEW_OBJECT_ID;70004;0;2 (CMXLIF/CMXKND)."""
        raw = 'NEW_OBJECT_ID;70004;0;2\nMESSAGE;S;204020;"Datenübertragung erfolgreich."\n'
        resp = client._parse_response(raw)
        assert resp.success is True
        assert resp.new_ids == ["70004"]

    def test_data_rows_filter(self, client):
        raw = (
            "ACCBAL;1;1200;Bank;50000,00;0,00\n"
            "ACCBAL;1;1400;Forderungen;12000,00;0,00\n"
            'MESSAGE;S;0;"OK"\n'
        )
        resp = client._parse_response(raw)
        data = resp.data_rows
        assert len(data) == 2
        assert data[0][0] == "ACCBAL"
        assert data[1][0] == "ACCBAL"

    def test_empty_response(self, client):
        resp = client._parse_response("")
        assert resp.success is True
        assert resp.rows == []
        assert resp.messages == []


# ===================================================================
# CSV Parsing
# ===================================================================


class TestCsvParsing:
    """Test: CSV-Parsing mit Semikolon und Umlauten."""

    def test_basic_semicolon_parsing(self):
        text = "ACCDOC;1;42;1;4400;Bürobedarf;S;500,00;EUR"
        rows = _parse_csv_response(text)
        assert len(rows) == 1
        assert rows[0][0] == "ACCDOC"
        assert rows[0][4] == "4400"
        assert rows[0][5] == "Bürobedarf"
        assert rows[0][7] == "500,00"

    def test_umlauts(self):
        text = "ACCDOC;1;1;1;4400;Büroermoebel für Geschäftsführer;S;1200,00;EUR"
        rows = _parse_csv_response(text)
        assert "Büroermoebel" in rows[0][5]
        assert "Geschäftsführer" in rows[0][5]

    def test_real_umlauts(self):
        """Echte deutsche Umlaute (nicht ASCII-Ersatz)."""
        text = 'ACCDOC;1;1;1;4400;"Bürobedarf & Zubehoer";S;500,00;EUR'
        rows = _parse_csv_response(text)
        assert "Bürobedarf & Zubehoer" in rows[0][5]

    def test_quoted_fields_with_semicolons(self):
        text = 'MESSAGE;S;0;"Import OK; 3 Sätze verarbeitet."'
        rows = _parse_csv_response(text)
        assert len(rows) == 1
        assert rows[0][3] == "Import OK; 3 Sätze verarbeitet."

    def test_multiline_response(self):
        text = (
            "ACCBAL;1;1200;Bank;50000,00;0,00\n"
            "ACCBAL;1;1400;Forderungen;12000,00;0,00\n"
            'MESSAGE;S;0;"OK"\n'
        )
        rows = _parse_csv_response(text)
        assert len(rows) == 3

    def test_empty_fields(self):
        text = "ACCDOC;1;;1;4400;;S;500,00;EUR;;"
        rows = _parse_csv_response(text)
        assert rows[0][2] == ""  # Belegnummer leer
        assert rows[0][5] == ""  # Bezeichnung leer

    def test_empty_lines_skipped(self):
        text = "ACCBAL;1;1200;Bank\n\n\nMESSAGE;S;0;OK\n"
        rows = _parse_csv_response(text)
        assert len(rows) == 2


# ===================================================================
# Betragsformatierung
# ===================================================================


class TestAmountFormatting:
    """Test: Decimal -> '500,00' Collmex-Format und zurück."""

    def test_decimal_to_collmex(self):
        assert format_amount(Decimal("500.00")) == "500,00"

    def test_float_to_collmex(self):
        assert format_amount(1234.5) == "1234,50"

    def test_int_to_collmex(self):
        assert format_amount(0) == "0,00"

    def test_negative_amount(self):
        assert format_amount(Decimal("-99.99")) == "-99,99"

    def test_large_amount(self):
        assert format_amount(Decimal("1234567.89")) == "1234567,89"

    def test_string_with_dot(self):
        assert format_amount("500.00") == "500,00"

    def test_string_with_comma(self):
        assert format_amount("500,00") == "500,00"

    def test_invalid_string_raises(self):
        with pytest.raises(CollmexError):
            format_amount("abc")

    def test_parse_collmex_amount(self):
        assert parse_amount("500,00") == Decimal("500.00")

    def test_parse_with_thousands_separator(self):
        assert parse_amount("-1.234,56") == Decimal("-1234.56")

    def test_parse_empty(self):
        assert parse_amount("") == Decimal("0")

    def test_parse_invalid_raises(self):
        with pytest.raises(CollmexError):
            parse_amount("abc")

    def test_roundtrip(self):
        """format -> parse -> format bleibt konsistent."""
        original = Decimal("12345.67")
        formatted = format_amount(original)
        parsed = parse_amount(formatted)
        assert parsed == original


# ===================================================================
# Client-Methoden (gemockt)
# ===================================================================


class TestEncoding:
    """Test: Collmex ISO-8859-1 Response wird korrekt dekodiert."""

    @patch("collmex.api.requests.post")
    def test_umlauts_decoded_correctly(self, mock_post, client):
        """Umlaute aus Collmex (ISO-8859-1) müssen korrekt ankommen."""
        text = (
            'ACC_BAL;4830;"Abschreibungen auf Sachanlagen (ohne Afa auf Kfz und Gebäude)";1850,00\n'
        )
        text += 'MESSAGE;S;0;"OK"\n'
        mock = MagicMock()
        mock.content = text.encode("iso-8859-1")
        mock.status_code = 200
        mock.raise_for_status = MagicMock()
        mock_post.return_value = mock

        resp = client.request(["ACCBAL_GET;1;2026;3;4830"])
        assert resp.success is True
        row = resp.data_rows[0]
        assert "Gebäude" in row[2]

    @patch("collmex.api.requests.post")
    def test_erlöse_umlaut(self, mock_post, client):
        """Erlöse mit ö muss korrekt dekodiert werden."""
        text = 'ACC_BAL;8400;"Erlöse 19% Umsatzsteuer";-4500,00\n'
        text += 'MESSAGE;S;0;"OK"\n'
        mock = MagicMock()
        mock.content = text.encode("iso-8859-1")
        mock.status_code = 200
        mock.raise_for_status = MagicMock()
        mock_post.return_value = mock

        resp = client.request(["ACCBAL_GET;1;2026;3;8400"])
        row = resp.data_rows[0]
        assert "Erlöse" in row[2]


class TestClientRequest:
    """Test: request() sendet korrekten Payload und parst Response."""

    @patch("collmex.api.requests.post")
    def test_request_sends_login_and_data(self, mock_post, client):
        mock_post.return_value = _mock_response('MESSAGE;S;0;"OK"')

        client.request(["ACCBAL_GET;1;2026;1;"])

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args.kwargs.get("data") or call_args[1].get("data") or call_args[0][0]
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        assert "LOGIN;testuser;testpass;123456;1" in payload
        assert "ACCBAL_GET;1;2026;1;" in payload

    @patch("collmex.api.requests.post")
    def test_request_content_type(self, mock_post, client):
        mock_post.return_value = _mock_response('MESSAGE;S;0;"OK"')

        client.request(["ACCBAL_GET;1;2026;1;"])

        call_args = mock_post.call_args
        headers = call_args.kwargs.get("headers") or call_args[1].get("headers")
        assert headers["Content-Type"] == "text/csv; charset=UTF-8"

    @patch("collmex.api.requests.post")
    def test_request_error_raises_not(self, mock_post, client):
        """request() selbst wirft nicht bei API-Errors, gibt CollmexResponse zurück."""
        mock_post.return_value = _mock_response('MESSAGE;E;500;"Konto ungültig"')
        resp = client.request(["ACCDOC;1;..."])
        assert resp.success is False
        assert resp.first_error == "Konto ungültig"

    @patch("collmex.api.requests.post")
    def test_network_error_raises(self, mock_post, client):
        from requests.exceptions import ConnectionError

        mock_post.side_effect = ConnectionError("Keine Verbindung")
        with pytest.raises(CollmexError, match="HTTP-Fehler"):
            client.request(["ACCBAL_GET;1;2026;1;"])


class TestStatusMethod:
    """Test: status() Verbindungstest."""

    @patch("collmex.api.requests.post")
    def test_status_success(self, mock_post, client):
        mock_post.return_value = _mock_response('MESSAGE;S;0;"OK"')
        assert client.status() is True

    @patch("collmex.api.requests.post")
    def test_status_failure(self, mock_post, client):
        mock_post.return_value = _mock_response('MESSAGE;E;1;"Login fehlgeschlagen"')
        assert client.status() is False

    @patch("collmex.api.requests.post")
    def test_status_network_error(self, mock_post, client):
        from requests.exceptions import ConnectionError

        mock_post.side_effect = ConnectionError("timeout")
        assert client.status() is False


class TestGetBalances:
    """Test: get_balances() -> ACCBAL_GET."""

    @patch("collmex.api.requests.post")
    def test_returns_data_rows(self, mock_post, client):
        raw = 'ACCBAL;1;1200;Bank;50000,00;0,00\nMESSAGE;S;0;"OK"\n'
        mock_post.return_value = _mock_response(raw)
        result = client.get_balances(2026, 1)
        assert len(result) == 1
        assert result[0][0] == "ACCBAL"
        assert result[0][2] == "1200"

    @patch("collmex.api.requests.post")
    def test_with_account_filter(self, mock_post, client):
        mock_post.return_value = _mock_response('MESSAGE;S;0;"OK"')
        client.get_balances(2026, 1, account=1200)
        payload = mock_post.call_args[1]["data"].decode("utf-8")
        assert "ACCBAL_GET;1;2026;1;1200" in payload

    @patch("collmex.api.requests.post")
    def test_error_raises(self, mock_post, client):
        mock_post.return_value = _mock_response('MESSAGE;E;100;"Fehler"')
        with pytest.raises(CollmexError):
            client.get_balances(2026, 1)


class TestGetBookings:
    """Test: get_bookings() -> ACCDOC_GET."""

    @patch("collmex.api.requests.post")
    def test_by_id(self, mock_post, client):
        mock_post.return_value = _mock_response('MESSAGE;S;0;"OK"')
        client.get_bookings(booking_id=42)
        payload = mock_post.call_args[1]["data"].decode("utf-8")
        assert "ACCDOC_GET;1;42;;" in payload

    @patch("collmex.api.requests.post")
    def test_by_date_range(self, mock_post, client):
        mock_post.return_value = _mock_response('MESSAGE;S;0;"OK"')
        client.get_bookings(date_from="20260101", date_to="20260331")
        payload = mock_post.call_args[1]["data"].decode("utf-8")
        assert "ACCDOC_GET;1;;;20260101;20260331" in payload


class TestPostBooking:
    """Test: post_booking() -> CMXLRN/CMXUMS Import."""

    @patch("collmex.api.requests.post")
    def test_success_with_new_id(self, mock_post, client):
        raw = 'NEW_OBJECT_ID;42\nMESSAGE;S;0;"Datenimport erfolgreich. 1 Sätze verarbeitet."\n'
        mock_post.return_value = _mock_response(raw)

        lines = [
            "CMXLRN;70000;1;20260303;;500,00;95,00;;;;;;;;Büromaterial;;4400;;;",
        ]
        result = client.post_booking(lines)

        assert result.success is True
        assert result.booking_id == "42"
        assert result.first_error is None

    @patch("collmex.api.requests.post")
    def test_cmxums_success(self, mock_post, client):
        raw = 'NEW_OBJECT_ID;43\nMESSAGE;S;0;"Datenimport erfolgreich. 1 Sätze verarbeitet."\n'
        mock_post.return_value = _mock_response(raw)

        lines = [
            "CMXUMS;10000;1;20260303;;1000,00;190,00;;;;;;;;;;Beratung;;8400;;;;;;;;;;;;;",
        ]
        result = client.post_booking(lines)

        assert result.success is True
        assert result.booking_id == "43"

    @patch("collmex.api.requests.post")
    def test_failure(self, mock_post, client):
        mock_post.return_value = _mock_response('MESSAGE;E;200;"Konto ungültig"')
        lines = ["CMXLRN;70000;1;20260303;;500,00;95,00;;;;;;;;Test;;4400;;;"]
        result = client.post_booking(lines)
        assert result.success is False
        assert "Konto ungültig" in result.first_error

    def test_invalid_prefix_raises(self, client):
        with pytest.raises(CollmexError, match="CMXLRN/CMXUMS"):
            client.post_booking(["CUSTOMER_GET;1"])


# ===================================================================
# Credentials / Konfiguration
# ===================================================================


class TestCredentials:
    """Test: Fehlende Credentials werfen CollmexError.

    Wir patchen die Umgebungsvariablen weg, damit load_dotenv() keine
    Werte aus der .env-Datei laden kann.
    """

    _empty_env = {
        "COLLMEX_URL": "",
        "COLLMEX_USER": "",
        "COLLMEX_PASSWORD": "",
        "COLLMEX_CUSTOMER": "",
    }

    @patch.dict("os.environ", _empty_env, clear=False)
    @patch("collmex.api.load_dotenv")
    def test_missing_url(self, _mock_dotenv):
        with pytest.raises(CollmexError, match="COLLMEX_URL"):
            CollmexClient(url="", user="u", password="p", customer="c")

    @patch.dict("os.environ", _empty_env, clear=False)
    @patch("collmex.api.load_dotenv")
    def test_missing_user(self, _mock_dotenv):
        with pytest.raises(CollmexError, match="COLLMEX_USER"):
            CollmexClient(url="http://x", user="", password="p", customer="c")

    @patch.dict("os.environ", _empty_env, clear=False)
    @patch("collmex.api.load_dotenv")
    def test_missing_password(self, _mock_dotenv):
        with pytest.raises(CollmexError, match="COLLMEX_PASSWORD"):
            CollmexClient(url="http://x", user="u", password="", customer="c")

    @patch.dict("os.environ", _empty_env, clear=False)
    @patch("collmex.api.load_dotenv")
    def test_missing_customer(self, _mock_dotenv):
        with pytest.raises(CollmexError, match="COLLMEX_CUSTOMER"):
            CollmexClient(url="http://x", user="u", password="p", customer="")

    def test_repr(self, client):
        r = repr(client)
        assert "CollmexClient" in r
        assert "testuser" in r
        assert "testpass" not in r  # Passwort nicht im repr anzeigen... wait
        # repr zeigt URL und User, aber das Passwort ist nicht direkt
        # enthalten. Es wird über url=, user=, customer= angezeigt.


# ===================================================================
# Dataclass-Tests
# ===================================================================


class TestDataclasses:
    def test_collmex_response_defaults(self):
        resp = CollmexResponse()
        assert resp.success is True
        assert resp.rows == []
        assert resp.messages == []
        assert resp.new_ids == []
        assert resp.first_error is None

    def test_booking_result_defaults(self):
        result = BookingResult(success=True)
        assert result.booking_id is None
        assert result.first_error is None


# ===================================================================
# Live Tests (echte API)
# ===================================================================


@pytest.mark.live
class TestLive:
    """Tests gegen die echte Collmex-API.

    Nur ausführen mit: pytest -m live
    Benötigt gültige .env Konfiguration.
    """

    def test_status(self, live_client):
        """Prüft ob Login funktioniert."""
        assert live_client.status() is True

    def test_get_balances(self, live_client):
        """Prüft Kontensalden-Abfrage."""
        # Sollte nicht werfen, auch wenn keine Buchungen existieren
        result = live_client.get_balances(2026, 1)
        assert isinstance(result, list)

    def test_get_bookings_empty(self, live_client):
        """Prüft Buchungsabfrage (kann leer sein)."""
        result = live_client.get_bookings(date_from="20260101", date_to="20260131")
        assert isinstance(result, list)

    def test_query_customers(self, live_client):
        """Prüft generische Abfrage mit CUSTOMER_GET."""
        result = live_client.query("CUSTOMER_GET", "", 1)
        assert isinstance(result, list)
