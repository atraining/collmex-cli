"""Dataclasses für das collmex-Projekt.

Alle Geldbeträge verwenden Decimal für exakte kaufmännische Arithmetik.

Collmex-API-Modelle:
- CollmexEingangsrechnung -> CMXLRN (Lieferantenrechnung, 20 Felder)
- CollmexAusgangsrechnung -> CMXUMS (Erlöse/Umsätze, 31 Felder)
- BookingLine/Booking      -> Interne Repräsentation / ACCDOC_GET-Ergebnis
  (ACCDOC kann NICHT importiert werden, nur lesen via ACCDOC_GET)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ValidationError(Exception):
    """Fehler bei der Validierung von Buchungsdaten."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details: dict = details or {}
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Stammdaten
# ---------------------------------------------------------------------------


@dataclass
class Account:
    """Ein Konto aus dem Kontenrahmen (SKR03/SKR04)."""

    konto_nr: int
    bezeichnung: str
    konto_typ: str  # "aktiv" | "passiv" | "aufwand" | "ertrag"
    ust_relevant: bool

    def __post_init__(self) -> None:
        erlaubte_typen = {"aktiv", "passiv", "aufwand", "ertrag"}
        if self.konto_typ not in erlaubte_typen:
            raise ValueError(
                f"konto_typ muss einer von {erlaubte_typen} sein, erhalten: {self.konto_typ!r}"
            )


@dataclass
class CollmexKunde:
    """Kundenstammsatz -> CMXKND (mind. 35 Felder).

    Erzeugt eine CSV-Zeile für den Collmex-Import.
    Bei kunde_nr=None vergibt Collmex automatisch ab 10001.
    """

    firma_nr: int = 1
    kunde_nr: int | None = None
    anrede: str = "Firma"
    name: str = ""  # Idx 7: Firmenname (PFLICHT)
    straße: str = ""
    plz: str = ""
    ort: str = ""
    land: str = "DE"
    telefon: str = ""
    email: str = ""
    ust_id: str = ""
    zahlungsbedingung: str = ""
    ausgabemedium: int = 1  # 1=E-Mail

    def to_csv_line(self) -> str:
        """Generiert die CMXKND-CSV-Zeile (35 Felder, Semikolon-getrennt)."""
        f = [""] * 35
        f[0] = "CMXKND"
        f[1] = str(self.kunde_nr) if self.kunde_nr else ""
        f[2] = str(self.firma_nr)
        f[3] = self.anrede
        f[7] = self.name
        f[9] = self.straße
        f[10] = self.plz
        f[11] = self.ort
        f[14] = self.land
        f[15] = self.telefon
        f[17] = self.email
        f[25] = self.ust_id
        f[29] = str(self.ausgabemedium)
        return ";".join(f)


@dataclass
class CollmexLieferant:
    """Lieferantenstammsatz -> CMXLIF (41 Felder).

    Erzeugt eine CSV-Zeile für den Collmex-Import.
    Bei lieferant_nr=None vergibt Collmex automatisch ab 70001.
    """

    firma_nr: int = 1
    lieferant_nr: int | None = None
    anrede: str = "Firma"
    name: str = ""  # Idx 7: Firmenname (PFLICHT)
    straße: str = ""
    plz: str = ""
    ort: str = ""
    land: str = "DE"
    telefon: str = ""
    email: str = ""
    ust_id: str = ""
    aufwandskonto: int | None = None  # Idx 35: Default-Aufwandskonto
    vorsteuer: int = 0  # 0=19%, 1=7%, 2=steuerfrei
    zahlungsbedingung: str = ""
    url: str = ""

    def to_csv_line(self) -> str:
        """Generiert die CMXLIF-CSV-Zeile (41 Felder, Semikolon-getrennt)."""
        f = [""] * 41
        f[0] = "CMXLIF"
        f[1] = str(self.lieferant_nr) if self.lieferant_nr else ""
        f[2] = str(self.firma_nr)
        f[3] = self.anrede
        f[7] = self.name
        f[9] = self.straße
        f[10] = self.plz
        f[11] = self.ort
        f[14] = self.land
        f[15] = self.telefon
        f[17] = self.email
        f[24] = self.ust_id
        f[25] = self.zahlungsbedingung
        f[35] = str(self.aufwandskonto) if self.aufwandskonto else ""
        f[36] = str(self.vorsteuer)
        f[40] = self.url
        return ";".join(f)


# Backwards-compatible aliases
Customer = CollmexKunde
Supplier = CollmexLieferant


