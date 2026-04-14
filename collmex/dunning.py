"""Mahnwesen-Modul.

Analysiert offene Posten (Debitoren), berechnet Mahnstufen,
erstellt Altersstrukturanalysen und generiert Mahnvorschlaege.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from collmex.api import CollmexClient, parse_amount

logger = logging.getLogger(__name__)


class DunningEngine:
    """Mahnwesen-Engine: Ueberfaellige Posten, Altersstruktur, Mahnlaeufe.

    Arbeitet mit OPEN_ITEMS_GET aus der Collmex-API.
    """

    def __init__(self, api_client: CollmexClient) -> None:
        self.api = api_client

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(datum_str: str) -> date | None:
        """Parst ein Datum im Format YYYYMMDD zu einem date-Objekt."""
        if not datum_str or len(datum_str) != 8:
            return None
        try:
            return date(
                int(datum_str[:4]),
                int(datum_str[4:6]),
                int(datum_str[6:8]),
            )
        except ValueError:
            return None

    @staticmethod
    def _mahnstufe(tage_ueberfaellig: int) -> int:
        """Bestimmt die Mahnstufe basierend auf Tagen ueberfaellig.

        0 = nicht faellig oder 0-30 Tage
        1 = 31-60 Tage
        2 = 61-90 Tage
        3 = > 90 Tage
        """
        if tage_ueberfaellig <= 30:
            return 0
        if tage_ueberfaellig <= 60:
            return 1
        if tage_ueberfaellig <= 90:
            return 2
        return 3

    def _parse_open_items(self) -> list[dict]:
        """Laedt und parst alle offenen Posten aus Collmex.

        OPEN_ITEM Feld-Indizes (verifiziert gegen echte API, 2026-03):
        Index  0: Satzart (OPEN_ITEM)
        Index  1: Firma Nr
        Index  2: Geschaeftsjahr
        Index  3: Buchungsperiode
        Index  4: Positionsnummer
        Index  5: Kontonummer (Debitor/Kreditor)
        Index  6: Name (Kunde/Lieferant)
        Index  7-8: (leer)
        Index  9: Belegnummer
        Index 10: Belegdatum (YYYYMMDD)
        Index 11: Zahlungsbedingung
        Index 12: Faelligkeitsdatum (YYYYMMDD)
        Index 13-18: diverse Felder
        Index 19: Offener Betrag
        """
        rows = self.api.get_open_items()
        items: list[dict] = []
        heute = date.today()

        for row in rows:
            if len(row) < 20:
                continue

            try:
                konto_nr = int(row[5])
            except (ValueError, IndexError):
                continue

            # Nur Debitoren (Personenkonten 10000-69999)
            if not (10000 <= konto_nr < 70000):
                continue

            beleg_nr = row[9] if len(row) > 9 else ""
            datum_str = row[10] if len(row) > 10 else ""
            faellig_str = row[12] if len(row) > 12 else ""
            betrag_str = row[19] if len(row) > 19 else "0"
            kunde = row[6] if len(row) > 6 else ""
            kunde_name = kunde  # Name ist direkt in Feld 6

            datum = self._parse_date(datum_str)
            faellig = self._parse_date(faellig_str)

            if not datum or not faellig:
                continue

            try:
                betrag = parse_amount(betrag_str)
            except Exception:
                continue

            tage = (heute - faellig).days
            if tage < 0:
                tage = 0

            items.append(
                {
                    "kunde": kunde_name or kunde,
                    "kunde_nr": kunde,
                    "beleg_nr": beleg_nr,
                    "betrag": betrag,
                    "datum": datum_str,
                    "faellig": faellig_str,
                    "tage_ueberfaellig": tage,
                    "mahnstufe": self._mahnstufe(tage),
                }
            )

        return items

    # ------------------------------------------------------------------
    # Oeffentliche Methoden
    # ------------------------------------------------------------------

    def get_overdue_items(self) -> list[dict]:
        """Gibt alle ueberfaelligen Debitoren-Posten zurueck.

        Filtert auf offene Posten mit Faelligkeitsdatum in der Vergangenheit
        und mindestens 1 Tag ueberfaellig.

        Returns:
            Liste von dicts mit:
                - kunde: Kundenname oder -nummer
                - kunde_nr: Kundennummer
                - beleg_nr: Belegnummer
                - betrag: Decimal
                - datum: Belegdatum (YYYYMMDD)
                - faellig: Faelligkeitsdatum (YYYYMMDD)
                - tage_ueberfaellig: int
                - mahnstufe: int (0-3)
        """
        alle_items = self._parse_open_items()
        ueberfaellig = [item for item in alle_items if item["tage_ueberfaellig"] > 0]
        # Sortiert nach Tagen ueberfaellig (aelteste zuerst)
        ueberfaellig.sort(key=lambda x: x["tage_ueberfaellig"], reverse=True)
        return ueberfaellig

    def altersstruktur(self) -> dict:
        """Gruppiert offene Posten nach Mahnstufe mit Anzahl und Summen.

        Returns:
            dict mit Schluessel:
                - nicht_faellig: {"anzahl": N, "summe": Decimal}
                - stufe_1: {"anzahl": N, "summe": Decimal}
                - stufe_2: {"anzahl": N, "summe": Decimal}
                - stufe_3: {"anzahl": N, "summe": Decimal}
                - gesamt: {"anzahl": N, "summe": Decimal}
        """
        alle_items = self._parse_open_items()

        struktur = {
            "nicht_faellig": {"anzahl": 0, "summe": Decimal("0")},
            "stufe_1": {"anzahl": 0, "summe": Decimal("0")},
            "stufe_2": {"anzahl": 0, "summe": Decimal("0")},
            "stufe_3": {"anzahl": 0, "summe": Decimal("0")},
            "gesamt": {"anzahl": 0, "summe": Decimal("0")},
        }

        stufe_keys = {
            0: "nicht_faellig",
            1: "stufe_1",
            2: "stufe_2",
            3: "stufe_3",
        }

        for item in alle_items:
            stufe = item["mahnstufe"]
            key = stufe_keys.get(stufe, "stufe_3")
            struktur[key]["anzahl"] += 1
            struktur[key]["summe"] += item["betrag"]
            struktur["gesamt"]["anzahl"] += 1
            struktur["gesamt"]["summe"] += item["betrag"]

        return struktur

    def mahnlauf(self, stufe: int | None = None) -> list[dict]:
        """Generiert Mahnvorschlaege fuer ueberfaellige Posten.

        Args:
            stufe: Optional. Nur Mahnungen fuer diese Stufe erstellen.
                   None = alle ueberfaelligen Stufen (1, 2, 3).

        Returns:
            Liste von dicts pro Mahnvorschlag:
                - kunde: Kundenname/-nummer
                - kunde_nr: Kundennummer
                - beleg_nr: Belegnummer
                - betrag: Decimal
                - datum: Belegdatum
                - faellig: Faelligkeitsdatum
                - tage_ueberfaellig: int
                - mahnstufe: int
                - mahnaktion: str (Beschreibung der empfohlenen Aktion)
        """
        alle_items = self._parse_open_items()

        # Nur ueberfaellige Posten (mahnstufe >= 1)
        ueberfaellig = [item for item in alle_items if item["mahnstufe"] >= 1]

        # Optional nach Stufe filtern
        if stufe is not None:
            ueberfaellig = [item for item in ueberfaellig if item["mahnstufe"] == stufe]

        # Mahnaktionen zuweisen
        aktionen = {
            1: "Zahlungserinnerung versenden",
            2: "2. Mahnung mit Fristsetzung versenden",
            3: "Letzte Mahnung vor Inkasso / rechtliche Schritte pruefen",
        }

        vorschlaege: list[dict] = []
        for item in ueberfaellig:
            vorschlag = dict(item)
            vorschlag["mahnaktion"] = aktionen.get(
                item["mahnstufe"],
                "Individuell pruefen",
            )
            vorschlaege.append(vorschlag)

        # Sortiert: hoechste Mahnstufe zuerst, dann nach Betrag absteigend
        vorschlaege.sort(
            key=lambda x: (x["mahnstufe"], x["betrag"]),
            reverse=True,
        )

        return vorschlaege
