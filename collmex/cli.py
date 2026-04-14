"""collmex CLI — FiBu & Controlling Kommandozeile fuer Collmex.

Verwendet Click als CLI-Framework und Rich fuer formatierte Tabellenausgabe.
"""

from __future__ import annotations

import sys
from datetime import datetime
from decimal import Decimal

# Windows-Konsole: stdout/stderr auf UTF-8 umstellen,
# damit Umlaute aus Collmex (ö, ä, ü) korrekt dargestellt werden.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import click
from rich.console import Console
from rich.table import Table

from collmex import __version__
from collmex.accounts import SKR03, get_account, suggest_account
from collmex.api import CollmexClient, CollmexError
from collmex.models import CollmexKunde, CollmexLieferant

console = Console()
error_console = Console(stderr=True)


# ---------------------------------------------------------------------------
# SectionedGroup — Gruppierte Hilfe-Ausgabe
# ---------------------------------------------------------------------------

# Sektionen: (Titel, [Befehlsnamen])
# Reihenfolge = Reihenfolge in --help
COMMAND_SECTIONS: list[tuple[str, list[str]]] = [
    ("Buchen", ["buchen", "ausgang", "storno"]),
    ("Auswertungen", ["salden", "buchungen", "op", "bwa", "soll-ist", "dashboard"]),
    (
        "Controlling & Steuern",
        ["ustva", "liquiditaet", "mahnlauf", "saeumige", "fristen", "datev-export"],
    ),
    (
        "Stammdaten & API",
        ["lieferant-anlegen", "kunde-anlegen", "abfrage", "hilfe", "konten", "konto"],
    ),
    ("System", ["status", "onboarding", "handbuch", "version", "webui"]),
]


class SectionedGroup(click.Group):
    """Click-Group mit gruppierten Befehlen in --help."""

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        assigned = set()
        for title, names in COMMAND_SECTIONS:
            rows = []
            for name in names:
                cmd = self.commands.get(name)
                if cmd is None or cmd.hidden:
                    continue
                assigned.add(name)
                help_text = cmd.get_short_help_str(limit=formatter.width)
                rows.append((name, help_text))
            if rows:
                with formatter.section(title):
                    formatter.write_dl(rows)

        # Nicht zugeordnete Befehle (Sicherheitsnetz)
        rest = []
        for name in self.list_commands(ctx):
            if name in assigned:
                continue
            cmd = self.commands.get(name)
            if cmd is None or cmd.hidden:
                continue
            rest.append((name, cmd.get_short_help_str(limit=formatter.width)))
        if rest:
            with formatter.section("Weitere"):
                formatter.write_dl(rest)


# ---------------------------------------------------------------------------
# Globaler Kontext
# ---------------------------------------------------------------------------


class CliContext:
    """Globaler Kontext, der zwischen Commands geteilt wird."""

    def __init__(self, verbose: bool = False, json_output: bool = False) -> None:
        self.verbose = verbose
        self.json_output = json_output
        self._client: CollmexClient | None = None
        self._booking_engine = None
        self._reports_engine = None

    @property
    def client(self) -> CollmexClient:
        if self._client is None:
            try:
                self._client = CollmexClient()
            except CollmexError as exc:
                error_console.print(f"[bold red]Fehler:[/] {exc}")
                sys.exit(1)
        return self._client

    @client.setter
    def client(self, value: CollmexClient) -> None:
        self._client = value

    @property
    def booking_engine(self):
        if self._booking_engine is None:
            from collmex.booking import BookingEngine

            self._booking_engine = BookingEngine(self.client)
        return self._booking_engine

    @property
    def reports_engine(self):
        if self._reports_engine is None:
            from collmex.reports import ReportsEngine

            self._reports_engine = ReportsEngine(self.client)
        return self._reports_engine


pass_ctx = click.make_pass_decorator(CliContext, ensure=True)


# ---------------------------------------------------------------------------
# Hauptgruppe
# ---------------------------------------------------------------------------


@click.group(cls=SectionedGroup)
@click.option("--verbose", "-v", is_flag=True, help="Ausfuehrliche Ausgabe")
@click.option("--json", "json_output", is_flag=True, help="Ausgabe als JSON")
@click.pass_context
def main(ctx: click.Context, verbose: bool, json_output: bool) -> None:
    """collmex -- FiBu & Controlling CLI fuer Collmex."""
    ctx.ensure_object(CliContext)
    ctx.obj.verbose = verbose
    ctx.obj.json_output = json_output


# ---------------------------------------------------------------------------
# Befehle
# ---------------------------------------------------------------------------


@main.command()
@pass_ctx
def status(ctx: CliContext) -> None:
    """API-Verbindungstest und Kurzuebersicht."""
    try:
        ok = ctx.client.status()
    except CollmexError as exc:
        error_console.print(f"[bold red]Verbindungsfehler:[/] {exc}")
        sys.exit(1)

    if ok:
        console.print("[bold green]Verbindung OK[/]")
        if ctx.verbose:
            console.print(f"  URL:    {ctx.client.url}")
            console.print(f"  User:   {ctx.client.user}")
            console.print(f"  Kunde:  {ctx.client.customer}")
            console.print(f"  Firma:  {ctx.client.company}")
    else:
        error_console.print("[bold red]Verbindung fehlgeschlagen[/]")
        sys.exit(1)


