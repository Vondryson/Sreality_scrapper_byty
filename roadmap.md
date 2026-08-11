# Roadmap projektu Sreality Chaty Tracker

## 1. Jak roadmapu používat

Tato roadmapa převádí [specifikaci](specifikace.md) na proveditelné tasky. `specifikace.md` zůstává autoritativním zdrojem produktových a architektonických rozhodnutí. Aktuální stav práce se zapisuje do [progresu](progres.md).

Každý člověk nebo agent musí před zahájením práce:

1. přečíst `specifikace.md`, `roadmap.md` a `progres.md`,
2. vybrat první neblokovaný task podle závislostí,
3. označit právě jeden hlavní task jako rozpracovaný,
4. implementovat jeho akceptační kritéria včetně testů a dokumentace,
5. aktualizovat `progres.md` ve stejné sadě změn.

Task se nepovažuje za dokončený pouze proto, že existuje kód. Musí projít uvedenými kontrolami a nesmí porušovat rozpočet, bezpečnost ani rozsah MVP.

## 2. Milníky a pořadí

`M0 Ověření → M1 Datová pipeline → M2 API a vzdálenosti → M3 Frontend → M4 GCP provoz → M5 MVP validace`

Frontend může po stabilizaci API kontraktů částečně běžet paralelně s dokončením backendu. Produkční infrastruktura se připravuje až po ověření nákladů v M0. Každý milník má výstupní bránu; bez jejího splnění se nemá přecházet k závislým produkčním krokům.

Odhad velikosti:

- `S` – malý, typicky jedna soustředěná pracovní relace,
- `M` – střední, několik souvisejících změn,
- `L` – velký, má být implementován po logických částech, ale uzavírá jeden výsledek.

Odhady nejsou kalendářní závazek. Prioritu určuje závislost a riziko, ne velikost.

## 3. M0 – Ověření zdroje, návrhu a nákladů

Cíl: odstranit největší nejistoty dříve, než se vytvoří produkční schéma a infrastruktura.

| ID | Task | Velikost | Závisí na | Hotovo, když |
| --- | --- | --- | --- | --- |
| M0-01 | Založit cílovou strukturu projektu a vývojové standardy | M | DOC-01 | Existuje oddělení backendu, scraperu, frontendu, infrastruktury a testů; Python/Node verze, lint, formátování a testovací příkazy jsou zdokumentované; starý kód zůstane dočasně dohledatelný. |
| M0-02 | Ověřit živé filtry a stránkování Sreality | M | M0-01 | Šetrný integrační skript potvrdí kategorie 33 a 43, filtrované počty, stránkování, limit stránky a stabilní ID; výsledky jsou zaznamenané bez tajných údajů. |
| M0-03 | Zachytit anonymizované fixtures chaty a chalupy | S | M0-02 | Repozitář obsahuje malé sanitizované fixtures seznamu a detailu pro oba podtypy a alespoň jeden neúplný/okrajový případ. |
| M0-04 | Udělat profil polí a fotografií | M | M0-03 | Je zdokumentovaná četnost polí, chybějící hodnoty, varianty ploch a cen, struktura obrázků a reprezentativní odhad počtu/velikosti fotografií. |
| M0-05 | Ověřit GCP náklady a technické předpoklady | M | DOC-01 | Aktuální kalkulace pro `europe-west1` pokrývá Cloud SQL, Cloud Run, Storage, Scheduler, Routes, logy a zálohy; je potvrzen billing, dostupnost služeb, limity 200/300 Kč a rozhodnutí pokračovat cloudově. |

### Brána M0

- Obě cílové kategorie lze spolehlivě a šetrně načíst.
- Z fixtures lze navrhnout datový model bez bytových předpokladů.
- Odhad provozu nepřekračuje schválený rozpočet, nebo uživatel schválil upravený plán.
- Všechny nové nejasnosti jsou zapsané v `progres.md` a významná rozhodnutí ve specifikaci nebo ADR.

## 4. M1 – PostgreSQL a spolehlivá datová pipeline

Cíl: nahradit SQLite/CSV/JSON tok testovatelnou, idempotentní pipeline s auditovatelnou historií.

