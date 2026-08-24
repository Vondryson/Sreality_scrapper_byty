# Progres projektu Sreality Chaty Tracker

## Aktuální stav

- Poslední aktualizace: 2026-08-24
- Aktuální milník: M4 – GCP infrastruktura a automatizovaný provoz
- Aktuální hlavní task: žádný – `M4-07` je uzavřeno
- Následující doporučený task: `M4-08` – Nastavit a ověřit rozpočtové pojistky
- Blokátory: žádné
- Souhrn: 38 dokončeno, 0 rozpracováno, 0 blokováno, 5 čeká

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
- [x] `M0-05` – Ověřit GCP náklady a technické předpoklady.

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

- [x] `M2-01` – Definovat a verzovat referenční bod Prahy.
- [x] `M2-02` – Implementovat vzdušnou vzdálenost.
- [x] `M2-03` – Integrovat Google Routes s cache a kvótou.
- [x] `M2-04` – Založit FastAPI aplikaci a API kontrakty.
- [x] `M2-05` – Implementovat seznam, filtry, řazení a stránkování.
- [x] `M2-06` – Implementovat detail, historii, mapu a medián.
- [x] `M2-07` – Implementovat oblíbené, poznámky a archivaci fotografií.
- [x] `M2-08` – Implementovat Google OAuth, allowlist a provozní endpointy.

## M3 – Český responzivní frontend

- [x] `M3-01` – Založit Next.js frontend a UI základ.
- [x] `M3-02` – Implementovat přihlášení a chráněný shell.
- [x] `M3-03` – Implementovat dashboard mediánu.
- [x] `M3-04` – Implementovat tabulku nabídek a URL filtry.
- [x] `M3-05` – Implementovat mapu.
- [x] `M3-06` – Implementovat detail a historii ceny.
- [x] `M3-07` – Implementovat oblíbené a soukromé poznámky.
- [x] `M3-08` – Dokončit responzivitu, přístupnost a E2E testy.

## M4 – GCP infrastruktura a automatizovaný provoz

- [x] `M4-01` – Připravit produkční Docker images.
- [x] `M4-02` – Založit Terraform state a základ projektu.
- [x] `M4-03` – Vytvořit Cloud SQL, Storage a lifecycle.
- [x] `M4-04` – Vytvořit IAM, service accounts a secrets.
- [x] `M4-05` – Nasadit Cloud Run services a scraper job.
- [x] `M4-06` – Přidat Scheduler, ruční běh a CI/CD.
- [x] `M4-07` – Přidat monitoring, e-mail a obnovu.
- [ ] `M4-08` – Nastavit a ověřit rozpočtové pojistky.

## M5 – End-to-end validace a předání MVP

- [ ] `M5-01` – Ověřit první kompletní produkční běh.
- [ ] `M5-02` – Provést failure, security a restore drill.
- [ ] `M5-03` – Uzavřít MVP checklist a provozní dokumentaci.

## Pracovní poznámky k aktivnímu tasku

### 2026-08-23 – `M4-07`