@main.command()
@click.argument("beschreibung")
@click.option("--betrag", type=float, required=True, help="Nettobetrag")
@click.option("--lieferant", type=int, required=True, help="Collmex-Lieferantennummer (Pflicht!)")
@click.option("--konto", type=int, default=None, help="Aufwandskonto (auto wenn leer)")
@click.option("--ust", type=int, default=19, help="USt-Satz in Prozent (Standard: 19)")
@click.option("--datum", default=None, help="Belegdatum YYYYMMDD (Standard: heute)")
@click.option("--rechnungsnr", default="", help="Externe Rechnungsnummer")
@click.option("--dry-run", is_flag=True, help="Nur anzeigen, nicht buchen")
@pass_ctx
def buchen(
    ctx: CliContext,
    beschreibung: str,
    betrag: float,
    lieferant: int,
    konto: int | None,
    ust: int,
    datum: str | None,
    rechnungsnr: str,
    dry_run: bool,
) -> None:
    """Eingangsrechnung buchen (ueber Nebenbuch/Personenkonto)."""
    if datum is None:
        datum = datetime.now().strftime("%Y%m%d")

    if konto is None:
        konto = suggest_account(beschreibung)
        konto_info = get_account(konto)
        konto_name = konto_info.bezeichnung if konto_info else str(konto)
        console.print(f"Auto-Konto: [cyan]{konto}[/] ({konto_name})")

    engine = ctx.booking_engine
    betrag_decimal = Decimal(str(betrag))
    ust_betrag = (betrag_decimal * Decimal(ust) / Decimal("100")).quantize(Decimal("0.01"))
    brutto = betrag_decimal + ust_betrag

    # Buchungssatz anzeigen
    table = Table(title="Buchungssatz")
    table.add_column("Pos", style="dim", width=4)
    table.add_column("Konto", style="cyan", width=6)
    table.add_column("Bezeichnung", width=30)
    table.add_column("S/H", width=4)
    table.add_column("Betrag", justify="right", style="green", width=12)

    konto_info = get_account(konto)
    konto_name = konto_info.bezeichnung if konto_info else str(konto)

    table.add_row("1", str(konto), konto_name, "S", f"{betrag_decimal:,.2f} EUR")

    if ust > 0:
        vst_konto = 1576 if ust == 19 else (1571 if ust == 7 else 1570)
        table.add_row("2", str(vst_konto), f"Vorsteuer {ust}%", "S", f"{ust_betrag:,.2f} EUR")
    table.add_row(
        "3" if ust > 0 else "2", str(lieferant), f"Lieferant {lieferant}", "H", f"{brutto:,.2f} EUR"
    )

    console.print(table)
    console.print(f"Text: {beschreibung}")
    console.print(f"Datum: {datum}")
    if rechnungsnr:
        console.print(f"Rechnungs-Nr: {rechnungsnr}")

    if dry_run:
        console.print("\n[yellow]--dry-run: Buchung wurde NICHT ausgefuehrt.[/]")
        return

    try:
        booking = engine.create_eingangsrechnung(
            betrag_netto=betrag_decimal,
            ust_satz=ust,
            aufwandskonto=konto,
            buchungstext=beschreibung,
            belegdatum=datum,
            lieferant_nr=lieferant,
            rechnungs_nr=rechnungsnr,
        )
        result = engine.post_and_validate(booking)

        if result.ok:
            console.print(f"\n[bold green]Buchung erfolgreich![/] Beleg-Nr: {result.beleg_nr}")
        else:
            error_console.print("\n[bold red]Buchung fehlgeschlagen:[/]")
            for fehler in result.fehler:
                error_console.print(f"  - {fehler}")
            sys.exit(1)
    except Exception as exc:
        error_console.print(f"\n[bold red]Fehler:[/] {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Stammdaten anlegen
# ---------------------------------------------------------------------------


@main.command(name="lieferant-anlegen")
@click.option("--name", required=True, help="Firmenname (Pflicht)")
@click.option("--strasse", default="", help="Strasse")
@click.option("--plz", default="", help="PLZ")
@click.option("--ort", default="", help="Ort")
@click.option("--land", default="DE", help="Land (ISO-2, Standard: DE)")
@click.option("--email", default="", help="E-Mail")
@click.option("--ust-id", default="", help="USt-IdNr (z.B. DE123456789)")
@click.option("--aufwandskonto", type=int, default=None, help="Standard-Aufwandskonto (z.B. 4900)")
@click.option("--dry-run", is_flag=True, help="Nur anzeigen, nicht anlegen")
@pass_ctx
def lieferant_anlegen(
    ctx: CliContext,
    name: str,
    strasse: str,
    plz: str,
    ort: str,
    land: str,
    email: str,
    ust_id: str,
    aufwandskonto: int | None,
    dry_run: bool,
) -> None:
    """Neuen Lieferanten anlegen (CMXLIF)."""
    lif = CollmexLieferant(
        name=name,
        strasse=strasse,
        plz=plz,
        ort=ort,
        land=land,
        email=email,
        ust_id=ust_id,
        aufwandskonto=aufwandskonto,
    )

    # Preview-Tabelle
    table = Table(title="Neuer Lieferant")
    table.add_column("Feld", style="cyan", width=20)
    table.add_column("Wert", width=40)
    table.add_row("Name", name)
    if strasse:
        table.add_row("Strasse", strasse)
    if plz or ort:
        table.add_row("PLZ / Ort", f"{plz} {ort}".strip())
    table.add_row("Land", land)
    if email:
        table.add_row("E-Mail", email)
    if ust_id:
        table.add_row("USt-IdNr", ust_id)
    if aufwandskonto:
        table.add_row("Aufwandskonto", str(aufwandskonto))
    console.print(table)

    if dry_run:
        console.print("\n[yellow]--dry-run: Lieferant wurde NICHT angelegt.[/]")
        console.print(f"CSV: {lif.to_csv_line()}")
        return

    try:
        engine = ctx.booking_engine
        neue_nr = engine.post_stammdaten(lif)
        console.print(f"\n[bold green]Lieferant angelegt![/] Nr: {neue_nr}")
    except CollmexError as exc:
        error_console.print(f"\n[bold red]Fehler:[/] {exc}")
        sys.exit(1)


@main.command(name="kunde-anlegen")
@click.option("--name", required=True, help="Firmenname (Pflicht)")
@click.option("--strasse", default="", help="Strasse")
@click.option("--plz", default="", help="PLZ")
@click.option("--ort", default="", help="Ort")
@click.option("--land", default="DE", help="Land (ISO-2, Standard: DE)")
@click.option("--email", default="", help="E-Mail")
@click.option("--ust-id", default="", help="USt-IdNr (z.B. DE123456789)")
@click.option("--dry-run", is_flag=True, help="Nur anzeigen, nicht anlegen")
@pass_ctx
def kunde_anlegen(
    ctx: CliContext,
    name: str,
    strasse: str,
    plz: str,
    ort: str,
    land: str,
    email: str,
    ust_id: str,
    dry_run: bool,
) -> None:
    """Neuen Kunden anlegen (CMXKND)."""
    knd = CollmexKunde(
        name=name,
        strasse=strasse,
        plz=plz,
        ort=ort,
        land=land,
        email=email,
        ust_id=ust_id,
    )

    # Preview-Tabelle
    table = Table(title="Neuer Kunde")
    table.add_column("Feld", style="cyan", width=20)
    table.add_column("Wert", width=40)
    table.add_row("Name", name)
    if strasse:
        table.add_row("Strasse", strasse)
    if plz or ort:
        table.add_row("PLZ / Ort", f"{plz} {ort}".strip())
    table.add_row("Land", land)
    if email:
        table.add_row("E-Mail", email)
    if ust_id:
        table.add_row("USt-IdNr", ust_id)
    console.print(table)

    if dry_run:
        console.print("\n[yellow]--dry-run: Kunde wurde NICHT angelegt.[/]")
        console.print(f"CSV: {knd.to_csv_line()}")
        return

    try:
        engine = ctx.booking_engine
        neue_nr = engine.post_stammdaten(knd)
        console.print(f"\n[bold green]Kunde angelegt![/] Nr: {neue_nr}")
    except CollmexError as exc:
        error_console.print(f"\n[bold red]Fehler:[/] {exc}")
        sys.exit(1)


@main.command()
@click.option("--monat", type=int, default=None, help="Buchungsperiode (1-12)")
@click.option("--jahr", type=int, default=None, help="Geschaeftsjahr")
@pass_ctx
def salden(ctx: CliContext, monat: int | None, jahr: int | None) -> None:
    """Kontensalden anzeigen (ACCBAL_GET)."""
    now = datetime.now()
    if jahr is None:
        jahr = now.year
    if monat is None:
        monat = now.month

    try:
        reports = ctx.reports_engine
        susa_daten = reports.susa(jahr, monat)
    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    if not susa_daten:
        console.print("[yellow]Keine Kontensalden fuer diesen Zeitraum.[/]")
        return

    table = Table(title=f"Kontensalden {monat:02d}/{jahr}")
    table.add_column("Konto", style="cyan", width=6)
    table.add_column("Bezeichnung", width=45)
    table.add_column("Saldo", justify="right", width=14)

    for konto in susa_daten:
        saldo = konto["saldo"]
        saldo_style = "green" if saldo >= 0 else "red"
        table.add_row(
            str(konto["konto_nr"]),
            konto["bezeichnung"],
            f"[{saldo_style}]{saldo:,.2f} EUR[/]",
        )

    console.print(table)


@main.command()
@click.option("--monat", type=int, default=None, help="Buchungsperiode (1-12)")
@click.option("--jahr", type=int, default=None, help="Geschaeftsjahr")
@pass_ctx
def bwa(ctx: CliContext, monat: int | None, jahr: int | None) -> None:
    """Betriebswirtschaftliche Auswertung."""
    now = datetime.now()
    if jahr is None:
        jahr = now.year
    if monat is None:
        monat = now.month

    try:
        reports = ctx.reports_engine
        bwa_daten = reports.bwa(jahr, monat)
    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    table = Table(title=f"BWA {monat:02d}/{jahr}")
    table.add_column("Position", width=35)
    table.add_column("Betrag", justify="right", style="green", width=14)

    for pos in bwa_daten["positionen"]:
        bezeichnung = pos["bezeichnung"]
        betrag = pos["betrag"]
        style = "bold green" if bezeichnung == "Betriebsergebnis" else None
        if bezeichnung == "Summe Kosten":
            style = "bold"
        betrag_style = "red" if betrag < 0 else "green"
        if style:
            table.add_row(
                f"[{style}]{bezeichnung}[/]",
                f"[{betrag_style}]{betrag:,.2f} EUR[/]",
            )
        else:
            table.add_row(bezeichnung, f"[{betrag_style}]{betrag:,.2f} EUR[/]")

    console.print(table)


@main.command()
@pass_ctx
def op(ctx: CliContext) -> None:
    """Offene Posten anzeigen."""
    try:
        reports = ctx.reports_engine
        op_daten = reports.op_liste()
    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    # Debitoren
    if op_daten["debitoren"]:
        table = Table(title="Offene Posten — Debitoren")
        table.add_column("Beleg", style="cyan", width=10)
        table.add_column("Kunde", width=30)
        table.add_column("Datum", width=10)
        table.add_column("Faellig", width=10)
        table.add_column("Betrag", justify="right", style="green", width=14)
        table.add_column("Tage", justify="right", width=6)

        for p in op_daten["debitoren"]:
            tage_style = (
                "red"
                if p["tage_ueberfaellig"] > 30
                else "yellow"
                if p["tage_ueberfaellig"] > 0
                else "green"
            )
            table.add_row(
                p["beleg_nr"],
                p["name"],
                p["datum"],
                p["faellig"],
                f"{p['betrag']:,.2f}",
                f"[{tage_style}]{p['tage_ueberfaellig']}[/]",
            )

        console.print(table)
        console.print(f"Summe Debitoren: [green]{op_daten['summe_debitoren']:,.2f} EUR[/]\n")
    else:
        console.print("[green]Keine offenen Debitoren-Posten.[/]\n")

    # Kreditoren
    if op_daten["kreditoren"]:
        table = Table(title="Offene Posten — Kreditoren")
        table.add_column("Beleg", style="cyan", width=10)
        table.add_column("Lieferant", width=30)
        table.add_column("Datum", width=10)
        table.add_column("Faellig", width=10)
        table.add_column("Betrag", justify="right", style="green", width=14)
        table.add_column("Tage", justify="right", width=6)

        for p in op_daten["kreditoren"]:
            tage_style = (
                "red"
                if p["tage_ueberfaellig"] > 30
                else "yellow"
                if p["tage_ueberfaellig"] > 0
                else "green"
            )
            table.add_row(
                p["beleg_nr"],
                p["name"],
                p["datum"],
                p["faellig"],
                f"{p['betrag']:,.2f}",
                f"[{tage_style}]{p['tage_ueberfaellig']}[/]",
            )

        console.print(table)
        console.print(f"Summe Kreditoren: [green]{op_daten['summe_kreditoren']:,.2f} EUR[/]")
    else:
        console.print("[green]Keine offenen Kreditoren-Posten.[/]")

    # Altersstruktur
    alters = op_daten.get("altersstruktur", {})
    if alters:
        console.print("\n[bold]Altersstruktur Debitoren:[/]")
        console.print(f"  Aktuell (0-30 Tage):    {alters.get('aktuell', 0):>12,.2f} EUR")
        console.print(f"  31-60 Tage:             {alters.get('ueberfaellig_30', 0):>12,.2f} EUR")
        console.print(f"  61-90 Tage:             {alters.get('ueberfaellig_60', 0):>12,.2f} EUR")
        console.print(f"  >90 Tage:               {alters.get('ueberfaellig_90', 0):>12,.2f} EUR")


@main.command()
@pass_ctx
def saeumige(ctx: CliContext) -> None:
    """Saeumige Kunden anzeigen."""
    try:
        reports = ctx.reports_engine
        saeumige_liste = reports.saeumige_kunden()
    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    if not saeumige_liste:
        console.print("[green]Keine saeumigen Kunden.[/]")
        return

    table = Table(title="Saeumige Kunden")
    table.add_column("Kunde", width=30)
    table.add_column("Beleg", style="cyan", width=10)
    table.add_column("Betrag", justify="right", style="green", width=14)
    table.add_column("Faellig", width=10)
    table.add_column("Tage", justify="right", width=6)
    table.add_column("Mahnstufe", justify="center", width=10)

    for kunde in saeumige_liste:
        tage = kunde["tage_ueberfaellig"]
        mahnstufe = kunde["mahnstufe"]
        stufe_style = "red" if mahnstufe >= 2 else "yellow" if mahnstufe == 1 else "green"

        table.add_row(
            kunde["name"],
            kunde["beleg_nr"],
            f"{kunde['betrag']:,.2f}",
            kunde["faellig"],
            str(tage),
            f"[{stufe_style}]{mahnstufe}[/]",
        )

    console.print(table)


@main.command()
@pass_ctx
def konten(ctx: CliContext) -> None:
    """Kontenrahmen SKR03 anzeigen."""
    table = Table(title="Kontenrahmen SKR03")
    table.add_column("Konto", style="cyan", width=6)
    table.add_column("Bezeichnung", width=50)
    table.add_column("Typ", width=10)

    typ_farben = {
        "aktiv": "green",
        "passiv": "blue",
        "aufwand": "red",
        "ertrag": "yellow",
    }

    for nr in sorted(SKR03.keys()):
        acct = SKR03[nr]
        farbe = typ_farben.get(acct.typ, "white")
        table.add_row(
            str(acct.nr),
            acct.bezeichnung,
            f"[{farbe}]{acct.typ}[/]",
        )

    console.print(table)


@main.command()
@click.argument("nummer", type=int)
@pass_ctx
def konto(ctx: CliContext, nummer: int) -> None:
    """Einzelnes Konto anzeigen."""
    acct = get_account(nummer)
    if acct is None:
        error_console.print(f"[bold red]Konto {nummer} nicht im Kontenrahmen.[/]")
        sys.exit(1)

    console.print(f"[bold]Konto {acct.nr}[/]")
    console.print(f"  Bezeichnung: {acct.bezeichnung}")
    console.print(f"  Typ:         {acct.typ}")


@main.command()
@pass_ctx
def dashboard(ctx: CliContext) -> None:
    """KPI-Dashboard."""
    now = datetime.now()
    jahr = now.year
    monat = now.month

    console.print(f"[bold]Dashboard — {monat:02d}/{jahr}[/]\n")

    try:
        reports = ctx.reports_engine

        # BWA
        bwa_daten = reports.bwa(jahr, monat)
        erloese = bwa_daten.get("umsatzerloese", Decimal("0"))
        kosten = bwa_daten.get("summe_kosten", Decimal("0"))
        ergebnis = bwa_daten.get("betriebsergebnis", Decimal("0"))

        ergebnis_style = "green" if ergebnis >= 0 else "red"

        console.print("[bold]Ergebnis:[/]")
        console.print(f"  Umsatzerloese:      {erloese:>12,.2f} EUR")
        console.print(f"  Gesamtkosten:       {kosten:>12,.2f} EUR")
        console.print(f"  Betriebsergebnis:   [{ergebnis_style}]{ergebnis:>12,.2f} EUR[/]")

        if erloese > 0:
            marge = (ergebnis / erloese * 100).quantize(Decimal("0.1"))
            console.print(f"  Umsatzrendite:      {marge:>11}%")

        # Offene Posten
        console.print("\n[bold]Offene Posten:[/]")
        op_daten = reports.op_liste()
        console.print(f"  Debitoren:          {op_daten['summe_debitoren']:>12,.2f} EUR")
        console.print(f"  Kreditoren:         {op_daten['summe_kreditoren']:>12,.2f} EUR")

        # Saeumige Kunden
        saeumige_liste = reports.saeumige_kunden()
        if saeumige_liste:
            summe_saeumig = sum(s["betrag"] for s in saeumige_liste)
            console.print(f"\n[bold yellow]Saeumige Kunden:[/] {len(saeumige_liste)}")
            console.print(f"  Gesamtbetrag:       [red]{summe_saeumig:>12,.2f} EUR[/]")
        else:
            console.print("\n[green]Keine saeumigen Kunden.[/]")

    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)


