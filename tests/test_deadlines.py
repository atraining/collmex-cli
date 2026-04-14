"""Tests fuer collmex.deadlines — Fristenkalender und DeadlineTracker.

Alle Tests sind deterministisch und benoetigen keine API-Calls.
Datums-abhaengige Tests verwenden ein festes Referenzdatum.
"""

from __future__ import annotations

from datetime import date

import pytest

from collmex.deadlines import (
    Deadline,
    DeadlineTracker,
    Kategorie,
    Prioritaet,
    feiertage_deutschland,
    ist_werktag,
    n_ter_letzter_werktag,
    naechster_werktag,
    schonfrist,
)

# ---------------------------------------------------------------------------
# Hilfsfunktionen: Feiertage
# ---------------------------------------------------------------------------


class TestFeiertage:
    def test_neujahr(self):
        """1. Januar ist immer ein Feiertag."""
        ft = feiertage_deutschland(2026)
        assert date(2026, 1, 1) in ft

    def test_tag_der_arbeit(self):
        """1. Mai ist immer ein Feiertag."""
        ft = feiertage_deutschland(2026)
        assert date(2026, 5, 1) in ft

    def test_tag_der_einheit(self):
        """3. Oktober ist immer ein Feiertag."""
        ft = feiertage_deutschland(2026)
        assert date(2026, 10, 3) in ft

    def test_weihnachten(self):
        """25. und 26. Dezember sind Feiertage."""
        ft = feiertage_deutschland(2026)
        assert date(2026, 12, 25) in ft
        assert date(2026, 12, 26) in ft

    def test_karfreitag_2026(self):
        """Karfreitag 2026 ist am 3. April."""
        ft = feiertage_deutschland(2026)
        assert date(2026, 4, 3) in ft

    def test_ostermontag_2026(self):
        """Ostermontag 2026 ist am 6. April."""
        ft = feiertage_deutschland(2026)
        assert date(2026, 4, 6) in ft

    def test_christi_himmelfahrt_2026(self):
        """Christi Himmelfahrt 2026 ist am 14. Mai."""
        ft = feiertage_deutschland(2026)
        assert date(2026, 5, 14) in ft

    def test_pfingstmontag_2026(self):
        """Pfingstmontag 2026 ist am 25. Mai."""
        ft = feiertage_deutschland(2026)
        assert date(2026, 5, 25) in ft

    def test_anzahl_feiertage(self):
        """Es gibt 9 bundesweite Feiertage."""
        ft = feiertage_deutschland(2026)
        assert len(ft) == 9

    def test_verschiedene_jahre(self):
        """Feiertage werden pro Jahr korrekt berechnet."""
        ft_2025 = feiertage_deutschland(2025)
        ft_2026 = feiertage_deutschland(2026)
        # Ostern faellt auf verschiedene Daten
        # 2025: Ostersonntag 20.04, 2026: Ostersonntag 05.04
        assert date(2025, 4, 18) in ft_2025  # Karfreitag 2025
        assert date(2026, 4, 3) in ft_2026  # Karfreitag 2026


# ---------------------------------------------------------------------------
# Hilfsfunktionen: Werktage
# ---------------------------------------------------------------------------


class TestIstWerktag:
    def test_montag_ist_werktag(self):
        """Ein normaler Montag ist ein Werktag."""
        # 2026-03-02 ist ein Montag
        assert ist_werktag(date(2026, 3, 2)) is True

    def test_freitag_ist_werktag(self):
        """Ein normaler Freitag ist ein Werktag."""
        # 2026-03-06 ist ein Freitag
        assert ist_werktag(date(2026, 3, 6)) is True

    def test_samstag_kein_werktag(self):
        """Samstag ist kein Werktag."""
        # 2026-03-07 ist ein Samstag
        assert ist_werktag(date(2026, 3, 7)) is False

    def test_sonntag_kein_werktag(self):
        """Sonntag ist kein Werktag."""
        # 2026-03-08 ist ein Sonntag
        assert ist_werktag(date(2026, 3, 8)) is False

    def test_feiertag_kein_werktag(self):
        """Neujahr (Mittwoch 2025-01-01) ist kein Werktag."""
        assert ist_werktag(date(2025, 1, 1)) is False

    def test_tag_nach_feiertag_ist_werktag(self):
        """2. Januar 2025 (Donnerstag) ist ein Werktag."""
        assert ist_werktag(date(2025, 1, 2)) is True