- Plán: sjednotit měřitelné scraper události, přidat log-based metriky/dashboard a e-mailové alerty, potvrdit 30denní retenci logů a zdokumentovat bezpečný Cloud SQL restore drill.
- Rozsah: aplikační JSON logy pro výsledek/délku/počty/retry/Routes/storage, Terraform Monitoring a Logging zdroje, notification channel, alert policies a recovery runbook.
- Rizika a předpoklady: e-mailový kanál může vyžadovat potvrzení příjemce; absence a propadové alerty musí zabránit falešným poplachům; restore se nesmí provádět přes produkční instanci a případný placený drill bude vyžadovat samostatné produkční schválení.
- Implementace: scraper emituje jednotný výsledek, délku, počty, category completion a HTTP/Routes retry události; produkční práh podezřelého poklesu je 2 500 nabídek. Terraform přidává 13 log-based metrik, provozní dashboard, e-mailový kanál a čtyři alert policies pro aplikační/platformní selhání, propad počtu a zaplnění Cloud SQL.
- Obnova: Cloud SQL nadále drží sedm denních záloh a nový runbook obnovuje pouze do samostatné dočasné instance s read-only datovou kontrolou; placený praktický drill zůstává explicitně v `M5-02`.
- Lokální ověření: Ruff, mypy, 117 backend testů (11 integračních/live korektně přeskočeno), `terraform validate` a všechny tři Terraform guardrail testy prošly. Zbývá nový scraper image, kontrolovaný produkční plán/apply, potvrzení e-mailového kanálu a praktický test incidentu.
- Produkční plán: při trvale nastaveném příjemci v ignorovaném `workloads.auto.tfvars` obsahuje přesně `19 add, 1 in-place change, 0 destroy`; jediná změna existujícího zdroje přidává scraper jobu práh 2 500. Uložený plán se nesmí aplikovat před promotion nového scraper image digestu a opakovanou kontrolou plánu.
- Schválení 2026-08-24: vlastník schválil commit/push, promotion nového scraper image a produkční apply pouze při zachování přesně `19 add, 1 in-place change, 0 destroy`.
- První apply 2026-08-24: Cloud Run job, nový scraper digest, všech 13 log-based metrik a e-mailový kanál byly vytvořeny. Google API odmítlo zbývající čtyři metric-threshold alerty kvůli nepovolenému `notification_rate_limit` a dashboard kvůli nepodporovaným `x`/`y` souřadnicím mosaic tiles; žádný destroy ani replace neproběhl.
- První oprava: rate-limit bloky a nepodporovaná `x`/`y` pole byly odstraněny a oba případy dostaly regresní Terraform guardrail. `terraform validate` a všechny tři testovací sady po opravě znovu prošly.
- Druhý apply: všechny čtyři alert policies byly vytvořeny. Dashboard bez pozic API odmítlo kvůli překryvu tiles; kontrakt vyžaduje pole `xPos`/`yPos` (původní `x`/`y` jsou neplatná). Poslední oprava i guardrail se týkají už pouze dashboardu.
- Dashboard apply: dashboard byl vytvořen, následný drift check ale odhalil API normalizaci výchozí osy `targetAxis=Y1` a vynechávání nulových `xPos`/`yPos`. Deklarace byla srovnána s vraceným kontraktem; serverová `name`/`etag` pole provider podle svého JSON diff pravidla ignoruje, jakmile nezůstává jiná věcná změna.
- Finální produkční stav: nový scraper image `sha256:4fd885185625f23e9f0443942dfb5ee985a4c427825c73165c708ff1a46b8dab`, práh 2 500, všech 13 metrik, čtyři aktivní alert policies, e-mailový kanál a dashboard jsou nasazené. Terraform po normalizaci dashboard JSON hlásí `No changes`.
- Provozní ověření: read-only execution `sreality-tracker-scraper-kls56` na novém image skončila `succeededCount=1` a emitovala `status=ready, mode=read_only`. Syntetická událost `monitoring:test:20260824-01` dorazila do správného `cloud_run_job` logu a failure metrika vrací hodnotu `1`; čeká se pouze na potvrzení skutečného doručení e-mailu vlastníkem.
- Uzavření: vlastník potvrdil doručení e-mailu z policy `Sreality scraper: unsuccessful run` pro metriku `logging.googleapis.com/user/sreality-tracker-scrape-failures`, job `sreality-tracker-scraper` a syntetický log `sreality-monitoring-test`. Celý incidentní řetězec je tím prakticky ověřený a `M4-07` je dokončeno; rozpočty, kvóty a 30denní retence pokračují v `M4-08`.

### 2026-08-23 – `M4-05`

