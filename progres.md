# Progres projektu Sreality Chaty Tracker

## Aktuální stav

- Poslední aktualizace: 2026-08-11
- Aktuální milník: M1 – implementace PostgreSQL pipeline dokončena; plný řízený live běh brány dosud nebyl spuštěn (cloudová brána `M0-05` zůstává blokovaná)
- Aktuální hlavní task: žádný – sekce M1 je implementačně dokončená
- Následující doporučený task: `M2-01` – Definovat a verzovat referenční bod Prahy
- Blokátory: read-only ověření projektu/billingu/API selhává při obnově `gcloud` OAuth tokenu kvůli lokálnímu TLS certifikátu; je potřeba kontrola správným osobním účtem
- Souhrn: 15 dokončeno, 0 rozpracováno, 1 blokováno, 27 čeká

## Legenda

- `[ ]` čeká,
- `[~]` rozpracováno,
- `[x]` dokončeno,
- `[!]` blokováno.

Najednou má být `[~]` označen nejvýše jeden hlavní task. Dílčí paralelní práce se popíše v poznámce hlavního tasku, aby tracker nepůsobil, že existuje více vlastníků kritické cesty.

## Dokumentace a plánování

- [x] `DOC-01` – Prozkoumat původní kód, potvrdit produktová rozhodnutí a vytvořit `specifikace.md`, `roadmap.md` a `progres.md`.

## M0 – Ověření zdroje, návrhu a nákladů

- [x] `M0-01` – Založit cílovou strukturu projektu a vývojové standardy.
- [x] `M0-02` – Ověřit živé filtry a stránkování Sreality.
- [x] `M0-03` – Zachytit anonymizované fixtures chaty a chalupy.
- [x] `M0-04` – Udělat profil polí a fotografií.
- [!] `M0-05` – Ověřit GCP náklady a technické předpoklady.

## M1 – PostgreSQL a spolehlivá datová pipeline

- [x] `M1-01` – Navrhnout finální databázové schéma z profilu dat.
- [x] `M1-02` – Přidat lokální PostgreSQL a migrační základ.
- [x] `M1-03` – Zavést validovanou konfiguraci a strukturované logování.
- [x] `M1-04` – Implementovat odolného Sreality HTTP klienta.
- [x] `M1-05` – Implementovat tolerantní parser a doménové modely.
- [x] `M1-06` – Implementovat raw-storage rozhraní.
- [x] `M1-07` – Implementovat běh a ukládání pozorování.
- [x] `M1-08` – Implementovat události a stavový automat nabídek.
- [x] `M1-09` – Přidat bezpečnostní bránu deaktivace.
- [x] `M1-10` – Dokončit CLI a testovací pokrytí pipeline.

## M2 – Vzdálenosti, FastAPI a zabezpečené operace

- [ ] `M2-01` – Definovat a verzovat referenční bod Prahy.
- [ ] `M2-02` – Implementovat vzdušnou vzdálenost.
- [ ] `M2-03` – Integrovat Google Routes s cache a kvótou.
- [ ] `M2-04` – Založit FastAPI aplikaci a API kontrakty.
- [ ] `M2-05` – Implementovat seznam, filtry, řazení a stránkování.
- [ ] `M2-06` – Implementovat detail, historii, mapu a medián.
- [ ] `M2-07` – Implementovat oblíbené, poznámky a archivaci fotografií.
- [ ] `M2-08` – Implementovat Google OAuth, allowlist a provozní endpointy.

## M3 – Český responzivní frontend

- [ ] `M3-01` – Založit Next.js frontend a UI základ.
- [ ] `M3-02` – Implementovat přihlášení a chráněný shell.
- [ ] `M3-03` – Implementovat dashboard mediánu.
- [ ] `M3-04` – Implementovat tabulku nabídek a URL filtry.
- [ ] `M3-05` – Implementovat mapu.
- [ ] `M3-06` – Implementovat detail a historii ceny.
- [ ] `M3-07` – Implementovat oblíbené a soukromé poznámky.
- [ ] `M3-08` – Dokončit responzivitu, přístupnost a E2E testy.

## M4 – GCP infrastruktura a automatizovaný provoz