@main.command()
@click.option("--monat", type=int, default=None, help="Fristen fuer einen bestimmten Monat (1-12)")
@click.option("--jahr", type=int, default=None, help="Kalenderjahr (Standard: aktuelles Jahr)")
@click.option("--tage", type=int, default=30, help="Anstehende Fristen in N Tagen (Standard: 30)")
@click.option("--ueberfaellig", is_flag=True, help="Nur ueberfaellige Fristen anzeigen")
@pass_ctx
def fristen(
    ctx: CliContext,
    monat: int | None,
    jahr: int | None,
    tage: int,
    ueberfaellig: bool,
) -> None:
    """Steuerliche und buchhalterische Fristen anzeigen."""
    from collmex.deadlines import DeadlineTracker

    now = datetime.now()
    tracker = DeadlineTracker(heute=now.date())

    if ueberfaellig:
        deadlines = tracker.get_overdue()
        titel = "Ueberfaellige Fristen"
    elif monat is not None:
        if jahr is None:
            jahr = now.year
        deadlines = tracker.get_monthly_deadlines(jahr, monat)
        titel = f"Fristen {monat:02d}/{jahr}"
    else:
        deadlines = tracker.get_upcoming(tage=tage)
        titel = f"Anstehende Fristen (naechste {tage} Tage)"

    if not deadlines:
        console.print(f"[green]Keine {titel.lower()}.[/]")
        return

    table = Table(title=titel)
    table.add_column("Datum", style="cyan", width=12)
    table.add_column("Name", width=25)
    table.add_column("Kategorie", width=14)
    table.add_column("Prioritaet", justify="center", width=10)
    table.add_column("Beschreibung", width=50)

    prio_styles = {"critical": "bold red", "high": "yellow", "medium": "white"}

    for dl in deadlines:
        prio_style = prio_styles.get(dl.prioritaet.value, "white")
        kat_style = {"steuer": "red", "buchhaltung": "blue", "meldung": "cyan"}.get(
            dl.kategorie.value, "white"
        )
        table.add_row(
            dl.datum.isoformat(),
            dl.name,
            f"[{kat_style}]{dl.kategorie.value}[/]",
            f"[{prio_style}]{dl.prioritaet.value}[/]",
            dl.beschreibung[:50],
        )

    console.print(table)
    console.print(f"\n[dim]{len(deadlines)} Fristen[/]")