- Plán: doplnit Artifact Registry, nasadit API a frontend jako Cloud Run services škálující na nulu a scraper jako Cloud Run job; připojit Cloud SQL socket, runtime identities, secrets a aplikační bucket.
- Rozsah: produkční image promotion, Cloud Run v2 services/job, ingress a invoker hranice, health/startup probes, resource limity a provozní proměnné.
- Stav: produkční Docker images, GCS wiring, runtime service accounts, IAM, Cloud SQL a pět aktivních secret verzí jsou připravené. Cloud Run Terraform zdroje a deployment postup zatím chybí.
- Zbývá: navrhnout oddělený veřejný frontend a neveřejný API/job přístup, sestavit a pushnout image do Artifact Registry, aplikovat pouze zkontrolované M4-05 zdroje a prakticky ověřit health, autentizaci, DB i Storage.
- Dílčí pokračování 2026-08-23: Terraform návrh přidává deletion-protected Artifact Registry s immutable tagy a cleanup pravidly, dvě Cloud Run v2 služby s `min=0`/`max=1` a jeden nerekurzivní scraper job s Cloud SQL socketem, GCS a vyhrazenými identitami. API transport zůstává dosažitelný pro browserový same-origin proxy, ale všechna aplikační data a provozní endpointy dál vynucují podepsanou owner session.
- Ověření 2026-08-23: `terraform validate`, oba `terraform test` guardraily, cílené scraper CLI testy, Ruff i mypy prošly. Live plán s prázdnými image referencemi má přesně `1 add, 0 change, 0 destroy` a týká se pouze Artifact Registry; apply čeká na výslovné produkční schválení.
- Produkční nasazení 2026-08-23: vznikl Artifact Registry `europe-west1-docker.pkg.dev/sreality-scrapper-504307/sreality-tracker`, API a frontend Cloud Run service a neveřejný scraper job. Finální služby používají immutable image digesty, deletion protection a scale-to-zero; následný Terraform drift check hlásí `No changes`.
- Produkční smoke test 2026-08-23: frontend, frontendový API proxy, API liveness i databázová readiness vracejí `200`; anonymní listings vracejí `401`. Read-only scraper execution `sreality-tracker-scraper-55l2n` přes vlastní identitu, Secret Manager a Cloud SQL skončila úspěšně. OAuth login vrací `302` na `accounts.google.com` a nastaví podepsanou flow cookie.
- Uzavření M4-05: produkční redirect URI byla přidána do OAuth web klienta a vlastník prakticky potvrdil úspěšné Google přihlášení. Plný scraper běh a jeho plánování patří do M4-06.

### 2026-08-23 – `M4-06`