- [ ] `M4-01` – Připravit produkční Docker images.
- [ ] `M4-02` – Založit Terraform state a základ projektu.
- [ ] `M4-03` – Vytvořit Cloud SQL, Storage a lifecycle.
- [ ] `M4-04` – Vytvořit IAM, service accounts a secrets.
- [ ] `M4-05` – Nasadit Cloud Run services a scraper job.
- [ ] `M4-06` – Přidat Scheduler, ruční běh a CI/CD.
- [ ] `M4-07` – Přidat monitoring, e-mail a obnovu.
- [ ] `M4-08` – Nastavit a ověřit rozpočtové pojistky.

## M5 – End-to-end validace a předání MVP

- [ ] `M5-01` – Ověřit první kompletní produkční běh.
- [ ] `M5-02` – Provést failure, security a restore drill.
- [ ] `M5-03` – Uzavřít MVP checklist a provozní dokumentaci.

## Pracovní poznámky k aktivnímu tasku

### Žádný aktivní task

- M1-01 až M1-10 jsou implementované a testované.
- Před zahájením M2 je doporučeno commitnout současný celek a samostatně naplánovat plný live běh, protože znamená tisíce zdvořile sekvenčních requestů.

Při zahájení tasku sem zapsat:

- datum a ID tasku,
- stručný plán,
- soubory nebo komponenty v rozsahu,
- rizika a předpoklady,
- provedené testy,
- co zbývá před označením `[x]`.

Po dokončení stručnou poznámku přesunout do historie níže.

## Blokátory a otevřené otázky

### `M0-05` – potvrzení cílového GCP projektu

- Blokující podmínka: nelze potvrdit billing a API stav projektu `sreality-scrapper-504307`.
- Ověřeno: veřejné ceny a regionální dostupnost, lokální SDK, explicitní read-only pokusy bez změny aktivního pracovního projektu.
- Příčina: `gcloud` selže při obnově OAuth tokenu na lokální chybě důvěryhodnosti TLS; dostupný aktivní účet navíc není osobní účet vlastníka cílového projektu.
- Chybí: kontrola v Cloud Console správným účtem, daňový režim billing accountu a uživatelovo potvrzení podmíněného cloudového pokračování při odhadu kolem horního rozpočtového limitu.
- Dopad: blokuje uzavření brány M0 a cloudové tasky závislé na M0-05 (`M2-03`, `M4-02`); neblokuje lokální návrh databáze od `M1-01`.

Položka označená `[!]` musí zde uvést:

- konkrétní blokující podmínku,
- co již bylo ověřeno,
- jaké rozhodnutí nebo přístup chybí,
- které další tasky blokuje.

## Historie dokončené práce

### 2026-08-11 – `M1-10`

- Přidán console entry point `sreality-scrape` s ručním `run` příkazem a povinným idempotency klíčem.
- Read-only `check` ověří konfiguraci a `SELECT 1` bez DB zápisu a bez HTTP requestu; skutečný nainstalovaný entry point vrátil `{"status":"ready","mode":"read_only"}`.
- CLI skládá settings, PostgreSQL session factory, lokální raw storage, odolný klient, stránkovaný source a pipeline; výstup je jeden JSON objekt.
- Chyby CLI zveřejňují pouze typ výjimky, nikoli zprávu s potenciálními credentials nebo obsahem zdroje.
- PostgreSQL rollback test záměrně vyvolá porušení image constraintu a ověřuje, že listing, observation i event chybného detailu nezůstanou v DB, zatímco druhá kategorie se korektně uloží jako partial run.
- Závěrečná M1 regrese: 62 passed, 1 explicitní live skipped; 15 dotčených zdrojů/testů prošlo Ruff format/check a strict mypy, `git diff --check` je čistý.
- Plný live scrape celé nabídky nebyl automaticky spuštěn: při potvrzeném objemu by znamenal tisíce sekvenčních requestů; je vhodné jej provést jako samostatně sledovaný řízený běh.

### 2026-08-11 – `M1-09`

- Hromadná deaktivace je dostupná pouze přes guard vyžadující dokončený `succeeded` run a `chata_complete = chalupa_complete = true`.
- Výběr kandidátů používá absenci observation v aktuálním kompletním runu a zamyká pouze dosud aktivní listingy.
- Deaktivace atomicky nastaví stav, `inactive_at`, auditní event a přesný `deactivated_count`; již neaktivní listing nevytvoří duplicitní událost.
- Částečný či neúspěšný run gate vůbec nevolá a zachová aktivitu všech nenalezených nabídek.
- Ověření: PostgreSQL test prokázal nulovou deaktivaci po selhání chalup a přesně jednu deaktivaci až po následujícím kompletním běhu.
- Plná sada: 59 passed, 1 live skipped; dotčený kód prošel Ruff format/check, strict mypy a `git diff --check`.

