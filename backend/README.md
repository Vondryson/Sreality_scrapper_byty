# Backend

Nový Python backend, scraper a datová pipeline. Balíček používá `src` layout:

- `sreality_tracker/api` – FastAPI transportní vrstva,
- `sreality_tracker/core` – konfigurace a společné průřezové služby,
- `sreality_tracker/db` – databázové modely, repositories a migrace,
- `sreality_tracker/domain` – doménové modely a pravidla bez frameworkových závislostí,
- `sreality_tracker/scraper` – klient, parser a orchestrace sběru,
- `sreality_tracker/storage` – raw payloady a fotografie.

Adresáře jsou zatím scaffold. Implementace se doplňuje podle tasků M0–M2.