- Plán: přidat dedikovanou Scheduler identitu a autorizovaný pondělní trigger v `03:00 Europe/Prague`, zapojit owner-only API endpoint na per-execution Cloud Run job override a zavést CI s kontrolovaným deployment runbookem.
- Stav: Cloud Run scraper job je Ready a read-only execution je ověřená; produkční API zatím ruční trigger záměrně nenabízí a repozitář nemá CI workflow.
- Dílčí implementace: API adaptér používá ADC a Cloud Run v2 per-execution override, target i logical key jsou allowlistované. Terraform přidává Scheduler service account, job-level invoker pro Scheduler a custom roli API omezenou přesně na `run.jobs.run` + `run.jobs.runWithOverrides`; Scheduler má `0 3 * * 1`, `Europe/Prague` a nulový retry count.
- CI a dokumentace: nový GitHub Actions workflow testuje Python 3.13 s PostgreSQL 16, frontend na Node 24 a Terraform 1.15; deployment runbook vyžaduje immutable digesty, uložený plán, ruční kontrolu a popisuje rollback.
- Ověření: Ruff, mypy (51 source files), 113 backend testů, 28 frontend testů, Next production build, `terraform validate` a oba Terraform guardrail testy prošly. Live plán M4-06 obsahuje přesně `5 add, 1 change, 0 destroy`; apply čeká na výslovné produkční schválení.
- Produkční apply: po vypnutí Avastu proběhl plán přesně `5 add, 1 change, 0 destroy`. Scheduler `sreality-tracker-weekly` je `ENABLED`, používá `0 3 * * 1` a `Europe/Prague`; Scheduler service agent i dedikovaný invoker binding jsou přítomné. API liveness/readiness vracejí `200` a anonymní listings `401`.
- IAM ověření: job policy váže API pouze na custom roli s přesně `run.jobs.run` a `run.jobs.runWithOverrides`; Scheduler má pouze `roles/run.invoker`. Osobní účet záměrně nemá Token Creator a API impersonace proto bezpečně selhala. Policy Troubleshooter API nebylo kvůli testu dodatečně zapnuto.
- Drift: explicitní nulový `retry_config` blok byl odstraněn, protože Cloud Scheduler API používá stejné výchozí hodnoty, ale prázdný blok nevrací. Terraform guardrail zůstává a závěrečný plán hlásí `No changes`.
- Produkční plný běh 2026-08-23: po výslovném souhlasu byl kvůli nedostupné sdílené browser session spuštěn přímo Cloud Run Job s manuálním logical key. Execution `sreality-tracker-scraper-cnzxd` skončila úspěšně za 25 min 34 s bez retry; run `d50dd841-57c2-49d1-be53-802e408e8d23` uložil 3 580 nabídek (`new=3580`, `changed=0`, `errors=0`, `deactivated=0`) a obě kategorie označil jako kompletní. Raw payload každé nabídky je přítomný v GCS.
- Owner-trigger ověření 2026-08-23: přihlášená produkční session s platným CSRF tokenem dostala `202` a vytvořila run `6562af34-8e02-4b77-aee4-d9e681563d5b`. Execution `sreality-tracker-scraper-nl62g` vytvořila přímo API service account přes omezenou custom roli a skončila úspěšně za 14 min 13 s; výsledek byl `found=3583`, `new=7`, `changed=15`, `deactivated=4`, `errors=0`, obě kategorie kompletní. Tím je prakticky ověřen celý tok browser session/CSRF → API → Cloud Run Job → Cloud SQL/GCS.
- Předcommitové CI ověření: backend Ruff check/format, mypy nad 51 source soubory a 113 testů prošly; frontend lint/typecheck, 28 testů a production build prošly; Terraform validate a oba guardrail testy prošly. Přidán úzký `.gitattributes` guard pro Python `LF`, protože lokální `core.autocrlf=true` jinak porušoval explicitní Ruff konfiguraci.
- CI ověření a uzavření: PR #4 spustil GitHub Actions run `32650052383`; backend, frontend i Terraform job skončily zeleně. První run odhalil dvě portability mezery: partial GCS backend neměl deklarované prázdné klíče pro čistý `init -backend=false` a Linux nepovažoval `C:/private/data` za absolutní `Path`. Backend nyní nezávisle na host OS odmítá POSIX, Windows, UNC i traversal cesty a Terraform partial backend explicitně deklaruje `bucket`/`prefix`; opravný backend CI provedl i všech devět PostgreSQL integračních testů.
- Dílčí pokračování 2026-08-22: zahájen aplikační wiring `M4-05`; API i scraper umějí přes validovanou konfiguraci používat společný produkční GCS bucket. Archiv obrázků je create-only, kontroluje CRC32C a magic header a odmítá konfliktní obsah; lokální backend zůstává výchozí pro vývoj a smoke testy.

Při zahájení tasku sem zapsat:

- datum a ID tasku,
- stručný plán,
- soubory nebo komponenty v rozsahu,
- rizika a předpoklady,
- provedené testy,
- co zbývá před označením `[x]`.

Po dokončení stručnou poznámku přesunout do historie níže.

## Blokátory a otevřené otázky

Žádné otevřené blokátory. Rozpočtová brána `M0-05` byla 12. srpna 2026 uzavřena podmíněným schválením cloudového provozu.

Položka označená `[!]` musí zde uvést:

- konkrétní blokující podmínku,
- co již bylo ověřeno,
- jaké rozhodnutí nebo přístup chybí,
- které další tasky blokuje.

## Historie dokončené práce

### 2026-08-23 – `M4-06`

- Terraformem je nasazen autorizovaný pondělní Scheduler v `03:00 Europe/Prague`, dedikovaná invoker identita a nejmenší custom role umožňující API pouze spuštění scraper jobu s per-execution override.
- Owner-only trigger byl prakticky ověřen přes produkční session a CSRF: API service account vytvořil execution `sreality-tracker-scraper-nl62g`, která úspěšně zpracovala 3 583 nabídek bez chyby a korektně vyhodnotila nové, změněné i deaktivované nabídky.
- GitHub Actions na PR #4 ověřuje Python 3.13/PostgreSQL 16, frontend Node 24 a Terraform 1.15. Finální run `32650052383` skončil třemi zelenými joby; kontrolovaný deployment a rollback popisuje produkční runbook.

### 2026-08-23 – `M4-04`

