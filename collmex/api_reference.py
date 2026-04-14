"""Collmex API-Referenz — alle Satzarten, Kategorien und Doku-Links.

Dient als Nachschlagewerk für den `collmex api-help` CLI-Befehl.
Quelle: https://www.collmex.de/c.cmx?1005,1,help,api
"""

from __future__ import annotations

DOKU_BASIS = "https://www.collmex.de/c.cmx?1005,1,help,"
BEISPIEL_BASIS = "https://www.collmex.de/"

SATZARTEN: list[dict] = [
    # =======================================================================
    # Datenimport
    # =======================================================================
    {
        "satzart": "CMXINV",
        "name": "Rechnungen",
        "kategorie": "import",
        "felder": 94,
        "beschreibung": "Rechnungen erstellen/importieren (mit Positionen, Kunde, USt)",
        "doku": "daten_importieren_rechnungen",
        "beispiel_csv": "rechnung.csv",
    },
    {
        "satzart": "CMXLRN",
        "name": "Lieferantenrechnungen",
        "kategorie": "import",
        "felder": 20,
        "beschreibung": "Eingangsrechnungen buchen (Aufwand, VSt, Kreditor)",
        "doku": "daten_importieren_lieferantenrechnung",
    },
    {
        "satzart": "CMXUMS",
        "name": "Umsätze/Erlöse",
        "kategorie": "import",
        "felder": 31,
        "beschreibung": "Ausgangsrechnungen/Erlöse buchen (Ertrag, USt, Debitor)",
        "doku": "daten_importieren_umsätze",
    },
    {
        "satzart": "CMXKND",
        "name": "Kunden",
        "kategorie": "import",
        "felder": 35,
        "beschreibung": "Kundenstammdaten anlegen/aktualisieren. CLI: collmex kunde-anlegen",
        "doku": "daten_importieren_kunde",
        "antwort": "CMXKND",
    },
    {
        "satzart": "CMXLIF",
        "name": "Lieferanten",
        "kategorie": "import",
        "felder": 41,
        "beschreibung": "Lieferantenstammdaten anlegen/aktualisieren. CLI: collmex lieferant-anlegen",
        "doku": "daten_importieren_lieferant",
        "antwort": "CMXLIF",
    },
    {
        "satzart": "CMXPRD",
        "name": "Produkte",
        "kategorie": "import",
        "beschreibung": "Produktstammdaten anlegen/aktualisieren",
        "doku": "daten_importieren_produkt",
    },
    {
        "satzart": "CMXPRI",
        "name": "Produktpreise",
        "kategorie": "import",
        "beschreibung": "Produktpreise importieren",
        "doku": "daten_importieren_preise",
    },
    {
        "satzart": "CMXPRC",
        "name": "Preisänderungen",
        "kategorie": "import",
        "beschreibung": "Preisänderungen importieren (prozentual/absolut)",
        "doku": "daten_importieren_preisänderung",
    },
    {
        "satzart": "CMXPGR",
        "name": "Produktgruppen",
        "kategorie": "import",
        "beschreibung": "Produktgruppen anlegen/aktualisieren",
        "doku": "daten_importieren_produktgruppen",
    },
    {
        "satzart": "CMXBOM",
        "name": "Stücklisten",
        "kategorie": "import",
        "beschreibung": "Stücklisten (Bill of Materials) importieren",
        "doku": "daten_importieren_stücklisten",
    },
    {
        "satzart": "CMXSTK",
        "name": "Bestand",
        "kategorie": "import",
        "beschreibung": "Lagerbestände setzen/importieren",
        "doku": "daten_importieren_bestand",
    },
    {
        "satzart": "CMXSC",
        "name": "Bestandsänderungen",
        "kategorie": "import",
        "beschreibung": "Bestandsänderungen (Zu-/Abgänge) importieren",
        "doku": "daten_importieren_bestandsänderungen",
    },
    {
        "satzart": "CMXQTN",
        "name": "Angebote",
        "kategorie": "import",
        "beschreibung": "Angebote erstellen/importieren",
        "doku": "daten_importieren_angebote",
    },
    {
        "satzart": "CMXORD",
        "name": "Kundenaufträge",
        "kategorie": "import",
        "beschreibung": "Kundenaufträge erstellen/importieren",
        "doku": "daten_importieren_kundenaufträge",
    },
    {
        "satzart": "CMXDLV",
        "name": "Lieferungen",
        "kategorie": "import",
        "beschreibung": "Lieferungen erstellen/importieren",
        "doku": "daten_importieren_lieferungen",
    },
    {
        "satzart": "CMXPOD",
        "name": "Lieferantenaufträge",
        "kategorie": "import",
        "beschreibung": "Lieferantenaufträge (Bestellungen) importieren",
        "doku": "daten_importieren_lieferantenaufträge",
    },
    {
        "satzart": "CMXVCR",
        "name": "Gutschriften an Lieferant",
        "kategorie": "import",
        "beschreibung": "Gutschriften an Lieferanten importieren",
        "doku": "daten_importieren_gutschriften_an_lieferant",
    },
    {
        "satzart": "CMXADR",
        "name": "Adressen",
        "kategorie": "import",
        "beschreibung": "Adressen importieren/aktualisieren",
        "doku": "daten_importieren_adressen",
    },
    {
        "satzart": "CMXAGR",
        "name": "Adressgruppen",
        "kategorie": "import",
        "beschreibung": "Adressgruppen importieren",
        "doku": "daten_importieren_adressgruppen",
    },
    {
        "satzart": "CMXCON",
        "name": "Ansprechpartner",
        "kategorie": "import",
        "beschreibung": "Ansprechpartner importieren",
        "doku": "daten_importieren_anspr",
    },
    {
        "satzart": "CMXCNT",
        "name": "Kontakte",
        "kategorie": "import",
        "beschreibung": "Kontakte (CRM) importieren",
        "doku": "daten_importieren_kontakte",
    },
    {
        "satzart": "CMXPRJ",
        "name": "Projekte",
        "kategorie": "import",
        "beschreibung": "Projekte anlegen/aktualisieren",
        "doku": "daten_importieren_projekt",
    },
    {
        "satzart": "CMXACT",
        "name": "Tätigkeiten",
        "kategorie": "import",
        "beschreibung": "Tätigkeiten (Zeiterfassung) importieren",
        "doku": "daten_importieren_taetigkeiten",
    },
    {
        "satzart": "CMXEMP",
        "name": "Mitarbeiter",
        "kategorie": "import",
        "beschreibung": "Mitarbeiterstammdaten importieren",
        "doku": "daten_importieren_mitarbeiter",
    },
    {
        "satzart": "CMXWGE",
        "name": "Lohn",
        "kategorie": "import",
        "beschreibung": "Lohndaten importieren",
        "doku": "daten_importieren_lohn",
    },
    {
        "satzart": "CMXABW",
        "name": "Abw. Lieferadresse",
        "kategorie": "import",
        "beschreibung": "Abweichende Lieferadressen importieren",
        "doku": "daten_importieren_abw",
    },
    {
        "satzart": "CMXREC",
        "name": "Periodische Rechnung",
        "kategorie": "import",
        "beschreibung": "Periodische (wiederkehrende) Rechnungen importieren",
        "doku": "daten_importieren_periodische_rechnung",
    },
    {
        "satzart": "CMXLVA",
        "name": "Lieferantenvereinbarungen",
        "kategorie": "import",
        "beschreibung": "Lieferantenvereinbarungen importieren",
        "doku": "daten_importieren_lieferantenvereinbarungen",
    },
    {
        "satzart": "CMXTRK",
        "name": "Sendungsnummer",
        "kategorie": "import",
        "beschreibung": "Sendungsnummern (Tracking) importieren",
        "doku": "daten_importieren_sendungsnummer",
    },
    {
        "satzart": "INVOICE_OUTPUT_SET",
        "name": "Rechnung ausgegeben",
        "kategorie": "import",
        "beschreibung": "Rechnung als ausgegeben markieren",
        "doku": "api_Rechnung_ausgegeben",
    },
    {
        "satzart": "CMXPAY",
        "name": "Zahlung",
        "kategorie": "import",
        "beschreibung": "Zahlungsbestätigung importieren (z.B. PayPal, Stripe)",
        "doku": "api_Payment",
    },
    # =======================================================================
    # Abfragen
    # =======================================================================
    {
        "satzart": "ACCDOC_GET",
        "name": "Buchungen abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Buchungsbelege lesen (nur lesend, kein Import möglich)",
        "doku": "api_Buchungen",
        "antwort": "ACCDOC",
    },
    {
        "satzart": "ACCBAL_GET",
        "name": "Kontensalden",
        "kategorie": "abfrage",
        "beschreibung": "Kontensalden abfragen (SuSa). Antwort: ACC_BAL (4 Felder)",
        "doku": "api_Salden",
        "antwort": "ACC_BAL",
    },
    {
        "satzart": "PRODUCT_GET",
        "name": "Produkte abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Produktstammdaten abfragen",
        "doku": "api_Produkte",
        "antwort": "CMXPRD",
    },
    {
        "satzart": "PRODUCT_PRICE_GET",
        "name": "Produktpreise abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Produktpreise nach Preisgruppe abfragen",
        "doku": "api_Produktpreise",
    },
    {
        "satzart": "PRODUCT_GROUP_GET",
        "name": "Produktgruppen abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Produktgruppen abfragen",
        "doku": "api_Produktgruppen",
    },
    {
        "satzart": "STOCK_AVAILABLE_GET",
        "name": "Verfügbarkeit",
        "kategorie": "abfrage",
        "beschreibung": "Verfügbare Lagerbestände abfragen",
        "doku": "api_Verfügbarkeit",
    },
    {
        "satzart": "STOCK_GET",
        "name": "Bestand abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Lagerbestände abfragen",
        "doku": "api_Bestand",
    },
    {
        "satzart": "STOCK_CHANGE_GET",
        "name": "Bestandsänderungen",
        "kategorie": "abfrage",
        "beschreibung": "Bestandsänderungen (Zu-/Abgänge) abfragen",
        "doku": "api_Bestandsänderungen",
    },
    {
        "satzart": "BATCH_GET",
        "name": "Chargen abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Chargen-Informationen abfragen",
        "doku": "api_Chargen",
    },
    {
        "satzart": "QUOTATION_GET",
        "name": "Angebote abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Angebote abfragen",
        "doku": "api_Angebote",
        "antwort": "CMXQTN",
    },
    {
        "satzart": "SALES_ORDER_GET",
        "name": "Kundenaufträge abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Kundenaufträge abfragen",
        "doku": "api_Kundenaufträge",
        "antwort": "CMXORD-2",
    },
    {
        "satzart": "INVOICE_GET",
        "name": "Rechnungen abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Rechnungen abfragen (Positionen, Summen, Status)",
        "doku": "api_Rechnungen",
        "antwort": "CMXINV",
    },
    {
        "satzart": "DELIVERY_GET",
        "name": "Lieferungen abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Lieferungen/Lieferscheine abfragen",
        "doku": "api_Lieferungen",
        "antwort": "CMXDLV",
    },
    {
        "satzart": "PURCHASE_ORDER_GET",
        "name": "Lieferantenaufträge",
        "kategorie": "abfrage",
        "beschreibung": "Lieferantenaufträge (Bestellungen) abfragen",
        "doku": "api_Lieferantenaufträge",
    },
    {
        "satzart": "CUSTOMER_GET",
        "name": "Kunden abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Kundenstammdaten abfragen",
        "doku": "api_Kunden",
        "antwort": "CMXKND",
    },
    {
        "satzart": "VENDOR_GET",
        "name": "Lieferanten abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Lieferantenstammdaten abfragen",
        "doku": "api_Lieferanten",
        "antwort": "CMXLIF",
    },
    {
        "satzart": "OPEN_ITEMS_GET",
        "name": "Offene Posten",
        "kategorie": "abfrage",
        "beschreibung": "Offene Posten (Debitoren/Kreditoren) abfragen. Antwort: OPEN_ITEM (20 Felder)",
        "doku": "api_Offene_Posten",
        "antwort": "OPEN_ITEM",
    },
    {
        "satzart": "PAYMENT_GET",
        "name": "Zahlungen abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Zahlungseingänge/-ausgänge abfragen",
        "doku": "api_Zahlungen",
    },
    {
        "satzart": "PAYMENT_TO_ORDER_GET",
        "name": "Zahlungen zu Aufträgen",
        "kategorie": "abfrage",
        "beschreibung": "Zuordnung Zahlungen zu Aufträgen abfragen",
        "doku": "api_Zahlungen_zu_Aufträgen",
    },
    {
        "satzart": "PAYMENT_CONDITION_GET",
        "name": "Zahlungsbedingungen",
        "kategorie": "abfrage",
        "beschreibung": "Zahlungsbedingungen abfragen",
        "doku": "api_Zahlungsbedingungen",
    },
    {
        "satzart": "PROJECT_GET",
        "name": "Projekte abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Projekte abfragen",
        "doku": "api_Projekte",
    },
    {
        "satzart": "EMPLOYEE_GET",
        "name": "Mitarbeiter abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Mitarbeiterstammdaten abfragen",
        "doku": "api_Mitarbeiter",
    },
    {
        "satzart": "ADDRESS_GET",
        "name": "Adressen abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Adressen abfragen",
        "doku": "api_Adressen",
    },
    {
        "satzart": "CONTACT_GET",
        "name": "Kontakte abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Kontakte (CRM) abfragen",
        "doku": "api_Kontakte",
    },
    {
        "satzart": "ADDRESS_GROUP_GET",
        "name": "Adressgruppen abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Adressgruppen abfragen",
        "doku": "api_Adressgruppen",
    },
    {
        "satzart": "RECURRING_INVOICE_GET",
        "name": "Periodische Rechnungen",
        "kategorie": "abfrage",
        "beschreibung": "Periodische (wiederkehrende) Rechnungen abfragen",
        "doku": "api_Periodische_rechnung",
    },
    {
        "satzart": "CUSTOMER_AGREEMENT_GET",
        "name": "Kundenvereinbarungen",
        "kategorie": "abfrage",
        "beschreibung": "Kundenvereinbarungen abfragen",
        "doku": "api_Kundenvereinbarungen",
    },
    {
        "satzart": "VENDOR_AGREEMENT_GET",
        "name": "Lieferantenvereinbarungen",
        "kategorie": "abfrage",
        "beschreibung": "Lieferantenvereinbarungen abfragen",
        "doku": "api_Lieferantenvereinbarungen",
    },
    {
        "satzart": "ABW_GET",
        "name": "Abw. Lieferadressen",
        "kategorie": "abfrage",
        "beschreibung": "Abweichende Lieferadressen abfragen",
        "doku": "api_abw",
    },
    {
        "satzart": "ACTIVITIES_GET",
        "name": "Tätigkeiten abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Tätigkeiten (Zeiterfassung) abfragen",
        "doku": "api_Taetigkeiten",
    },
    {
        "satzart": "PROJECT_STAFF_GET",
        "name": "Projektmitarbeiter",
        "kategorie": "abfrage",
        "beschreibung": "Projektmitarbeiter-Zuordnungen abfragen",
        "doku": "api_Projektmitarbeiter",
    },
    {
        "satzart": "PRODUCTION_ORDER_GET",
        "name": "Produktionsaufträge",
        "kategorie": "abfrage",
        "beschreibung": "Produktionsaufträge abfragen",
        "doku": "api_Produktionsaufträge",
    },
    {
        "satzart": "BOM_GET",
        "name": "Stücklisten abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Stücklisten (Bill of Materials) abfragen",
        "doku": "api_Stücklisten",
    },
    {
        "satzart": "PRICE_GROUP_GET",
        "name": "Preisgruppen abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Preisgruppen abfragen",
        "doku": "api_Preisgruppen",
    },
    {
        "satzart": "VOUCHER_GET",
        "name": "Gutscheine abfragen",
        "kategorie": "abfrage",
        "beschreibung": "Gutscheine abfragen",
        "doku": "api_Gutscheine",
    },
    {
        "satzart": "VENDOR_CREDIT_GET",
        "name": "Gutschriften an Lieferant",
        "kategorie": "abfrage",
        "beschreibung": "Gutschriften an Lieferanten abfragen",
        "doku": "api_Gutschriften_an_lieferant",
    },
    {
        "satzart": "ORDER_BACKLOG_GET",
        "name": "Auftragsbestand",
        "kategorie": "abfrage",
        "beschreibung": "Auftragsbestand (offene Aufträge) abfragen",
        "doku": "api_Auftragsbestand",
    },
    {
        "satzart": "SEARCH_ENGINE_GET",
        "name": "Suchmaschinen",
        "kategorie": "abfrage",
        "beschreibung": "Suchmaschinen-Konfiguration abfragen",
        "doku": "api_Suchmaschinen",
    },
    {
        "satzart": "DATEV_GET",
        "name": "DATEV-Export",
        "kategorie": "abfrage",
        "beschreibung": "Buchungen im DATEV-Format abfragen",
        "doku": "api_Datev",
    },
    # =======================================================================
    # Aktionen
    # =======================================================================
    {
        "satzart": "ABRECHNUNGSLAUF",
        "name": "Abrechnungslauf",
        "kategorie": "aktion",
        "beschreibung": "Abrechnungslauf ausführen (wiederkehrende Rechnungen erstellen)",
        "doku": "api_Abrechnungslauf",
    },
    {
        "satzart": "INVOICE_COLLECTION_OUTPUT",
        "name": "Rechnungen Sammelausgabe",
        "kategorie": "aktion",
        "beschreibung": "Mehrere Rechnungen auf einmal als PDF ausgeben",
        "doku": "api_Rechnungen_Sammelausgabe",
    },
    {
        "satzart": "DUE_DELIVERIES",
        "name": "Fällige Lieferungen",
        "kategorie": "aktion",
        "beschreibung": "Fällige Lieferungen ermitteln und auslösen",
        "doku": "api_Fällige_Lieferungen",
    },
    {
        "satzart": "DUE_PURCHASE_ORDERS",
        "name": "Fällige Lieferantenaufträge",
        "kategorie": "aktion",
        "beschreibung": "Fällige Lieferantenaufträge ermitteln",
        "doku": "api_Fällige_Lieferantenaufträge",
    },
    {
        "satzart": "PAYMENT_CONFIRMATION_MAIL",
        "name": "Zahlungseingangs-Mail",
        "kategorie": "aktion",
        "beschreibung": "Zahlungseingangsbestätigung per E-Mail senden",
        "doku": "api_Zahlungseingangs_Mail",
    },
    {
        "satzart": "SHIPPING_HANDOVER",
        "name": "Versandübergabe",
        "kategorie": "aktion",
        "beschreibung": "Versandübergabe an Logistikdienstleister",
        "doku": "api_Versanduebergabe",
    },
    {
        "satzart": "SHIPPING_NOTIFICATION",
        "name": "Versandbenachrichtigung",
        "kategorie": "aktion",
        "beschreibung": "Versandbenachrichtigung an Kunden senden",
        "doku": "api_Versandbenachrichtigung",
    },
    {
        "satzart": "SHIPPING_CONFIRMATION",
        "name": "Versandbestätigung",
        "kategorie": "aktion",
        "beschreibung": "Versandbestätigung setzen",
        "doku": "api_Versandbestätigung",
    },
    {
        "satzart": "ADDRESS_ASSIGN",
        "name": "Adressen zuordnen",
        "kategorie": "aktion",
        "beschreibung": "Adressen einer Adressgruppe zuordnen",
        "doku": "api_Adressen_zuordnen",
    },
    {
        "satzart": "BANK_STATEMENT_GET",
        "name": "Bankauszug abholen",
        "kategorie": "aktion",
        "beschreibung": "Kontoauszug per HBCI/FinTS abholen",
        "doku": "api_Bankkonto_Auszug_abholen",
    },
]


