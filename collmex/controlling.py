"""Controlling-Modul.

Berechnet KPIs, Liquiditaetsvorschau und Soll-Ist-Vergleiche
auf Basis der Collmex-API-Daten (ACCBAL_GET, OPEN_ITEMS_GET).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from collmex.api import CollmexClient, parse_amount

logger = logging.getLogger(__name__)


class ControllingEngine:
    """Controlling-Engine fuer KPIs, Liquiditaetsplanung und Soll-Ist-Vergleich.

    Arbeitet ausschliesslich mit Daten aus der Collmex-API.
    Alle Geldbetraege als Decimal fuer kaufmaennische Exaktheit.
    """

    def __init__(self, api_client: CollmexClient) -> None:
        self.api = api_client

    # ------------------------------------------------------------------
    # Hilfsfunktionen
    # ------------------------------------------------------------------

    def _get_balance(self, account: int, year: int, period: int) -> Decimal:
        """Liest den Saldo eines einzelnen Kontos via ACCBAL_GET.

        Gibt Decimal(0) zurueck wenn das Konto keine Daten hat.
        """
        rows = self.api.get_balances(year, period, account)
        if not rows:
            return Decimal("0")
        # ACC_BAL-Format: [Satzart, Kontonummer, Bezeichnung, Saldo]
        total = Decimal("0")
        for row in rows:
            if len(row) >= 4:
                saldo = parse_amount(row[3]) if row[3] else Decimal("0")
                total += saldo
        return total

    def _get_account_range_total(
        self,
        start: int,
        end: int,
        year: int,
        period: int,
    ) -> Decimal:
        """Summiert Salden aller Konten in einem Nummernbereich.

        Ruft ACCBAL_GET ohne Kontofilter ab und filtert clientseitig.
        """
        # ACC_BAL-Format: [Satzart, Kontonummer, Bezeichnung, Saldo]
        rows = self.api.get_balances(year, period)
        total = Decimal("0")
        for row in rows:
            if len(row) >= 4:
                try:
                    konto_nr = int(row[1])
                except (ValueError, IndexError):
                    continue
                if start <= konto_nr <= end:
                    saldo = parse_amount(row[3]) if row[3] else Decimal("0")
                    total += saldo
        return total

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def dashboard(self) -> dict:
        """Berechnet die wichtigsten KPIs als Dictionary.

        Returns:
            dict mit Schluessel:
                - kontostand: Bankbestand (Konto 1200)
                - offene_forderungen: Forderungen a.LL. (Konto 1400)
                - offene_verbindlichkeiten: Verbindlichkeiten a.LL. (Konto 1600)
                - umsatz_monat: Erloese 8100-8700 aktueller Monat
                - kosten_monat: Aufwendungen 4000-4999 aktueller Monat
                - ergebnis_monat: umsatz - kosten
                - liquiditaet_1: (Bank + Kasse) / kurzfr. Verbindlichkeiten
                - dso: (Forderungen / Umsatz) * 365 (Days Sales Outstanding)
        """
        heute = date.today()
        jahr = heute.year
        monat = heute.month

        # Einzelkonten-Salden
        kontostand = self._get_balance(1200, jahr, monat)
        kasse = self._get_balance(1000, jahr, monat)
        offene_forderungen = self._get_balance(1400, jahr, monat)
        # Verbindlichkeiten: Passivkonto, Saldo Haben - Soll = positiv
        offene_verbindlichkeiten = abs(self._get_balance(1600, jahr, monat))

        # Erloese: 8100-8700 (Ertragskonten: Haben-Saldo ist positiv)
        umsatz_raw = self._get_account_range_total(8100, 8700, jahr, monat)
        # Ertragskonten haben Haben-Saldo, daher Soll-Haben ist negativ
        umsatz_monat = abs(umsatz_raw)

        # Kosten: 4000-4999 (Aufwandskonten: Soll-Saldo ist positiv)
        kosten_monat = self._get_account_range_total(4000, 4999, jahr, monat)

        # Ergebnis
        ergebnis_monat = umsatz_monat - kosten_monat

        # Liquiditaet 1. Grades: (Bank + Kasse) / kurzfr. Verbindl.
        if offene_verbindlichkeiten > Decimal("0"):
            liquiditaet_1 = ((kontostand + kasse) / offene_verbindlichkeiten).quantize(
                Decimal("0.01")
            )
        else:
            liquiditaet_1 = Decimal("0")

        # DSO: Days Sales Outstanding = (Forderungen / Umsatz) * 365
        if umsatz_monat > Decimal("0"):
            # Jahresumsatz schaetzen: Monatsumsatz * 12
            jahresumsatz_schaetzung = umsatz_monat * 12
            dso = ((offene_forderungen / jahresumsatz_schaetzung) * 365).quantize(Decimal("0.1"))
        else:
            dso = Decimal("0")

        return {
            "kontostand": kontostand,
            "offene_forderungen": offene_forderungen,
            "offene_verbindlichkeiten": offene_verbindlichkeiten,
            "umsatz_monat": umsatz_monat,
            "kosten_monat": kosten_monat,
            "ergebnis_monat": ergebnis_monat,
            "liquiditaet_1": liquiditaet_1,
            "dso": dso,
        }

    # ------------------------------------------------------------------
    # Liquiditaetsvorschau
    # ------------------------------------------------------------------

    def liquiditaetsvorschau(self, wochen: int = 13) -> list[dict]:
        """Erstellt eine woechentliche Liquiditaetsvorschau.

        Basiert auf offenen Posten (OPEN_ITEMS_GET) und verteilt
        erwartete Ein-/Ausgaenge nach Faelligkeitsdatum auf Kalenderwochen.

        Args:
            wochen: Anzahl Wochen in die Zukunft (Standard: 13 = 1 Quartal).

        Returns:
            Liste von dicts pro Woche:
                - woche: ISO-Kalenderwoche (z.B. "2026-W10")
                - start: Montag der Woche (date)
                - erwartete_eingaenge: Decimal
                - erwartete_ausgaenge: Decimal
                - saldo: eingaenge - ausgaenge
        """
        heute = date.today()
        # Wochenanfaenge berechnen (Montag)
        montag = heute - timedelta(days=heute.weekday())
        wochen_liste: list[dict] = []

        for i in range(wochen):
            start = montag + timedelta(weeks=i)
            wochen_liste.append(
                {
                    "woche": f"{start.isocalendar()[0]}-W{start.isocalendar()[1]:02d}",
                    "start": start,
                    "erwartete_eingaenge": Decimal("0"),
                    "erwartete_ausgaenge": Decimal("0"),
                    "saldo": Decimal("0"),
                }
            )

        # Offene Posten laden
        rows = self.api.get_open_items()
        ende = montag + timedelta(weeks=wochen)

        # OPEN_ITEM Feld-Indizes (verifiziert gegen echte API, 2026-03)
        _IDX_KONTO = 5
        _IDX_FAELLIG = 12
        _IDX_BETRAG = 19  # Offener Betrag

        for row in rows:
            if len(row) <= _IDX_BETRAG:
                continue

            try:
                betrag_str = row[_IDX_BETRAG] if row[_IDX_BETRAG] else "0"
                betrag = parse_amount(betrag_str)
                faellig_str = row[_IDX_FAELLIG] if row[_IDX_FAELLIG] else ""
            except Exception:
                continue

            if not faellig_str or len(faellig_str) != 8:
                continue

            try:
                faellig = date(
                    int(faellig_str[:4]),
                    int(faellig_str[4:6]),
                    int(faellig_str[6:8]),
                )
            except ValueError:
                continue

            if faellig < montag or faellig >= ende:
                continue

            # Woche bestimmen
            delta_tage = (faellig - montag).days
            wochen_index = delta_tage // 7
            if 0 <= wochen_index < len(wochen_liste):
                konto_nr_str = row[_IDX_KONTO] if row[_IDX_KONTO] else ""
                try:
                    konto_nr = int(konto_nr_str)
                except ValueError:
                    konto_nr = 0

                # Debitoren (Personenkonten 10000-69999): Eingaenge
                # Kreditoren (Personenkonten 70000+): Ausgaenge
                if 10000 <= konto_nr < 70000:
                    wochen_liste[wochen_index]["erwartete_eingaenge"] += abs(betrag)
                elif konto_nr >= 70000:
                    wochen_liste[wochen_index]["erwartete_ausgaenge"] += abs(betrag)

        # Salden berechnen
        for w in wochen_liste:
            w["saldo"] = w["erwartete_eingaenge"] - w["erwartete_ausgaenge"]

        return wochen_liste

    # ------------------------------------------------------------------
    # Soll-Ist-Vergleich
    # ------------------------------------------------------------------

    def soll_ist(
        self,
        monat: int,
        jahr: int,
        budget: dict[int, Decimal],
    ) -> list[dict]:
        """Soll-Ist-Vergleich pro Konto.

        Args:
            monat: Buchungsperiode (1-12).
            jahr: Geschaeftsjahr.
            budget: Dictionary {Kontonummer: Budget-Betrag als Decimal}.

        Returns:
            Liste von dicts pro Konto:
                - konto: Kontonummer
                - budget: Soll-Betrag
                - ist: tatsaechlicher Saldo
                - abweichung: ist - budget
                - prozent: (ist / budget) * 100 (oder 0 wenn budget == 0)
                - ampel: "gruen" (<= 100%), "gelb" (101-120%), "rot" (> 120%)
        """
        ergebnis: list[dict] = []

        for konto_nr, budget_betrag in sorted(budget.items()):
            ist = abs(self._get_balance(konto_nr, jahr, monat))
            abweichung = ist - budget_betrag

            if budget_betrag > Decimal("0"):
                prozent = ((ist / budget_betrag) * 100).quantize(Decimal("0.1"))
            else:
                prozent = Decimal("0")

            # Ampel-Logik
            if prozent <= Decimal("100"):
                ampel = "gruen"
            elif prozent <= Decimal("120"):
                ampel = "gelb"
            else:
                ampel = "rot"

            ergebnis.append(
                {
                    "konto": konto_nr,
                    "budget": budget_betrag,
                    "ist": ist,
                    "abweichung": abweichung,
                    "prozent": prozent,
                    "ampel": ampel,
                }
            )

        return ergebnis