class TestNaechsterWerktag:
    def test_werktag_bleibt(self):
        """Ein Werktag wird nicht verschoben."""
        # 2026-03-10 ist ein Dienstag
        assert naechster_werktag(date(2026, 3, 10)) == date(2026, 3, 10)

    def test_samstag_wird_montag(self):
        """Samstag wird auf Montag verschoben."""
        # 2026-03-07 ist Samstag -> 2026-03-09 Montag
        assert naechster_werktag(date(2026, 3, 7)) == date(2026, 3, 9)

    def test_sonntag_wird_montag(self):
        """Sonntag wird auf Montag verschoben."""
        # 2026-03-08 ist Sonntag -> 2026-03-09 Montag
        assert naechster_werktag(date(2026, 3, 8)) == date(2026, 3, 9)

    def test_feiertag_wird_verschoben(self):
        """Karfreitag 2026 (03.04.) -> Dienstag 07.04. (Mo ist Ostermontag)."""
        assert naechster_werktag(date(2026, 4, 3)) == date(2026, 4, 7)

    def test_feiertag_plus_wochenende(self):
        """Karfreitag -> Sa -> So -> Ostermontag -> Dienstag."""
        # Karfreitag 2026 = 03.04., Ostermontag = 06.04.
        assert naechster_werktag(date(2026, 4, 4)) == date(2026, 4, 7)


# ---------------------------------------------------------------------------
# Hilfsfunktionen: Letzter Werktag
# ---------------------------------------------------------------------------


class TestNterLetzterWerktag:
    def test_letzter_werktag_maerz_2026(self):
        """Letzter Werktag im Maerz 2026 ist der 31.03. (Dienstag)."""
        assert n_ter_letzter_werktag(2026, 3, 1) == date(2026, 3, 31)

    def test_dritter_letzter_werktag_maerz_2026(self):
        """3. letzter Werktag im Maerz 2026."""
        # Maerz 2026: 31. Di, 30. Mo, 27. Fr -> 27.03.
        assert n_ter_letzter_werktag(2026, 3, 3) == date(2026, 3, 27)

    def test_fuenfter_letzter_werktag_maerz_2026(self):
        """5. letzter Werktag im Maerz 2026."""
        # Maerz 2026: 31. Di, 30. Mo, 27. Fr, 26. Do, 25. Mi -> 25.03.
        assert n_ter_letzter_werktag(2026, 3, 5) == date(2026, 3, 25)

    def test_letzter_werktag_dezember_2026(self):
        """Letzter Werktag im Dezember 2026."""
        # 31.12.2026 ist Donnerstag, kein Feiertag -> korrekt
        # Aber 25. und 26. sind Feiertage
        assert n_ter_letzter_werktag(2026, 12, 1) == date(2026, 12, 31)

    def test_dritter_letzter_werktag_dezember_2026(self):
        """3. letzter Werktag im Dezember 2026 beruecksichtigt Weihnachten."""
        # Dez 2026: 31. Do, 30. Mi, 29. Di, 28. Mo, 27. So, 26. Sa(Feiertag),
        # 25. Fr(Feiertag), 24. Do, 23. Mi
        # Werktage rueckwaerts: 31.(1), 30.(2), 29.(3)
        assert n_ter_letzter_werktag(2026, 12, 3) == date(2026, 12, 29)

    def test_monat_mit_feiertag_am_ende(self):
        """April 2026: 30.04. Donnerstag, 01.05. Feiertag betrifft Maerz nicht."""
        # April 2026: 30. Do(1), 29. Mi(2), 28. Di(3)
        assert n_ter_letzter_werktag(2026, 4, 3) == date(2026, 4, 28)


# ---------------------------------------------------------------------------
# Hilfsfunktionen: Schonfrist
# ---------------------------------------------------------------------------