@main.command()
@click.option("--monat", type=int, default=None, help="Voranmeldungszeitraum (1-12)")
@click.option("--jahr", type=int, default=None, help="Geschaeftsjahr")
@pass_ctx
def ustva(ctx: CliContext, monat: int | None, jahr: int | None) -> None:
    """Umsatzsteuer-Voranmeldung berechnen."""
    from collmex.taxes import TaxEngine

    now = datetime.now()
    if jahr is None:
        jahr = now.year
    if monat is None:
        # UStVA fuer den Vormonat
        monat = now.month - 1 if now.month > 1 else 12
        if monat == 12:
            jahr -= 1

    try:
        tax = TaxEngine(ctx.client)
        result = tax.ustva(jahr, monat)
    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    console.print(f"[bold]UStVA {monat:02d}/{jahr}[/]\n")

    # Umsaetze
    console.print("[bold]Steuerpflichtige Umsaetze:[/]")
    console.print(f"  KZ 81 (19% netto):   {result['kz81']:>12,.2f} EUR")
    console.print(f"  KZ 86 (7% netto):    {result['kz86']:>12,.2f} EUR")
    console.print(f"  USt 19%:             {result['ust_19']:>12,.2f} EUR")
    console.print(f"  USt 7%:              {result['ust_7']:>12,.2f} EUR")
    console.print(f"  [bold]Zahllast:          {result['ust_zahllast']:>12,.2f} EUR[/]")

    # Vorsteuer
    console.print("\n[bold]Vorsteuerabzug:[/]")
    console.print(f"  KZ 66 (VSt 19%):    {result['kz66']:>12,.2f} EUR")
    console.print(f"  KZ 61 (VSt 7%):     {result['kz61']:>12,.2f} EUR")
    console.print(f"  KZ 67 (VSt §13b):   {result['kz67']:>12,.2f} EUR")
    console.print(f"  [bold]Abzug:             {result['vst_abzug']:>12,.2f} EUR[/]")

    # Vorauszahlung
    vz = result["vorauszahlung"]
    vz_style = "red" if vz > 0 else "green"
    console.print("\n[bold]KZ 83 — Vorauszahlung:[/]")
    console.print(f"  [{vz_style}]{vz:>12,.2f} EUR[/]")
    if vz > 0:
        console.print("  [dim](Zahlung an Finanzamt)[/]")
    elif vz < 0:
        console.print("  [dim](Erstattung vom Finanzamt)[/]")


@main.command()
@click.option("--wochen", type=int, default=13, help="Prognosezeitraum in Wochen (Standard: 13)")
@pass_ctx
def liquiditaet(ctx: CliContext, wochen: int) -> None:
    """Liquiditaetsvorschau (13-Wochen-Prognose)."""
    from collmex.controlling import ControllingEngine

    try:
        ctrl = ControllingEngine(ctx.client)
        vorschau = ctrl.liquiditaetsvorschau(wochen=wochen)
    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    table = Table(title=f"Liquiditaetsvorschau ({wochen} Wochen)")
    table.add_column("Woche", style="cyan", width=12)
    table.add_column("Beginn", width=12)
    table.add_column("Eingaenge", justify="right", style="green", width=14)
    table.add_column("Ausgaenge", justify="right", style="red", width=14)
    table.add_column("Saldo", justify="right", width=14)

    for w in vorschau:
        saldo = w["saldo"]
        saldo_style = "green" if saldo >= 0 else "bold red"
        table.add_row(
            w["woche"],
            str(w["start"]),
            f"{w['erwartete_eingaenge']:,.2f}",
            f"{w['erwartete_ausgaenge']:,.2f}",
            f"[{saldo_style}]{saldo:,.2f}[/]",
        )

    console.print(table)


@main.command("soll-ist")
@click.option("--monat", type=int, default=None, help="Buchungsperiode (1-12)")
@click.option("--jahr", type=int, default=None, help="Geschaeftsjahr")
@click.option(
    "--budget-file",
    type=click.Path(exists=True),
    default=None,
    help='JSON-Datei mit Budget: {"4830": 2000, "4100": 5000}',
)
@pass_ctx
def soll_ist(
    ctx: CliContext,
    monat: int | None,
    jahr: int | None,
    budget_file: str | None,
) -> None:
    """Soll-Ist-Vergleich (Budget vs. tatsaechliche Kosten)."""
    import json

    from collmex.controlling import ControllingEngine

    now = datetime.now()
    if jahr is None:
        jahr = now.year
    if monat is None:
        monat = now.month

    # Budget laden
    if budget_file:
        with open(budget_file) as f:
            raw = json.load(f)
        budget = {int(k): Decimal(str(v)) for k, v in raw.items()}
    else:
        # Standard-Budget fuer typische Aufwandskonten
        budget = {
            4100: Decimal("5000"),  # Personalkosten
            4210: Decimal("1500"),  # Miete
            4830: Decimal("2000"),  # Abschreibungen
            4400: Decimal("500"),  # Buerobedarf
            4900: Decimal("1000"),  # Sonstige
        }

    try:
        ctrl = ControllingEngine(ctx.client)
        result = ctrl.soll_ist(monat, jahr, budget)
    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    table = Table(title=f"Soll-Ist {monat:02d}/{jahr}")
    table.add_column("Konto", style="cyan", width=6)
    table.add_column("Budget", justify="right", width=12)
    table.add_column("Ist", justify="right", width=12)
    table.add_column("Abweichung", justify="right", width=12)
    table.add_column("%", justify="right", width=8)
    table.add_column("Ampel", justify="center", width=6)

    ampel_styles = {"gruen": "green", "gelb": "yellow", "rot": "bold red"}

    for pos in result:
        ampel = pos["ampel"]
        style = ampel_styles.get(ampel, "white")
        abw = pos["abweichung"]
        abw_style = "red" if abw > 0 else "green"
        table.add_row(
            str(pos["konto"]),
            f"{pos['budget']:,.2f}",
            f"{pos['ist']:,.2f}",
            f"[{abw_style}]{abw:,.2f}[/]",
            f"{pos['prozent']:.1f}",
            f"[{style}]{ampel}[/]",
        )

    console.print(table)


