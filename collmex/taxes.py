"""Steuer-Modul.

Berechnet UStVA-Werte (Umsatzsteuer-Voranmeldung) auf Basis
der Kontensalden aus der Collmex-API.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from collmex.api import CollmexClient, CollmexError, parse_amount

logger = logging.getLogger(__name__)


class TaxEngine:
    """Steuer-Engine: UStVA-Berechnung aus Collmex-Kontensalden.

    Liest die relevanten Konten via ACCBAL_GET und berechnet
    die Kennzahlen der Umsatzsteuer-Voranmeldung.
    """

    def __init__(self, api_client: CollmexClient) -> None:
        self.api = api_client

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------

    def _get_saldo(self, konto: int, jahr: int, monat: int) -> Decimal:
        """Liest den Saldo eines Kontos fuer eine bestimmte Periode.

        Gibt den Nettobetrag zurueck:
        - Aktivkonten/Aufwandskonten: Soll - Haben (positiv = Soll-Saldo)
        - Passivkonten/Ertragskonten: Haben - Soll (positiv = Haben-Saldo)

        Fuer die UStVA-Berechnung wird der absolute Saldo benoetigt,
        die Vorzeichen-Interpretation erfolgt in ustva().

        Gibt Decimal(0) zurueck wenn das Konto in Collmex nicht existiert
        (z.B. Konto 1580 Vorsteuer §13b, wenn nicht angelegt).
        """
        try:
            rows = self.api.get_balances(jahr, monat, konto)
        except CollmexError as exc:
            # Konto existiert nicht in Collmex -> Saldo ist 0
            logger.debug("Konto %d nicht vorhanden, Saldo = 0: %s", konto, exc)
            return Decimal("0")
        if not rows:
            return Decimal("0")

        # ACC_BAL-Format: [Satzart, Kontonummer, Bezeichnung, Saldo]
        total = Decimal("0")
        for row in rows:
            if len(row) >= 4:
                saldo = parse_amount(row[3]) if row[3] else Decimal("0")
                total += saldo
        return total

    # ------------------------------------------------------------------
    # UStVA
    # ------------------------------------------------------------------

    def ustva(self, jahr: int, monat: int) -> dict:
        """Berechnet die Werte fuer die Umsatzsteuer-Voranmeldung.

        Liest die relevanten SKR03-Konten und berechnet die UStVA-Kennzahlen.

        Args:
            jahr: Geschaeftsjahr (z.B. 2026).
            monat: Voranmeldungszeitraum (1-12).

        Returns:
            dict mit UStVA-Kennzahlen:
                - kz81: Steuerpflichtige Umsaetze 19% (Netto, Konto 8400)
                - kz86: Steuerpflichtige Umsaetze 7% (Netto, Konto 8300)
                - ust_19: USt auf Umsaetze 19% (Konto 1776)
                - ust_7: USt auf Umsaetze 7% (Konto 1771)
                - ust_zahllast: Gesamte USt-Zahllast (1776 + 1771)
                - kz66: Vorsteuer 19% (Konto 1576)
                - kz61: Vorsteuer 7% (Konto 1571)
                - kz67: Vorsteuer §13b (Konto 1580)
                - vst_abzug: Gesamter Vorsteuerabzug (1576 + 1571 + 1580)
                - vorauszahlung: Zahllast - Abzug
                - kz83: Verbleibende USt-Vorauszahlung (= vorauszahlung)
                - jahr: Geschaeftsjahr
                - monat: Voranmeldungszeitraum
        """
        # --- Umsaetze (Ertragskonten: Haben-Saldo, daher negativ) ---
        # Konto 8400: Erloese 19% USt
        raw_8400 = self._get_saldo(8400, jahr, monat)
        kz81 = abs(raw_8400)

        # Konto 8300: Erloese 7% USt
        raw_8300 = self._get_saldo(8300, jahr, monat)
        kz86 = abs(raw_8300)

        # --- Umsatzsteuer (Passivkonten: Haben-Saldo) ---
        # Konto 1776: Umsatzsteuer 19%
        raw_1776 = self._get_saldo(1776, jahr, monat)
        ust_19 = abs(raw_1776)

        # Konto 1771: Umsatzsteuer 7%
        raw_1771 = self._get_saldo(1771, jahr, monat)
        ust_7 = abs(raw_1771)

        ust_zahllast = ust_19 + ust_7

        # --- Vorsteuer (Aktivkonten: Soll-Saldo) ---
        # Konto 1576: Vorsteuer 19%
        raw_1576 = self._get_saldo(1576, jahr, monat)
        kz66 = abs(raw_1576)

        # Konto 1571: Vorsteuer 7%
        raw_1571 = self._get_saldo(1571, jahr, monat)
        kz61 = abs(raw_1571)

        # Konto 1580: Vorsteuer nach §13b UStG
        raw_1580 = self._get_saldo(1580, jahr, monat)
        kz67 = abs(raw_1580)

        vst_abzug = kz66 + kz61 + kz67

        # --- Vorauszahlung ---
        vorauszahlung = ust_zahllast - vst_abzug
        kz83 = vorauszahlung

        return {
            "kz81": kz81,
            "kz86": kz86,
            "ust_19": ust_19,
            "ust_7": ust_7,
            "ust_zahllast": ust_zahllast,
            "kz66": kz66,
            "kz61": kz61,
            "kz67": kz67,
            "vst_abzug": vst_abzug,
            "vorauszahlung": vorauszahlung,
            "kz83": kz83,
            "jahr": jahr,
            "monat": monat,
        }