class TestSchonfrist:
    def test_schonfrist_3_tage(self):
        """Schonfrist betraegt genau 3 Kalendertage."""
        assert schonfrist(date(2026, 3, 10)) == date(2026, 3, 13)

    def test_schonfrist_monatsende(self):
        """Schonfrist kann in den naechsten Monat fallen."""
        assert schonfrist(date(2026, 1, 30)) == date(2026, 2, 2)

    def test_schonfrist_jahresende(self):
        """Schonfrist kann in das naechste Jahr fallen."""
        assert schonfrist(date(2026, 12, 30)) == date(2027, 1, 2)


# ---------------------------------------------------------------------------
# Deadline Dataclass
# ---------------------------------------------------------------------------


class TestDeadline:
    def test_deadline_erstellen(self):
        """Deadline-Objekt kann korrekt erstellt werden."""
        d = Deadline(
            name="UStVA",
            datum=date(2026, 3, 10),
            kategorie=Kategorie.STEUER,
            beschreibung="UStVA fuer 02/2026",
            wiederkehrend=True,
            prioritaet=Prioritaet.CRITICAL,
        )
        assert d.name == "UStVA"
        assert d.datum == date(2026, 3, 10)
        assert d.kategorie == Kategorie.STEUER
        assert d.wiederkehrend is True
        assert d.prioritaet == Prioritaet.CRITICAL

    def test_deadline_frozen(self):
        """Deadline ist immutable (frozen dataclass)."""
        d = Deadline(
            name="UStVA",
            datum=date(2026, 3, 10),
            kategorie=Kategorie.STEUER,
            beschreibung="Test",
            wiederkehrend=True,
            prioritaet=Prioritaet.CRITICAL,
        )
        with pytest.raises(AttributeError):
            d.name = "Geaendert"  # type: ignore[misc]

    def test_kategorien(self):
        """Alle Kategorien haben die korrekten Werte."""
        assert Kategorie.STEUER.value == "steuer"
        assert Kategorie.BUCHHALTUNG.value == "buchhaltung"
        assert Kategorie.MELDUNG.value == "meldung"

    def test_prioritaeten(self):
        """Alle Prioritaeten haben die korrekten Werte."""
        assert Prioritaet.CRITICAL.value == "critical"
        assert Prioritaet.HIGH.value == "high"
        assert Prioritaet.MEDIUM.value == "medium"


# ---------------------------------------------------------------------------
# DeadlineTracker: Jahreskalender
# ---------------------------------------------------------------------------