@main.command()
@click.argument("rechnungs_nr")
@click.option(
    "--typ",
    type=click.Choice(["eingang", "ausgang"]),
    default="eingang",
    help="Rechnungstyp (Standard: eingang)",
)
@click.option("--betrag", type=float, required=True, help="Nettobetrag der Originalrechnung")
@click.option("--konto", type=int, required=True, help="Aufwands-/Ertragskonto")
@click.option("--ust", type=int, default=19, help="USt-Satz (Standard: 19)")
@click.option("--lieferant", type=int, default=None, help="Lieferant-Nr (fuer Eingang)")
@click.option("--kunde", type=int, default=None, help="Kunden-Nr (fuer Ausgang)")
@click.option("--datum", default=None, help="Storno-Datum YYYYMMDD (Standard: heute)")
@click.option("--dry-run", is_flag=True, help="Nur anzeigen, nicht buchen")
@pass_ctx
def storno(
    ctx: CliContext,
    rechnungs_nr: str,
    typ: str,
    betrag: float,
    konto: int,
    ust: int,
    lieferant: int | None,
    kunde: int | None,
    datum: str | None,
    dry_run: bool,
) -> None:
    """Storno einer Rechnung erstellen."""
    if datum is None:
        datum = datetime.now().strftime("%Y%m%d")

    engine = ctx.booking_engine
    betrag_decimal = Decimal(str(betrag))

    if typ == "eingang":
        if not lieferant:
            error_console.print(
                "[bold red]Fehler:[/] --lieferant ist Pflicht fuer Eingangs-Storno."
            )
            sys.exit(1)
        original = engine.create_eingangsrechnung(
            betrag_netto=betrag_decimal,
            ust_satz=ust,
            aufwandskonto=konto,
            buchungstext=f"Original zu {rechnungs_nr}",
            belegdatum=datum,
            rechnungs_nr=rechnungs_nr,
            lieferant_nr=lieferant,
        )
        storno_rechnung = engine.create_storno_eingang(original)
        storno_rechnung.rechnungs_nr = f"{rechnungs_nr}-S"
    else:
        if not kunde:
            error_console.print("[bold red]Fehler:[/] --kunde ist Pflicht fuer Ausgangs-Storno.")
            sys.exit(1)
        original = engine.create_ausgangsrechnung(
            betrag_netto=betrag_decimal,
            ust_satz=ust,
            ertragskonto=konto,
            buchungstext=f"Original zu {rechnungs_nr}",
            belegdatum=datum,
            rechnungs_nr=rechnungs_nr,
            kunde_nr=kunde,
        )
        storno_rechnung = engine.create_storno_ausgang(original)
        storno_rechnung.rechnungs_nr = f"{rechnungs_nr}-S"

    console.print(f"[bold]Storno fuer {rechnungs_nr}[/]")
    console.print(f"  Typ:    {'Eingangsrechnung' if typ == 'eingang' else 'Ausgangsrechnung'}")
    console.print(f"  Betrag: {betrag_decimal:,.2f} EUR netto ({ust}% USt)")
    console.print(f"  Konto:  {konto}")
    console.print(f"  Datum:  {datum}")
    console.print(f"  Nr:     {storno_rechnung.rechnungs_nr}")

    if dry_run:
        console.print("\n[yellow]--dry-run: Storno wurde NICHT ausgefuehrt.[/]")
        return

    try:
        result = engine.post_and_validate(storno_rechnung)
        if result.ok:
            console.print("\n[bold green]Storno erfolgreich![/]")
        else:
            error_console.print("\n[bold red]Storno fehlgeschlagen:[/]")
            for fehler in result.fehler:
                error_console.print(f"  - {fehler}")
            sys.exit(1)
    except Exception as exc:
        error_console.print(f"\n[bold red]Fehler:[/] {exc}")
        sys.exit(1)


@main.command()
@click.argument("beschreibung")
@click.option("--betrag", type=float, required=True, help="Nettobetrag")
@click.option("--kunde", type=int, required=True, help="Collmex-Kundennummer (Pflicht!)")
@click.option("--konto", type=int, default=None, help="Ertragskonto (Standard: 8400)")
@click.option("--ust", type=int, default=19, help="USt-Satz in Prozent (Standard: 19)")
@click.option("--datum", default=None, help="Belegdatum YYYYMMDD (Standard: heute)")
@click.option("--rechnungsnr", default="", help="Externe Rechnungsnummer")
@click.option("--dry-run", is_flag=True, help="Nur anzeigen, nicht buchen")
@pass_ctx
def ausgang(
    ctx: CliContext,
    beschreibung: str,
    betrag: float,
    kunde: int,
    konto: int | None,
    ust: int,
    datum: str | None,
    rechnungsnr: str,
    dry_run: bool,
) -> None:
    """Ausgangsrechnung buchen (ueber Nebenbuch/Personenkonto)."""
    if datum is None:
        datum = datetime.now().strftime("%Y%m%d")

    # Ertragskonto: Standard nach USt-Satz
    if konto is None:
        konto = 8400 if ust == 19 else (8300 if ust == 7 else 8200)
        konto_info = get_account(konto)
        konto_name = konto_info.bezeichnung if konto_info else str(konto)
        console.print(f"Auto-Konto: [cyan]{konto}[/] ({konto_name})")

    engine = ctx.booking_engine
    betrag_decimal = Decimal(str(betrag))
    ust_betrag = (betrag_decimal * Decimal(ust) / Decimal("100")).quantize(Decimal("0.01"))
    brutto = betrag_decimal + ust_betrag

    # Buchungssatz anzeigen
    table = Table(title="Ausgangsrechnung")
    table.add_column("Pos", style="dim", width=4)
    table.add_column("Konto", style="cyan", width=6)
    table.add_column("Bezeichnung", width=30)
    table.add_column("S/H", width=4)
    table.add_column("Betrag", justify="right", style="green", width=12)

    konto_info = get_account(konto)
    konto_name = konto_info.bezeichnung if konto_info else str(konto)

    table.add_row("1", str(kunde), f"Kunde {kunde}", "S", f"{brutto:,.2f} EUR")
    table.add_row("2", str(konto), konto_name, "H", f"{betrag_decimal:,.2f} EUR")
    if ust > 0:
        ust_konto = 1776 if ust == 19 else (1771 if ust == 7 else 1770)
        table.add_row("3", str(ust_konto), f"Umsatzsteuer {ust}%", "H", f"{ust_betrag:,.2f} EUR")

    console.print(table)
    console.print(f"Text: {beschreibung}")
    console.print(f"Datum: {datum}")
    if rechnungsnr:
        console.print(f"Rechnungs-Nr: {rechnungsnr}")

    if dry_run:
        console.print("\n[yellow]--dry-run: Buchung wurde NICHT ausgefuehrt.[/]")
        return

    try:
        rechnung = engine.create_ausgangsrechnung(
            betrag_netto=betrag_decimal,
            ust_satz=ust,
            ertragskonto=konto,
            buchungstext=beschreibung,
            belegdatum=datum,
            kunde_nr=kunde,
            rechnungs_nr=rechnungsnr,
        )
        result = engine.post_and_validate(rechnung)

        if result.ok:
            console.print(f"\n[bold green]Buchung erfolgreich![/] Beleg-Nr: {result.beleg_nr}")
        else:
            error_console.print("\n[bold red]Buchung fehlgeschlagen:[/]")
            for fehler in result.fehler:
                error_console.print(f"  - {fehler}")
            sys.exit(1)
    except Exception as exc:
        error_console.print(f"\n[bold red]Fehler:[/] {exc}")
        sys.exit(1)


