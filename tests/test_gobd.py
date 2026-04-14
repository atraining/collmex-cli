"""Tests für collmex.gobd: AuditTrail.

Alle Tests verwenden ein temporäres Verzeichnis, keine echten API-Calls.
"""

from __future__ import annotations

import json
import os
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from collmex.gobd import AuditTrail

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dir():
    """Erzeugt ein temporäres Verzeichnis für Audit-Logs."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def trail(tmp_dir):
    """Erzeugt einen AuditTrail mit temporärem Verzeichnis."""
    return AuditTrail(log_dir=tmp_dir)


# ---------------------------------------------------------------------------
# Tests: log_action
# ---------------------------------------------------------------------------


class TestLogAction:
    def test_creates_log_file(self, trail, tmp_dir):
        """log_action erzeugt die audit.log Datei."""
        trail.log_action("TEST", {"input": 1}, {"req": 2}, {"resp": 3})
        assert (Path(tmp_dir) / "audit.log").exists()

    def test_entry_has_all_fields(self, trail):
        """Der geschriebene Eintrag enthält alle Pflichtfelder."""
        entry = trail.log_action(
            "BUCHUNG",
            {"beleg": "test"},
            {"csv": "ACCDOC;..."},
            {"status": "ok"},
            beleg_nr="12345",
            validierung={"soll_haben": True},
        )
        assert "timestamp" in entry
        assert entry["action"] == "BUCHUNG"
        assert entry["beleg_nr"] == "12345"
        assert entry["input_data"] == {"beleg": "test"}
        assert entry["request_data"] == {"csv": "ACCDOC;..."}
        assert entry["response_data"] == {"status": "ok"}
        assert entry["validierung"] == {"soll_haben": True}
        assert "hash" in entry
        assert "prev_hash" in entry

    def test_first_entry_has_genesis_hash(self, trail):
        """Der erste Eintrag referenziert den Genesis-Hash (64 Nullen)."""
        entry = trail.log_action("TEST", {}, {}, {})
        assert entry["prev_hash"] == "0" * 64

    def test_second_entry_references_first_hash(self, trail):
        """Der zweite Eintrag referenziert den Hash des ersten."""
        entry1 = trail.log_action("FIRST", {}, {}, {})
        entry2 = trail.log_action("SECOND", {}, {}, {})
        assert entry2["prev_hash"] == entry1["hash"]

    def test_hash_is_sha256(self, trail):
        """Der Hash ist ein 64-Zeichen Hex-String (SHA-256)."""
        entry = trail.log_action("TEST", {}, {}, {})
        assert len(entry["hash"]) == 64
        assert all(c in "0123456789abcdef" for c in entry["hash"])

    def test_beleg_nr_none(self, trail):
        """beleg_nr kann None sein."""
        entry = trail.log_action("TEST", {}, {}, {})
        assert entry["beleg_nr"] is None

    def test_beleg_nr_int_converted_to_str(self, trail):
        """Integer beleg_nr wird zu String konvertiert."""
        entry = trail.log_action("TEST", {}, {}, {}, beleg_nr=42)
        assert entry["beleg_nr"] == "42"

    def test_decimal_values_serialized(self, trail):
        """Decimal-Werte werden korrekt serialisiert."""
        entry = trail.log_action(
            "TEST",
            {"betrag": Decimal("1234.56")},
            {},
            {},
        )
        # Eintrag wurde geschrieben und kann gelesen werden
        entries = trail.get_entries()
        assert len(entries) == 1

    def test_log_is_append_only(self, trail):
        """Mehrere Einträge werden angehängt, nicht überschrieben."""
        trail.log_action("FIRST", {}, {}, {})
        trail.log_action("SECOND", {}, {}, {})
        trail.log_action("THIRD", {}, {}, {})
        entries = trail.get_entries()
        assert len(entries) == 3

    def test_returns_written_entry(self, trail):
        """log_action gibt den geschriebenen Eintrag zurück."""
        result = trail.log_action("TEST", {"a": 1}, {"b": 2}, {"c": 3})
        assert isinstance(result, dict)
        assert result["action"] == "TEST"


# ---------------------------------------------------------------------------
# Tests: get_entries
# ---------------------------------------------------------------------------


class TestGetEntries:
    def test_empty_log(self, trail):
        """Leeres Log ergibt leere Liste."""
        entries = trail.get_entries()
        assert entries == []

    def test_returns_all_entries(self, trail):
        """Gibt alle Einträge zurück wenn kein Filter gesetzt."""
        trail.log_action("A", {}, {}, {})
        trail.log_action("B", {}, {}, {})
        entries = trail.get_entries()
        assert len(entries) == 2

    def test_filter_von(self, trail):
        """Filtert Einträge nach Startzeitpunkt."""
        trail.log_action("OLD", {}, {}, {})
        entries_all = trail.get_entries()
        ts = entries_all[0]["timestamp"]
        # Alle Einträge ab diesem Zeitstempel
        entries = trail.get_entries(von=ts)
        assert len(entries) >= 1

    def test_filter_bis(self, trail):
        """Filtert Einträge nach Endzeitpunkt."""
        trail.log_action("A", {}, {}, {})
        # Bis weit in die Zukunft
        entries = trail.get_entries(bis="2099-12-31T23:59:59")
        assert len(entries) == 1

    def test_filter_excludes_future(self, trail):
        """Filter 'bis' in der Vergangenheit schliesst aktuelle Einträge aus."""
        trail.log_action("A", {}, {}, {})
        entries = trail.get_entries(bis="2000-01-01T00:00:00")
        assert len(entries) == 0

    def test_nonexistent_log_file(self, tmp_dir):
        """Nicht existierende Logdatei ergibt leere Liste."""
        trail = AuditTrail(log_dir=os.path.join(tmp_dir, "nonexistent"))
        entries = trail.get_entries()
        assert entries == []

    def test_entries_are_dicts(self, trail):
        """Einträge werden als dicts zurückgegeben."""
        trail.log_action("TEST", {}, {}, {})
        entries = trail.get_entries()
        assert isinstance(entries[0], dict)


# ---------------------------------------------------------------------------
# Tests: ensure_immutable
# ---------------------------------------------------------------------------


class TestEnsureImmutable:
    def test_empty_log_is_valid(self, trail):
        """Leeres Log ist valide."""
        assert trail.ensure_immutable() is True

    def test_single_entry_valid(self, trail):
        """Ein einzelner Eintrag ist valide."""
        trail.log_action("TEST", {}, {}, {})
        assert trail.ensure_immutable() is True

    def test_multiple_entries_valid(self, trail):
        """Mehrere korrekte Einträge sind valide."""
        trail.log_action("FIRST", {"a": 1}, {}, {})
        trail.log_action("SECOND", {"b": 2}, {}, {})
        trail.log_action("THIRD", {"c": 3}, {}, {})
        assert trail.ensure_immutable() is True

    def test_tampered_entry_detected(self, trail, tmp_dir):
        """Manipulation eines Eintrags wird erkannt."""
        trail.log_action("ORIGINAL", {"amount": 100}, {}, {})
        trail.log_action("SECOND", {}, {}, {})

        # Ersten Eintrag manipulieren
        log_path = Path(tmp_dir) / "audit.log"
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        entry = json.loads(lines[0])
        entry["input_data"]["amount"] = 999999  # Manipulation
        lines[0] = json.dumps(entry, sort_keys=True)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        assert trail.ensure_immutable() is False

    def test_deleted_entry_detected(self, trail, tmp_dir):
        """Löschen eines Eintrags bricht die Hash-Kette."""
        trail.log_action("FIRST", {}, {}, {})
        trail.log_action("SECOND", {}, {}, {})
        trail.log_action("THIRD", {}, {}, {})

        # Zweiten Eintrag löschen
        log_path = Path(tmp_dir) / "audit.log"
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        del lines[1]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        assert trail.ensure_immutable() is False

    def test_nonexistent_log_valid(self, tmp_dir):
        """Nicht existierende Logdatei ist valide (nichts zu prüfen)."""
        trail = AuditTrail(log_dir=os.path.join(tmp_dir, "empty"))
        assert trail.ensure_immutable() is True

    def test_corrupted_json_detected(self, trail, tmp_dir):
        """Korruptes JSON in der Logdatei wird erkannt."""
        trail.log_action("TEST", {}, {}, {})
        log_path = Path(tmp_dir) / "audit.log"
        log_path.write_text("this is not json\n", encoding="utf-8")
        assert trail.ensure_immutable() is False

    def test_hash_chain_integrity(self, trail):
        """Hash-Kette über 5 Einträge bleibt intakt."""
        for i in range(5):
            trail.log_action(f"ACTION_{i}", {"step": i}, {}, {})
        assert trail.ensure_immutable() is True

    def test_swapped_entries_detected(self, trail, tmp_dir):
        """Vertauschte Einträge brechen die Hash-Kette."""
        trail.log_action("FIRST", {}, {}, {})
        trail.log_action("SECOND", {}, {}, {})

        log_path = Path(tmp_dir) / "audit.log"
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        # Reihenfolge vertauschen
        lines[0], lines[1] = lines[1], lines[0]
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        assert trail.ensure_immutable() is False


# ---------------------------------------------------------------------------
# Tests: _DecimalEncoder
# ---------------------------------------------------------------------------


class TestDecimalEncoder:
    def test_decimal_in_log(self, trail):
        """Decimal-Werte werden als Strings im JSON gespeichert."""
        trail.log_action("TEST", {"betrag": Decimal("42.50")}, {}, {})
        entries = trail.get_entries()
        # Der Wert sollte als String serialisiert sein
        assert entries[0]["input_data"]["betrag"] == "42.50"

    def test_nested_decimal(self, trail):
        """Verschachtelte Decimal-Werte werden korrekt serialisiert."""
        trail.log_action(
            "TEST",
            {"positionen": [{"betrag": Decimal("100.00")}, {"betrag": Decimal("200.00")}]},
            {},
            {},
        )
        entries = trail.get_entries()
        assert entries[0]["input_data"]["positionen"][0]["betrag"] == "100.00"