| ID | Task | Velikost | Závisí na | Hotovo, když |
| --- | --- | --- | --- | --- |
| M1-01 | Navrhnout finální databázové schéma z profilu dat | M | M0-04 | ER návrh pokrývá `scrape_runs`, `listings`, `listing_observations`, `listing_events`, `listing_images`, `listing_distances` a `user_listing_data`; typy, NULL, indexy a unikátní omezení odpovídají specifikaci. |
| M1-02 | Přidat lokální PostgreSQL a migrační základ | M | M1-01 | PostgreSQL lze spustit reprodukovatelně lokálně; SQLAlchemy a Alembic fungují; počáteční migrace vytvoří a vrátí schéma. |
| M1-03 | Zavést validovanou konfiguraci a strukturované logování | S | M0-01 | Neexistují absolutní cesty; konfigurace selže s jasnou chybou; `.env.example` je bezpečný; logy jsou strukturované a neobsahují secrets. |
| M1-04 | Implementovat odolného Sreality HTTP klienta | M | M0-03, M1-03 | Jedna session podporuje timeout, retry/backoff/jitter, tempo požadavků, validaci odpovědi a oba filtry; síťové testy jsou oddělené od běžné sady. |
| M1-05 | Implementovat tolerantní parser a doménové modely | L | M0-04, M1-03 | Fixtures obou kategorií se parsují; chybějící pole jsou `NULL`; všechny textové údaje a metadata obrázků se zachovají; neznámé pole parser bezpečně zvládne. |
| M1-06 | Implementovat raw-storage rozhraní | M | M1-03 | Jednotné rozhraní podporuje lokální filesystem pro vývoj a GCS adaptér pro produkci; payloady jsou komprimované, adresovatelné přes run/listing a zápis je idempotentní. |
| M1-07 | Implementovat běh a ukládání pozorování | L | M1-02, M1-04, M1-05, M1-06 | Pipeline vytvoří run, načte obě kategorie, upsertuje současný stav a uloží nejvýše jedno pozorování listing/run bez duplicit. |
| M1-08 | Implementovat události a stavový automat nabídek | L | M1-07 | Vznikají korektní události created, změna ceny/detailu, deactivated a reactivated; historie zůstává zachovaná. |
| M1-09 | Přidat bezpečnostní bránu deaktivace | M | M1-08 | Nabídky se deaktivují jen po úplném úspěšném načtení obou kategorií; částečný nebo neúspěšný běh je nikdy hromadně nedeaktivuje. |
| M1-10 | Dokončit CLI a testovací pokrytí pipeline | M | M1-09 | Existuje ruční CLI příkaz, dry-run nebo bezpečný validační režim; unit a PostgreSQL integrační testy ověřují parser, idempotenci, události, rollback a deaktivaci. |

### Brána M1

- Lokální kompletní běh naplní čistou PostgreSQL databázi.
- Opakování stejného vstupu nevytvoří duplicity.
- Simulované selhání nepoškodí historii ani stav aktivních nabídek.
- Starý SQLite tok není potřeba pro nový scraper.

## 5. M2 – Vzdálenosti, FastAPI a zabezpečené operace

Cíl: zpřístupnit data přes stabilní interní API a doplnit vzdálenosti od Prahy.