# ---------------------------------------------------------------------------
# Buchungsdaten
# ---------------------------------------------------------------------------


@dataclass
class BookingLine:
    """Eine einzelne Position eines Buchungsbelegs (= eine ACCDOC-Zeile)."""

    positions_nr: int
    konto: int
    bezeichnung: str
    soll_haben: str  # "S" | "H"
    betrag: Decimal
    währung: str = "EUR"
    steuersatz: str = ""
    buchungstext: str = ""
    kostenstelle: str = ""

    def __post_init__(self) -> None:
        if self.soll_haben not in ("S", "H"):
            raise ValueError(f"soll_haben muss 'S' oder 'H' sein, erhalten: {self.soll_haben!r}")
        if not isinstance(self.betrag, Decimal):
            self.betrag = Decimal(str(self.betrag))
        if self.betrag < 0:
            raise ValueError(f"betrag darf nicht negativ sein, erhalten: {self.betrag}")


@dataclass
class Booking:
    """Ein vollständiger Buchungsbeleg mit mehreren Positionen.

    Entspricht einem logischen Geschäftsvorfall, der aus mehreren
    ACCDOC-Zeilen mit gleicher Belegnummer besteht.
    """

    beleg_nr: int | None
    belegdatum: str  # Format: YYYYMMDD
    positionen: list[BookingLine]
    referenz: str = ""
    firma_nr: int = 1

    def __post_init__(self) -> None:
        if len(self.belegdatum) != 8 or not self.belegdatum.isdigit():
            raise ValueError(
                f"belegdatum muss im Format YYYYMMDD sein, erhalten: {self.belegdatum!r}"
            )

    @property
    def summe_soll(self) -> Decimal:
        """Summe aller Soll-Positionen."""
        return sum(
            (p.betrag for p in self.positionen if p.soll_haben == "S"),
            Decimal("0"),
        )

    @property
    def summe_haben(self) -> Decimal:
        """Summe aller Haben-Positionen."""
        return sum(
            (p.betrag for p in self.positionen if p.soll_haben == "H"),
            Decimal("0"),
        )

    def validate(self) -> None:
        """Prüft ob Soll = Haben.  Wirft ValidationError wenn nicht."""
        if not self.positionen:
            raise ValidationError(
                "Buchungsbeleg hat keine Positionen.",
                {"beleg_nr": self.beleg_nr},
            )

        soll = self.summe_soll
        haben = self.summe_haben

        if soll != haben:
            raise ValidationError(
                f"Soll ({soll}) != Haben ({haben}), Differenz: {abs(soll - haben)}",
                {
                    "beleg_nr": self.beleg_nr,
                    "summe_soll": str(soll),
                    "summe_haben": str(haben),
                    "differenz": str(abs(soll - haben)),
                },
            )

    def to_csv_lines(self) -> list[str]:
        """Generiert ACCDOC-CSV-Zeilen für den Collmex-API-Import.

        Jede Position wird zu einer ACCDOC-Zeile.  Die Belegnummer wird
        leer gelassen wenn ``beleg_nr`` None ist (automatische Vergabe).

        Betrag wird im deutschen Format mit Komma als Dezimaltrennzeichen
        ausgegeben, da die Collmex-API dies erwartet.
        """
        lines: list[str] = []
        beleg = str(self.beleg_nr) if self.beleg_nr is not None else ""

        for pos in self.positionen:
            betrag_str = str(pos.betrag).replace(".", ",")
            felder = [
                "ACCDOC",
                str(self.firma_nr),
                beleg,
                str(pos.positions_nr),
                str(pos.konto),
                pos.bezeichnung,
                pos.soll_haben,
                betrag_str,
                pos.währung,
                pos.steuersatz,
                self.belegdatum,
                pos.buchungstext,
                self.referenz,
                pos.kostenstelle,
            ]
            lines.append(";".join(felder))

        return lines


# ---------------------------------------------------------------------------
# Rechnungen
# ---------------------------------------------------------------------------


@dataclass
class Invoice:
    """Eine Rechnung (Ausgangsrechnung)."""

    id: int | None
    kunde_id: int
    datum: str  # Format: YYYYMMDD
    betrag_netto: Decimal
    ust_satz: int  # z.B. 19, 7, 0
    buchungstext: str
    status: str = "offen"

    def __post_init__(self) -> None:
        if not isinstance(self.betrag_netto, Decimal):
            self.betrag_netto = Decimal(str(self.betrag_netto))

    @property
    def ust_betrag(self) -> Decimal:
        """Umsatzsteuerbetrag."""
        return (self.betrag_netto * Decimal(self.ust_satz) / Decimal("100")).quantize(
            Decimal("0.01")
        )

    @property
    def betrag_brutto(self) -> Decimal:
        """Bruttobetrag (netto + USt)."""
        return self.betrag_netto + self.ust_betrag