@main.command()
@click.option("--beleg-nr", type=int, default=None, help="Einzelne Belegnummer")
@click.option("--von", default=None, help="Startdatum YYYYMMDD")
@click.option("--bis", default=None, help="Enddatum YYYYMMDD")
@pass_ctx
def buchungen(
    ctx: CliContext,
    beleg_nr: int | None,
    von: str | None,
    bis: str | None,
) -> None:
    """Buchungsbelege abfragen (ACCDOC_GET)."""
    try:
        rows = ctx.client.get_bookings(
            booking_id=beleg_nr,
            date_from=von,
            date_to=bis,
        )
    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    if not rows:
        console.print("[yellow]Keine Buchungsbelege gefunden.[/]")
        return

    table = Table(title="Buchungsbelege")
    table.add_column("Beleg", style="cyan", width=8)
    table.add_column("Pos", style="dim", width=4)
    table.add_column("Konto", style="cyan", width=8)
    table.add_column("S/H", width=4)
    table.add_column("Betrag", justify="right", width=14)
    table.add_column("Datum", width=10)
    table.add_column("Text", width=35)

    for row in rows:
        if len(row) < 10 or row[0] != "ACCDOC":
            continue
        # ACCDOC: [Satzart, Firma, BelegNr, PosNr, Konto, Bezeichnung,
        #          Soll/Haben(0/1), Betrag, Waehrung, BU, Datum, Text, ...]
        beleg = row[2] if len(row) > 2 else ""
        pos = row[3] if len(row) > 3 else ""
        konto = row[4] if len(row) > 4 else ""
        sh_raw = row[6] if len(row) > 6 else ""
        sh = "S" if sh_raw == "0" else "H"
        betrag_raw = row[7] if len(row) > 7 else "0"
        from collmex.api import parse_amount as _pa

        betrag = _pa(betrag_raw)
        datum = row[10] if len(row) > 10 else ""
        text = row[11] if len(row) > 11 else ""

        betrag_style = "green" if sh == "S" else "red"
        table.add_row(
            beleg,
            pos,
            konto,
            sh,
            f"[{betrag_style}]{betrag:,.2f} EUR[/]",
            datum,
            text[:35],
        )

    console.print(table)
    console.print(f"\n[dim]{len([r for r in rows if r and r[0] == 'ACCDOC'])} Positionen[/]")


@main.command()
@click.option(
    "--stufe", type=click.IntRange(1, 3), default=None, help="Nur Mahnungen fuer diese Stufe (1-3)"
)
@click.option("--dry-run", is_flag=True, default=True, help="Nur Vorschau (Standard: aktiv)")
@pass_ctx
def mahnlauf(ctx: CliContext, stufe: int | None, dry_run: bool) -> None:
    """Mahnlauf durchfuehren (ueberfaellige Debitoren mahnen)."""
    from collmex.dunning import DunningEngine

    try:
        dunning = DunningEngine(ctx.client)
        vorschlaege = dunning.mahnlauf(stufe=stufe)
    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    if not vorschlaege:
        console.print("[green]Keine offenen Mahnungen.[/]")
        return

    table = Table(title=f"Mahnlauf{f' — Stufe {stufe}' if stufe else ''}")
    table.add_column("Kunde", width=25)
    table.add_column("Beleg", style="cyan", width=12)
    table.add_column("Betrag", justify="right", width=12)
    table.add_column("Faellig", width=10)
    table.add_column("Tage", justify="right", width=6)
    table.add_column("Stufe", justify="center", width=6)
    table.add_column("Aktion", width=35)

    stufe_styles = {1: "yellow", 2: "bold yellow", 3: "bold red"}
    summe = Decimal("0")

    for v in vorschlaege:
        s = v["mahnstufe"]
        style = stufe_styles.get(s, "white")
        summe += v["betrag"]
        table.add_row(
            v["kunde"][:25],
            v["beleg_nr"],
            f"{v['betrag']:,.2f}",
            v["faellig"],
            str(v["tage_ueberfaellig"]),
            f"[{style}]{s}[/]",
            v["mahnaktion"][:35],
        )

    console.print(table)
    console.print(
        f"\n[bold]{len(vorschlaege)} Mahnvorschlaege[/], Gesamtbetrag: [red]{summe:,.2f} EUR[/]"
    )

    if dry_run:
        console.print("\n[yellow]Vorschau — keine Mahnungen versendet.[/]")


@main.command("datev-export")
@click.option("--monat", type=int, default=None, help="Buchungsperiode (1-12)")
@click.option("--jahr", type=int, default=None, help="Geschaeftsjahr")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Ausgabedatei (Standard: EXTF_Buchungsstapel_YYYY_MM.csv)",
)
@click.option("--berater", type=int, default=12345, help="DATEV Beraternummer")
@click.option("--mandant", type=int, default=1, help="DATEV Mandantennummer")
@click.option("--gruppiert", is_flag=True, help="Belege mit Gegenkonto gruppieren")
@pass_ctx
def datev_export(
    ctx: CliContext,
    monat: int | None,
    jahr: int | None,
    output: str | None,
    berater: int,
    mandant: int,
    gruppiert: bool,
) -> None:
    """Buchungen im DATEV-Format exportieren (fuer Steuerberater)."""
    from collmex.datev import DatevExporter

    now = datetime.now()
    if jahr is None:
        jahr = now.year
    if monat is None:
        monat = now.month

    # Zeitraum berechnen
    datum_von = f"{jahr}{monat:02d}01"
    if monat == 12:
        datum_bis = f"{jahr}1231"
    else:
        import calendar

        letzter_tag = calendar.monthrange(jahr, monat)[1]
        datum_bis = f"{jahr}{monat:02d}{letzter_tag:02d}"

    if output is None:
        output = f"EXTF_Buchungsstapel_{jahr}_{monat:02d}.csv"

    try:
        exporter = DatevExporter(
            ctx.client,
            berater_nr=berater,
            mandant_nr=mandant,
        )
        if gruppiert:
            csv_text = exporter.export_grouped(datum_von, datum_bis)
        else:
            csv_text = exporter.export(datum_von, datum_bis)
    except CollmexError as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    # In Datei schreiben (Windows-1252 fuer DATEV-Kompatibilitaet)
    with open(output, "w", encoding="windows-1252", newline="") as f:
        f.write(csv_text)

    console.print(f"[bold green]DATEV-Export gespeichert:[/] {output}")
    console.print(f"  Zeitraum: {monat:02d}/{jahr}")
    console.print(f"  Berater:  {berater}")
    console.print(f"  Mandant:  {mandant}")