| ID | Task | Velikost | Závisí na | Hotovo, když |
| --- | --- | --- | --- | --- |
| M2-01 | Definovat a verzovat referenční bod Prahy | S | M1-02 | Souřadnice a verze referenčního bodu jsou centrální konfigurace s odůvodněním a testem. |
| M2-02 | Implementovat vzdušnou vzdálenost | S | M2-01 | Geodetický výpočet je deterministický, testovaný a ukládaný pouze pro validní GPS. |
| M2-03 | Integrovat Google Routes s cache a kvótou | L | M2-02, M0-05 | Nové/přemístěné nabídky získají silniční vzdálenost a čas bez provozu; výsledky se cachují; chyba nezablokuje nabídku; existuje retry/backfill a metrika využití. |
| M2-04 | Založit FastAPI aplikaci a API kontrakty | M | M1-02 | Aplikace má verzované routy, dependency injection, health/readiness endpointy, jednotné chyby a generované OpenAPI. |
| M2-05 | Implementovat seznam, filtry, řazení a stránkování | L | M2-04, M2-02 | API podporuje všechny filtry ze specifikace, serverové stránkování, bezpečné řazení a stabilní odpovědi nad realistickým objemem dat. |
| M2-06 | Implementovat detail, historii, mapu a medián | L | M2-05 | API vrací detail, cenu v čase, mapová data, aktuální filtrovaný medián a týdenní medián pouze z odpovídajících běhů. |
| M2-07 | Implementovat oblíbené, poznámky a archivaci fotografií | L | M2-04, M1-06 | Autorizovaný zápis je idempotentní; poznámky jsou oddělené od zdrojových dat; oblíbení spustí bezpečnou deduplikovanou archivaci obrázků. |
| M2-08 | Implementovat Google OAuth, allowlist a provozní endpointy | L | M2-04, M1-10 | Backend ověří identitu i allowlist; sessions jsou bezpečné; stav posledního běhu a ruční spuštění jsou dostupné pouze vlastníkovi; API testy pokryjí zákaz přístupu. |

### Brána M2

- Celý API kontrakt MVP funguje nad PostgreSQL.
- Nepřihlášený nebo nepovolený účet nezíská soukromá data ani provozní operace.
- Externí výpadek Routes či obrázku neznepřístupní hlavní data.
- Medián a historie jsou ověřené testovacími daty.

## 6. M3 – Český responzivní frontend

Cíl: dodat použitelnou vizualizaci pro každodenní analýzu trhu.

| ID | Task | Velikost | Závisí na | Hotovo, když |
| --- | --- | --- | --- | --- |
| M3-01 | Založit Next.js frontend a UI základ | M | M2-04 | Existuje typovaný API klient, layout, české formátování, design tokeny a společné loading/empty/error stavy. |
| M3-02 | Implementovat přihlášení a chráněný shell | M | M2-08, M3-01 | Google login/logout funguje; chráněné routy nezobrazí data bez autorizace; session se bezpečně obnovuje. |
| M3-03 | Implementovat dashboard mediánu | M | M2-06, M3-01 | Dashboard ukáže filtrovaný aktuální medián a jeho týdenní vývoj s jasným označením nabídkových cen. |
| M3-04 | Implementovat tabulku nabídek a URL filtry | L | M2-05, M3-01 | Tabulka podporuje všechna potvrzená kritéria, řazení a serverové stránkování; stav filtrů lze obnovit z URL. |
| M3-05 | Implementovat mapu | L | M2-06, M3-01 | Nabídky se zobrazí na Leaflet mapě; provider dlaždic je konfigurovatelný; mapa spolupracuje s filtry a zvládá chybějící GPS. |
| M3-06 | Implementovat detail a historii ceny | L | M2-06, M3-01 | Detail zobrazí texty, parametry, vzdálenosti, obrázky, stav, zdrojový odkaz a čitelný graf cenové historie. |
| M3-07 | Implementovat oblíbené a soukromé poznámky | M | M2-07, M3-06 | Uživatel může měnit oblíbené a poznámku s jasným stavem ukládání; archivní fotografie se zobrazí bezpečným způsobem. |
| M3-08 | Dokončit responzivitu, přístupnost a E2E testy | L | M3-02 až M3-07 | Kritické cesty fungují na mobilním i desktopovém viewportu, klávesnicí a v automatickém E2E testu. |

### Brána M3

- Jediný povolený uživatel dokončí všechny kritické cesty bez přístupu do databáze nebo terminálu.
- UI je použitelné na telefonu i desktopu.
- Texty a metriky nezaměňují nabídkovou a skutečnou prodejní cenu.

## 7. M4 – GCP infrastruktura a automatizovaný provoz

Cíl: bezpečně a reprodukovatelně provozovat MVP v projektu `sreality-scrapper-504307`.