### 2026-08-11 – `M1-08`

- Přidán čistý doménový stavový automat pro `created`, zvýšení/snížení ceny, změnu detailu, deaktivaci a reaktivaci.
- Cena je oddělena od detail hashe, takže samotná cenová změna nevytváří falešnou událost `details_changed`; přechody ceny z/do neznámé hodnoty si nevymýšlejí směr.
- Pipeline ukládá události ve stejné transakci jako aktuální stav a observation; unikátní DB omezení chrání retry stejného runu.
- Návrat neaktivní nabídky obnoví původní listing řádek a přidá `reactivated`, takže historie zůstane zachovaná.
- Přidána nízkoúrovňová deaktivační operace připravená pro povinnou complete-run bránu M1-09.
- Ověření: unit testy přechodů a PostgreSQL historie pokrývají všech šest typů událostí; plná sada 58 passed, 1 live skipped a nový kód prošel Ruff/strict mypy.

### 2026-08-11 – `M1-07`

- Přidán stránkovaný `SrealityListingSource`, který používá skutečné detail odkazy ze search HTML, deduplikuje externí ID a validuje detail vůči očekávané kategorii.
- `ScrapePipeline` zakládá unikátní auditní run, zpracuje chatu i chalupu a atomicky ukládá raw reference, aktuální listing, metadata obrázků a observation.
- Opakovaný dokončený `logical_key` je no-op bez dalších zdrojových requestů; duplicita listingu uvnitř runu nevytvoří druhé pozorování.
- Run eviduje úplnost obou kategorií, bezpečné typy chyb a stav `succeeded`, `partial` nebo `failed`, což připravuje bránu deaktivace.
- Ověření: unit test HTML linků/stránkování a PostgreSQL integrační test dvou běhů ověřily upsert, změnu stavu, raw round trip a 4 unikátní pozorování pro 2 listingy × 2 runy.
- Plná sada: 53 passed, 1 explicitní live skipped; všechny nové M1-06/M1-07 soubory prošly Ruff format/check a strict mypy.

### 2026-08-11 – `M1-06`

- Přidáno jednotné `RawStorage` rozhraní s lokálním filesystem a Google Cloud Storage adaptérem.
- Payload se serializuje jako kanonický UTF-8 JSON, komprimuje deterministickým gzipem a adresuje klíčem `raw/runs/{run_id}/listings/{sreality_id}.json.gz`.
- Zápis je create-only a idempotentní; stejný obsah je no-op, odlišný obsah na stejném klíči vyvolá konflikt místo přepsání auditních dat.
- GCS adaptér používá generation precondition a CRC32C; jeho testy používají lokální fake bucket bez credentials a sítě.
- Dokumentace backendu popisuje kontrakt, metadata a plánovanou 90denní retenci řízenou až infrastrukturou.
- Ověření: 7 cílených storage testů a plná sada 50 passed, 1 live skipped; nový kód prošel Ruff a strict mypy. Celoprojektové kontroly nadále hlásí starší formátovací a typové nálezy v discovery skriptech mimo rozsah M1-06.

### 2026-08-11 – `M1-05`

- Přidány frameworkově nezávislé doménové modely search stránky, detailu, ceny, lokality a metadat obrázků.
- Tolerantní parser načítá `__NEXT_DATA__`, vyhledá `estatesSearch`/`estate` query a zpracuje fixtures chat i chalup bez bytových předpokladů.
- Chybějící volitelná pole se mapují na `None`/prázdnou kolekci; nulová cena zůstává zdrojově zachovaná, ale analyticky je `None` s příznakem.
- Úplný detail, params, texty a raw metadata obrázků se zachovávají pro JSONB/raw storage; neznámá budoucí pole parser bezpečně ponechá.
- `ListingKind` byl sjednocen pro klient, parser i SQLAlchemy modely bez změny databázového schématu.
- Ověření: 9 parser testů, plná sada 43 passed a 1 explicitní live skipped; Ruff/mypy prošly a `alembic check` nehlásí drift.

### 2026-08-11 – `M1-04`