@main.command(context_settings={"ignore_unknown_options": True})
@click.argument("satzart")
@click.argument("felder", nargs=-1)
@click.option("--suche", default=None, help="In allen Feldern suchen")
@pass_ctx
def abfrage(ctx: CliContext, satzart: str, felder: tuple, suche: str | None) -> None:
    """Collmex-Daten abfragen — alle ~30 GET-Satzarten, mit Filtern.

    \b
    SATZART   Eine GET-Satzart (siehe: collmex hilfe)
    FELDER    Optionale API-Parameter (Feld 2, 3, ... laut Collmex-Doku)
              Leere Felder mit "" uebergeben.
              Welche Felder moeglich sind: collmex hilfe <SATZART>

    \b
    Beispiele:
      collmex abfrage CUSTOMER_GET                          Alle Kunden
      collmex abfrage CUSTOMER_GET --suche helm             Suche in Ergebnissen
      collmex abfrage VENDOR_GET                            Alle Lieferanten
      collmex abfrage PRODUCT_GET 1                         Produkte Firma 1
      collmex abfrage INVOICE_GET "" 1 "" 20260301 20260331 Rechnungen Maerz
      collmex abfrage QUOTATION_GET                         Alle Angebote
      collmex abfrage SALES_ORDER_GET                       Alle Auftraege
    """
    from collmex.stammdaten import render_stammdaten

    render_stammdaten(ctx, satzart.upper(), suche, console, error_console, felder=felder)


@main.command()
@click.argument("satzart", required=False, default=None)
@click.option("--suche", default=None, help="Nach Stichwort filtern")
def hilfe(satzart: str | None, suche: str | None) -> None:
    """Collmex API-Referenz (Satzarten, Doku-Links)."""
    from collmex.api_reference import (
        KATEGORIE_LABELS,
        KATEGORIE_REIHENFOLGE,
        beispiel_url,
        doku_url,
        get_satzart,
        nach_kategorie,
    )
    from collmex.api_reference import (
        suche as suche_fn,
    )

    # Detail zu einer einzelnen Satzart
    if satzart is not None:
        sa = get_satzart(satzart)
        if sa is None:
            error_console.print(f"[bold red]Satzart '{satzart}' nicht gefunden.[/]")
            error_console.print("Tipp: collmex api-help --suche <stichwort>")
            sys.exit(1)

        console.print(f"\n[bold]{sa['satzart']}[/] — {sa['name']}")
        console.print(f"  Kategorie:    {KATEGORIE_LABELS[sa['kategorie']]}")
        if "felder" in sa:
            console.print(f"  Felder:       {sa['felder']}")
        if "antwort" in sa:
            console.print(f"  Antwort:      {sa['antwort']}")
        console.print(f"  Beschreibung: {sa['beschreibung']}")
        console.print(f"  Doku:         {doku_url(sa)}")
        bsp = beispiel_url(sa)
        if bsp:
            console.print(f"  Beispiel:     {bsp}")

        # Felder aus Doku-Seite anzeigen
        # Bei GET-Satzarten: Felder der Antwort-Satzart zeigen (dort sind die Felddefinitionen)
        felder_doku = None
        if "antwort" in sa:
            antwort_sa = get_satzart(sa["antwort"])
            if antwort_sa and "doku" in antwort_sa:
                felder_doku = antwort_sa["doku"]
        if not felder_doku and "doku" in sa:
            felder_doku = sa["doku"]

        if felder_doku:
            from collmex.stammdaten import fetch_help_table

            try:
                fields = fetch_help_table(felder_doku)
            except Exception:
                fields = []
            if fields:
                console.print("\n[bold]Felder:[/]")
                console.print("[dim]Nr  Feld                 Typ  Max  Bemerkung[/]")
                for nr, feld, typ, max_len, bemerkung in fields:
                    bemerkung_short = bemerkung[:60] if bemerkung else ""
                    console.print(
                        f"  {nr:>2}  {feld:<20s} {typ:<4s} {max_len:<4s} {bemerkung_short}"
                    )
        return

    # Suche nach Stichwort
    if suche is not None:
        treffer = suche_fn(suche)
        if not treffer:
            console.print(f"[yellow]Keine Treffer fuer '{suche}'.[/]")
            return

        console.print(f"[bold]Suche: '{suche}'[/] — {len(treffer)} Treffer\n")
        table = Table()
        table.add_column("Satzart", style="cyan", width=24)
        table.add_column("Name", width=28)
        table.add_column("Kategorie", width=14)

        for sa in treffer:
            table.add_row(
                sa["satzart"],
                sa["name"],
                KATEGORIE_LABELS[sa["kategorie"]],
            )
        console.print(table)
        return

    # Uebersicht nach Kategorie
    console.print("[bold]Collmex API-Referenz[/]\n")
    gruppen = nach_kategorie()

    for kat in KATEGORIE_REIHENFOLGE:
        eintraege = gruppen.get(kat, [])
        if not eintraege:
            continue

        table = Table(title=KATEGORIE_LABELS[kat], show_header=False, padding=(0, 1))
        table.add_column("Satzart", style="cyan", width=24)
        table.add_column("Beschreibung", width=55)

        for sa in eintraege:
            felder_info = f" ({sa['felder']} Felder)" if "felder" in sa else ""
            table.add_row(sa["satzart"], f"{sa['name']}{felder_info}")

        console.print(table)
        console.print()


@main.command()
@click.argument("thema", required=False, default=None)
@click.option("--suche", default=None, help="Im Handbuch nach Stichwort suchen")
def handbuch(thema: str | None, suche: str | None) -> None:
    """Collmex-Handbuch nachschlagen (Buchhaltung, USt, Mahnung, ...).

    \b
    Beispiele:
      collmex handbuch                  Alle verfuegbaren Themen
      collmex handbuch buchen           Wie man in Collmex bucht
      collmex handbuch ust              Umsatzsteuer
      collmex handbuch mahnung          Mahnwesen
      collmex handbuch reverse-charge   §13b Steuerschuldumkehr
      collmex handbuch gwg              Geringwertige Wirtschaftsgueter
      collmex handbuch cmxlrn           Lieferantenrechnung (Import)
    """
    from collmex.stammdaten import HANDBUCH_SEKTIONEN, fetch_handbuch_section

    if thema is None and suche is None:
        # Uebersicht aller Themen
        console.print("[bold]Collmex-Handbuch — Verfuegbare Themen[/]\n")
        table = Table(show_header=True)
        table.add_column("Thema", style="cyan", width=22)
        table.add_column("Beschreibung", width=50)
        for key, (_, titel) in sorted(HANDBUCH_SEKTIONEN.items()):
            table.add_row(key, titel)
        console.print(table)
        console.print(
            f"\n[dim]{len(HANDBUCH_SEKTIONEN)} Themen. Aufruf: collmex handbuch <thema>[/]"
        )
        return

    if suche:
        suche_lower = suche.lower()
        treffer = {
            k: v
            for k, v in HANDBUCH_SEKTIONEN.items()
            if suche_lower in k.lower() or suche_lower in v[1].lower()
        }
        if not treffer:
            console.print(f"[yellow]Keine Treffer fuer '{suche}'.[/]")
            return
        console.print(f"[bold]Handbuch-Suche: '{suche}'[/]\n")
        for key, (_, titel) in sorted(treffer.items()):
            console.print(f"  [cyan]{key:<22}[/] {titel}")
        return

    # Thema nachschlagen
    thema_lower = thema.lower()
    if thema_lower in HANDBUCH_SEKTIONEN:
        anchor, titel = HANDBUCH_SEKTIONEN[thema_lower]
    else:
        # Fuzzy: Praefix-Match
        matches = {
            k: v
            for k, v in HANDBUCH_SEKTIONEN.items()
            if k.startswith(thema_lower) or thema_lower in k
        }
        if len(matches) == 1:
            key = next(iter(matches))
            anchor, titel = matches[key]
        elif matches:
            console.print(f"[yellow]Mehrere Treffer fuer '{thema}':[/]")
            for key, (_, t) in sorted(matches.items()):
                console.print(f"  [cyan]{key}[/] — {t}")
            return
        else:
            # Direkter Anker-Versuch
            anchor = thema_lower
            titel = thema

    console.print(f"[bold]{titel}[/]")
    console.print(f"[dim]Quelle: https://www.collmex.de/handbuch_pro.html#{anchor}[/]\n")
    text = fetch_handbuch_section(anchor)
    console.print(text)