- Terraform po výslovném schválení vytvořil přesně 21 zdrojů: tři oddělené runtime service accounts, tři nejmenší project IAM granty, čtyři bucket object granty bez mazání, pět regionálních Secret Manager kontejnerů a šest explicitních accessor vazeb. Cílený post-apply plán hlásí `No changes`.
- V databázi vznikla role `sreality_app` bez superuser/createdb/createrole/replication oprávnění; má pouze connect, schema usage, DML nad aplikačními tabulkami a práci se sekvencemi. Přihlášení a čtení tabulky `listings` byly prakticky ověřené.
- Přes Secret Manager API bylo mimo Terraform state vloženo přesně pět verzí `1`: produkční Cloud SQL socket URL, OAuth client ID/secret, owner e-mail a session secret. Všechny mají stav `ENABLED`; hodnoty nebyly vypsané ani zapsané do repozitáře.
- Avast Web Shield musel být dočasně vypnut, protože nahrazoval připnutý Cloud SQL certifikát. Podepsaný proxy proces i všechny dočasné soubory byly po běhu odstraněné.

### 2026-08-23 – `M4-03`

- Terraform vytvořil zonální PostgreSQL 16 `db-f1-micro`, databázi `sreality_tracker` a neveřejný regionální bucket `sreality-scrapper-504307-application-data`; cílený post-apply plán hlásí `No changes`.
- SQL instance má 10GiB SSD s limitem 15 GiB, sedm denních záloh, connector enforcement a dvojitou deletion protection. Bucket má public access prevention, sedmidenní soft delete a 90denní lifecycle omezený na `raw/`.
- Mockovaný guardrail test prošel `1 passed, 0 failed`. Podepsaný Windows Cloud SQL Auth Proxy 2.25.3 ověřil spojení přes `SELECT 1` a Alembic úspěšně aplikoval `20260811_0001 (head)`.
- Avast Web Shield původně nahrazoval připnutý Cloud SQL certifikát na portu 3307; po jeho dočasném vypnutí proběhla migrace standardním TLS bez vlastního CA override. Proxy i dočasné soubory byly po běhu odstraněny.

### 2026-08-23 – `M4-02`

- Bootstrap vytvořil chráněný regionální bucket `sreality-scrapper-504307-tfstate` s uniform access, public access prevention, versioningem a lifecycle starších verzí; následný bootstrap plán byl čistý.
- Hlavní modul používá GCS backend s prefixem `production`. Terraform state obsahuje 14 explicitně spravovaných základních API v projektu `sreality-scrapper-504307`; cílený post-apply plán hlásí `No changes`.
- Každý apply předcházela strojová kontrola JSON plánu. Bootstrap provedl přesně `1 add, 0 change, 0 destroy`, API enablement přesně `14 add, 0 change, 0 destroy`; pozdější M4 zdroje bezpečnostní kontrola neaplikovala.
- Avast TLS inspekce byla obsloužena připojením jejího root CA pouze do Terraform kontejneru; ověřování TLS nebylo vypnuto a dočasné certifikáty byly po běhu odstraněny.

### 2026-08-12 – `M4-01`

- Přidány multi-stage produkční images pro API a scraper z jednoho Python Dockerfile a samostatný Next.js standalone frontend image; dependency grafy jsou zamčené přes `requirements-prod.txt` a `package-lock.json`.
- Images běží jako `10001:10001`, neobsahují lokální data, secrets ani vývojové build kontexty a mají velikosti 74,4 MiB (API), 74,4 MiB (scraper) a 88,2 MiB (frontend).
- Izolovaný Compose smoke stack používá PostgreSQL v `tmpfs`; ověřil zdravý API/backend, frontend proxy, liveness, readiness a read-only scraper DB check. První smoke odhalil poškozený lock po timeoutu, následná atomická regenerace a instalace do `/opt/venv` problém odstranila.
- Ověření: Docker build všech tří images prošel; 105 backend unit testů, 28 frontend testů a produkční Next.js standalone build prošly.

### 2026-08-11 – oprava živého scraperu po změně detailního SSR

