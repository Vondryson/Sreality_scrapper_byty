# Vývojové standardy

## Workflow tasku

1. Přečíst `specifikace.md`, definici tasku v `roadmap.md` a stav v `progres.md`.
2. Ověřit závislosti tasku a označit jej `[~]`.
3. Udělat nejmenší ucelenou změnu, která splní jeho „Hotovo, když“.
4. Přidat nebo upravit testy ve stejné změně jako produkční kód.
5. Spustit relevantní lint, type-check a testy.
6. Zapsat výsledky do `progres.md` a teprve poté task označit `[x]`.

## Python

- Produkční balíček je `sreality_tracker` pod `backend/src`.
- Používat type hints pro veřejná i interní rozhraní; mypy běží ve strict režimu.
- Formátování a lint zajišťuje Ruff podle `pyproject.toml`.
- Doménová logika nesmí záviset přímo na FastAPI, SQLAlchemy ani síti, pokud to není odpovědnost daného adaptéru.
- Zachytávat konkrétní výjimky a přidávat užitečný kontext. Holý `except:` je zakázaný.
- Čas předávat jako timezone-aware UTC; v testech používat řízené hodiny místo přímého spoléhání na aktuální čas.
- Peníze ukládat jako celočíselné CZK a chybějící hodnoty jako `None`/SQL `NULL`.

## Testy

- `backend/tests/unit` nevolá síť, GCP ani skutečnou databázi.
- `backend/tests/integration` testuje hranice adaptérů, zejména PostgreSQL.
- `backend/tests/live` obsahuje pouze explicitně spouštěné šetrné kontroly externích API.
- Fixtures nesmějí obsahovat osobní údaje prodejců, credentials ani zbytečně celé cizí texty či fotografie.
- Oprava chyby má mít regresní test.

## Frontend

- TypeScript v strict režimu.
- API kontrakt generovat nebo typovat z OpenAPI; neduplikovat ručně rozdílné datové modely.
- Filtry držet v URL a data stránkovat serverově.
- Každá stránka má mít loading, empty a error stav.
- Interaktivní prvky musí být ovladatelné klávesnicí a mít srozumitelný český popisek.

Konkrétní frontendové lint/test příkazy budou doplněny v `M3-01`, kdy vznikne `package.json` a lockfile.

## Infrastruktura

- Produkční infrastruktura se mění pouze přes Terraform, pokud specifikace nestanoví jinak.
- Před aplikací vždy zkontrolovat plán a destruktivní změny řešit explicitně.
- Secrets nevkládat do Git historie, Terraform variables ani state v otevřené podobě.
- Cloud Run používá `min-instances=0`; nové fixní náklady vyžadují upozornění uživatele.

## Commity a dokumentace

- Jeden commit nebo logická sada změn má řešit jeden task nebo jasně popsanou část velkého tasku.
- Commit message doporučeně začíná ID tasku, například `M1-04: add resilient Sreality client`.
- Změna produktového rozhodnutí vyžaduje aktualizaci `specifikace.md`.
- Změna pořadí nebo akceptace tasku vyžaduje aktualizaci `roadmap.md`.