- Přidán sdílený synchronní `httpx.Client` pro celý běh s timeoutem, globálním pacingem, omezeným exponenciálním retry a jitterem.
- Klient podporuje potvrzené search filtry chata 33/chalupa 43, bezpečné detail cesty a validuje status, host, Content-Type a SSR `__NEXT_DATA__` marker.
- Redirecty mimo `www.sreality.cz` se nenásledují; veřejný tok používá zdrojem vracený `noredirect=1`, takže nevstupuje do autologin/CMP řetězce.
- TLS validace zůstává zapnutá a používá systémový trust store, což řeší lokální firemní CA bez nebezpečného `verify=False`.
- Přidány deterministické unit testy session, filtrů, pacingu, retry, validace a redirectů a explicitní dvourequestový live test.
- Ověření: live chata/chalupa prošel; plná sada 34 passed, 1 live skipped ve výchozím režimu; nový kód prošel Ruff a strict mypy.

### 2026-08-11 – `M1-03`

- Přidána Pydantic Settings konfigurace načítaná výhradně z environment variables s prefixem `SREALITY_`.
- Databázová URL je chráněná jako secret, validuje psycopg/PostgreSQL a chyby neobsahují vstupní hodnoty; lokální storage cesta nesmí být absolutní ani opustit workspace.
- Legacy `.env.example` byl nahrazen bezpečným vzorem pro nový backend bez produkčních credentials a bez absolutních cest.
- Přidán izolovaný JSON logger s kontextem `event`, `step`, `run_id`, `listing_id`, redakcí běžných credentials a bezpečným záznamem typu výjimky.
- Dokumentace popisuje explicitní konfiguraci a strukturované logování.
- Ověření: 26 testů včetně PostgreSQL integrace prošlo; nový kód prošel Ruff format/check a strict mypy; `git diff --check` bez chyb.

### 2026-08-11 – `M1-02`

- Přidán PostgreSQL 16.10 v Docker Compose se zdravotní kontrolou, perzistentním volume a oddělenou disposable testovací databází.
- Přidány SQLAlchemy 2 modely všech sedmi entit a PostgreSQL enumy, omezení, cizí klíče a indexy podle návrhu M1-01.
- Přidán Alembic základ a počáteční migrace `20260811_0001`; automaticky nalezená chyba downgrade byla opravena explicitním odstraněním enum typů.
- Lokální dokumentace popisuje start, migraci, zastavení a bezpečné spuštění destruktivního integračního testu pouze nad `sreality_tracker_test`.
- Ověření: reálný cyklus upgrade/downgrade/upgrade, `alembic check` bez driftu, PostgreSQL head `20260811_0001`, Compose config validní.
- Testy: 19 passed včetně PostgreSQL integrace; nový M1-02 kód prošel Ruff format/check a strict mypy.
- Opakované ověření po reinstalaci Dockeru odhalilo, že zděděná `SREALITY_DATABASE_URL` mohla přepsat explicitní testovací URL. Hlavní prázdné lokální schéma bylo obnoveno a Alembic nyní preferuje explicitní atribut, ověřuje očekávaný název databáze a regresní test prokázal, že konfliktní env hlavní schéma nezmění.

### 2026-08-11 – `M1-01`

- Přidán finální ER návrh sedmi povinných entit v `docs/architecture/m1-01-database-schema.md`.
- Typy, nullable pravidla a mapování vycházejí z fixtures a profilů detailů z 2. a 11. srpna 2026.
- Návrh odděluje externí Sreality ID od interních klíčů, normalizuje nulovou cenu na `NULL` s příznakem a zachovává proměnlivá pole v JSONB.
- Popsány unikátní klíče pro běhy, pozorování, události, fotografie a cache vzdáleností, včetně indexů pro filtry, historii a týdenní medián.
- Zakotven invariant, že hromadná deaktivace je možná pouze po úplném úspěšném načtení obou kategorií.
- Ověření: automatická kontrola přítomnosti všech sedmi entit a klíčových invariantů prošla; `git diff --check` bez chyb.

### 2026-08-02 – `M0-04`