- Živě ověřeno, že search SSR pro chaty i chalupy zůstává funkční, ale detail inzerátu nově přesměrovává přes consent flow Seznamu a bezpečnostní validace klienta jej správně odmítne.
- Zdroj po prvním nedostupném detailu přejde pro zbytek kategorie na omezená data ze search payloadu; zachová ID, název, cenu, lokalitu, GPS a obrázky a neprovádí tisíce dalších chybných detail requestů. Popis, plochy a detailní parametry zůstávají v tomto režimu prázdné.
- Odmítnutý cross-host consent/autologin redirect zároveň vyčistí cookies, které by jinak kontaminovaly sdílenou HTTP session a odklonily i následující search stránky.
- Ověření: živý smoke test přes dvě search stránky prošel; 105 unit testů, Ruff a cílený mypy check prošly. Plný mypy nad repozitářem nadále hlásí pět dříve existujících chyb ve třech M0 skriptech.

### 2026-08-11 – `M3-08`

- Doplněn skip link, viditelné focus stavy, reduced-motion režim a responzivní layouty tabulky, mapy, galerie, detailu i soukromých ovládacích prvků.
- Playwright testuje owner cestu, URL filtry, detail, CSRF oblíbení, nepřihlášený shell a klávesnicovou navigaci v desktopovém Chromiu i Pixel 7 viewportu.
- Ověření: 6/6 E2E scénářů prošlo; browser skill neměl v relaci připojený interaktivní browser, rendery byly vizuálně zkontrolovány z Playwright screenshotů.

### 2026-08-11 – `M3-07`

- Detail ukládá oblíbený stav a soukromou poznámku s jasným průběhem, chybou a potvrzením počtu archivovaných fotografií.
- Archivované bitmapy vydává nový owner-only endpoint; key se bere pouze z DB, cesta zůstává pod storage rootem a odpověď používá validovaný magic header, private cache a `nosniff`.
- Ověření: CSRF frontend test, owner/API test a storage test odmítající nebitmapový obsah; backend 103 passed, 11 environment/live skipped.

### 2026-08-11 – `M3-06`

- Responzivní detail zobrazuje bezpečně escapovaný popis, parametry, plochy, vzdálenosti, stav, zdrojový odkaz, galerii, cenovou historii a události.
- Zdrojové obrázky i odkazy procházejí explicitním HTTPS host allowlistem; test ověřuje, že text obsahující `<script>` nevytvoří spustitelný element.
- Ověření: frontend lint, strict typecheck, unit testy a produkční build s dynamickou routou `/nabidky/[id]` prošly.

### 2026-08-11 – `M3-05`

- Leaflet mapa sdílí URL filtry s tabulkou a mediánem, automaticky přizpůsobuje výřez a uvádí počet bodů i výsledků bez GPS.
- Tile provider je bezpečně konfigurovatelný přes preset OSM/CARTO s pevnou správnou atribucí; libovolná URL se nepřijímá.
- Ověření: konfigurační testy, lint, strict typecheck a produkční build prošly.

### 2026-08-11 – `M3-04`

- Tabulka podporuje všechny M2 filtry, whitelistované řazení a serverové stránkování; stav se serializuje do obnovitelné URL.
- Nevalidní nebo neznámé query hodnoty bezpečně přecházejí na výchozí filtry a analytika/mapa používají stejný výběr bez prezentačního stránkování.
- Ověření: parser round-trip/invalid input testy, frontend lint, strict typecheck a produkční build prošly.

### 2026-08-11 – `M3-03`

- Dashboard zobrazuje aktuální medián nabídkových cen, velikost filtrovaného vzorku a přístupný SVG vývoj po úspěšných bězích.
- Jasné vysvětlení odděluje nabídkové ceny od skutečných realizovaných cen; dostupné jsou loading, empty, error a retry stavy.
- Ověření: frontend lint, strict typecheck, 14 testů a produkční Next.js build prošly.

### 2026-08-11 – `M3-02`

- Frontend obnovuje owner session pouze přes HttpOnly cookie, drží CSRF token v paměti a bez autorizace nevyrenderuje chráněný obsah.
- Google callback nastaví Secure session a vrací uživatele na pevně validovaný frontend origin; host je lokálně sjednocený na `localhost`.
- Logout používá CSRF hlavičku; frontend automaticky znovu ověří session při návratu na viditelnou kartu.
- Ověření: frontendové auth testy a backend callback/session test; backend 101 passed, 11 environment/live skipped.

### 2026-08-11 – `M3-01`