# ---------------------------------------------------------------------------
# Offene Posten
# ---------------------------------------------------------------------------


@dataclass
class OpenItem:
    """Ein offener Posten (Debitor oder Kreditor)."""

    beleg_nr: int
    kunde_oder_lieferant: str
    typ: str  # "debitor" | "kreditor"
    betrag: Decimal
    datum: str  # Format: YYYYMMDD
    fällig_am: str  # Format: YYYYMMDD
    tage_ueberfällig: int

    def __post_init__(self) -> None:
        if self.typ not in ("debitor", "kreditor"):
            raise ValueError(f"typ muss 'debitor' oder 'kreditor' sein, erhalten: {self.typ!r}")
        if not isinstance(self.betrag, Decimal):
            self.betrag = Decimal(str(self.betrag))

    @property
    def mahnstufe(self) -> int:
        """Mahnstufe basierend auf Tagen überfällig.

        0 = nicht fällig (0-30 Tage oder nicht überfällig)
        1 = 31-60 Tage überfällig
        2 = 61-90 Tage überfällig
        3 = >90 Tage überfällig
        """
        if self.tage_ueberfällig <= 30:
            return 0
        if self.tage_ueberfällig <= 60:
            return 1
        if self.tage_ueberfällig <= 90:
            return 2
        return 3


# ---------------------------------------------------------------------------
# Collmex API Import-Modelle (Schreiben)
# ---------------------------------------------------------------------------


def _fmt(value: Decimal | int | float | str) -> str:
    """Formatiert einen Betrag im Collmex-Format (Komma als Dezimaltrenner)."""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        value = Decimal(str(value))
    return f"{value:.2f}".replace(".", ",")