# ---- Hilfsfunktionen ----

# Index für schnellen Zugriff (case-insensitive)
_INDEX: dict[str, dict] = {s["satzart"].upper(): s for s in SATZARTEN}

KATEGORIE_LABELS = {
    "import": "Datenimport",
    "abfrage": "Abfragen",
    "aktion": "Aktionen",
}

KATEGORIE_REIHENFOLGE = ["import", "abfrage", "aktion"]


def get_satzart(name: str) -> dict | None:
    """Satzart-Dict nach Name (case-insensitive)."""
    return _INDEX.get(name.upper())


def suche(stichwort: str) -> list[dict]:
    """Satzarten nach Stichwort filtern (case-insensitive, sucht in allen Textfeldern)."""
    s = stichwort.lower()
    return [
        sa
        for sa in SATZARTEN
        if s in sa["satzart"].lower()
        or s in sa["name"].lower()
        or s in sa["beschreibung"].lower()
        or s in sa.get("doku", "").lower()
    ]


def nach_kategorie() -> dict[str, list[dict]]:
    """Satzarten gruppiert nach Kategorie zurückgeben."""
    result: dict[str, list[dict]] = {}
    for sa in SATZARTEN:
        kat = sa["kategorie"]
        result.setdefault(kat, []).append(sa)
    return result


def doku_url(sa: dict) -> str:
    """Vollständige Doku-URL für eine Satzart."""
    return f"{DOKU_BASIS}{sa['doku']}"


def beispiel_url(sa: dict) -> str | None:
    """Beispiel-CSV-URL (falls vorhanden)."""
    csv = sa.get("beispiel_csv")
    return f"{BEISPIEL_BASIS}{csv}" if csv else None