- Založen Next.js 16 App Router, React 19, strict TypeScript 6, ESLint 9, Vitest a reprodukovatelný npm lockfile.
- Přidán typovaný klient celého M2 API se same-origin proxy, české formátování a společné loading/empty/error stavy.
- Responzivní layout používá centrální design tokeny, viditelné focus stavy a respektuje reduced motion.
- Ověření: lint, strict typecheck, unit testy a produkční build prošly.

### 2026-08-11 – `M2-08`

- Přidán Google authorization-code flow se state, nonce, PKCE a serverovým ověřením ID tokenu; backend vyžaduje ověřený e-mail a přesný owner allowlist.
- Osmihodinová HMAC session používá `HttpOnly`, `Secure`, `SameSite=Lax`; pozměněná, expirovaná nebo cizí session je odmítnuta.
- Všechny listing, detail, mapové, analytické a provozní endpointy jsou soukromé; zápisové operace navíc vyžadují shodný CSRF token.
- Přidán owner-only stav posledního scraper běhu a idempotentní manuální trigger, který rezervuje unikátní run a práci spouští po HTTP odpovědi.
- OAuth, owner a session secrets jsou validované/redigované a zůstávají pouze v ignorovaném `.env`; neúplná konfigurace nebo session secret kratší než 32 bajtů bezpečně selže.
- Live login přes osobní projekt a účet vrátil `authenticated: true`; sanitizovaný důkaz je v `docs/discovery/m2-08-google-oauth-validation.md`.
- Ověření: 108 passed, 2 explicitní live skipped; Ruff, strict mypy pro 45 source souborů a `git diff --check` čisté.

### 2026-08-11 – `M2-03`

- Ověřen osobní GCP projekt, aktivní billing, zapnuté Routes API a denní consumer quota 300 pro `compute_routes_requests`; pracovní projekt zůstal mimo rozsah.
- Jediný live OAuth request Praha–Brno v režimu `TRAFFIC_UNAWARE` a s minimálním field maskem vrátil `207588 m` a `8233 s`; sanitizovaný důkaz je v `docs/discovery/m2-03-google-routes-validation.md`.
- Přidán odolný Compute Routes klient s retry pouze pro 429/5xx/transport, bezpečnými chybami, procesním request budgetem a logovatelnou metrikou každého provider callu.
- Silniční vzdálenost a doba jízdy se cachují podle listingu, verze reference a hashe GPS; 8233 sekund se konzervativně ukládá jako 138 minut.
- Pipeline používá cache a výpadek Routes nikdy nezruší uloženou nabídku; samostatný backfill projde i přes již cachované položky a reportuje requesty/cache/failure.
- Přidán explicitně opt-in live test omezený na jeden request a CLI `routes-backfill --limit 1..300` s krátkodobým tokenem pouze v process environment.
- Ověření: 102 passed, 2 explicitní live skipped; Ruff, strict mypy pro 42 source souborů a `git diff --check` čisté.

### 2026-08-11 – `M2-07`

- Přidán owner-only `PATCH /api/v1/listings/{listing_id}/user-data` s částečnou změnou oblíbeného stavu a samostatné soukromé poznámky.
- Autorizační seam odmítá chybějící ověřenou identitu jednotnou 401 odpovědí a je připravený pro Google OAuth wiring v M2-08.
- Oblíbení spouští archivaci po jednotlivých obrázcích; externí chyba nevrací uživatelský stav ani úspěšné archivace.
- Lokální archiv používá immutable create-only zápis a deterministický klíč `favorite-images/{listing_id}/{source_fingerprint}.bin`.
- Již archivované fotografie se nestahují znovu, `failed` položky se při dalším oblíbení retryují a odznačení archiv nemaže.
- Ověření: failure/retry/idempotency PostgreSQL test, API 401 test a unit testy immutable archivu/host allowlistu; plná sada 92 passed, 1 live skipped, Ruff/strict mypy a `git diff --check` čisté.

### 2026-08-11 – `M2-06`

