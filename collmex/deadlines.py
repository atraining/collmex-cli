"""Fristen-Modul.

Verwaltet steuerliche und buchhalterische Fristen einer deutschen GmbH.
Berechnet Faelligkeiten unter Beruecksichtigung von Wochenenden,
Feiertagen und der Schonfrist (3 Tage fuer Bankueberweisungen nach dem 10.).

Deutsche Steuerfristen (Auswahl):
- UStVA: 10. des Folgemonats (monatlich)
- Lohnsteueranmeldung: 10. des Folgemonats (monatlich)
- Sozialversicherung: Beitragsnachweis ~5. letzter Werktag,
  Zahlung ~3. letzter Werktag (monatlich)
- Gewerbesteuer-VZ: 15.02, 15.05, 15.08, 15.11 (quartalsweise)
- KSt-VZ: 10.03, 10.06, 10.09, 10.12 (quartalsweise)
- Jahresabschluss, Steuererklärung, Offenlegung (jaehrlich)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Kategorie(str, Enum):
    """Kategorie einer Frist."""

    STEUER = "steuer"
    BUCHHALTUNG = "buchhaltung"
    MELDUNG = "meldung"


class Prioritaet(str, Enum):
    """Prioritaet einer Frist.

    critical = Versaeumnis fuehrt zu Saumniszuschlaegen oder Bussgeldern
    high     = Versaeumnis fuehrt zu Nachteilen (z.B. Verspaetungszuschlag)
    medium   = Interne Frist ohne direkte Sanktion
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Deadline:
    """Eine steuerliche oder buchhalterische Frist.

    Attributes:
        name: Kurzbezeichnung der Frist (z.B. "UStVA").
        datum: Faelligkeitsdatum.
        kategorie: Steuer, Buchhaltung oder Meldung.
        beschreibung: Ausfuehrliche Erlaeuterung.
        wiederkehrend: True fuer monatliche/quartalsweise Fristen.
        prioritaet: critical / high / medium.
    """

    name: str
    datum: date
    kategorie: Kategorie
    beschreibung: str
    wiederkehrend: bool
    prioritaet: Prioritaet


# ---------------------------------------------------------------------------
# Hilfsfunktionen: Werktage und Schonfrist
# ---------------------------------------------------------------------------

# Deutsche gesetzliche Feiertage (bundesweit).
# Bewegliche Feiertage (Ostern etc.) werden pro Jahr berechnet.


def _ostersonntag(jahr: int) -> date:
    """Berechnet Ostersonntag nach dem Gauss'schen Algorithmus.

    Der Algorithmus bestimmt das Datum des Ostersonntags fuer ein
    gegebenes Jahr im gregorianischen Kalender.
    """
    a = jahr % 19
    b = jahr // 100
    c = jahr % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
    m = (a + 11 * h + 22 * l) // 451
    monat = (h + l - 7 * m + 114) // 31
    tag = ((h + l - 7 * m + 114) % 31) + 1
    return date(jahr, monat, tag)


def feiertage_deutschland(jahr: int) -> set[date]:
    """Gibt die bundesweiten gesetzlichen Feiertage fuer ein Jahr zurueck.

    Enthaelt nur bundeseinheitliche Feiertage, keine laenderspezifischen.
    Fuer die Fristenberechnung relevant: Wenn eine Frist auf einen
    Feiertag faellt, verschiebt sie sich auf den naechsten Werktag.
    """
    ostern = _ostersonntag(jahr)
    return {
        date(jahr, 1, 1),  # Neujahr
        ostern - timedelta(days=2),  # Karfreitag
        ostern + timedelta(days=1),  # Ostermontag
        date(jahr, 5, 1),  # Tag der Arbeit
        ostern + timedelta(days=39),  # Christi Himmelfahrt
        ostern + timedelta(days=50),  # Pfingstmontag
        date(jahr, 10, 3),  # Tag der Deutschen Einheit
        date(jahr, 12, 25),  # 1. Weihnachtstag
        date(jahr, 12, 26),  # 2. Weihnachtstag
    }


def ist_werktag(tag: date, feiertage: set[date] | None = None) -> bool:
    """Prueft ob ein Datum ein Werktag ist (Mo-Fr, kein Feiertag).

    Args:
        tag: Das zu pruefende Datum.
        feiertage: Menge von Feiertagen. Wird automatisch berechnet
                   wenn nicht angegeben.
    """
    if feiertage is None:
        feiertage = feiertage_deutschland(tag.year)
    # Samstag = 5, Sonntag = 6
    return tag.weekday() < 5 and tag not in feiertage