@main.command()
@pass_ctx
def onboarding(ctx: CliContext) -> None:
    """Mandanten-Onboarding: Verbindung pruefen, Kontenrahmen erkennen, Stammdaten lesen."""
    console.print("[bold]Mandanten-Onboarding[/]\n")

    # 1. Verbindungstest
    console.print("[bold]1. Verbindungstest[/]")
    try:
        ok = ctx.client.status()
    except CollmexError as exc:
        error_console.print(f"[bold red]Verbindungsfehler:[/] {exc}")
        sys.exit(1)
    if not ok:
        error_console.print("[bold red]Verbindung fehlgeschlagen[/]")
        sys.exit(1)
    console.print(f"  [green]OK[/] — Kunde {ctx.client.customer}, Firma {ctx.client.company}")

    # 2. Kontenrahmen erkennen
    # Logik: ACCBAL_GET fuer ein Konto → Fehler "nicht vorhanden" = Konto existiert nicht
    # Kein Fehler (auch leere Antwort) = Konto existiert im Kontenrahmen
    console.print("\n[bold]2. Kontenrahmen erkennen[/]")
    jahr = datetime.now().year
    kontenrahmen = "unbekannt"

    def _konto_existiert(konto: str) -> bool:
        try:
            ctx.client.query("ACCBAL_GET", ctx.client.company, jahr, 0, konto)
            return True  # Kein Fehler → Konto existiert
        except CollmexError as exc:
            if "nicht vorhanden" in str(exc):
                return False  # Konto existiert nicht im Kontenrahmen
            return True  # Anderer Fehler → Konto koennte existieren
        except Exception:
            return True  # Im Zweifel: annehmen es existiert

    has_8400 = _konto_existiert("8400")
    has_4400 = _konto_existiert("4400")

    if has_8400 and not has_4400:
        kontenrahmen = "SKR03"
    elif has_4400 and not has_8400:
        kontenrahmen = "SKR04"
    elif has_8400 and has_4400:
        kontenrahmen = "individuell (SKR03+SKR04 Konten gefunden)"
    else:
        kontenrahmen = "nicht erkennbar"
    console.print(f"  Kontenrahmen: [cyan]{kontenrahmen}[/]")

    # 3. Stammdaten zaehlen
    console.print("\n[bold]3. Stammdaten[/]")
    counts = {}
    for label, satzart, antwort, felder in [
        ("Kunden", "CUSTOMER_GET", "CMXKND", ("", ctx.client.company)),
        ("Lieferanten", "VENDOR_GET", "CMXLIF", ("", ctx.client.company)),
        ("Produkte", "PRODUCT_GET", "CMXPRD", (ctx.client.company, "")),
    ]:
        try:
            rows = ctx.client.query(satzart, *felder)
            data = [r for r in rows if r and r[0] == antwort]
            counts[label] = len(data)
            console.print(f"  {label}: [cyan]{len(data)}[/]")
        except Exception as exc:
            counts[label] = 0
            console.print(f"  {label}: [yellow]Fehler ({exc})[/]")

    # 4. Offene Posten
    console.print("\n[bold]4. Offene Posten[/]")
    try:
        op_rows = ctx.client.get_open_items()
        op_data = [r for r in op_rows if r and r[0] == "OPEN_ITEM"]
        debitoren = [r for r in op_data if len(r) > 6 and not r[6].startswith("-")]
        kreditoren = [r for r in op_data if len(r) > 6 and r[6].startswith("-")]
        console.print(f"  Debitoren-OP: [cyan]{len(debitoren)}[/]")
        console.print(f"  Kreditoren-OP: [cyan]{len(kreditoren)}[/]")
    except Exception:
        console.print("  [yellow]Offene Posten nicht abrufbar[/]")

    # 5. Zusammenfassung
    console.print("\n[bold]Zusammenfassung[/]")
    console.print(f"  Collmex-Kunde: {ctx.client.customer}")
    console.print(f"  Firma-Nr: {ctx.client.company}")
    console.print(f"  Kontenrahmen: {kontenrahmen}")
    for label, count in counts.items():
        console.print(f"  {label}: {count}")
    console.print("\n[dim]Tipp: Mandant-Profil in mandant/<name>/profil.md dokumentieren.[/]")


@main.group()
def webui() -> None:
    """Collmex Web-UI Daten abrufen (Mengeneinheiten, Zahlungsbedingungen, Firma).

    Braucht COLLMEX_WEB_USER und COLLMEX_WEB_PASSWORD in .env
    (separater Web-Benutzer, nicht der API-User).
    """


main.add_command(webui)


def _get_webui():
    """Erstellt CollmexWebUI-Instanz mit Fehlerbehandlung."""
    from collmex.webui import CollmexWebUI

    try:
        return CollmexWebUI()
    except ValueError as exc:
        error_console.print(f"[bold red]Web-UI Fehler:[/] {exc}")
        sys.exit(1)


@webui.command("mengeneinheiten")
def webui_mengeneinheiten() -> None:
    """Alle Mengeneinheiten aus Collmex-Einstellungen."""
    wui = _get_webui()
    try:
        einheiten = wui.mengeneinheiten()
    except Exception as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    if not einheiten:
        console.print("[yellow]Keine Mengeneinheiten gefunden.[/]")
        return

    table = Table(title="Mengeneinheiten")
    table.add_column("Code", style="cyan", width=6)
    table.add_column("Kuerzel", width=6)
    table.add_column("EN", width=6)
    table.add_column("Nk", justify="right", width=4)
    table.add_column("ISO", style="cyan", width=6)
    table.add_column("Bezeichnung", width=20)

    for e in einheiten:
        table.add_row(
            e.code, e.kuerzel, e.kuerzel_en, str(e.nachkommastellen), e.iso_code, e.bezeichnung
        )

    console.print(table)
    console.print(f"\n[dim]{len(einheiten)} Mengeneinheiten[/]")


@webui.command("zahlungsbedingungen")
def webui_zahlungsbedingungen() -> None:
    """Alle Zahlungsbedingungen aus Collmex-Einstellungen."""
    wui = _get_webui()
    try:
        zb = wui.zahlungsbedingungen()
    except Exception as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    if not zb:
        console.print("[yellow]Keine Zahlungsbedingungen gefunden.[/]")
        return

    table = Table(title="Zahlungsbedingungen")
    table.add_column("Nr", style="cyan", justify="right", width=4)
    table.add_column("Bezeichnung", width=40)

    for z in zb:
        table.add_row(str(z.nr), z.bezeichnung)

    console.print(table)
    console.print(f"\n[dim]{len(zb)} Zahlungsbedingungen[/]")


@webui.command("firma")
def webui_firma() -> None:
    """Firmenstammdaten aus Collmex-Einstellungen."""
    wui = _get_webui()
    try:
        firma = wui.firmenstammdaten()
    except Exception as exc:
        error_console.print(f"[bold red]Fehler:[/] {exc}")
        sys.exit(1)

    console.print("[bold]Firmenstammdaten[/]\n")
    console.print(f"  Firma:          {firma.firma}")
    console.print(f"  Strasse:        {firma.strasse}")
    console.print(f"  PLZ/Ort:        {firma.plz} {firma.ort}")
    console.print(f"  Land:           {firma.land}")
    console.print(f"  E-Mail:         {firma.email}")
    console.print(f"  USt-IdNr:       {firma.ust_idnr}")
    console.print(f"  Steuernummer:   {firma.steuernummer}")
    console.print(f"  Bankkonto:      {firma.bankkonto}")
    console.print(f"  Kontenrahmen:   {firma.kontenrahmen}")


@main.command()
def version() -> None:
    """Version anzeigen."""
    console.print(f"collmex {__version__}")
