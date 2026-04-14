"""Tests für collmex.accounts — SKR03 Kontenrahmen."""

from __future__ import annotations

import pytest

from collmex.accounts import (
    SKR03,
    Account,
    find_accounts,
    get_account,
    get_accounts_by_type,
    is_valid_account,
    suggest_account,
)

# ---------------------------------------------------------------------------
# 1. Account-Dataclass
# ---------------------------------------------------------------------------


class TestAccountDataclass:
    def test_account_creation(self) -> None:
        acct = Account(nr=1200, bezeichnung="Bank", typ="aktiv")
        assert acct.nr == 1200
        assert acct.bezeichnung == "Bank"
        assert acct.typ == "aktiv"

    def test_account_is_frozen(self) -> None:
        acct = Account(nr=1200, bezeichnung="Bank", typ="aktiv")
        with pytest.raises(AttributeError):
            acct.nr = 9999  # type: ignore[misc]

    def test_account_invalid_typ_raises(self) -> None:
        with pytest.raises(ValueError, match="Ungültiger Kontotyp"):
            Account(nr=9999, bezeichnung="Egal", typ="fantasy")


# ---------------------------------------------------------------------------
# 2. Vollständigkeit des Kontenrahmen
# ---------------------------------------------------------------------------


class TestSKR03Vollständigkeit:
    """Prüft, dass alle spezifizierten Konten vorhanden sind."""

    EXPECTED_AKTIV = [400, 600, 1000, 1200, 1300, 1400, 1500, 1570, 1571, 1576, 1580, 1780]
    EXPECTED_PASSIV = [970, 1600, 1700, 1770, 1771, 1776, 1790, 1800, 1810, 1820, 1860]
    EXPECTED_AUFWAND = [
        4100,
        4110,
        4120,
        4200,
        4210,
        4220,
        4300,
        4400,
        4410,
        4420,
        4430,
        4440,
        4510,
        4600,
        4630,
        4700,
        4730,
        4800,
        4810,
        4822,
        4830,
        4900,
        4910,
    ]
    EXPECTED_ERTRAG = [8100, 8200, 8300, 8400, 8500, 8700]

    def test_alle_aktiv_konten_vorhanden(self) -> None:
        for nr in self.EXPECTED_AKTIV:
            assert nr in SKR03, f"Konto {nr} fehlt im SKR03"
            assert SKR03[nr].typ == "aktiv", f"Konto {nr} hat falschen Typ"

    def test_alle_passiv_konten_vorhanden(self) -> None:
        for nr in self.EXPECTED_PASSIV:
            assert nr in SKR03, f"Konto {nr} fehlt im SKR03"
            assert SKR03[nr].typ == "passiv", f"Konto {nr} hat falschen Typ"

    def test_alle_aufwand_konten_vorhanden(self) -> None:
        for nr in self.EXPECTED_AUFWAND:
            assert nr in SKR03, f"Konto {nr} fehlt im SKR03"
            assert SKR03[nr].typ == "aufwand", f"Konto {nr} hat falschen Typ"

    def test_alle_ertrag_konten_vorhanden(self) -> None:
        for nr in self.EXPECTED_ERTRAG:
            assert nr in SKR03, f"Konto {nr} fehlt im SKR03"
            assert SKR03[nr].typ == "ertrag", f"Konto {nr} hat falschen Typ"

    def test_gesamtzahl_konten(self) -> None:
        expected_total = (
            len(self.EXPECTED_AKTIV)
            + len(self.EXPECTED_PASSIV)
            + len(self.EXPECTED_AUFWAND)
            + len(self.EXPECTED_ERTRAG)
        )
        assert len(SKR03) == expected_total

    def test_konto_nummern_stimmen_ueberein(self) -> None:
        """Dict-Key muss mit Account.nr uebereinstimmen."""
        for key, acct in SKR03.items():
            assert key == acct.nr, f"Key {key} != Account.nr {acct.nr}"


# ---------------------------------------------------------------------------
# 3. get_account
# ---------------------------------------------------------------------------


class TestGetAccount:
    def test_existierendes_konto(self) -> None:
        acct = get_account(1200)
        assert acct is not None
        assert acct.nr == 1200
        assert "Bank" in acct.bezeichnung

    def test_unbekanntes_konto_gibt_none(self) -> None:
        assert get_account(9999) is None

    def test_konto_0_gibt_none(self) -> None:
        assert get_account(0) is None

    def test_negatives_konto_gibt_none(self) -> None:
        assert get_account(-1) is None

    def test_alle_konten_abrufbar(self) -> None:
        for nr in SKR03:
            acct = get_account(nr)
            assert acct is not None
            assert acct.nr == nr


# ---------------------------------------------------------------------------
# 4. find_accounts
# ---------------------------------------------------------------------------


class TestFindAccounts:
    def test_suche_bank(self) -> None:
        ergebnis = find_accounts("Bank")
        nummern = [a.nr for a in ergebnis]
        assert 1200 in nummern

    def test_suche_case_insensitive(self) -> None:
        gross = find_accounts("BANK")
        klein = find_accounts("bank")
        assert gross == klein

    def test_suche_vorsteuer(self) -> None:
        ergebnis = find_accounts("Vorsteuer")
        nummern = [a.nr for a in ergebnis]
        assert 1570 in nummern
        assert 1571 in nummern
        assert 1576 in nummern
        assert 1580 in nummern

    def test_suche_kein_treffer(self) -> None:
        assert find_accounts("xyznichtvorhanden") == []

    def test_suche_sortiert_nach_nr(self) -> None:
        ergebnis = find_accounts("Umsatzsteuer")
        nummern = [a.nr for a in ergebnis]
        assert nummern == sorted(nummern)

    def test_suche_teilstring(self) -> None:
        ergebnis = find_accounts("Abschreibung")
        nummern = [a.nr for a in ergebnis]
        assert 4822 in nummern
        assert 4830 in nummern