def naechster_werktag(tag: date, feiertage: set[date] | None = None) -> date:
    """Gibt den naechsten Werktag zurueck (oder den Tag selbst, falls Werktag).

    Verschiebt ein Datum auf den naechsten Montag-Freitag, der kein
    Feiertag ist. Wird benoetigt wenn eine Frist auf ein Wochenende
    oder einen Feiertag faellt.
    """
    if feiertage is None:
        feiertage = feiertage_deutschland(tag.year)
    aktuell = tag
    while not ist_werktag(aktuell, feiertage):
        aktuell += timedelta(days=1)
    return aktuell


def n_ter_letzter_werktag(jahr: int, monat: int, n: int) -> date:
    """Berechnet den n-ten letzten Werktag eines Monats.

    Fuer die Sozialversicherung relevant:
    - Beitragsnachweis: 5. letzter Werktag
    - Zahlung: 3. letzter Werktag (= Faelligkeitstag)

    Args:
        jahr: Kalenderjahr.
        monat: Kalendermonat (1-12).
        n: Der wievielte letzte Werktag (1 = letzter, 2 = vorletzter, ...).

    Returns:
        Das berechnete Datum.
    """
    feiertage = feiertage_deutschland(jahr)
    # Letzter Tag des Monats
    if monat == 12:
        letzter_tag = date(jahr, 12, 31)
    else:
        letzter_tag = date(jahr, monat + 1, 1) - timedelta(days=1)

    gefunden = 0
    aktuell = letzter_tag
    while gefunden < n:
        if ist_werktag(aktuell, feiertage):
            gefunden += 1
            if gefunden == n:
                return aktuell
        aktuell -= timedelta(days=1)
    return aktuell  # Sollte nicht erreicht werden


def schonfrist(frist_datum: date) -> date:
    """Berechnet das Ende der Schonfrist (3 Tage nach Fristablauf).

    Die Schonfrist gilt fuer Steuerzahlungen per Bankueberweisung.
    Gemaess §240 AO betraegt sie 3 Tage. Das Ende der Schonfrist
    wird NICHT auf Werktage verschoben — es zaehlen Kalendertage.

    Beispiel: UStVA faellig am 10.03. -> Schonfrist bis 13.03.
              Zahlung muss bis 13.03. beim Finanzamt eingehen.

    Args:
        frist_datum: Das eigentliche Fristdatum.

    Returns:
        Datum des Schonfrist-Endes (frist_datum + 3 Kalendertage).
    """
    return frist_datum + timedelta(days=3)


# ---------------------------------------------------------------------------
# DeadlineTracker
# ---------------------------------------------------------------------------