| ID | Task | Velikost | Závisí na | Hotovo, když |
| --- | --- | --- | --- | --- |
| M4-01 | Připravit produkční Docker images | M | M1-10, M2-08, M3-08 | Backend, scraper/job a frontend mají malé reproducibilní image, běží jako non-root a projdou smoke/health kontrolou. |
| M4-02 | Založit Terraform state a základ projektu | M | M0-05 | Bezpečně je definován provider, remote state, API enablement, naming, labels a region; plán neobsahuje nečekané destruktivní změny. |
| M4-03 | Vytvořit Cloud SQL, Storage a lifecycle | L | M4-02, M1-02, M1-06 | PostgreSQL `db-f1-micro` bez HA, regionální neveřejné buckety a 90denní raw lifecycle jsou spravované Terraformem; migrace fungují. |
| M4-04 | Vytvořit IAM, service accounts a secrets | M | M4-02 | Každá služba má nejmenší nutná práva; secrets nejsou v Terraform state v otevřené podobě, kódu ani logu. |
| M4-05 | Nasadit Cloud Run services a scraper job | L | M4-01, M4-03, M4-04 | Backend/frontend škálují na nulu; job se připojí k DB a Storage; služby nejsou veřejně použitelné bez aplikační autentizace. |
| M4-06 | Přidat Scheduler, ruční běh a CI/CD | L | M4-05 | Pondělní běh 03:00 `Europe/Prague` je autorizovaný; ruční trigger funguje; CI testuje a kontrolovaný deployment je zdokumentovaný. |
| M4-07 | Přidat monitoring, e-mail a obnovu | L | M4-05 | Logy/metry pokrývají specifikaci; chybný běh vyvolá e-mail; existuje rozumná DB záloha a ověřený postup obnovy. |
| M4-08 | Nastavit a ověřit rozpočtové pojistky | M | M4-03 až M4-07 | Budget upozornění 200/300 Kč, API kvóty a retence logů 30 dní jsou aktivní; aktuální run-rate je zdokumentovaný podle služby. |

### Brána M4

- Produkci lze obnovit z repozitáře, Terraformu, migrací a secrets postupu.
- Týdenní běh nevyžaduje ruční zásah.
- Bezpečnostní a nákladové mantinely jsou ověřené v reálném projektu.

## 8. M5 – End-to-end validace a předání MVP

Cíl: prokázat, že celý systém splňuje Definition of Done ze specifikace.

| ID | Task | Velikost | Závisí na | Hotovo, když |
| --- | --- | --- | --- | --- |
| M5-01 | Ověřit první kompletní produkční běh | M | M4-08 | Počty obou kategorií dávají smysl; data, vzdálenosti, události, raw payloady, UI a upozornění jsou konzistentní; chyby jsou vyřešené nebo evidované. |
| M5-02 | Provést failure, security a restore drill | L | M5-01 | Simulované selhání nezpůsobí deaktivaci; nepovolený přístup selže; obnova databáze je prakticky ověřená; nejsou nalezené kritické úniky secrets. |
| M5-03 | Uzavřít MVP checklist a provozní dokumentaci | M | M5-02 | Všech 14 akceptačních kritérií specifikace je doložených; README/runbook popisuje lokální běh, deployment, migraci, rollback, obnovu, náklady a známá omezení. |

## 9. Kritická cesta

Nejdelší závislá posloupnost je přibližně:

`M0-02 → M0-03 → M0-04 → M1-01 → M1-02 → M1-07 → M1-08 → M1-09 → M1-10 → M2-04 → M2-05 → M2-06 → M3-04/M3-06 → M3-08 → M4-01 → M4-05 → M4-06 → M4-08 → M5-01 → M5-03`

Největší rizika na kritické cestě jsou změny neoficiálního API, nečekaná struktura chat/chalup, korektnost stavového automatu a cena trvale běžící Cloud SQL.

## 10. Doporučený první pracovní blok

První implementační blok má uzavřít M0 a nezasahovat zatím do produkčního GCP:

1. `M0-01` – cílový scaffold a nástroje,
2. `M0-02` – validace živého API,
3. `M0-03` – fixtures,
4. `M0-04` – profil dat a fotografií,
5. `M0-05` – kalkulace a cloudové rozhodnutí.

Teprve výstup M0 určí přesné typované sloupce a definitivní implementační detaily M1.

