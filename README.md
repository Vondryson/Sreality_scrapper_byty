# Sreality Chaty Tracker

Neveřejná aplikace pro dlouhodobou analýzu chat a chalup nabízených k prodeji na Sreality.cz. Produktový rozsah a cílovou architekturu určuje [specifikace](specifikace.md), pořadí práce [roadmapa](roadmap.md) a aktuální stav [progres](progres.md).

Projekt je ve fázi M0 – ověření zdroje, dat a nákladů. Původní scraper z roku 2024 zůstává dočasně v kořenových souborech a adresářích jako referenční legacy implementace; nový produkční kód vzniká odděleně v `backend/`.

## Cílová struktura

```text
backend/
  src/sreality_tracker/   Python backend, scraper a datová pipeline
  tests/                  unit a integrační testy
frontend/                 Next.js aplikace (inicializace v M3-01)
infra/terraform/          GCP infrastruktura (implementace od M4-02)
docs/adr/                 architektonická rozhodnutí
scripts/                  bezpečné pomocné a validační skripty
```

Kořenové `scraper/`, `db_managment/`, `utils/`, `run.py`, `run_scheduled.py`, `config.py` a `old version/` jsou původní kód. Nové moduly je nesmějí importovat.

## Požadovaný toolchain

- Python 3.13,
- Node.js 24 LTS a npm 11,
- Docker Desktop s Docker Compose,
- Terraform bude potřeba až v M4 a zatím není lokální podmínkou,
- Ruff, mypy a pytest se instalují přes Python dev dependencies.

Python 3.13 je [podporovaná stabilní řada](https://devguide.python.org/versions/) do října 2029. Node.js 24 je [LTS řada](https://nodejs.org/en/about/previous-releases) podporovaná do dubna 2028. Patch verze lze průběžně aktualizovat bez změny architektury.

## První lokální nastavení

V PowerShellu:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Na Linuxu/macOS se aktivace liší:

```bash
source .venv/bin/activate
```

Frontend zatím nemá `package.json`; vznikne až v tasku `M3-01`, aby nebyl předčasně zvolen frameworkový scaffold bez stabilního API kontraktu.

## Kontroly kvality

```powershell
python -m ruff check backend scripts
python -m ruff format --check backend scripts
python -m mypy
python -m pytest
```

Automatická oprava formátu:

```powershell
python -m ruff check --fix backend scripts
python -m ruff format backend scripts
```

Pokud dev dependencies ještě nejsou nainstalované, lze základ syntaxe ověřit příkazem:

```powershell
python -m compileall backend/src backend/tests
```

## Pravidla práce

- Nezačínat task bez kontroly `specifikace.md`, `roadmap.md` a `progres.md`.
- Stav tasku aktualizovat v `progres.md` ve stejné sadě změn.
- Tajné údaje patří pouze do lokálního `.env` nebo později do Secret Manageru.
- Nový kód nesmí používat absolutní uživatelské cesty ani SQLite/CSV jako autoritativní úložiště.
- Živé integrační testy musí být explicitní a šetrné; nesmějí běžet v běžné unit test sadě.
- Produkční GCP změny se nedělají před uzavřením validační brány M0.

Detailnější pokyny pro přispívání jsou v [CONTRIBUTING.md](CONTRIBUTING.md).
