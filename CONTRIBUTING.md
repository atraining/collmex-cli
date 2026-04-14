# Contributing

Danke fuer dein Interesse an `collmex-cli`. Dieses Dokument beschreibt, wie
du das Projekt lokal aufsetzt und gegen eine eigene Collmex-Instanz testest.

> **Lizenz-Hinweis:** Der Code ist proprietaer (siehe [LICENSE](LICENSE)).
> Pull Requests und Patches sind willkommen, werden aber bei Merge dem
> Copyright-Inhaber (Christopher Helm) zugerechnet. Bei groesseren
> Aenderungen vorher kurz anfragen: **me@christopher-helm.com**.

## Lokales Setup

```bash
git clone https://github.com/atraining/collmex-cli.git
cd collmex-cli
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env            # Credentials eintragen
```

## Tests

```bash
pytest                          # Unit-Tests (Mock-API, default)
pytest -m live                  # Live-Tests (braucht echte .env)
pytest --cov=collmex            # mit Coverage
```

Unit-Tests laufen ohne Collmex-Account. Live-Tests schreiben/lesen gegen
die echte API — **nur gegen einen Test-Mandanten** laufen lassen.

## Eigenen Test-Mandanten bei Collmex anlegen

1. Account auf [collmex.de](https://www.collmex.de) registrieren. Fuer
   API-Zugriff mindestens Tarif "buchhaltung basic".
2. In Collmex: **Verwaltung -> Benutzer** — einen neuen Benutzer `apiuser`
   anlegen. Dieser User ist der API-Zugang.
3. In Collmex: **Verwaltung -> Einstellungen -> API** — API aktivieren,
   die Kundennummer notieren.
4. `.env` ausfuellen:
   ```
   COLLMEX_CUSTOMER=<deine-kundennr>
   COLLMEX_USER=apiuser
   COLLMEX_PASSWORD=<api-passwort>
   ```
5. Verbindung pruefen:
   ```bash
   collmex status
   ```

> **Achtung:** Schreibende Satzarten (CMXLRN, CMXUMS, CMXKND, CMXLIF,
> CMXINV) erzeugen **echte** Buchungen in dem Mandanten, der in
> `COLLMEX_CUSTOMER` steht. Niemals gegen einen Produktiv-Mandanten
> ohne expliziten Test-Flow entwickeln.

## Code-Stil

- Formatter/Linter: `ruff` (Konfiguration in `pyproject.toml`)
  ```bash
  ruff check .
  ruff format .
  ```
- Tests: `pytest`. Neue Features brauchen Tests.
- Python: `>= 3.11`.
- Sprache im Code: Englisch fuer Bezeichner, Deutsch fuer User-Output und
  Dokumentation (das Zielpublikum sind deutsche Buchhalter).

## Neue API-Erkenntnisse

Wenn du beim Testen auf undokumentiertes API-Verhalten stoesst: bitte
dokumentieren in:

- `docs/docs/api/api-fields.md` — verifizierte Feldstrukturen
- `docs/docs/api/api-patterns.md` — Gotchas und Workarounds
- `collmex/api_reference.py` — wenn eine neue Satzart hinzukommt

## Pull Requests

1. Fork und Branch (`feature/...` oder `fix/...`)
2. Tests schreiben + lokal laufen lassen (`pytest`)
3. `ruff check .` und `ruff format .`
4. Commit-Message auf Deutsch oder Englisch, aber beschreibend
5. PR gegen `main` oeffnen

## Sicherheit

**Keine Credentials committen.** `.env` ist in `.gitignore`. Wenn dir
versehentlich ein Secret in einen Commit rutscht: sofort das Passwort
rotieren, dann Historie bereinigen (`git filter-repo`) und force-push.