class TestGetAnnualCalendar:
    def test_kalender_nicht_leer(self):
        """Jahreskalender enthaelt Fristen."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        kalender = tracker.get_annual_calendar(2026)
        assert len(kalender) > 0

    def test_kalender_chronologisch_sortiert(self):
        """Fristen sind nach Datum aufsteigend sortiert."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        kalender = tracker.get_annual_calendar(2026)
        daten = [f.datum for f in kalender]
        assert daten == sorted(daten)

    def test_kalender_enthaelt_monatliche_fristen(self):
        """Kalender enthaelt UStVA fuer jeden Monat."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        kalender = tracker.get_annual_calendar(2026)
        ustva_fristen = [f for f in kalender if f.name == "UStVA"]
        assert len(ustva_fristen) == 12

    def test_kalender_enthaelt_quartalsfristen(self):
        """Kalender enthaelt Gewerbesteuer-VZ (4x) und KSt-VZ (4x)."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        kalender = tracker.get_annual_calendar(2026)
        gewst = [f for f in kalender if f.name == "GewSt-Vorauszahlung"]
        kst = [f for f in kalender if f.name == "KSt-Vorauszahlung"]
        assert len(gewst) == 4
        assert len(kst) == 4

    def test_kalender_enthaelt_jahresfristen(self):
        """Kalender enthaelt die wichtigsten Jahresfristen."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        kalender = tracker.get_annual_calendar(2026)
        namen = {f.name for f in kalender}
        assert "Dauerfristverlaengerung" in namen
        assert "Jahresabschluss Aufstellung" in namen
        assert "Steuererklaerung (ohne StB)" in namen
        assert "Jahresabschluss Feststellung" in namen
        assert "Offenlegung Bundesanzeiger" in namen
        assert "Inventur" in namen

    def test_alle_fristen_sind_deadline_objekte(self):
        """Jedes Element im Kalender ist ein Deadline-Objekt."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        kalender = tracker.get_annual_calendar(2026)
        for frist in kalender:
            assert isinstance(frist, Deadline)

    def test_monatliche_fristen_pro_monat(self):
        """Jeder Monat hat 4 monatliche Fristen (UStVA, LSt, SV-Nachweis, SV-Zahlung)."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        kalender = tracker.get_annual_calendar(2026)
        monatlich_wiederkehrend = [
            f
            for f in kalender
            if f.wiederkehrend
            and f.name
            in (
                "UStVA",
                "Lohnsteueranmeldung",
                "SV-Beitragsnachweis",
                "SV-Beitragszahlung",
            )
        ]
        # 4 Fristen * 12 Monate = 48
        assert len(monatlich_wiederkehrend) == 48

    def test_gesamtanzahl_fristen(self):
        """Jahreskalender hat die erwartete Gesamtanzahl.

        48 monatlich (4 * 12) + 8 quartalsweise (4 GewSt + 4 KSt)
        + 6 jaehrlich = 62 Fristen.
        """
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        kalender = tracker.get_annual_calendar(2026)
        assert len(kalender) == 62


# ---------------------------------------------------------------------------
# DeadlineTracker: Monatsfristen
# ---------------------------------------------------------------------------


class TestGetMonthlyDeadlines:
    def test_maerz_2026_fristen(self):
        """Maerz 2026 enthaelt mindestens die monatlichen Fristen."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        fristen = tracker.get_monthly_deadlines(2026, 3)
        namen = [f.name for f in fristen]
        assert "UStVA" in namen
        assert "Lohnsteueranmeldung" in namen
        assert "SV-Beitragsnachweis" in namen
        assert "SV-Beitragszahlung" in namen

    def test_maerz_2026_kst(self):
        """Maerz 2026 enthaelt die KSt-Vorauszahlung Q1."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        fristen = tracker.get_monthly_deadlines(2026, 3)
        kst = [f for f in fristen if f.name == "KSt-Vorauszahlung"]
        assert len(kst) == 1

    def test_februar_2026_gewst(self):
        """Februar 2026 enthaelt die GewSt-Vorauszahlung Q1."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        fristen = tracker.get_monthly_deadlines(2026, 2)
        gewst = [f for f in fristen if f.name == "GewSt-Vorauszahlung"]
        assert len(gewst) == 1

    def test_februar_dauerfristverlaengerung(self):
        """Februar 2026 enthaelt die Dauerfristverlaengerung."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        fristen = tracker.get_monthly_deadlines(2026, 2)
        dfv = [f for f in fristen if f.name == "Dauerfristverlaengerung"]
        assert len(dfv) == 1

    def test_april_keine_quartalsfristen(self):
        """April hat keine Quartalsfristen (GewSt/KSt)."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        fristen = tracker.get_monthly_deadlines(2026, 4)
        quartals = [f for f in fristen if f.name in ("GewSt-Vorauszahlung", "KSt-Vorauszahlung")]
        assert len(quartals) == 0

    def test_chronologisch_sortiert(self):
        """Monatsfristen sind nach Datum sortiert."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        fristen = tracker.get_monthly_deadlines(2026, 3)
        daten = [f.datum for f in fristen]
        assert daten == sorted(daten)


# ---------------------------------------------------------------------------
# DeadlineTracker: Anstehende Fristen
# ---------------------------------------------------------------------------


class TestGetUpcoming:
    def test_30_tage_standard(self):
        """Standard: Fristen innerhalb von 30 Tagen."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        fristen = tracker.get_upcoming()
        # Alle Fristen muessen zwischen 03.03. und 02.04. liegen
        for f in fristen:
            assert date(2026, 3, 3) <= f.datum <= date(2026, 4, 2)

    def test_benutzerdefinierter_zeitraum(self):
        """Benutzerdefinierter Zeitraum: 7 Tage."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        fristen = tracker.get_upcoming(tage=7)
        for f in fristen:
            assert date(2026, 3, 3) <= f.datum <= date(2026, 3, 10)

    def test_enthaelt_ustva_10_maerz(self):
        """UStVA am 10. Maerz erscheint bei 30-Tage-Vorschau ab 03.03."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        fristen = tracker.get_upcoming(tage=30)
        ustva = [f for f in fristen if f.name == "UStVA"]
        assert len(ustva) >= 1

    def test_chronologisch_sortiert(self):
        """Anstehende Fristen sind chronologisch sortiert."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        fristen = tracker.get_upcoming(tage=60)
        daten = [f.datum for f in fristen]
        assert daten == sorted(daten)

    def test_jahreswechsel(self):
        """Fristen ueber den Jahreswechsel werden korrekt berechnet."""
        tracker = DeadlineTracker(heute=date(2026, 12, 15))
        fristen = tracker.get_upcoming(tage=30)
        # Sollte Fristen aus 2026 und 2027 enthalten
        jahre = {f.datum.year for f in fristen}
        assert 2026 in jahre or 2027 in jahre

    def test_null_tage(self):
        """0 Tage: Nur Fristen von heute."""
        tracker = DeadlineTracker(heute=date(2026, 3, 10))
        fristen = tracker.get_upcoming(tage=0)
        for f in fristen:
            assert f.datum == date(2026, 3, 10)


# ---------------------------------------------------------------------------
# DeadlineTracker: Ueberfaellige Fristen
# ---------------------------------------------------------------------------


class TestGetOverdue:
    def test_anfang_januar_keine_ueberfaelligen(self):
        """Am 1. Januar gibt es keine ueberfaelligen Fristen."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        fristen = tracker.get_overdue()
        assert len(fristen) == 0

    def test_mitte_maerz_ueberfaellige(self):
        """Mitte Maerz gibt es ueberfaellige Fristen aus Jan/Feb."""
        tracker = DeadlineTracker(heute=date(2026, 3, 15))
        fristen = tracker.get_overdue()
        assert len(fristen) > 0

    def test_ueberfaellige_alle_in_vergangenheit(self):
        """Alle ueberfaelligen Fristen liegen vor heute."""
        tracker = DeadlineTracker(heute=date(2026, 6, 15))
        fristen = tracker.get_overdue()
        for f in fristen:
            assert f.datum < date(2026, 6, 15)

    def test_ueberfaellige_chronologisch(self):
        """Ueberfaellige Fristen sind chronologisch sortiert."""
        tracker = DeadlineTracker(heute=date(2026, 6, 15))
        fristen = tracker.get_overdue()
        daten = [f.datum for f in fristen]
        assert daten == sorted(daten)