@dataclass
class CollmexEingangsrechnung:
    """Eingangsrechnung / Lieferantenrechnung -> CMXLRN (20 Felder).

    Collmex erzeugt automatisch die doppelte Buchführung:
    - Aufwandskonto (Soll) gemäß konto_voll/konto_erm/sonstige_konto
    - Vorsteuer (Soll) automatisch berechnet
    - Verbindlichkeiten ggue. Lieferant (Haben) oder Gegenkonto

    Felder:
    1  Satzart           "CMXLRN"
    2  Lieferantennummer  Collmex-Lieferanten-ID (oder leer bei Gegenkonto)
    3  Firma_Nr           Standard: 1
    4  Rechnungsdatum     YYYYMMDD
    5  Rechnungsnummer    Extern oder leer (Collmex vergibt)
    6  Netto voller USt   Nettobetrag 19%
    7  Steuer voller USt  USt-Betrag 19% (leer = Collmex berechnet)
    8  Netto erm. USt     Nettobetrag 7%
    9  Steuer erm. USt    USt-Betrag 7% (leer = Collmex berechnet)
    10 Sonstige: Konto    Aufwandskonto für steuerfreie Beträge
    11 Sonstige: Betrag   Betrag steuerfrei
    12 Währung           ISO-Code (EUR)
    13 Gegenkonto         Alternativ zu Lieferantennummer (z.B. 1200 Bank)
    14 Gutschrift         1 = Gutschrift, sonst leer
    15 Buchungstext       Beschreibung
    16 Zahlungsbedingung  Collmex-Zahlungsbedingung-ID
    17 Konto voller USt   Aufwandskonto für 19%-Anteil
    18 Konto erm. USt     Aufwandskonto für 7%-Anteil
    19 Storno             1 = Storno, sonst leer
    20 Kostenstelle       Kostenstelle
    """

    firma_nr: int = 1
    lieferant_nr: int | None = None
    datum: str = ""  # YYYYMMDD
    rechnungs_nr: str = ""
    netto_voll: Decimal = field(default_factory=lambda: Decimal("0"))
    steuer_voll: Decimal | None = None  # None = Collmex berechnet
    netto_erm: Decimal = field(default_factory=lambda: Decimal("0"))
    steuer_erm: Decimal | None = None
    sonstige_konto: int | None = None
    sonstige_betrag: Decimal = field(default_factory=lambda: Decimal("0"))
    währung: str = "EUR"
    gegenkonto: int | None = None
    gutschrift: bool = False
    buchungstext: str = ""
    zahlungsbedingung: int | None = None
    konto_voll: int | None = None  # Aufwandskonto für 19%-Anteil
    konto_erm: int | None = None  # Aufwandskonto für 7%-Anteil
    storno: bool = False
    kostenstelle: str = ""

    def __post_init__(self) -> None:
        for attr in ("netto_voll", "netto_erm", "sonstige_betrag"):
            val = getattr(self, attr)
            if not isinstance(val, Decimal):
                setattr(self, attr, Decimal(str(val)))
        if self.steuer_voll is not None and not isinstance(self.steuer_voll, Decimal):
            self.steuer_voll = Decimal(str(self.steuer_voll))
        if self.steuer_erm is not None and not isinstance(self.steuer_erm, Decimal):
            self.steuer_erm = Decimal(str(self.steuer_erm))

    @property
    def betrag_netto(self) -> Decimal:
        """Gesamter Nettobetrag."""
        return self.netto_voll + self.netto_erm + self.sonstige_betrag

    @property
    def betrag_brutto(self) -> Decimal:
        """Bruttobetrag (netto + berechnete Steuern)."""
        steuer_v = (
            self.steuer_voll
            if self.steuer_voll is not None
            else (self.netto_voll * Decimal("19") / Decimal("100")).quantize(Decimal("0.01"))
        )
        steuer_e = (
            self.steuer_erm
            if self.steuer_erm is not None
            else (self.netto_erm * Decimal("7") / Decimal("100")).quantize(Decimal("0.01"))
        )
        return self.betrag_netto + steuer_v + steuer_e

    def to_csv_line(self) -> str:
        """Generiert die CMXLRN-CSV-Zeile (20 Felder, Semikolon-getrennt)."""
        felder = [
            "CMXLRN",
            str(self.lieferant_nr) if self.lieferant_nr else "",
            str(self.firma_nr),
            self.datum,
            self.rechnungs_nr,
            _fmt(self.netto_voll) if self.netto_voll else "",
            _fmt(self.steuer_voll) if self.steuer_voll is not None else "",
            _fmt(self.netto_erm) if self.netto_erm else "",
            _fmt(self.steuer_erm) if self.steuer_erm is not None else "",
            str(self.sonstige_konto) if self.sonstige_konto else "",
            _fmt(self.sonstige_betrag) if self.sonstige_betrag else "",
            self.währung,
            str(self.gegenkonto) if self.gegenkonto else "",
            "1" if self.gutschrift else "",
            self.buchungstext,
            str(self.zahlungsbedingung) if self.zahlungsbedingung else "",
            str(self.konto_voll) if self.konto_voll else "",
            str(self.konto_erm) if self.konto_erm else "",
            "1" if self.storno else "",
            self.kostenstelle,
        ]
        return ";".join(felder)


