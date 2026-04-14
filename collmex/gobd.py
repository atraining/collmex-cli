"""GoBD-konformer Audit Trail.

Protokolliert alle Buchungsaktionen als unveränderbare JSON-Logeinträge.
Jeder Eintrag erhält einen SHA-256-Hash zur Integritätsprüfung.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class _DecimalEncoder(json.JSONEncoder):
    """JSON-Encoder der Decimal-Werte als Strings serialisiert."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


class AuditTrail:
    """GoBD-konformer Audit Trail.

    Schreibt JSON-Zeilen (JSON Lines / JSONL) in eine Logdatei.
    Jeder Eintrag enthält einen SHA-256-Hash über den vorherigen
    Eintrag, sodass nachträgliche Manipulation erkennbar wird
    (einfache Hash-Kette).

    Attributes:
        log_dir: Verzeichnis für die Audit-Logdatei.
        log_file: Pfad zur audit.log Datei.
    """

    def __init__(self, log_dir: str = ".collmex") -> None:
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / "audit.log"
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Erstellt das Log-Verzeichnis falls es nicht existiert."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_last_hash(self) -> str:
        """Liest den Hash des letzten Eintrags oder gibt den Genesis-Hash zurück."""
        if not self.log_file.exists():
            return "0" * 64  # Genesis-Hash

        last_line = ""
        try:
            with open(self.log_file, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        last_line = stripped
        except OSError:
            return "0" * 64

        if not last_line:
            return "0" * 64

        try:
            entry = json.loads(last_line)
            return entry.get("hash", "0" * 64)
        except (json.JSONDecodeError, KeyError):
            return "0" * 64

    @staticmethod
    def _compute_hash(data: str) -> str:
        """Berechnet SHA-256 Hash einer Zeichenkette."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Öffentliche Methoden
    # ------------------------------------------------------------------

    def log_action(
        self,
        action: str,
        input_data: Any,
        request_data: Any,
        response_data: Any,
        beleg_nr: str | int | None = None,
        validierung: Any = None,
    ) -> dict:
        """Protokolliert eine Aktion im Audit Trail.

        Schreibt einen JSON-Eintrag als neue Zeile in die audit.log.
        Der Eintrag enthält einen Hash des vorherigen Eintrags
        für die Integritätskette.

        Args:
            action: Art der Aktion (z.B. "BUCHUNG", "STORNO", "VALIDIERUNG").
            input_data: Eingabedaten (z.B. Belegdaten, Benutzeranweisung).
            request_data: An die API gesendete Daten.
            response_data: Von der API empfangene Antwort.
            beleg_nr: Optionale Belegnummer.
            validierung: Optionale Validierungsergebnisse.

        Returns:
            Der geschriebene Audit-Eintrag als dict.
        """
        prev_hash = self._get_last_hash()

        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "beleg_nr": str(beleg_nr) if beleg_nr is not None else None,
            "input_data": input_data,
            "request_data": request_data,
            "response_data": response_data,
            "validierung": validierung,
            "prev_hash": prev_hash,
        }

        # Hash berechnen über den gesamten Eintrag (ohne das hash-Feld selbst)
        entry_json = json.dumps(entry, cls=_DecimalEncoder, sort_keys=True)
        entry["hash"] = self._compute_hash(entry_json)

        # Als JSON-Zeile schreiben (append-only)
        self._ensure_dir()
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, cls=_DecimalEncoder, sort_keys=True) + "\n")

        logger.info(
            "Audit: %s beleg_nr=%s hash=%s",
            action,
            beleg_nr,
            entry["hash"][:16] + "...",
        )

        return entry

    def get_entries(
        self,
        von: str | None = None,
        bis: str | None = None,
    ) -> list[dict]:
        """Liest und filtert Audit-Einträge.

        Args:
            von: ISO-Timestamp ab dem gefiltert wird (inklusive).
                 z.B. "2026-01-01T00:00:00"
            bis: ISO-Timestamp bis zu dem gefiltert wird (inklusive).
                 z.B. "2026-03-31T23:59:59"

        Returns:
            Liste der Audit-Einträge als dicts,
            gefiltert und chronologisch sortiert.
        """
        if not self.log_file.exists():
            return []

        entries: list[dict] = []
        try:
            with open(self.log_file, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        entry = json.loads(stripped)
                    except json.JSONDecodeError:
                        logger.warning("Ungültige Zeile in audit.log: %s", stripped[:80])
                        continue

                    ts = entry.get("timestamp", "")

                    if von and ts < von:
                        continue
                    if bis and ts > bis:
                        continue

                    entries.append(entry)
        except OSError as exc:
            logger.error("Fehler beim Lesen von audit.log: %s", exc)
            return []

        return entries

    def ensure_immutable(self) -> bool:
        """Prüft die Integrität der Audit-Log-Datei.

        Verifiziert die Hash-Kette: Jeder Eintrag referenziert den Hash
        des vorherigen Eintrags. Wenn ein Eintrag verändert oder
        entfernt wurde, bricht die Kette.

        Returns:
            True wenn die Hash-Kette intakt ist, False wenn manipuliert.

        Raises:
            Keine — gibt False zurück bei Problemen.
        """
        if not self.log_file.exists():
            # Kein Log = keine Manipulation
            return True

        entries: list[dict] = []
        try:
            with open(self.log_file, encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        entries.append(json.loads(stripped))
                    except json.JSONDecodeError:
                        logger.error("Ungültige JSON-Zeile in audit.log")
                        return False
        except OSError as exc:
            logger.error("Fehler beim Lesen von audit.log: %s", exc)
            return False

        if not entries:
            return True

        expected_prev_hash = "0" * 64  # Genesis-Hash

        for i, entry in enumerate(entries):
            # Prüfen: prev_hash stimmt mit erwartetem überein
            actual_prev = entry.get("prev_hash", "")
            if actual_prev != expected_prev_hash:
                logger.error(
                    "Hash-Kette gebrochen bei Eintrag %d: erwartet prev_hash=%s, gefunden=%s",
                    i,
                    expected_prev_hash[:16] + "...",
                    actual_prev[:16] + "...",
                )
                return False

            # Hash des aktuellen Eintrags verifizieren
            stored_hash = entry.get("hash", "")
            # Eintrag ohne hash-Feld rekonstruieren
            entry_without_hash = {k: v for k, v in entry.items() if k != "hash"}
            entry_json = json.dumps(entry_without_hash, cls=_DecimalEncoder, sort_keys=True)
            computed_hash = self._compute_hash(entry_json)

            if stored_hash != computed_hash:
                logger.error(
                    "Hash-Verifikation fehlgeschlagen bei Eintrag %d: gespeichert=%s, berechnet=%s",
                    i,
                    stored_hash[:16] + "...",
                    computed_hash[:16] + "...",
                )
                return False

            expected_prev_hash = stored_hash

        logger.info("Audit-Log Integrität OK: %d Einträge verifiziert.", len(entries))
        return True
