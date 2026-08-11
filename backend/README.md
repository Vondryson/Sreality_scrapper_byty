# Backend

Nový Python backend, scraper a datová pipeline. Balíček používá `src` layout:

- `sreality_tracker/api` – FastAPI transportní vrstva,
- `sreality_tracker/core` – konfigurace a společné průřezové služby,
- `sreality_tracker/db` – databázové modely, repositories a migrace,
- `sreality_tracker/domain` – doménové modely a pravidla bez frameworkových závislostí,
- `sreality_tracker/scraper` – klient, parser a orchestrace sběru,
- `sreality_tracker/storage` – raw payloady a fotografie.

Implementace se doplňuje podle tasků M0–M2.

## Lokální PostgreSQL

Task `M1-02` přidává PostgreSQL 16 v Docker Compose. Vývojové credentials jsou
záměrně lokální a nesmějí se použít v produkci.

```powershell
docker compose up -d postgres
docker compose ps
```

Výchozí aplikační URL:

```text
postgresql+psycopg://sreality:sreality_local_only@localhost:5432/sreality_tracker
```

Migrace:

```powershell
$env:SREALITY_DATABASE_URL = "postgresql+psycopg://sreality:sreality_local_only@localhost:5432/sreality_tracker"
python -m alembic upgrade head
python -m alembic current
```

Databázový kontejner lze zastavit bez smazání dat:

```powershell
docker compose stop postgres
```

Příkaz `docker compose down --volumes` smaže lokální databázová data a není
součástí běžného workflow.

## Integrační test migrací

Compose při prvním založení volume vytvoří samostatnou databázi
`sreality_tracker_test`. Test z bezpečnostních důvodů odmítne jiný název
databáze a provede destruktivní cyklus upgrade/downgrade/upgrade pouze v ní.

```powershell
$env:SREALITY_TEST_DATABASE_URL = "postgresql+psycopg://sreality:sreality_local_only@localhost:5432/sreality_tracker_test"
python -m pytest -m integration backend/tests/integration/test_migrations.py
```

## Konfigurace a logování

Nový backend čte pouze environment variables s prefixem `SREALITY_`; legacy
názvy z původního scraperu se nepoužívají. Bez povinné databázové URL start
selže stručnou validovanou chybou, která nevypisuje zadanou hodnotu.

Bezpečné lokální hodnoty jsou v kořenovém `.env.example`. Soubor je vzor, není
automaticky načítán a nesmí obsahovat produkční credentials. V PowerShellu lze
hodnoty nastavit například takto:

```powershell
$env:SREALITY_DATABASE_URL = "postgresql+psycopg://sreality:sreality_local_only@localhost:5432/sreality_tracker"
$env:SREALITY_ENVIRONMENT = "local"
$env:SREALITY_RAW_STORAGE_PATH = "data/raw"
$env:SREALITY_LOG_LEVEL = "INFO"
```

Logy backendu jsou JSON Lines. Podporovaný kontext zahrnuje `event`, `step`,
`run_id`, `listing_id` a `error_type`. Formatter rediguje běžné tokeny, hesla,
API klíče, cookies a hesla vložená v URL; výjimka zapisuje pouze svůj typ, ne
potenciálně citlivou zprávu.

## Sreality HTTP klient

`sreality_tracker.scraper.client.SrealityClient` používá jednu synchronní
`httpx.Client` session pro celý běh. Podporuje potvrzené filtry `chata` (33) a
`chalupa` (43), timeout, globální prodlevu, omezený exponenciální retry s
jitterem a kontrolu HTTP statusu, cílového hostu, Content-Type a přítomnosti
SSR `__NEXT_DATA__`.

Klient je záměrně sekvenční. Neobchází CAPTCHA, blokace ani jiné omezení
zdroje. Síťový smoke test je oddělený od běžné testovací sady a popsaný v
`backend/tests/live/README.md`.

## Parser a doménové modely

`sreality_tracker.scraper.parser` převádí search a detail `__NEXT_DATA__` na
frameworkově nezávislé modely v `sreality_tracker.domain.listings`. Povinná je
pouze identita a potvrzená kategorie; volitelná nebo neznámá pole parser
nezpůsobí pád.

Analytická cena `0` se normalizuje na `None` s `price_on_request=true`, původní
hodnota ale zůstává zachována. Typované modely obsahují klíčové ceny, plochy,
lokalitu a metadata obrázků; současně uchovávají úplný detail a `params` mapping
pro budoucí JSONB snapshot, takže nová zdrojová pole nejsou tiše zahozena.