@dataclass
class CollmexAusgangsrechnung:
    """Ausgangsrechnung / Umsatz -> CMXUMS (31 Felder).

    Collmex erzeugt automatisch die doppelte Buchführung:
    - Forderungen (Soll) oder Gegenkonto
    - Erlöskonto (Haben) gemäß konto_voll/konto_erm
    - Umsatzsteuer (Haben) automatisch berechnet

    Felder:
    1  Satzart           "CMXUMS"
    2  Kundennummer       Collmex-Kunden-ID (oder leer bei Gegenkonto)
    3  Firma_Nr           Standard: 1
    4  Rechnungsdatum     YYYYMMDD
    5  Rechnungsnummer    Extern oder leer
    6  Netto voller USt   Nettobetrag 19%
    7  Steuer voller USt  USt-Betrag 19% (leer = Collmex berechnet)
    8  Netto erm. USt     Nettobetrag 7%
    9  Steuer erm. USt    USt-Betrag 7%
    10 IG Lieferung       Innergemeinschaftliche Lieferung (Betrag)
    11 Export             Exportumsätze (Betrag)
    12 Steuerfrei Konto   Erlöskonto für steuerfreie Beträge
    13 Steuerfrei Betrag  Steuerfreier Betrag
    14 Währung           ISO-Code (EUR)
    15 Gegenkonto         Alternativ zu Kundennummer (z.B. 1200 Bank)
    16 Rechnungsart       0=normal, 1=Sammelrechnung
    17 Buchungstext       Beschreibung
    18 Zahlungsbedingung  Collmex-Zahlungsbedingung-ID
    19 Konto voller USt   Erlöskonto für 19%-Anteil (z.B. 8400)
    20 Konto erm. USt     Erlöskonto für 7%-Anteil (z.B. 8300)
    21 Verwendungszweck   Für Banküberweisung
    22 Bestellnummer      Kundenbestellnummer
    23 Storno             1 = Storno
    24 Schlussrechnung    Referenz für Schlussrechnung
    25 Umsatzart          0=normal
    26 Systemname         Externes System
    27 Gutschrift Gegen   Gegenrechnungsnummer bei Gutschrift
    28 Kostenstelle       Kostenstelle
    29 Lastschrift Datum  Ausführungsdatum (YYYYMMDD)
    30 Land               ISO-2 Ländercode
    31 Produktart         Produkt- oder Dienstleistungskennzeichen
    """

    firma_nr: int = 1
    kunde_nr: int | None = None
    datum: str = ""  # YYYYMMDD
    rechnungs_nr: str = ""
    netto_voll: Decimal = field(default_factory=lambda: Decimal("0"))
    steuer_voll: Decimal | None = None
    netto_erm: Decimal = field(default_factory=lambda: Decimal("0"))
    steuer_erm: Decimal | None = None
    ig_lieferung: Decimal = field(default_factory=lambda: Decimal("0"))
    export_umsätze: Decimal = field(default_factory=lambda: Decimal("0"))
    steuerfrei_konto: int | None = None
    steuerfrei_betrag: Decimal = field(default_factory=lambda: Decimal("0"))
    währung: str = "EUR"
    gegenkonto: int | None = None
    rechnungsart: int = 0
    buchungstext: str = ""
    zahlungsbedingung: int | None = None
    konto_voll: int | None = None  # Erlöskonto für 19% (z.B. 8400)
    konto_erm: int | None = None  # Erlöskonto für 7% (z.B. 8300)
    verwendungszweck: str = ""
    bestellnummer: str = ""
    storno: bool = False
    schlussrechnung: str = ""
    umsatzart: int = 0
    systemname: str = ""
    gutschrift_gegen: str = ""
    kostenstelle: str = ""
    lastschrift_datum: str = ""
    land: str = ""
    produktart: int | None = None

    def __post_init__(self) -> None:
        for attr in (
            "netto_voll",
            "netto_erm",
            "ig_lieferung",
            "export_umsätze",
            "steuerfrei_betrag",
        ):
            val = getattr(self, attr)
            if not isinstance(val, Decimal):
                setattr(self, attr, Decimal(str(val)))
        if self.steuer_voll is not None and not isinstance(self.steuer_voll, Decimal):
            self.steuer_voll = Decimal(str(self.steuer_voll))
        if self.steuer_erm is not None and not isinstance(self.steuer_erm, Decimal):
            self.steuer_erm = Decimal(str(self.steuer_erm))

    @property
    def betrag_netto(self) -> Decimal:
        """Gesamter Nettobetrag."""
        return (
            self.netto_voll
            + self.netto_erm
            + self.ig_lieferung
            + self.export_umsätze
            + self.steuerfrei_betrag
        )

    def to_csv_line(self) -> str:
        """Generiert die CMXUMS-CSV-Zeile (31 Felder, Semikolon-getrennt)."""
        felder = [
            "CMXUMS",
            str(self.kunde_nr) if self.kunde_nr else "",
            str(self.firma_nr),
            self.datum,
            self.rechnungs_nr,
            _fmt(self.netto_voll) if self.netto_voll else "",
            _fmt(self.steuer_voll) if self.steuer_voll is not None else "",
            _fmt(self.netto_erm) if self.netto_erm else "",
            _fmt(self.steuer_erm) if self.steuer_erm is not None else "",
            _fmt(self.ig_lieferung) if self.ig_lieferung else "",
            _fmt(self.export_umsätze) if self.export_umsätze else "",
            str(self.steuerfrei_konto) if self.steuerfrei_konto else "",
            _fmt(self.steuerfrei_betrag) if self.steuerfrei_betrag else "",
            self.währung,
            str(self.gegenkonto) if self.gegenkonto else "",
            str(self.rechnungsart) if self.rechnungsart else "",
            self.buchungstext,
            str(self.zahlungsbedingung) if self.zahlungsbedingung else "",
            str(self.konto_voll) if self.konto_voll else "",
            str(self.konto_erm) if self.konto_erm else "",
            self.verwendungszweck,
            self.bestellnummer,
            "1" if self.storno else "",
            self.schlussrechnung,
            str(self.umsatzart) if self.umsatzart else "",
            self.systemname,
            self.gutschrift_gegen,
            self.kostenstelle,
            self.lastschrift_datum,
            self.land,
            str(self.produktart) if self.produktart else "",
        ]
        return ";".join(felder)
