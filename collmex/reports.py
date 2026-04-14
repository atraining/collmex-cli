"""Report-Module für BWA, SuSa, Offene Posten und Säumige Kunden.

Berechnet kaufmännische Auswertungen aus Collmex-API-Daten.
Alle Geldbeträge verwenden Decimal für exakte Arithmetik.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from collmex.api import CollmexClient, parse_amount

# ---------------------------------------------------------------------------
# BWA Kontenbereiche (SKR03)
# ---------------------------------------------------------------------------

BWA_BEREICHE: dict[str, tuple[int, int]] = {
    "umsatzerlöse": (8100, 8700),
    "personalkosten": (4100, 4199),
    "raumkosten": (4200, 4299),
    "betriebskosten": (4300, 4499),
    "kfz_kosten": (4500, 4599),
    "reise_werbekosten": (4600, 4799),
    "abschreibungen": (4800, 4899),
    "sonstige_kosten": (4900, 4999),
}

BWA_BEZEICHNUNGEN: dict[str, str] = {
    "umsatzerlöse": "Umsatzerlöse",
    "personalkosten": "Personalkosten",
    "raumkosten": "Raumkosten",
    "betriebskosten": "Betriebskosten",
    "kfz_kosten": "Kfz-Kosten",
    "reise_werbekosten": "Reise- und Werbekosten",
    "abschreibungen": "Abschreibungen",
    "sonstige_kosten": "Sonstige Kosten",
}


# ---------------------------------------------------------------------------
# ACC_BAL-Feld-Indizes (verifiziert gegen echte API, 2026-03)
# ---------------------------------------------------------------------------
# ACC_BAL;Kontonummer;Bezeichnung;Saldo
# Indizes: 0=Satzart, 1=KontoNr, 2=Bezeichnung, 3=Saldo
# ACHTUNG: Kein Firma-Feld, kein Soll/Haben getrennt, kein Anfangsbestand.
# Die Collmex-API liefert nur 4 Felder pro ACC_BAL-Zeile.

_IDX_KONTO_NR = 1
_IDX_BEZEICHNUNG = 2
_IDX_SALDO = 3

# OPEN_ITEM Feld-Indizes (verifiziert gegen echte API, 2026-03)
# Reihenfolge: OPEN_ITEM;Firma;Jahr;Periode;PosNr;KontoNr;Name;
#              ;;BelegNr;Datum;Zahlungsbedingung;Fällig;;;
#              ;Bezahlt;Ursprung;Skonto;OffenerBetrag
_OP_IDX_KONTO_NR = 5
_OP_IDX_NAME = 6
_OP_IDX_BELEG_NR = 9
_OP_IDX_DATUM = 10
_OP_IDX_FAELLIG = 12
_OP_IDX_BETRAG = 19  # Offener Betrag (nicht Ursprungsbetrag)


def _safe_field(row: list[str], idx: int, default: str = "") -> str:
    """Gibt ein Feld zurück oder den Defaultwert bei fehlendem Index."""
    if idx < len(row):
        return row[idx]
    return default


def _ist_debitor(konto_nr: int) -> bool:
    """Prüft ob ein Konto ein Debitorenkonto (Forderungen/Kunden) ist.

    Collmex Personenkonten: 10000-69999 = Debitoren, 70000+ = Kreditoren.
    SKR03 Sachkonten: 1000-1399 = Forderungen (Debitor-nah).
    """
    if 10000 <= konto_nr < 70000:
        return True
    if 1000 <= konto_nr < 1400:
        return True
    return False


def _parse_date(datestr: str) -> date | None:
    """Parst ein Collmex-Datum (YYYYMMDD) in ein date-Objekt."""
    datestr = datestr.strip()
    if not datestr or len(datestr) != 8:
        return None
    try:
        return datetime.strptime(datestr, "%Y%m%d").date()
    except ValueError:
        return None


class ReportsEngine:
    """Erzeugt kaufmännische Auswertungen aus Collmex-Kontensalden.

    Args:
        api_client: Ein initialisierter CollmexClient.
    """

    def __init__(self, api_client: CollmexClient) -> None:
        self.client = api_client

    # ------------------------------------------------------------------
    # BWA — Betriebswirtschaftliche Auswertung
    # ------------------------------------------------------------------

    def bwa(self, jahr: int, monat: int) -> dict:
        """Berechnet eine BWA aus ACCBAL_GET-Daten.

        Struktur:
            1. Umsatzerlöse (8100-8700)
            2. - Personalkosten (4100-4199)
            3. - Raumkosten (4200-4299)
            4. - Betriebskosten (4300-4499)
            5. - Kfz-Kosten (4500-4599)
            6. - Reise-/Werbekosten (4600-4799)
            7. - Abschreibungen (4800-4899)
            8. - Sonstige Kosten (4900-4999)
            9. = Betriebsergebnis

        Args:
            jahr: Geschäftsjahr (z.B. 2026).
            monat: Buchungsperiode (1-12).

        Returns:
            dict mit Schlüssel für jede Position, 'summe_kosten',
            'betriebsergebnis', und 'positionen' (geordnete Liste).
        """
        rows = self.client.get_balances(jahr, monat)
        return self._berechne_bwa(rows, jahr=jahr, monat=monat)

    def _berechne_bwa(
        self,
        rows: list[list[str]],
        *,
        jahr: int = 0,
        monat: int = 0,
    ) -> dict:
        """Interne BWA-Berechnung aus ACCBAL-Zeilen."""
        # Konten in dict sammeln: konto_nr -> saldo
        konten: dict[int, Decimal] = {}
        for row in rows:
            konto_str = _safe_field(row, _IDX_KONTO_NR)
            saldo_str = _safe_field(row, _IDX_SALDO, "0")
            if not konto_str:
                continue
            try:
                konto_nr = int(konto_str)
            except ValueError:
                continue
            konten[konto_nr] = parse_amount(saldo_str)

        # Bereichssummen berechnen
        positionen: dict[str, Decimal] = {}
        for bereich, (von, bis) in BWA_BEREICHE.items():
            summe = Decimal("0")
            for konto_nr, saldo in konten.items():
                if von <= konto_nr <= bis:
                    summe += saldo
            positionen[bereich] = summe

        # Erlöse als positive Zahl (Ertragskonten haben Haben-Saldo,
        # der in Collmex negativ dargestellt sein kann — wir nehmen abs)
        erlöse = abs(positionen.get("umsatzerlöse", Decimal("0")))

        # Kosten summieren (Aufwandskonten)
        kosten_keys = [
            "personalkosten",
            "raumkosten",
            "betriebskosten",
            "kfz_kosten",
            "reise_werbekosten",
            "abschreibungen",
            "sonstige_kosten",
        ]
        summe_kosten = sum(abs(positionen.get(k, Decimal("0"))) for k in kosten_keys)

        betriebsergebnis = erlöse - summe_kosten

        result = {
            "jahr": jahr,
            "monat": monat,
            "umsatzerlöse": erlöse,
        }

        for key in kosten_keys:
            result[key] = abs(positionen.get(key, Decimal("0")))

        result["summe_kosten"] = summe_kosten
        result["betriebsergebnis"] = betriebsergebnis

        # Geordnete Liste für Anzeige
        result["positionen"] = (
            [
                {"bezeichnung": BWA_BEZEICHNUNGEN["umsatzerlöse"], "betrag": erlöse},
            ]
            + [{"bezeichnung": BWA_BEZEICHNUNGEN[k], "betrag": result[k]} for k in kosten_keys]
            + [
                {"bezeichnung": "Summe Kosten", "betrag": summe_kosten},
                {"bezeichnung": "Betriebsergebnis", "betrag": betriebsergebnis},
            ]
        )

        return result

    # ------------------------------------------------------------------
    # SuSa — Summen- und Saldenliste
    # ------------------------------------------------------------------

    def susa(self, jahr: int, monat: int) -> list[dict]:
        """Summen- und Saldenliste: alle bebuchten Konten.

        Args:
            jahr: Geschäftsjahr.
            monat: Buchungsperiode (1-12).

        Returns:
            Liste von dicts mit: konto_nr, bezeichnung,
            anfangsbestand, soll_umsatz, haben_umsatz, saldo.
        """
        rows = self.client.get_balances(jahr, monat)
        return self._berechne_susa(rows)

    def _berechne_susa(self, rows: list[list[str]]) -> list[dict]:
        """Interne SuSa-Berechnung aus ACCBAL-Zeilen."""
        ergebnis: list[dict] = []
        for row in rows:
            konto_str = _safe_field(row, _IDX_KONTO_NR)
            if not konto_str:
                continue
            try:
                konto_nr = int(konto_str)
            except ValueError:
                continue

            bezeichnung = _safe_field(row, _IDX_BEZEICHNUNG)
            saldo = parse_amount(_safe_field(row, _IDX_SALDO, "0"))
            # ACC_BAL liefert nur den Saldo, nicht Soll/Haben einzeln
            anfangsbestand = Decimal("0")
            soll_umsatz = Decimal("0")
            haben_umsatz = Decimal("0")

            ergebnis.append(
                {
                    "konto_nr": konto_nr,
                    "bezeichnung": bezeichnung,
                    "anfangsbestand": anfangsbestand,
                    "soll_umsatz": soll_umsatz,
                    "haben_umsatz": haben_umsatz,
                    "saldo": saldo,
                }
            )

        ergebnis.sort(key=lambda x: x["konto_nr"])
        return ergebnis

    # ------------------------------------------------------------------
    # Offene Posten
    # ------------------------------------------------------------------

    def op_liste(self) -> dict:
        """Offene Posten getrennt nach Debitoren/Kreditoren mit Altersstruktur.

        Returns:
            dict mit:
              - 'debitoren': Liste offener Debitoren-Posten
              - 'kreditoren': Liste offener Kreditoren-Posten
              - 'summe_debitoren': Gesamtsumme Debitoren
              - 'summe_kreditoren': Gesamtsumme Kreditoren
              - 'altersstruktur': dict mit Altersgruppen
        """
        rows = self.client.get_open_items()
        return self._berechne_op(rows)

    def _berechne_op(self, rows: list[list[str]]) -> dict:
        """Interne OP-Berechnung aus OPEN_ITEMS-Zeilen."""
        heute = date.today()
        debitoren: list[dict] = []
        kreditoren: list[dict] = []

        for row in rows:
            konto_str = _safe_field(row, _OP_IDX_KONTO_NR)
            if not konto_str:
                continue
            try:
                konto_nr = int(konto_str)
            except ValueError:
                continue

            name = _safe_field(row, _OP_IDX_NAME)
            beleg_nr = _safe_field(row, _OP_IDX_BELEG_NR)
            datum_str = _safe_field(row, _OP_IDX_DATUM)
            fällig_str = _safe_field(row, _OP_IDX_FAELLIG)
            betrag = parse_amount(_safe_field(row, _OP_IDX_BETRAG, "0"))

            fällig = _parse_date(fällig_str)
            tage_ueberfällig = 0
            if fällig and fällig < heute:
                tage_ueberfällig = (heute - fällig).days

            eintrag = {
                "konto_nr": konto_nr,
                "name": name,
                "beleg_nr": beleg_nr,
                "datum": datum_str,
                "fällig": fällig_str,
                "betrag": betrag,
                "tage_ueberfällig": tage_ueberfällig,
            }

            # Debitoren vs. Kreditoren:
            # - Personenkonten: 10000-69999 = Debitoren, 70000+ = Kreditoren
            # - SKR03: 1000-1399 = Debitoren-Sammelkonto, 1600-1699 = Kreditoren
            if _ist_debitor(konto_nr):
                eintrag["typ"] = "debitor"
                debitoren.append(eintrag)
            else:
                eintrag["typ"] = "kreditor"
                kreditoren.append(eintrag)

        summe_debitoren = sum(d["betrag"] for d in debitoren)
        summe_kreditoren = sum(k["betrag"] for k in kreditoren)

        # Altersstruktur der Debitoren
        altersstruktur = self._altersstruktur(debitoren)

        return {
            "debitoren": debitoren,
            "kreditoren": kreditoren,
            "summe_debitoren": summe_debitoren,
            "summe_kreditoren": summe_kreditoren,
            "altersstruktur": altersstruktur,
        }

    def _altersstruktur(self, posten: list[dict]) -> dict:
        """Berechnet Altersstruktur der offenen Posten.

        Returns:
            dict mit Altersgruppen und Summen:
            - 'aktuell': 0-30 Tage
            - 'überfällig_30': 31-60 Tage
            - 'überfällig_60': 61-90 Tage
            - 'überfällig_90': >90 Tage
        """
        gruppen: dict[str, Decimal] = {
            "aktuell": Decimal("0"),
            "überfällig_30": Decimal("0"),
            "überfällig_60": Decimal("0"),
            "überfällig_90": Decimal("0"),
        }
        for p in posten:
            tage = p.get("tage_ueberfällig", 0)
            betrag = p.get("betrag", Decimal("0"))
            if tage <= 30:
                gruppen["aktuell"] += betrag
            elif tage <= 60:
                gruppen["überfällig_30"] += betrag
            elif tage <= 90:
                gruppen["überfällig_60"] += betrag
            else:
                gruppen["überfällig_90"] += betrag
        return gruppen

    # ------------------------------------------------------------------
    # Säumige Kunden
    # ------------------------------------------------------------------

    def säumige_kunden(self) -> list[dict]:
        """Kunden mit überfälligen Rechnungen, sortiert nach Tage überfällig.

        Returns:
            Liste von dicts mit: name, beleg_nr, betrag, fällig,
            tage_ueberfällig, mahnstufe — absteigend sortiert nach
            tage_ueberfällig.
        """
        op = self.op_liste()
        säumige: list[dict] = []

        for posten in op["debitoren"]:
            if posten["tage_ueberfällig"] > 0:
                tage = posten["tage_ueberfällig"]
                mahnstufe = self._mahnstufe(tage)
                säumige.append(
                    {
                        "name": posten["name"],
                        "beleg_nr": posten["beleg_nr"],
                        "betrag": posten["betrag"],
                        "fällig": posten["fällig"],
                        "tage_ueberfällig": tage,
                        "mahnstufe": mahnstufe,
                    }
                )

        säumige.sort(key=lambda x: x["tage_ueberfällig"], reverse=True)
        return säumige

    @staticmethod
    def _mahnstufe(tage: int) -> int:
        """Berechnet Mahnstufe basierend auf Tagen überfällig.

        0 = nicht/kaum überfällig (1-30 Tage)
        1 = 31-60 Tage
        2 = 61-90 Tage
        3 = >90 Tage
        """
        if tage <= 30:
            return 0
        if tage <= 60:
            return 1
        if tage <= 90:
            return 2
        return 3
