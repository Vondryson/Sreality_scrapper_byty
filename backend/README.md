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

## Raw payload storage

`sreality_tracker.storage.raw` poskytuje jednotné rozhraní pro lokální filesystem
a neveřejný GCS bucket. Kanonický klíč má tvar:

```text
raw/runs/{run_id}/listings/{sreality_id}.json.gz
```

JSON se serializuje kanonicky do UTF-8 a ukládá jako deterministický gzip.
Opakovaný zápis stejného obsahu je no-op; jiný obsah pod stejným klíčem vyvolá
konflikt a nikdy se tiše nepřepíše. GCS adaptér používá create-only generation
precondition a CRC32C kontrolu. Lokální root se předává explicitně z validované
konfigurace; žádná uživatelská absolutní cesta není v kódu.

## Scrape pipeline

`sreality_tracker.scraper.source.SrealityListingSource` prochází všechny stránky
obou potvrzených kategorií, páruje nabídky se skutečnými detail odkazy v HTML a
načítá každý externí listing nejvýše jednou za kategorii. Orchestrace v
`sreality_tracker.scraper.pipeline.ScrapePipeline` vytvoří auditní `scrape_run`
a ukládá každý detail v jedné databázové transakci společně s aktuálním stavem,
metadaty obrázků a pozorováním.

`logical_key` běhu je unikátní. Opakované spuštění již dokončeného klíče vrátí
existující výsledek bez síťových požadavků a bez duplicit. Kategorie se označí
jako kompletní pouze po úplném průchodu jejího iterátoru; chyba se uloží jen jako
bezpečný typ a výsledný běh je `partial` nebo `failed`. Události a hromadná
deaktivace jsou záměrně až součástí M1-08 a M1-09.

## Ruční CLI

Po instalaci projektu lze bez zápisu a bez HTTP requestu ověřit konfiguraci a
spojení s databází:

```powershell
sreality-scrape check
```

Ruční kompletní běh vyžaduje explicitní unikátní klíč. Jeho opakování je
idempotentní a vrátí již uložený výsledek:

```powershell
sreality-scrape run --logical-key "manual:2026-08-11T1200"
```

CLI vypisuje jediný strojově čitelný JSON objekt a při chybě zveřejní pouze typ
výjimky, nikoli credentials nebo obsah odpovědi. Lokální `run` používá
`SREALITY_RAW_STORAGE_PATH`. Produkce přepne raw payloady scraperu i archiv
oblíbených fotografií na společný neveřejný bucket pomocí:

```text
SREALITY_STORAGE_BACKEND=gcs
SREALITY_GCP_PROJECT_ID=sreality-scrapper-504307
SREALITY_STORAGE_BUCKET=sreality-scrapper-504307-application-data
```

Jiný projekt nebo bucket validace odmítne. GCS adaptéry používají create-only
precondition, takže opakování stejného zápisu je idempotentní a odlišný obsah se
nikdy nepřepíše.

## Google Routes

Silniční vzdálenost používá výhradně Compute Routes `DRIVE` s
`TRAFFIC_UNAWARE` a minimálním field maskem `distanceMeters,duration`. Výsledek
se trvale cachuje podle listingu, verze referenční Prahy a hashe cílových GPS.
Chyba poskytovatele nevrací transakci nabídky; chybějící trasu lze retryovat:

```powershell
$env:SREALITY_ROUTES_PROJECT_ID = "sreality-scrapper-504307"
$env:SREALITY_ROUTES_ACCESS_TOKEN = gcloud auth print-access-token --configuration=sreality-tracker
sreality-scrape routes-backfill --limit 300
Remove-Item Env:SREALITY_ROUTES_ACCESS_TOKEN
```

Backfill nikdy nepřijme limit vyšší než 300 a klient má samostatný procesní
budget. Projektová denní consumer quota 300 zůstává hlavní tvrdou pojistkou.
Výstup CLI obsahuje `provider_requests`, `cache_hits`, `created` a `failed`.

## Google OAuth a soukromé API

Všechna data nabídek, analytika, mapa, uživatelská data a provozní endpointy
vyžadují owner session. Veřejné zůstávají pouze health/readiness, OpenAPI a
OAuth entry/callback. Login začíná na:

```text
GET /api/v1/auth/google/login
```

Backend používá authorization-code flow se state, nonce a PKCE, ověřuje Google
ID token a přesný `SREALITY_OWNER_EMAIL`. Osmihodinová session cookie je
`HttpOnly`, `Secure`, `SameSite=Lax`; zápisové requesty musí poslat CSRF token
z `GET /api/v1/auth/session` v hlavičce `X-CSRF-Token`.
Po úspěšném callbacku backend přesměruje pouze na pevně nakonfigurovaný a
validovaný origin `SREALITY_FRONTEND_URL` (lokálně `http://localhost:3000`).

Owner-only provozní API:

- `GET /api/v1/operations/scrape-runs/latest`,
- `POST /api/v1/operations/scrape-runs` s unikátním `logical_key`.

Ruční trigger nejprve rezervuje unikátní `manual:` run a práci spouští po
odpovědi. Opakování stejného klíče vrátí stejné run ID. Lokální server načte
ignorovaný `.env` například přes `uvicorn --env-file .env`; secrets se nikdy
nepřidávají do `.env.example` ani do Gitu.

## FastAPI

Aplikační factory je `sreality_tracker.api.create_app`; načtení modulu samo o
sobě nečte environment ani neotevírá databázi. Lokální server lze spustit:

```powershell
uvicorn sreality_tracker.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Veřejný kontrakt je verzovaný pod `/api/v1`. Liveness
`/api/v1/health/live` nekontroluje externí závislosti, readiness
`/api/v1/health/ready` provádí read-only DB probe. Chyby mají jednotný tvar
`{"error":{"code":"...","message":"..."}}` a OpenAPI je dostupné na
`/openapi.json`. Request-scoped SQLAlchemy session se získává přes FastAPI
dependency injection; autentizace bude doplněna v M2-08.

Datové endpointy M2:

- `GET /api/v1/listings` – filtrovaný, řazený a stránkovaný seznam,
- `GET /api/v1/listings/{listing_id}` – detail včetně fotografií a vzdáleností,
- `GET /api/v1/listings/{listing_id}/history` – ceny a události svázané s běhy,
- `GET /api/v1/map/listings` – filtrované nabídky s kompletní GPS dvojicí,
- `GET /api/v1/analytics/price-medians` – aktuální a historický filtrovaný medián.
- `PATCH /api/v1/listings/{listing_id}/user-data` – owner-only oblíbený stav a poznámka.

Historické mediány používají snapshotové ceny a plochy z jednotlivých
úspěšných běhů. Neúspěšné/částečné běhy, `NULL` ceny a ceny na vyžádání se do
historické řady nezapočítávají.

Zápis soukromých dat vyžaduje ověřenou owner identitu. Oblíbení nabídky
spustí odolnou archivaci jejích fotografií: archivní klíč je deterministický
podle interního listing ID a SHA-256 fingerprintu zdroje, již archivované
obrázky se nestahují znovu a jednotlivé chyby zůstanou ve stavu `failed` pro
pozdější retry. Odznačení nabídky archiv nemaže.