- Přidán detail nabídky s parametry, cenami, lokalitou, plochami, fotografiemi, aktuálními vzdálenostmi, aktivitou a soukromým stavem.
- Chronologická historie spojuje každé cenové pozorování se stavem konkrétního scraper běhu a samostatně vrací auditní události.
- Mapový endpoint sdílí filtry seznamu a vrací pouze nabídky s kompletní dvojicí zeměpisných souřadnic.
- Aktuální medián používá aktuální filtrovaný stav; historická řada počítá snapshotové ceny a plochy zvlášť pro každý `succeeded` run.
- `NULL` ceny/ceny na vyžádání a `partial`/`failed` běhy se z historického mediánu vylučují; test pokrývá i extrémní cenu v partial runu.
- Ověření: 84 passed, 1 explicitní live skipped; nové API moduly prošly Ruff a strict mypy, `git diff --check` je čistý.

### 2026-08-11 – `M2-05`

- Přidán `/api/v1/listings` se serverovým stránkováním (1–100 položek), celkovým počtem a počtem stran.
- Filtry pokrývají aktivitu/poslední-run události, kategorii, kraj, okres, cenu, plochy, cenu za m², vzdušnou/silniční vzdálenost, dobu jízdy a oblíbené.
- `new`, `price_decreased` a `reactivated` se vztahují k poslednímu úspěšnému runu, nikoli k libovolné historické události.
- Řazení je omezené enum whitelistou a vždy doplněné stabilním externím ID; NULL ceny a vzdálenosti se řadí nakonec.
- PostgreSQL test ověřuje cenové stránkování a kombinaci latest-run/kategorie/kraje/ceny/oblíbených/vzdálenosti; invalidní rozsah vrací jednotnou 422 chybu.
- Plná sada: 83 passed, 1 live skipped; 21 dotčených souborů prošlo Ruff, strict mypy a `git diff --check`.

### 2026-08-11 – `M2-04`

- Přidána FastAPI 0.139 aplikační factory bez import-time konfigurace či DB spojení a Uvicorn 0.51 runtime.
- Všechny aplikační routy jsou pod `/api/v1`; OpenAPI obsahuje verzi balíčku a stabilní response modely.
- App container poskytuje explicitní settings, engine, session factory a readiness probe přes dependency injection.
- Liveness je nezávislá na DB, readiness používá read-only `SELECT 1`; vlastnictví engine určuje bezpečné dispose při lifespan shutdownu.
- API chyby včetně 404, validace, readiness a neočekávané výjimky mají jednotný bezpečný envelope bez interních detailů.
- Ověření: contract testy pokrývají health, readiness failure, 404, OpenAPI a request-scoped session; plná sada 81 passed, 1 live skipped, Ruff/strict mypy čisté.

### 2026-08-11 – `M2-02`

- Přidán deterministický Haversinův výpočet s IUGG středním poloměrem Země a striktní validací párových WGS84 souřadnic.
- Cílové souřadnice mají stabilní SHA-256 fingerprint na sedm desetinných míst; chybějící, neúplné nebo nevalidní GPS se neukládají.
- Pipeline idempotentně ukládá lokální provider `local_haversine`/`straight_line` do `listing_distances`, zaokrouhlený na 0,001 km.
- Opakovaná pozorování stejných souřadnic používají existující cache řádek; změna cíle nebo reference vytvoří odlišnou cache identitu.
- Ověření: známý bod Praha–Brno vychází 186,221 km; unit a PostgreSQL testy pokrývají nulovou/symetrickou vzdálenost, invalidní GPS a dvě cache položky pro dva listingy.
- Plná sada: 78 passed, 1 live skipped; dotčený kód prošel Ruff, strict mypy a `git diff --check`.

### 2026-08-11 – `M2-01`

- Přidán neměnný centrální registr `ReferencePoint` s validací WGS84, stabilním klíčem, kladnou verzí a coordinate hashem.
- Praha v1 používá adresní místo RÚIAN 21714746 na Mariánském náměstí 2/2: `50.0871072, 14.4178281`.
- Cache identita obsahuje klíč, verzi a SHA-256 souřadnic normalizovaných na sedm desetinných míst.
- ADR `0001-prague-reference-point.md` dokumentuje zdroje, důvody, omezení a pravidlo, že změna souřadnic musí vytvořit novou verzi.
- Ověření: 9 unit testů pokrývá centrální lookup, neměnnost, hash, změnu verze a nevalidní konfigurace; Ruff a strict mypy prošly.

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