- Profilováno 5 aktuálních chat a 5 chalup bez uložení textů, ID, lokalit, URL nebo image bytes.
- Potvrzena struktura 29 top-level polí a přibližně 70 parametrů, přičemž mnoho hodnot je nullable.
- Zjištěno, že cena může být `0`; specifikace ji nově vyřazuje z mediánu a normalizuje jako neuvedenou.
- Medián počtu fotografií je 26,5; medián veřejné 800×600 WebP varianty je 96 708 B.
- Bodový odhad jedné kopie aktuálního trhu je přibližně 9,2 GB; strategie archivovat jen oblíbené nabídky zůstává správná.
- Přidán opakovatelný agregovaný profiler, JSON report a interpretace v `docs/discovery/m0-04-data-profile.md`.
- Ověření: 22 read-only requestů s prodlevou; všech 10 image měření úspěšných; předchozí unit sada procházela.

### 2026-08-02 – `M0-03`

- Ověřena detailní SSR query `estate` pro jednu chatu a jednu chalupu.
- Přidány sanitizované search/detail fixtures pro oba podtypy a syntetický případ s chybějícími volitelnými poli.
- Sanitizace nahrazuje původní texty, ID, ceny, plochy, souřadnice a mediální URL; fixtures neobsahují známé zdrojové domény ani původní vzorová ID/lokality.
- Přidán explicitní generátor `scripts/capture_sreality_fixtures.py` se čtyřmi pomalými read-only requesty a bezpečnostní kontrolou před zápisem.
- Dokumentována struktura a proces aktualizace fixtures.
- Ověření: pytest hlásí `7 passed`; `compileall` a kontrola zakázaných vzorů prošly.

### 2026-08-02 – `M0-02`

- Zjištěno, že původní `/api/cs/v2/estates` a `/count` endpointy vracejí HTTP 404 a nejsou použitelným základem nové pipeline.
- Ověřen aktuální strukturovaný Next.js `__NEXT_DATA__` SSR payload veřejných vyhledávacích stránek.
- Potvrzeny slugy `chaty`/`chalupy`, podtypy 33/43, prodej, domy, celá ČR a stránkování `?strana=N`.
- Při měření nalezeno 2 409 chat a 1 174 chalup; pozorovaný limit je 22 výsledků na stránku.
- Opakovaná první stránka měla pro oba podtypy shodná ID a stránky 1/2 se nepřekrývaly.
- Přidán read-only skript `scripts/validate_sreality_api.py`, agregovaný report v `docs/discovery/` a tři regresní testy parseru.
- Specifikace byla aktualizována tak, aby budoucí agent nepoužil nefunkční REST endpointy bez nového ověření.
- Ověření: živá validace prošla 6 requesty s prodlevou 0,75 s; pytest hlásí `4 passed`; `compileall` a TOML parsing prošly.

### 2026-08-02 – `M0-01`

- Vytvořen cílový scaffold pro Python backend/scraper, testy, budoucí Next.js frontend, Terraform, ADR a pomocné skripty.
- Standardizován Python 3.13 a Node.js 24 LTS; přidán `pyproject.toml`, EditorConfig a runtime version files.
- Zavedeny a zdokumentovány příkazy pro Ruff, mypy, pytest a základní syntaktickou kontrolu.
- Původní scraper zůstal beze změn na původních cestách a je označen jako referenční legacy implementace.
- Ověření: `pyproject.toml` načten přes `tomllib`, `compileall` prošel a pytest hlásí `1 passed`.
- Ruff a mypy nebyly spuštěny, protože zatím nejsou lokálně nainstalované; jejich konfigurace a instalační postup jsou připravené.

### 2026-08-02 – `DOC-01`

- Prozkoumán původní Python scraper, SQLite vrstva, transformace a konfigurace.
- Sepsána cílová produktová a technická specifikace.
- Potvrzen rozsah: chaty a chalupy na prodej v celé ČR, jeden uživatel, Praha jako referenční bod, týdenní běh a GCP rozpočet 200–300 Kč.
- Vytvořena roadmapa s milníky, závislostmi, branami a akceptačními kritérii.

## Pravidla aktualizace

Při každé změně stavu tasku je nutné současně:

1. změnit checkbox,
2. aktualizovat datum, aktuální task, následující task a souhrn nahoře,
3. zaznamenat testy a významná zjištění,
4. přidat nebo odstranit blokátor,
5. po dokončení přidat krátký záznam do historie,
6. při změně rozsahu aktualizovat také `specifikace.md`,
7. při změně pořadí, závislosti nebo akceptace aktualizovat také `roadmap.md`.

Task lze označit `[x]` pouze po splnění sloupce „Hotovo, když“ v `roadmap.md`.