# ---------------------------------------------------------------------------
# 5. is_valid_account
# ---------------------------------------------------------------------------


class TestIsValidAccount:
    def test_gültige_konten(self) -> None:
        assert is_valid_account(1200) is True
        assert is_valid_account(4400) is True
        assert is_valid_account(8400) is True

    def test_ungültige_konten(self) -> None:
        assert is_valid_account(9999) is False
        assert is_valid_account(0) is False
        assert is_valid_account(-1) is False


# ---------------------------------------------------------------------------
# 6. get_accounts_by_type
# ---------------------------------------------------------------------------


class TestGetAccountsByType:
    def test_aktiv_konten(self) -> None:
        konten = get_accounts_by_type("aktiv")
        assert len(konten) == 12
        assert all(a.typ == "aktiv" for a in konten)

    def test_passiv_konten(self) -> None:
        konten = get_accounts_by_type("passiv")
        assert len(konten) == 11
        assert all(a.typ == "passiv" for a in konten)

    def test_aufwand_konten(self) -> None:
        konten = get_accounts_by_type("aufwand")
        assert len(konten) == 23
        assert all(a.typ == "aufwand" for a in konten)

    def test_ertrag_konten(self) -> None:
        konten = get_accounts_by_type("ertrag")
        assert len(konten) == 6
        assert all(a.typ == "ertrag" for a in konten)

    def test_sortiert_nach_nr(self) -> None:
        for typ in ("aktiv", "passiv", "aufwand", "ertrag"):
            konten = get_accounts_by_type(typ)
            nummern = [a.nr for a in konten]
            assert nummern == sorted(nummern), f"{typ}-Konten nicht sortiert"

    def test_ungültiger_typ_raises(self) -> None:
        with pytest.raises(ValueError, match="Ungültiger Typ"):
            get_accounts_by_type("ungültig")


# ---------------------------------------------------------------------------
# 7. suggest_account — Keyword-Matching
# ---------------------------------------------------------------------------


class TestSuggestAccount:
    """Prüft alle Keyword-Mappings aus der Spezifikation."""

    # Bürobedarf
    @pytest.mark.parametrize("keyword", ["büromaterial", "büro", "papier", "toner"])
    def test_bürobedarf(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4400

    # Software / immat. VG
    @pytest.mark.parametrize(
        "keyword", ["software", "lizenz", "saas", "cloud", "hosting", "domain"]
    )
    def test_software(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4830

    # Beratung
    @pytest.mark.parametrize("keyword", ["beratung", "steuerberater", "anwalt"])
    def test_beratung(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4800

    # Miete
    @pytest.mark.parametrize("keyword", ["miete", "pacht"])
    def test_miete(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4210

    # Nebenkosten
    @pytest.mark.parametrize("keyword", ["strom", "heizung", "gas", "wasser"])
    def test_nebenkosten(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4220

    # Telefon/Internet
    @pytest.mark.parametrize("keyword", ["telefon", "internet", "mobilfunk"])
    def test_telefon(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4420

    # Porto
    @pytest.mark.parametrize("keyword", ["porto", "versand", "dhl"])
    def test_porto(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4410

    # Kfz
    @pytest.mark.parametrize("keyword", ["benzin", "tanken", "kfz"])
    def test_kfz(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4510

    # Reise
    @pytest.mark.parametrize("keyword", ["hotel", "flug", "bahn", "taxi", "reise"])
    def test_reise(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4600

    # Bewirtung
    @pytest.mark.parametrize("keyword", ["essen", "bewirtung", "restaurant"])
    def test_bewirtung(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4630

    # Werbung
    @pytest.mark.parametrize("keyword", ["werbung", "google_ads", "anzeige"])
    def test_werbung(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4730

    # Versicherung
    @pytest.mark.parametrize("keyword", ["versicherung", "haftpflicht"])
    def test_versicherung(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4430

    # Beiträge
    @pytest.mark.parametrize("keyword", ["ihk", "beitrag", "mitgliedschaft"])
    def test_beiträge(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4440

    # Bank
    @pytest.mark.parametrize("keyword", ["bank", "kontoführung"])
    def test_bank(self, keyword: str) -> None:
        assert suggest_account(keyword) == 4810

    # Fallback
    def test_fallback_auf_4900(self) -> None:
        assert suggest_account("irgendwas unbekanntes") == 4900

    def test_fallback_leerstring(self) -> None:
        assert suggest_account("") == 4900

    # Case-insensitive
    def test_case_insensitive(self) -> None:
        assert suggest_account("BÜROMATERIAL") == 4400
        assert suggest_account("Software-Lizenz") == 4830

    # Keyword als Teil eines längeren Satzes
    def test_keyword_in_satz(self) -> None:
        assert suggest_account("Rechnung für Büromaterial Amazon") == 4400
        assert suggest_account("Monatsrechnung Hosting Hetzner") == 4830
        assert suggest_account("Tankstellenquittung Shell benzin") == 4510
