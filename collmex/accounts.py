"""SKR03 Kontenrahmen.

Stellt den vollständigen Kontenplan als typisiertes Dictionary bereit
sowie Hilfsfunktionen für Kontensuche, Validierung und Kontierungsvorschläge.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Account:
    """Ein Konto im SKR03 Kontenrahmen.

    Attributes:
        nr: Kontonummer (z.B. 1200).
        bezeichnung: Bezeichnung des Kontos.
        typ: Einer von "aktiv", "passiv", "aufwand", "ertrag".
    """

    nr: int
    bezeichnung: str
    typ: str

    def __post_init__(self) -> None:
        if self.typ not in ("aktiv", "passiv", "aufwand", "ertrag"):
            raise ValueError(
                f"Ungültiger Kontotyp '{self.typ}'. Erlaubt: aktiv, passiv, aufwand, ertrag"
            )


# ---------------------------------------------------------------------------
# SKR03 Kontenrahmen: alle relevanten Konten
# ---------------------------------------------------------------------------

SKR03: dict[int, Account] = {
    # --- Bestandskonten (Aktiv) ------------------------------------------------
    400: Account(400, "Technische Anlagen und Maschinen", "aktiv"),
    600: Account(600, "Betriebs- und Geschäftsausstattung", "aktiv"),
    1000: Account(1000, "Kasse", "aktiv"),
    1200: Account(1200, "Bank", "aktiv"),
    1300: Account(1300, "Weitere Bankkonten", "aktiv"),
    1400: Account(1400, "Forderungen aus Lieferungen und Leistungen", "aktiv"),
    1500: Account(1500, "Sonstige Forderungen", "aktiv"),
    1570: Account(1570, "Abziehbare Vorsteuer", "aktiv"),
    1571: Account(1571, "Abziehbare Vorsteuer 7%", "aktiv"),
    1576: Account(1576, "Abziehbare Vorsteuer 19%", "aktiv"),
    1580: Account(1580, "Vorsteuer nach §13b UStG", "aktiv"),
    1780: Account(1780, "Umsatzsteuer-Vorauszahlung", "aktiv"),
    # --- Bestandskonten (Passiv) -----------------------------------------------
    970: Account(970, "Sonstige Rückstellungen", "passiv"),
    1600: Account(1600, "Verbindlichkeiten aus Lieferungen und Leistungen", "passiv"),
    1700: Account(1700, "Sonstige Verbindlichkeiten", "passiv"),
    1770: Account(1770, "Umsatzsteuer", "passiv"),
    1771: Account(1771, "Umsatzsteuer 7%", "passiv"),
    1776: Account(1776, "Umsatzsteuer 19%", "passiv"),
    1790: Account(1790, "Umsatzsteuer Vorjahr", "passiv"),
    1800: Account(1800, "Gezeichnetes Kapital", "passiv"),
    1810: Account(1810, "Kapitalrücklage", "passiv"),
    1820: Account(1820, "Gesellschafter-Darlehen", "passiv"),
    1860: Account(1860, "Gewinnvortrag", "passiv"),
    # --- Aufwandskonten --------------------------------------------------------
    4100: Account(4100, "Löhne und Gehälter", "aufwand"),
    4110: Account(4110, "Gesetzliche Sozialaufwendungen", "aufwand"),
    4120: Account(4120, "Freiwillige Sozialaufwendungen", "aufwand"),
    4200: Account(4200, "Raumkosten", "aufwand"),
    4210: Account(4210, "Miete", "aufwand"),
    4220: Account(4220, "Nebenkosten", "aufwand"),
    4300: Account(4300, "Instandhaltung und Reparatur", "aufwand"),
    4400: Account(4400, "Bürobedarf", "aufwand"),
    4410: Account(4410, "Porto", "aufwand"),
    4420: Account(4420, "Telefon und Internet", "aufwand"),
    4430: Account(4430, "Versicherungen", "aufwand"),
    4440: Account(4440, "Beiträge und Mitgliedschaften", "aufwand"),
    4510: Account(4510, "Kfz-Kosten", "aufwand"),
    4600: Account(4600, "Reisekosten", "aufwand"),
    4630: Account(4630, "Bewirtungskosten", "aufwand"),
    4700: Account(4700, "Kosten der Warenabgabe", "aufwand"),
    4730: Account(4730, "Werbekosten", "aufwand"),
    4800: Account(4800, "Rechts- und Beratungskosten", "aufwand"),
    4810: Account(4810, "Bankgebühren", "aufwand"),
    4822: Account(4822, "Abschreibungen auf Sachanlagen", "aufwand"),
    4830: Account(4830, "Abschreibungen auf immaterielle Vermögensgegenstände", "aufwand"),
    4900: Account(4900, "Sonstige betriebliche Aufwendungen", "aufwand"),
    4910: Account(4910, "Forderungsverluste", "aufwand"),
    # --- Ertragskonten ---------------------------------------------------------
    8100: Account(8100, "Steuerfreie Umsätze", "ertrag"),
    8200: Account(8200, "Erlöse 0%", "ertrag"),
    8300: Account(8300, "Erlöse 7%", "ertrag"),
    8400: Account(8400, "Erlöse 19%", "ertrag"),
    8500: Account(8500, "Sonstige betriebliche Erträge", "ertrag"),
    8700: Account(8700, "Erträge aus dem Abgang von Anlagevermögen", "ertrag"),
}


# ---------------------------------------------------------------------------
# Keyword-Mapping für automatische Kontierungsvorschläge
# ---------------------------------------------------------------------------

# Jeder Eintrag: (Schlüsselwörter-Tuple, Kontonummer)
# Die Reihenfolge bestimmt die Priorität. Spezifischere Begriffe zuerst.
_KEYWORD_MAP: list[tuple[tuple[str, ...], int]] = [
    (("büromaterial", "büro", "papier", "toner"), 4400),
    (("software", "lizenz", "saas", "cloud", "hosting", "domain"), 4830),
    (("beratung", "steuerberater", "anwalt"), 4800),
    (("miete", "pacht"), 4210),
    (("strom", "heizung", "gas", "wasser"), 4220),
    (("telefon", "internet", "mobilfunk"), 4420),
    (("porto", "versand", "dhl"), 4410),
    (("benzin", "tanken", "kfz"), 4510),
    (("hotel", "flug", "bahn", "taxi", "reise"), 4600),
    (("essen", "bewirtung", "restaurant"), 4630),
    (("werbung", "google_ads", "anzeige"), 4730),
    (("versicherung", "haftpflicht"), 4430),
    (("ihk", "beitrag", "mitgliedschaft"), 4440),
    (("bank", "kontoführung"), 4810),
]

_FALLBACK_ACCOUNT = 4900


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------


def get_account(nr: int) -> Account | None:
    """Gibt das Konto mit der angegebenen Nummer zurück oder ``None``."""
    return SKR03.get(nr)


def find_accounts(suchbegriff: str) -> list[Account]:
    """Sucht Konten anhand eines Teilstrings in der Bezeichnung (case-insensitive).

    Args:
        suchbegriff: Suchtext (wird case-insensitive verglichen).

    Returns:
        Liste der passenden Konten, sortiert nach Kontonummer.
    """
    needle = suchbegriff.lower()
    return sorted(
        (acct for acct in SKR03.values() if needle in acct.bezeichnung.lower()),
        key=lambda a: a.nr,
    )


def is_valid_account(nr: int) -> bool:
    """Prüft ob eine Kontonummer im SKR03 existiert."""
    return nr in SKR03


def get_accounts_by_type(typ: str) -> list[Account]:
    """Gibt alle Konten eines bestimmten Typs zurück.

    Args:
        typ: "aktiv", "passiv", "aufwand" oder "ertrag".

    Returns:
        Liste der Konten dieses Typs, sortiert nach Kontonummer.

    Raises:
        ValueError: Bei ungültigem Typ.
    """
    if typ not in ("aktiv", "passiv", "aufwand", "ertrag"):
        raise ValueError(f"Ungültiger Typ '{typ}'. Erlaubt: aktiv, passiv, aufwand, ertrag")
    return sorted(
        (acct for acct in SKR03.values() if acct.typ == typ),
        key=lambda a: a.nr,
    )


def suggest_account(beschreibung: str) -> int:
    """Schlägt anhand einer Beschreibung eine Kontonummer vor (Keyword-Matching).

    Durchsucht die Beschreibung nach bekannten Schlüsselwörtern und gibt
    die zugehörige Kontonummer zurück.  Bei keinem Treffer wird das
    Auffangkonto 4900 (Sonstige betriebliche Aufwendungen) zurückgegeben.

    Args:
        beschreibung: Freitext-Beschreibung des Geschäftsvorfalls.

    Returns:
        Vorgeschlagene Kontonummer.
    """
    text = beschreibung.lower()
    for keywords, konto_nr in _KEYWORD_MAP:
        for kw in keywords:
            if kw in text:
                return konto_nr
    return _FALLBACK_ACCOUNT