class DeadlineTracker:
    """Verwaltet steuerliche und buchhalterische Fristen einer GmbH.

    Generiert den Fristenkalender fuer ein Geschaeftsjahr und bietet
    Methoden zum Filtern nach Zeitraum, Faelligkeit und Kategorie.

    Alle Fristen werden unter Beruecksichtigung von Wochenenden und
    bundesweiten Feiertagen berechnet.
    """

    def __init__(self, heute: date | None = None) -> None:
        """Initialisiert den DeadlineTracker.

        Args:
            heute: Referenzdatum fuer Faelligkeitspruefungen.
                   Standard: date.today().
        """
        self.heute = heute or date.today()

    # ------------------------------------------------------------------
    # Fristengenerierung
    # ------------------------------------------------------------------

    def _monatliche_fristen(self, jahr: int, monat: int) -> list[Deadline]:
        """Generiert alle monatlichen Fristen fuer einen Monat.

        Monatliche Fristen beziehen sich immer auf den Vormonat:
        Die UStVA fuer Januar ist am 10. Februar faellig.

        Args:
            jahr: Kalenderjahr der Frist (nicht des Bezugsmonats).
            monat: Kalendermonat der Frist (nicht des Bezugsmonats).
        """
        feiertage = feiertage_deutschland(jahr)
        fristen: list[Deadline] = []

        # Bezugsmonat bestimmen (Vormonat)
        if monat == 1:
            bezugs_monat = 12
            bezugs_jahr = jahr - 1
        else:
            bezugs_monat = monat - 1
            bezugs_jahr = jahr

        # --- UStVA: 10. des Folgemonats ---
        ustva_datum = naechster_werktag(date(jahr, monat, 10), feiertage)
        fristen.append(
            Deadline(
                name="UStVA",
                datum=ustva_datum,
                kategorie=Kategorie.STEUER,
                beschreibung=(
                    f"Umsatzsteuer-Voranmeldung fuer "
                    f"{bezugs_monat:02d}/{bezugs_jahr}. "
                    f"Abgabe und Zahlung bis zum 10. des Folgemonats. "
                    f"Schonfrist fuer Zahlung: {schonfrist(ustva_datum).isoformat()}."
                ),
                wiederkehrend=True,
                prioritaet=Prioritaet.CRITICAL,
            )
        )

        # --- Lohnsteueranmeldung: 10. des Folgemonats ---
        lst_datum = naechster_werktag(date(jahr, monat, 10), feiertage)
        fristen.append(
            Deadline(
                name="Lohnsteueranmeldung",
                datum=lst_datum,
                kategorie=Kategorie.STEUER,
                beschreibung=(
                    f"Lohnsteueranmeldung fuer "
                    f"{bezugs_monat:02d}/{bezugs_jahr}. "
                    f"Abgabe und Zahlung bis zum 10. des Folgemonats."
                ),
                wiederkehrend=True,
                prioritaet=Prioritaet.CRITICAL,
            )
        )

        # --- Sozialversicherung Beitragsnachweis: ~5. letzter Werktag ---
        # Der Beitragsnachweis fuer den aktuellen Monat muss VOR dem
        # Faelligkeitstag eingereicht werden.
        sv_nachweis_datum = n_ter_letzter_werktag(jahr, monat, 5)
        fristen.append(
            Deadline(
                name="SV-Beitragsnachweis",
                datum=sv_nachweis_datum,
                kategorie=Kategorie.MELDUNG,
                beschreibung=(
                    f"Sozialversicherung: Beitragsnachweis fuer "
                    f"{monat:02d}/{jahr}. "
                    f"Einreichung bis zum 5. letzten Werktag des Monats."
                ),
                wiederkehrend=True,
                prioritaet=Prioritaet.CRITICAL,
            )
        )

        # --- Sozialversicherung Zahlung: ~3. letzter Werktag ---
        sv_zahlung_datum = n_ter_letzter_werktag(jahr, monat, 3)
        fristen.append(
            Deadline(
                name="SV-Beitragszahlung",
                datum=sv_zahlung_datum,
                kategorie=Kategorie.STEUER,
                beschreibung=(
                    f"Sozialversicherung: Beitragszahlung fuer "
                    f"{monat:02d}/{jahr}. "
                    f"Zahlung muss am 3. letzten Werktag beim "
                    f"Sozialversicherungstraeger eingehen."
                ),
                wiederkehrend=True,
                prioritaet=Prioritaet.CRITICAL,
            )
        )

        return fristen

    def _quartalsfristen(self, jahr: int) -> list[Deadline]:
        """Generiert alle quartalsweisen Fristen fuer ein Jahr.

        Gewerbesteuer-Vorauszahlungen: 15.02, 15.05, 15.08, 15.11
        KSt-Vorauszahlungen: 10.03, 10.06, 10.09, 10.12
        """
        fristen: list[Deadline] = []
        feiertage = feiertage_deutschland(jahr)

        # --- Gewerbesteuer-Vorauszahlung ---
        gew_st_termine = [
            (2, 15, "Q1"),
            (5, 15, "Q2"),
            (8, 15, "Q3"),
            (11, 15, "Q4"),
        ]
        for monat, tag, quartal in gew_st_termine:
            datum = naechster_werktag(date(jahr, monat, tag), feiertage)
            fristen.append(
                Deadline(
                    name="GewSt-Vorauszahlung",
                    datum=datum,
                    kategorie=Kategorie.STEUER,
                    beschreibung=(
                        f"Gewerbesteuer-Vorauszahlung {quartal}/{jahr}. "
                        f"Schonfrist: {schonfrist(datum).isoformat()}."
                    ),
                    wiederkehrend=True,
                    prioritaet=Prioritaet.HIGH,
                )
            )

        # --- Koerperschaftsteuer-Vorauszahlung ---
        kst_termine = [
            (3, 10, "Q1"),
            (6, 10, "Q2"),
            (9, 10, "Q3"),
            (12, 10, "Q4"),
        ]
        for monat, tag, quartal in kst_termine:
            datum = naechster_werktag(date(jahr, monat, tag), feiertage)
            fristen.append(
                Deadline(
                    name="KSt-Vorauszahlung",
                    datum=datum,
                    kategorie=Kategorie.STEUER,
                    beschreibung=(
                        f"Koerperschaftsteuer-Vorauszahlung {quartal}/{jahr}. "
                        f"Schonfrist: {schonfrist(datum).isoformat()}."
                    ),
                    wiederkehrend=True,
                    prioritaet=Prioritaet.HIGH,
                )
            )

        return fristen

    def _jahresfristen(self, jahr: int) -> list[Deadline]:
        """Generiert die jaehrlichen Fristen fuer ein Geschaeftsjahr.

        Die Fristen beziehen sich auf das VORJAHR als Geschaeftsjahr.
        Beispiel: Fuer GJ 2025 fallen die Fristen im Kalenderjahr 2026.

        Args:
            jahr: Kalenderjahr, in dem die Fristen liegen
                  (= Geschaeftsjahr + 1 fuer die meisten Fristen).
        """
        fristen: list[Deadline] = []
        feiertage = feiertage_deutschland(jahr)
        vorjahr = jahr - 1

        # --- Dauerfristverlaengerung: 10.02 ---
        # Antrag auf Verlaengerung der UStVA-Frist um 1 Monat
        dfv_datum = naechster_werktag(date(jahr, 2, 10), feiertage)
        fristen.append(
            Deadline(
                name="Dauerfristverlaengerung",
                datum=dfv_datum,
                kategorie=Kategorie.STEUER,
                beschreibung=(
                    f"Antrag auf Dauerfristverlaengerung fuer {jahr}. "
                    f"Verlaengert die UStVA-Frist um einen Monat "
                    f"(10. wird zum 10. des uebernachsten Monats). "
                    f"Sondervorauszahlung: 1/11 der Vorjahres-USt."
                ),
                wiederkehrend=False,
                prioritaet=Prioritaet.HIGH,
            )
        )

        # --- Jahresabschluss kleine GmbH: 30.06 ---
        # Aufstellungsfrist fuer kleine Kapitalgesellschaften gemaess §264 HGB
        ja_datum = naechster_werktag(date(jahr, 6, 30), feiertage)
        fristen.append(
            Deadline(
                name="Jahresabschluss Aufstellung",
                datum=ja_datum,
                kategorie=Kategorie.BUCHHALTUNG,
                beschreibung=(
                    f"Aufstellung Jahresabschluss fuer GJ {vorjahr} "
                    f"(kleine GmbH, 6-Monats-Frist gemaess §264 Abs. 1 HGB). "
                    f"Bilanz, GuV und Anhang muessen fertiggestellt sein."
                ),
                wiederkehrend=False,
                prioritaet=Prioritaet.HIGH,
            )
        )

        # --- Steuererklaerung ohne StB: 31.07 ---
        # Abgabefrist ohne Steuerberater gemaess §149 AO
        ste_datum = naechster_werktag(date(jahr, 7, 31), feiertage)
        fristen.append(
            Deadline(
                name="Steuererklaerung (ohne StB)",
                datum=ste_datum,
                kategorie=Kategorie.STEUER,
                beschreibung=(
                    f"Abgabe Steuererklaerung fuer GJ {vorjahr} "
                    f"ohne Steuerberater (Frist: 31.07. des Folgejahres). "
                    f"KSt, GewSt, USt-Jahreserklaerung."
                ),
                wiederkehrend=False,
                prioritaet=Prioritaet.CRITICAL,
            )
        )

        # --- Jahresabschluss Feststellung: 30.11 ---
        # Gesellschafterversammlung muss den Abschluss feststellen
        fest_datum = naechster_werktag(date(jahr, 11, 30), feiertage)
        fristen.append(
            Deadline(
                name="Jahresabschluss Feststellung",
                datum=fest_datum,
                kategorie=Kategorie.BUCHHALTUNG,
                beschreibung=(
                    f"Feststellung des Jahresabschlusses fuer GJ {vorjahr} "
                    f"durch die Gesellschafterversammlung "
                    f"(Frist: 11 Monate nach GJ-Ende)."
                ),
                wiederkehrend=False,
                prioritaet=Prioritaet.HIGH,
            )
        )

        # --- Offenlegung Bundesanzeiger: 31.12 ---
        # Kleine GmbH: 12 Monate nach GJ-Ende
        offen_datum = naechster_werktag(date(jahr, 12, 31), feiertage)
        fristen.append(
            Deadline(
                name="Offenlegung Bundesanzeiger",
                datum=offen_datum,
                kategorie=Kategorie.MELDUNG,
                beschreibung=(
                    f"Offenlegung des Jahresabschlusses fuer GJ {vorjahr} "
                    f"beim Bundesanzeiger (12 Monate nach GJ-Ende). "
                    f"Versaeumnis fuehrt zu Ordnungsgeld (mind. 2.500 EUR)."
                ),
                wiederkehrend=False,
                prioritaet=Prioritaet.CRITICAL,
            )
        )

        # --- Inventur: 31.12 ---
        # Stichtagsinventur zum Bilanzstichtag
        inv_datum = date(jahr, 12, 31)
        fristen.append(
            Deadline(
                name="Inventur",
                datum=inv_datum,
                kategorie=Kategorie.BUCHHALTUNG,
                beschreibung=(
                    f"Stichtagsinventur zum Bilanzstichtag {jahr}. "
                    f"Bestandsaufnahme aller Vermoegenswerte und Schulden "
                    f"gemaess §240 HGB."
                ),
                wiederkehrend=False,
                prioritaet=Prioritaet.HIGH,
            )
        )

        return fristen

    # ------------------------------------------------------------------
    # Oeffentliche API
    # ------------------------------------------------------------------

    def get_annual_calendar(self, jahr: int) -> list[Deadline]:
        """Gibt alle Fristen fuer ein Kalenderjahr zurueck.

        Enthaelt monatliche, quartalsweise und jaehrliche Fristen,
        sortiert nach Datum.

        Args:
            jahr: Kalenderjahr.

        Returns:
            Chronologisch sortierte Liste aller Fristen des Jahres.
        """
        fristen: list[Deadline] = []

        # Monatliche Fristen fuer jeden Monat des Jahres
        for monat in range(1, 13):
            fristen.extend(self._monatliche_fristen(jahr, monat))

        # Quartalsfristen
        fristen.extend(self._quartalsfristen(jahr))

        # Jahresfristen
        fristen.extend(self._jahresfristen(jahr))

        # Chronologisch sortieren
        fristen.sort(key=lambda f: f.datum)
        return fristen

    def get_monthly_deadlines(self, jahr: int, monat: int) -> list[Deadline]:
        """Gibt alle Fristen zurueck, die in einen bestimmten Monat fallen.

        Filtert den Jahreskalender auf Fristen deren Datum im
        angegebenen Monat liegt.

        Args:
            jahr: Kalenderjahr.
            monat: Kalendermonat (1-12).

        Returns:
            Chronologisch sortierte Liste der Fristen im Monat.
        """
        kalender = self.get_annual_calendar(jahr)
        return [f for f in kalender if f.datum.year == jahr and f.datum.month == monat]

    def get_upcoming(self, tage: int = 30) -> list[Deadline]:
        """Gibt Fristen zurueck, die innerhalb der naechsten N Tage faellig sind.

        Beruecksichtigt Fristen ab heute (einschliesslich) bis
        heute + tage (einschliesslich).

        Args:
            tage: Anzahl Tage in die Zukunft (Standard: 30).

        Returns:
            Chronologisch sortierte Liste der anstehenden Fristen.
        """
        von = self.heute
        bis = self.heute + timedelta(days=tage)

        # Kalender fuer die relevanten Jahre generieren
        jahre = {von.year}
        if bis.year != von.year:
            jahre.add(bis.year)

        alle_fristen: list[Deadline] = []
        for jahr in jahre:
            alle_fristen.extend(self.get_annual_calendar(jahr))

        return [f for f in alle_fristen if von <= f.datum <= bis]

    def get_overdue(self) -> list[Deadline]:
        """Gibt ueberfaellige Fristen zurueck (Datum vor heute).

        Prueft das aktuelle Jahr und gibt alle Fristen zurueck,
        deren Datum strikt vor dem heutigen Tag liegt.

        Returns:
            Chronologisch sortierte Liste der ueberfaelligen Fristen.
        """
        kalender = self.get_annual_calendar(self.heute.year)
        return [f for f in kalender if f.datum < self.heute]
