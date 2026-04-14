"""Fristen-Modul.

Verwaltet steuerliche und buchhalterische Fristen einer deutschen GmbH.
Berechnet Fälligkeiten unter Berücksichtigung von Wochenenden,
Feiertagen und der Schonfrist (3 Tage für Banküberweisungen nach dem 10.).

Deutsche Steuerfristen (Auswahl):
- UStVA: 10. des Folgemonats (monatlich)
- Lohnsteueranmeldung: 10. des Folgemonats (monatlich)
- Sozialversicherung: Beitragsnachweis ~5. letzter Werktag,
  Zahlung ~3. letzter Werktag (monatlich)
- Gewerbesteuer-VZ: 15.02, 15.05, 15.08, 15.11 (quartalsweise)
- KSt-VZ: 10.03, 10.06, 10.09, 10.12 (quartalsweise)
- Jahresabschluss, Steuererklärung, Offenlegung (jährlich)
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


class Priorität(str, Enum):
    """Priorität einer Frist.

    critical = Versäumnis führt zu Säumniszuschlägen oder Bußgeldern
    high     = Versäumnis führt zu Nachteilen (z.B. Verspätungszuschlag)
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
        datum: Fälligkeitsdatum.
        kategorie: Steuer, Buchhaltung oder Meldung.
        beschreibung: Ausführliche Erläuterung.
        wiederkehrend: True für monatliche/quartalsweise Fristen.
        priorität: critical / high / medium.
    """

    name: str
    datum: date
    kategorie: Kategorie
    beschreibung: str
    wiederkehrend: bool
    priorität: Priorität


# ---------------------------------------------------------------------------
# Hilfsfunktionen: Werktage und Schonfrist
# ---------------------------------------------------------------------------

# Deutsche gesetzliche Feiertage (bundesweit).
# Bewegliche Feiertage (Ostern etc.) werden pro Jahr berechnet.


def _ostersonntag(jahr: int) -> date:
    """Berechnet Ostersonntag nach dem Gauss'schen Algorithmus.

    Der Algorithmus bestimmt das Datum des Ostersonntags für ein
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
    """Gibt die bundesweiten gesetzlichen Feiertage für ein Jahr zurück.

    Enthält nur bundeseinheitliche Feiertage, keine länderspezifischen.
    Für die Fristenberechnung relevant: Wenn eine Frist auf einen
    Feiertag fällt, verschiebt sie sich auf den nächsten Werktag.
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
    """Prüft ob ein Datum ein Werktag ist (Mo-Fr, kein Feiertag).

    Args:
        tag: Das zu prüfende Datum.
        feiertage: Menge von Feiertagen. Wird automatisch berechnet
                   wenn nicht angegeben.
    """
    if feiertage is None:
        feiertage = feiertage_deutschland(tag.year)
    # Samstag = 5, Sonntag = 6
    return tag.weekday() < 5 and tag not in feiertage


def nächster_werktag(tag: date, feiertage: set[date] | None = None) -> date:
    """Gibt den nächsten Werktag zurück (oder den Tag selbst, falls Werktag).

    Verschiebt ein Datum auf den nächsten Montag-Freitag, der kein
    Feiertag ist. Wird benötigt wenn eine Frist auf ein Wochenende
    oder einen Feiertag fällt.
    """
    if feiertage is None:
        feiertage = feiertage_deutschland(tag.year)
    aktuell = tag
    while not ist_werktag(aktuell, feiertage):
        aktuell += timedelta(days=1)
    return aktuell


def n_ter_letzter_werktag(jahr: int, monat: int, n: int) -> date:
    """Berechnet den n-ten letzten Werktag eines Monats.

    Für die Sozialversicherung relevant:
    - Beitragsnachweis: 5. letzter Werktag
    - Zahlung: 3. letzter Werktag (= Fälligkeitstag)

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

    Die Schonfrist gilt für Steuerzahlungen per Banküberweisung.
    Gemäß §240 AO beträgt sie 3 Tage. Das Ende der Schonfrist
    wird NICHT auf Werktage verschoben. Es zählen Kalendertage.

    Beispiel: UStVA fällig am 10.03. -> Schonfrist bis 13.03.
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

    Generiert den Fristenkalender für ein Geschäftsjahr und bietet
    Methoden zum Filtern nach Zeitraum, Fälligkeit und Kategorie.

    Alle Fristen werden unter Berücksichtigung von Wochenenden und
    bundesweiten Feiertagen berechnet.
    """

    def __init__(self, heute: date | None = None) -> None:
        """Initialisiert den DeadlineTracker.

        Args:
            heute: Referenzdatum für Fälligkeitsprüfungen.
                   Standard: date.today().
        """
        self.heute = heute or date.today()

    # ------------------------------------------------------------------
    # Fristengenerierung
    # ------------------------------------------------------------------

    def _monatliche_fristen(self, jahr: int, monat: int) -> list[Deadline]:
        """Generiert alle monatlichen Fristen für einen Monat.

        Monatliche Fristen beziehen sich immer auf den Vormonat:
        Die UStVA für Januar ist am 10. Februar fällig.

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
        ustva_datum = nächster_werktag(date(jahr, monat, 10), feiertage)
        fristen.append(
            Deadline(
                name="UStVA",
                datum=ustva_datum,
                kategorie=Kategorie.STEUER,
                beschreibung=(
                    f"Umsatzsteuer-Voranmeldung für "
                    f"{bezugs_monat:02d}/{bezugs_jahr}. "
                    f"Abgabe und Zahlung bis zum 10. des Folgemonats. "
                    f"Schonfrist für Zahlung: {schonfrist(ustva_datum).isoformat()}."
                ),
                wiederkehrend=True,
                priorität=Priorität.CRITICAL,
            )
        )

        # --- Lohnsteueranmeldung: 10. des Folgemonats ---
        lst_datum = nächster_werktag(date(jahr, monat, 10), feiertage)
        fristen.append(
            Deadline(
                name="Lohnsteueranmeldung",
                datum=lst_datum,
                kategorie=Kategorie.STEUER,
                beschreibung=(
                    f"Lohnsteueranmeldung für "
                    f"{bezugs_monat:02d}/{bezugs_jahr}. "
                    f"Abgabe und Zahlung bis zum 10. des Folgemonats."
                ),
                wiederkehrend=True,
                priorität=Priorität.CRITICAL,
            )
        )

        # --- Sozialversicherung Beitragsnachweis: ~5. letzter Werktag ---
        # Der Beitragsnachweis für den aktuellen Monat muss VOR dem
        # Fälligkeitstag eingereicht werden.
        sv_nachweis_datum = n_ter_letzter_werktag(jahr, monat, 5)
        fristen.append(
            Deadline(
                name="SV-Beitragsnachweis",
                datum=sv_nachweis_datum,
                kategorie=Kategorie.MELDUNG,
                beschreibung=(
                    f"Sozialversicherung: Beitragsnachweis für "
                    f"{monat:02d}/{jahr}. "
                    f"Einreichung bis zum 5. letzten Werktag des Monats."
                ),
                wiederkehrend=True,
                priorität=Priorität.CRITICAL,
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
                    f"Sozialversicherung: Beitragszahlung für "
                    f"{monat:02d}/{jahr}. "
                    f"Zahlung muss am 3. letzten Werktag beim "
                    f"Sozialversicherungsträger eingehen."
                ),
                wiederkehrend=True,
                priorität=Priorität.CRITICAL,
            )
        )

        return fristen

    def _quartalsfristen(self, jahr: int) -> list[Deadline]:
        """Generiert alle quartalsweisen Fristen für ein Jahr.

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
            datum = nächster_werktag(date(jahr, monat, tag), feiertage)
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
                    priorität=Priorität.HIGH,
                )
            )

        # --- Körperschaftsteuer-Vorauszahlung ---
        kst_termine = [
            (3, 10, "Q1"),
            (6, 10, "Q2"),
            (9, 10, "Q3"),
            (12, 10, "Q4"),
        ]
        for monat, tag, quartal in kst_termine:
            datum = nächster_werktag(date(jahr, monat, tag), feiertage)
            fristen.append(
                Deadline(
                    name="KSt-Vorauszahlung",
                    datum=datum,
                    kategorie=Kategorie.STEUER,
                    beschreibung=(
                        f"Körperschaftsteuer-Vorauszahlung {quartal}/{jahr}. "
                        f"Schonfrist: {schonfrist(datum).isoformat()}."
                    ),
                    wiederkehrend=True,
                    priorität=Priorität.HIGH,
                )
            )

        return fristen

    def _jahresfristen(self, jahr: int) -> list[Deadline]:
        """Generiert die jährlichen Fristen für ein Geschäftsjahr.

        Die Fristen beziehen sich auf das VORJAHR als Geschäftsjahr.
        Beispiel: Für GJ 2025 fallen die Fristen im Kalenderjahr 2026.

        Args:
            jahr: Kalenderjahr, in dem die Fristen liegen
                  (= Geschäftsjahr + 1 für die meisten Fristen).
        """
        fristen: list[Deadline] = []
        feiertage = feiertage_deutschland(jahr)
        vorjahr = jahr - 1

        # --- Dauerfristverlängerung: 10.02 ---
        # Antrag auf Verlängerung der UStVA-Frist um 1 Monat
        dfv_datum = nächster_werktag(date(jahr, 2, 10), feiertage)
        fristen.append(
            Deadline(
                name="Dauerfristverlängerung",
                datum=dfv_datum,
                kategorie=Kategorie.STEUER,
                beschreibung=(
                    f"Antrag auf Dauerfristverlängerung für {jahr}. "
                    f"Verlängert die UStVA-Frist um einen Monat "
                    f"(10. wird zum 10. des uebernachsten Monats). "
                    f"Sondervorauszahlung: 1/11 der Vorjahres-USt."
                ),
                wiederkehrend=False,
                priorität=Priorität.HIGH,
            )
        )

        # --- Jahresabschluss kleine GmbH: 30.06 ---
        # Aufstellungsfrist für kleine Kapitalgesellschaften gemäß §264 HGB
        ja_datum = nächster_werktag(date(jahr, 6, 30), feiertage)
        fristen.append(
            Deadline(
                name="Jahresabschluss Aufstellung",
                datum=ja_datum,
                kategorie=Kategorie.BUCHHALTUNG,
                beschreibung=(
                    f"Aufstellung Jahresabschluss für GJ {vorjahr} "
                    f"(kleine GmbH, 6-Monats-Frist gemäß §264 Abs. 1 HGB). "
                    f"Bilanz, GuV und Anhang müssen fertiggestellt sein."
                ),
                wiederkehrend=False,
                priorität=Priorität.HIGH,
            )
        )

        # --- Steuererklärung ohne StB: 31.07 ---
        # Abgabefrist ohne Steuerberater gemäß §149 AO
        ste_datum = nächster_werktag(date(jahr, 7, 31), feiertage)
        fristen.append(
            Deadline(
                name="Steuererklärung (ohne StB)",
                datum=ste_datum,
                kategorie=Kategorie.STEUER,
                beschreibung=(
                    f"Abgabe Steuererklärung für GJ {vorjahr} "
                    f"ohne Steuerberater (Frist: 31.07. des Folgejahres). "
                    f"KSt, GewSt, USt-Jahreserklärung."
                ),
                wiederkehrend=False,
                priorität=Priorität.CRITICAL,
            )
        )

        # --- Jahresabschluss Feststellung: 30.11 ---
        # Gesellschafterversammlung muss den Abschluss feststellen
        fest_datum = nächster_werktag(date(jahr, 11, 30), feiertage)
        fristen.append(
            Deadline(
                name="Jahresabschluss Feststellung",
                datum=fest_datum,
                kategorie=Kategorie.BUCHHALTUNG,
                beschreibung=(
                    f"Feststellung des Jahresabschlusses für GJ {vorjahr} "
                    f"durch die Gesellschafterversammlung "
                    f"(Frist: 11 Monate nach GJ-Ende)."
                ),
                wiederkehrend=False,
                priorität=Priorität.HIGH,
            )
        )

        # --- Offenlegung Bundesanzeiger: 31.12 ---
        # Kleine GmbH: 12 Monate nach GJ-Ende
        offen_datum = nächster_werktag(date(jahr, 12, 31), feiertage)
        fristen.append(
            Deadline(
                name="Offenlegung Bundesanzeiger",
                datum=offen_datum,
                kategorie=Kategorie.MELDUNG,
                beschreibung=(
                    f"Offenlegung des Jahresabschlusses für GJ {vorjahr} "
                    f"beim Bundesanzeiger (12 Monate nach GJ-Ende). "
                    f"Versäumnis führt zu Ordnungsgeld (mind. 2.500 EUR)."
                ),
                wiederkehrend=False,
                priorität=Priorität.CRITICAL,
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
                    f"Bestandsaufnahme aller Vermögenswerte und Schulden "
                    f"gemäß §240 HGB."
                ),
                wiederkehrend=False,
                priorität=Priorität.HIGH,
            )
        )

        return fristen

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------

    def get_annual_calendar(self, jahr: int) -> list[Deadline]:
        """Gibt alle Fristen für ein Kalenderjahr zurück.

        Enthält monatliche, quartalsweise und jährliche Fristen,
        sortiert nach Datum.

        Args:
            jahr: Kalenderjahr.

        Returns:
            Chronologisch sortierte Liste aller Fristen des Jahres.
        """
        fristen: list[Deadline] = []

        # Monatliche Fristen für jeden Monat des Jahres
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
        """Gibt alle Fristen zurück, die in einen bestimmten Monat fallen.

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
        """Gibt Fristen zurück, die innerhalb der nächsten N Tage fällig sind.

        Berücksichtigt Fristen ab heute (einschliesslich) bis
        heute + tage (einschliesslich).

        Args:
            tage: Anzahl Tage in die Zukunft (Standard: 30).

        Returns:
            Chronologisch sortierte Liste der anstehenden Fristen.
        """
        von = self.heute
        bis = self.heute + timedelta(days=tage)

        # Kalender für die relevanten Jahre generieren
        jahre = {von.year}
        if bis.year != von.year:
            jahre.add(bis.year)

        alle_fristen: list[Deadline] = []
        for jahr in jahre:
            alle_fristen.extend(self.get_annual_calendar(jahr))

        return [f for f in alle_fristen if von <= f.datum <= bis]

    def get_overdue(self) -> list[Deadline]:
        """Gibt überfällige Fristen zurück (Datum vor heute).

        Prüft das aktuelle Jahr und gibt alle Fristen zurück,
        deren Datum strikt vor dem heutigen Tag liegt.

        Returns:
            Chronologisch sortierte Liste der überfälligen Fristen.
        """
        kalender = self.get_annual_calendar(self.heute.year)
        return [f for f in kalender if f.datum < self.heute]