# ---------------------------------------------------------------------------
# Spezifische Datumspruefungen
# ---------------------------------------------------------------------------


class TestSpezifischeDaten:
    def test_ustva_10_maerz_2026_ist_dienstag(self):
        """UStVA am 10.03.2026 (Dienstag) bleibt am 10.03."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ustva_maerz = [f for f in kalender if f.name == "UStVA" and f.datum.month == 3]
        assert len(ustva_maerz) == 1
        assert ustva_maerz[0].datum == date(2026, 3, 10)

    def test_ustva_januar_10_ist_samstag_2026(self):
        """10.01.2026 ist ein Samstag -> UStVA verschiebt auf Mo 12.01."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ustva_jan = [f for f in kalender if f.name == "UStVA" and f.datum.month == 1]
        assert len(ustva_jan) == 1
        # 10.01.2026 ist Samstag -> naechster Werktag ist Montag 12.01.
        assert ustva_jan[0].datum == date(2026, 1, 12)

    def test_gewst_15_februar_2026(self):
        """GewSt-VZ am 15.02.2026 (Sonntag) -> Montag 16.02."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        gewst_feb = [f for f in kalender if f.name == "GewSt-Vorauszahlung" and f.datum.month == 2]
        assert len(gewst_feb) == 1
        # 15.02.2026 ist Sonntag -> 16.02. Montag
        assert gewst_feb[0].datum == date(2026, 2, 16)

    def test_jahresabschluss_30_juni_2026(self):
        """Jahresabschluss-Aufstellung am 30.06.2026 (Dienstag)."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ja = [f for f in kalender if f.name == "Jahresabschluss Aufstellung"]
        assert len(ja) == 1
        assert ja[0].datum == date(2026, 6, 30)

    def test_steuererklaerung_31_juli_2026(self):
        """Steuererklaerung am 31.07.2026 (Freitag)."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ste = [f for f in kalender if f.name == "Steuererklaerung (ohne StB)"]
        assert len(ste) == 1
        assert ste[0].datum == date(2026, 7, 31)

    def test_inventur_immer_31_dezember(self):
        """Inventur ist immer am 31.12., unabhaengig vom Wochentag."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        inv = [f for f in kalender if f.name == "Inventur"]
        assert len(inv) == 1
        assert inv[0].datum == date(2026, 12, 31)

    def test_sv_nachweis_vor_zahlung(self):
        """SV-Beitragsnachweis liegt immer vor der SV-Beitragszahlung."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        for monat in range(1, 13):
            nachweis = [
                f for f in kalender if f.name == "SV-Beitragsnachweis" and f.datum.month == monat
            ]
            zahlung = [
                f for f in kalender if f.name == "SV-Beitragszahlung" and f.datum.month == monat
            ]
            if nachweis and zahlung:
                assert nachweis[0].datum <= zahlung[0].datum, (
                    f"Monat {monat}: Nachweis ({nachweis[0].datum}) "
                    f"nach Zahlung ({zahlung[0].datum})"
                )


# ---------------------------------------------------------------------------
# Prioritaeten und Kategorien
# ---------------------------------------------------------------------------


class TestPrioritaetenUndKategorien:
    def test_ustva_ist_critical(self):
        """UStVA hat Prioritaet critical."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ustva = [f for f in kalender if f.name == "UStVA"]
        for f in ustva:
            assert f.prioritaet == Prioritaet.CRITICAL

    def test_lohnsteuer_ist_critical(self):
        """Lohnsteueranmeldung hat Prioritaet critical."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        lst = [f for f in kalender if f.name == "Lohnsteueranmeldung"]
        for f in lst:
            assert f.prioritaet == Prioritaet.CRITICAL

    def test_sv_ist_critical(self):
        """SV-Fristen haben Prioritaet critical."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        sv = [f for f in kalender if f.name.startswith("SV-")]
        for f in sv:
            assert f.prioritaet == Prioritaet.CRITICAL

    def test_gewst_ist_high(self):
        """GewSt-VZ hat Prioritaet high."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        gewst = [f for f in kalender if f.name == "GewSt-Vorauszahlung"]
        for f in gewst:
            assert f.prioritaet == Prioritaet.HIGH

    def test_kst_ist_high(self):
        """KSt-VZ hat Prioritaet high."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        kst = [f for f in kalender if f.name == "KSt-Vorauszahlung"]
        for f in kst:
            assert f.prioritaet == Prioritaet.HIGH

    def test_offenlegung_ist_critical(self):
        """Offenlegung Bundesanzeiger hat Prioritaet critical."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        offen = [f for f in kalender if f.name == "Offenlegung Bundesanzeiger"]
        assert len(offen) == 1
        assert offen[0].prioritaet == Prioritaet.CRITICAL

    def test_steuererklaerung_ist_critical(self):
        """Steuererklaerung ohne StB hat Prioritaet critical."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ste = [f for f in kalender if f.name == "Steuererklaerung (ohne StB)"]
        assert len(ste) == 1
        assert ste[0].prioritaet == Prioritaet.CRITICAL

    def test_ustva_kategorie_steuer(self):
        """UStVA gehoert zur Kategorie Steuer."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ustva = [f for f in kalender if f.name == "UStVA"]
        for f in ustva:
            assert f.kategorie == Kategorie.STEUER

    def test_jahresabschluss_kategorie_buchhaltung(self):
        """Jahresabschluss gehoert zur Kategorie Buchhaltung."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ja = [f for f in kalender if f.name == "Jahresabschluss Aufstellung"]
        assert len(ja) == 1
        assert ja[0].kategorie == Kategorie.BUCHHALTUNG

    def test_sv_nachweis_kategorie_meldung(self):
        """SV-Beitragsnachweis gehoert zur Kategorie Meldung."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        sv = [f for f in kalender if f.name == "SV-Beitragsnachweis"]
        for f in sv:
            assert f.kategorie == Kategorie.MELDUNG


# ---------------------------------------------------------------------------
# Beschreibungen
# ---------------------------------------------------------------------------


class TestBeschreibungen:
    def test_ustva_beschreibung_enthaelt_bezugsmonat(self):
        """UStVA-Beschreibung nennt den Bezugsmonat (Vormonat)."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        # UStVA im Maerz bezieht sich auf Februar
        ustva_maerz = [f for f in kalender if f.name == "UStVA" and f.datum.month == 3]
        assert len(ustva_maerz) == 1
        assert "02/2026" in ustva_maerz[0].beschreibung

    def test_ustva_januar_bezieht_sich_auf_dezember_vorjahr(self):
        """UStVA im Januar bezieht sich auf Dezember des Vorjahres."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ustva_jan = [f for f in kalender if f.name == "UStVA" and f.datum.month == 1]
        assert len(ustva_jan) == 1
        assert "12/2025" in ustva_jan[0].beschreibung

    def test_ustva_beschreibung_enthaelt_schonfrist(self):
        """UStVA-Beschreibung erwaehnt die Schonfrist."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ustva = [f for f in kalender if f.name == "UStVA"][0]
        assert "Schonfrist" in ustva.beschreibung

    def test_offenlegung_beschreibung_erwaehnt_ordnungsgeld(self):
        """Offenlegung erwaehnt das Ordnungsgeld."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        offen = [f for f in kalender if f.name == "Offenlegung Bundesanzeiger"]
        assert len(offen) == 1
        assert "Ordnungsgeld" in offen[0].beschreibung

    def test_jahresabschluss_beschreibung_erwaehnt_vorjahr(self):
        """Jahresabschluss-Beschreibung referenziert das Geschaeftsjahr (Vorjahr)."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ja = [f for f in kalender if f.name == "Jahresabschluss Aufstellung"]
        assert len(ja) == 1
        assert "2025" in ja[0].beschreibung


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_tracker_ohne_heute(self):
        """Tracker ohne explizites Datum verwendet date.today()."""
        tracker = DeadlineTracker()
        assert tracker.heute == date.today()

    def test_upcoming_leeres_ergebnis(self):
        """Sehr kurzer Zeitraum kann leeres Ergebnis liefern."""
        # 01.01.2026 ist Donnerstag (Neujahr = Feiertag)
        # Keine Fristen am 01.01. selbst
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        fristen = tracker.get_upcoming(tage=0)
        # Es koennte Fristen geben oder nicht, aber es darf nicht crashen
        assert isinstance(fristen, list)

    def test_kalender_anderes_jahr(self):
        """Kalender fuer ein anderes Jahr funktioniert."""
        tracker = DeadlineTracker(heute=date(2026, 3, 3))
        kalender = tracker.get_annual_calendar(2025)
        assert len(kalender) > 0

    def test_wiederkehrend_flag_monatlich(self):
        """Monatliche Fristen sind als wiederkehrend markiert."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        monatliche = [f for f in kalender if f.name == "UStVA"]
        for f in monatliche:
            assert f.wiederkehrend is True

    def test_wiederkehrend_flag_jaehrlich(self):
        """Jaehrliche Fristen sind als NICHT wiederkehrend markiert."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        ja = [f for f in kalender if f.name == "Jahresabschluss Aufstellung"]
        assert len(ja) == 1
        assert ja[0].wiederkehrend is False

    def test_fristen_nur_werktage_ausser_inventur(self):
        """Alle Fristen (ausser Inventur) fallen auf Werktage."""
        tracker = DeadlineTracker(heute=date(2026, 1, 1))
        kalender = tracker.get_annual_calendar(2026)
        for f in kalender:
            if f.name == "Inventur":
                # Inventur ist immer am 31.12., auch an Wochenenden
                continue
            assert ist_werktag(f.datum), (
                f"{f.name} am {f.datum} ({f.datum.strftime('%A')}) ist kein Werktag"
            )
