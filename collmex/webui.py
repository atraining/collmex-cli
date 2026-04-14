"""Collmex Web-UI Scraper — Fallback fuer Daten die per API nicht verfuegbar sind.

Die Collmex-API deckt nicht alles ab. Einige Stammdaten (Mengeneinheiten,
Zahlungsbedingungen, Firmenstammdaten, Kontenrahmen) gibt es NUR per Web-UI.

Dieses Modul stellt einen Session-basierten Web-Client bereit, der sich
per 2-Schritt-Login anmeldet und HTML-Seiten scrapt.

Voraussetzung: COLLMEX_WEB_USER und COLLMEX_WEB_PASSWORD in .env
(das sind Web-Zugangsdaten, NICHT der API-User).
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

COLLMEX_BASE = "https://www.collmex.de/c.cmx"


# ---------------------------------------------------------------------------
# Datenklassen
# ---------------------------------------------------------------------------


@dataclass
class Mengeneinheit:
    """Eine Mengeneinheit aus den Collmex-Einstellungen."""

    code: str
    kuerzel: str
    kuerzel_en: str
    nachkommastellen: int
    bezeichnung: str
    iso_code: str


@dataclass
class Zahlungsbedingung:
    """Eine Zahlungsbedingung aus den Collmex-Einstellungen."""

    nr: int
    bezeichnung: str


@dataclass
class Firmenstammdaten:
    """Firmenstammdaten aus der Collmex Web-UI."""

    firma: str
    strasse: str
    plz: str
    ort: str
    land: str
    email: str
    ust_idnr: str
    steuernummer: str
    bankkonto: str
    kontenrahmen: str


# ---------------------------------------------------------------------------
# Web-UI Client
# ---------------------------------------------------------------------------


class CollmexWebUI:
    """Session-basierter Client fuer die Collmex Web-Oberflaeche.

    Login-Ablauf (2-Schritt):
    1. GET auf Login-Seite (initialisiert Session-Cookie)
    2. POST mit Web-Benutzer-Credentials

    WICHTIG: Der API-User (apiuser) hat KEINEN Web-Zugang!
    Es braucht einen separaten Web-Benutzer.
    """

    def __init__(
        self,
        customer: str | None = None,
        web_user: str | None = None,
        web_password: str | None = None,
    ):
        load_dotenv()
        self.customer = customer or os.getenv("COLLMEX_CUSTOMER", "")
        self.web_user = web_user or os.getenv("COLLMEX_WEB_USER", "")
        self.web_password = web_password or os.getenv("COLLMEX_WEB_PASSWORD", "")
        self._session: requests.Session | None = None

        if not self.customer:
            raise ValueError("COLLMEX_CUSTOMER nicht konfiguriert")
        if not self.web_user:
            raise ValueError(
                "COLLMEX_WEB_USER nicht konfiguriert. "
                "Web-UI-Zugang braucht einen Web-Benutzer (nicht den API-User)."
            )
        if not self.web_password:
            raise ValueError("COLLMEX_WEB_PASSWORD nicht konfiguriert")

    def _url(self, path: str) -> str:
        """Baut Collmex-URL zusammen."""
        return f"{COLLMEX_BASE}?{self.customer},{path}"

    def _login(self) -> requests.Session:
        """2-Schritt-Login und Session-Aufbau."""
        session = requests.Session()

        # Schritt 1: GET Login-Seite (initialisiert Session-Cookies)
        r1 = session.get(self._url("0,login"), timeout=15)
        r1.raise_for_status()
        logger.debug(
            "Login Schritt 1: Status %d, Cookies: %s", r1.status_code, list(session.cookies.keys())
        )

        # Schritt 2: POST mit Credentials
        login_data = {
            "group_benutzerId": self.web_user,
            "group_kennwort": self.web_password,
        }
        r2 = session.post(self._url("1,login"), data=login_data, timeout=15)
        r2.raise_for_status()
        logger.debug(
            "Login Schritt 2: Status %d, Cookies: %s", r2.status_code, list(session.cookies.keys())
        )

        # Pruefen ob Login erfolgreich (Session-Cookie muss da sein)
        sid_key = f"sid_{self.customer}"
        if sid_key not in session.cookies:
            raise ValueError("Web-UI Login fehlgeschlagen (kein Session-Cookie)")

        return session

    @property
    def session(self) -> requests.Session:
        """Lazy Login — Session wird beim ersten Zugriff aufgebaut."""
        if self._session is None:
            self._session = self._login()
        return self._session

    def _fetch(self, path: str) -> str:
        """Holt eine Seite und gibt den HTML-Text zurueck."""
        r = self.session.get(self._url(path), timeout=15)
        r.raise_for_status()
        r.encoding = "iso-8859-1"
        return r.text

    # ------------------------------------------------------------------
    # Seiten-Scraper
    # ------------------------------------------------------------------

    def mengeneinheiten(self) -> list[Mengeneinheit]:
        """Alle konfigurierten Mengeneinheiten abrufen."""
        html = self._fetch("1,uomch")

        codes = re.findall(r'name="table_\d+_me"[^>]*value="([^"]+)"', html)
        kuerzels = re.findall(r'name="table_\d+_kuerzel"[^>]*value="([^"]*?)"', html)
        kuerzels_en = re.findall(r'name="table_\d+_kuerzelEN"[^>]*value="([^"]*?)"', html)
        nachkomma = re.findall(r'name="table_\d+_nachkommastellen"[^>]*value="([^"]+)"', html)
        bezeichnungen = re.findall(r'name="table_\d+_bezeichnung"[^>]*value="([^"]+)"', html)
        iso_codes = re.findall(r'name="table_\d+_isoCode"[^>]*value="([^"]*?)"', html)

        result = []
        for i in range(len(codes)):
            result.append(
                Mengeneinheit(
                    code=codes[i],
                    kuerzel=kuerzels[i] if i < len(kuerzels) else "",
                    kuerzel_en=kuerzels_en[i] if i < len(kuerzels_en) else "",
                    nachkommastellen=int(nachkomma[i]) if i < len(nachkomma) else 2,
                    bezeichnung=bezeichnungen[i] if i < len(bezeichnungen) else "",
                    iso_code=iso_codes[i] if i < len(iso_codes) else "",
                )
            )
        return result

    def zahlungsbedingungen(self) -> list[Zahlungsbedingung]:
        """Alle konfigurierten Zahlungsbedingungen abrufen."""
        html = self._fetch("1,zbli")

        result = []
        lines = html.split("\n")
        for i, line in enumerate(lines):
            if "nowrap" in line and 'class="r"' in line:
                nr_match = re.search(r">(\d+)<", line) or re.search(r">(\d+)\s*$", line.strip())
                if nr_match and i + 1 < len(lines):
                    bez_match = re.search(r">([^<]+)<", lines[i + 1]) or re.search(
                        r">([^<]+)\s*$", lines[i + 1].strip()
                    )
                    if bez_match:
                        result.append(
                            Zahlungsbedingung(
                                nr=int(nr_match.group(1)),
                                bezeichnung=bez_match.group(1).strip(),
                            )
                        )
        return result

    def firmenstammdaten(self) -> Firmenstammdaten:
        """Firmenstammdaten abrufen."""
        html = self._fetch("1,coch,1")

        def _val(name: str) -> str:
            m = re.search(rf'name="{re.escape(name)}"[^>]*value="([^"]*?)"', html)
            return m.group(1).replace("&amp;", "&") if m else ""

        # Kontenrahmen aus Select
        kr_match = re.search(
            r'name="group_firmaNr".*?<option[^>]*selected[^>]*value="[^"]*"[^>]*>([^<]*)',
            html,
            re.DOTALL,
        )
        kontenrahmen = kr_match.group(1).strip().replace("&nbsp;", "").strip() if kr_match else ""

        return Firmenstammdaten(
            firma=_val("addresse_adrFirma"),
            strasse=_val("addresse_adrStrasse"),
            plz=_val("addresse_adrPLZOrt"),
            ort=_val("addresse_adrOrt"),
            land=_val("addresse_adrLand"),
            email=_val("addresse_adrEmail"),
            ust_idnr=_val("addresse_umsatzsteuernummer"),
            steuernummer=_val("addresse_steuernummer"),
            bankkonto=_val("addresse_kontoNr"),
            kontenrahmen=kontenrahmen,
        )


# ---------------------------------------------------------------------------
# URL-Referenz (fuer Dokumentation und zukuenftigen Ausbau)
# ---------------------------------------------------------------------------

SEITEN = {
    "settings": "1,settings",
    "firma": "1,coch,1",
    "kontenrahmen": "1,ac",
    "mengeneinheiten": "1,uomch",
    "zahlungsbedingungen": "1,zbli",
    "textbausteine": "1,tbli",
    "mahnungen": "1,dnst",
    "nummernvergabe": "1,nr",
    "druck": "1,stpr",
    "benutzer": "1,us",
    "login": "0,login",
}
"""Bekannte Web-UI-Seiten — Pfad nach der Kundennummer."""
