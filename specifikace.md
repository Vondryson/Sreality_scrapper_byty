# Specifikace projektu Sreality Chaty Tracker

## 1. Účel dokumentu

Tento dokument je hlavní a dlouhodobý zdroj pravdy pro vývoj projektu. Je určen lidem i AI agentům a musí umožnit pokračovat v práci i po ztrátě předchozího kontextu.

Před návrhem nebo implementací změny je nutné:

1. přečíst tento dokument,
2. ověřit aktuální stav repozitáře,
3. zachovat zde uvedená produktová a architektonická rozhodnutí,
4. nevymýšlet chybějící produktové požadavky bez jejich označení jako předpoklad,
5. aktualizovat tento dokument, pokud uživatel schválí změnu rozsahu nebo architektury.

Pokud je implementace v rozporu s tímto dokumentem, agent má rozpor uživateli oznámit. Dokument popisuje cílový stav; současný kód je pouze výchozí bod a může být výrazně refaktorován.

## 2. Vize a motivace

Sreality Chaty Tracker je neveřejná aplikace pro jednoho uživatele, který zvažuje koupi chaty nebo chalupy v České republice. Cílem je zabránit ukvapenému rozhodnutí a umožnit dlouhodobě sledovat:

- vývoj nabídkových cen,
- historii ceny konkrétní nemovitosti,
- vztah ceny a vzdálenosti od Prahy,
- nové, zlevněné, stažené a znovu zveřejněné nabídky,
- rozdíly mezi lokalitami pomocí mapy a filtrování.

Projekt má zároveň sloužit jako praktické cvičení v datovém inženýrství, cloudové architektuře a vizualizaci dat.

Nejde o veřejný komerční produkt, automatické oceňování nemovitostí ani náhradu odborné právní, technické nebo finanční kontroly před koupí.

## 3. Potvrzená produktová rozhodnutí

| Oblast | Rozhodnutí |
| --- | --- |
| Pracovní název | Sreality Chaty Tracker |
| Uživatelé | Jeden vlastník aplikace |
| Viditelnost | Neveřejná aplikace s přihlášením přes Google a allowlistem jednoho účtu |
| Zdroj dat | Sreality.cz |
| Územní rozsah | Celá Česká republika |
| Typ nabídky | Pouze prodej |
| Kategorie | `category_main_cb=2` (domy), `category_sub_cb=33` (chata) a `category_sub_cb=43` (chalupa) |
| Vyloučené kategorie | Byty, rodinné domy, usedlosti, mobilheimy a ostatní typy nemovitostí |
| Periodicita | Jednou týdně, v pondělí ve 03:00 v časové zóně `Europe/Prague` |
| Ruční spuštění | Ano, pouze autorizovaně |
| Referenční město | Praha |
| Vzdálenosti | Vzdušná vzdálenost, silniční vzdálenost a odhad doby jízdy autem bez aktuální dopravy |
| Jazyk UI | Čeština |
| Zařízení | Responzivní desktopové i mobilní rozhraní |
| Starší data | Nemigrovat stará data bytů ani současnou SQLite databázi |
| Cílový cloud | Google Cloud, projekt `sreality-scrapper-504307` |
| Preferovaný region | `europe-west1` (Belgie) |
| Cílový rozpočet | Maximálně přibližně 200–300 Kč měsíčně |

## 4. Rozsah MVP

### 4.1 Sběr dat

MVP musí:

- jednou týdně získat úplný seznam chat a chalup na prodej v celé ČR,
- stáhnout detail každé aktuální nabídky,
- ukládat všechny textové informace dostupné ve zdrojové odpovědi,
- ukládat klíčové strukturované údaje do typovaných databázových sloupců,
- uchovat původní odpověď zdroje po omezenou dobu pro opakovatelné zpracování a diagnostiku,
- zaznamenat přítomnost nabídky v každém úspěšném běhu,
- sledovat historii ceny a změny detailu,
- rozpoznat nové, zlevněné, stažené a znovu aktivní nabídky,
- vypočítat vzdálenosti od Prahy pouze pro novou nebo relevantně přemístěnou nabídku,
- umožnit ruční spuštění stejného idempotentního procesu.

### 4.2 Frontend

MVP musí obsahovat:

- přihlašovací obrazovku,
- přehled s mediánem nabídkové ceny,
- vývoj mediánu nabídkové ceny v čase,
- tabulku nabídek s filtrováním a řazením,
- mapu nabídek,
- detail nabídky,
- graf historie ceny konkrétní nabídky,
- viditelné označení nové, zlevněné, stažené nebo znovu aktivní nabídky,
- možnost označit nabídku jako oblíbenou,
- možnost přidat k nabídce soukromou poznámku,
- odkaz na původní inzerát na Sreality.

Minimální filtry:

- chata/chalupa,
- aktivní/neaktivní/nová/zlevněná/znovu aktivní,
- kraj a okres,
- cenový rozsah,
- užitná plocha,
- plocha pozemku,
- cena za m²,
- vzdušná nebo silniční vzdálenost od Prahy,
- doba jízdy autem,
- pouze oblíbené.

### 4.3 Analytika MVP

Jedinou agregovanou tržní metrikou MVP je medián nabídkové ceny. Musí být dostupný:

- pro aktuální aktivní nabídky po aplikování filtrů,
- jako týdenní časová řada nad nabídkami přítomnými v jednotlivých úspěšných bězích.

Historie ceny jednotlivého inzerátu není agregovaná tržní metrika a je součástí MVP.

Cena za m² je pomocný atribut pro filtrování a zobrazení. Pokud není známá vhodná plocha nebo je nulová, nesmí se dopočítat zavádějící hodnota.

### 4.4 Mimo rozsah MVP

Do MVP nepatří:

- predikce budoucích cen,
- investiční nebo doporučovací skóre,
- automatické párování stejné nemovitosti zveřejněné pod různými Sreality ID,
- více uživatelů a sdílení dat,
- vlastní správa hesel,
- veřejné API,
- mobilní aplikace,
- import historických bytových dat,
- jiné realitní portály,
- SMS nebo push notifikace,
- pokročilé agregace podle regionu, počty nabídek, statistiky slev nebo doby inzerce,
- trvalá archivace všech fotografií.

Tyto funkce mohou vzniknout v dalších fázích, ale nesmějí komplikovat nebo prodražit MVP bez explicitního schválení.

## 5. Zdroj dat a pravidla scrapingu

### 5.1 Zdrojové rozhraní

Výchozí kód z roku 2024 používal neoficiální JSON endpointy Sreality:

- seznam: `https://www.sreality.cz/api/cs/v2/estates`,
- počet: `https://www.sreality.cz/api/cs/v2/estates/count`,
- detail: `https://www.sreality.cz/api/cs/v2/estates/{code}`.

Při validaci 2. srpna 2026 vracely seznamový i count endpoint HTTP 404. Aktuální veřejné vyhledávací stránky jsou serverově renderované pomocí Next.js a obsahují strukturovaný `__NEXT_DATA__` payload s query `estatesSearch`. Byly ověřeny slugy `/hledani/prodej/domy/chaty` a `/hledani/prodej/domy/chalupy`, filtrování podtypů 33/43, stránkování přes `?strana=N` a limit 22 výsledků na stránku. Detailní datový zdroj bude ověřen v M0-03 před implementací produkčního klienta.

Žádné z těchto rozhraní není považováno za stabilní veřejný kontrakt. Parser proto musí být odolný vůči chybějícím polím a změnám struktury. Zdrojový payload se nesmí slepě mapovat do povinných databázových polí. Produkční implementace se nesmí vrátit ke starým REST endpointům bez nového živého ověření.

### 5.2 Chování scraperu

- Pro podtypy `33` a `43` používat samostatně správně filtrované dotazy a jejich filtrovaný počet výsledků.
- Stránkování nesmí být odvozeno od počtu všech nemovitostí na Sreality.
- Počet položek na stránku nesmí být natvrdo považován za věčně platný; chování je nutné integračně ověřit.
- Používat jednu znovupoužitelnou HTTP session, rozumné timeouty, omezenou paralelizaci, retry s exponenciálním backoffem a jitterem.
- Zachovat nízkou frekvenci a šetrné tempo požadavků. Neobcházet CAPTCHA, blokace ani jiná technická omezení služby.
- Použít pravdivý a identifikovatelný User-Agent projektu, pokud to podmínky zdroje umožňují.
- Validovat HTTP status, Content-Type a základní tvar odpovědi před parsováním.
- Obecný `except` bez zalogování příčiny je zakázán.
- Jedna vadná nabídka nemá shodit celý běh, ale běh musí vykázat chybu a počet neúspěšných položek.
- Každý běh má jednoznačné ID a stav `running`, `succeeded`, `partial` nebo `failed`.
- Opakované spuštění stejného logického běhu nesmí vytvářet duplicitní pozorování.

### 5.3 Stav a životní cyklus nabídky

Stav nabídky se smí změnit na neaktivní pouze po dokončení úplného a úspěšného načtení obou kategorií. Neúspěšný nebo částečný běh nesmí hromadně deaktivovat nabídky.

- První výskyt ID: `new` a `active`.
- Přítomnost v dalším běhu: aktualizovat `last_seen_at` a uložit pozorování.
- Pokles ceny: označit událost `price_decreased`.
- Růst ceny: uložit změnu ceny bez označení jako zlevnění.
- Nepřítomnost v úplném úspěšném běhu: `inactive` a uložit `inactive_at`.
- Návrat stejného Sreality ID: `reactivated`, zachovat původní historii a zrušit `inactive_at`.
- Jinému Sreality ID se v MVP nepřisuzuje automaticky identita starší nabídky.

## 6. Data a datový model

### 6.1 Zásady

- PostgreSQL je autoritativní úložiště aplikačních a analytických dat.
- Sreality ID je externí přirozený identifikátor, nikoli databázový primární klíč.
- Interní vazby používají vlastní UUID nebo bigint ID.
- Časy se ukládají v UTC jako timezone-aware hodnoty; UI je převádí do `Europe/Prague`.
- Částky se ukládají jako celá čísla v CZK, pokud zdroj výslovně neuvádí jinou měnu.
- Zdrojová cena `0` znamená neuvedenou cenu/cenu na vyžádání a pro analytiku se normalizuje na `NULL` se samostatným příznakem; nesmí snižovat medián.
- Chybějící údaj je `NULL`, nikoli `"-"`, nula nebo prázdný text.
- Zdrojový text se uchovává beze změny; odvozené a normalizované hodnoty jsou oddělené.
- Schéma musí používat migrace, například Alembic. Ruční vytváření tabulek při startu aplikace není cílové řešení.

### 6.2 Minimální entity

#### `scrape_runs`

Obsahuje alespoň:

- ID běhu,
- plánovaný/ruční typ spuštění,
- začátek a konec,
- stav,
- počty nalezených, nových, změněných, chybných a deaktivovaných nabídek,
- verzi scraperu,
- stručné informace o chybě.

#### `listings`

Obsahuje současný stav nabídky:

- interní ID,
- unikátní Sreality ID,
- typ `chata`/`chalupa`,
- URL zdroje,
- aktivní stav,
- `first_seen_at`, `last_seen_at`, `inactive_at`,
- současnou cenu,
- všechny aktuální normalizované textové a číselné parametry,
- popis a poznámku k ceně,
- lokalitu, GPS, kraj, okres a obec,
- užitnou plochu a plochu pozemku,
- odvozenou cenu za m²,
- hash relevantního obsahu pro detekci změn,
- datum poslední změny detailu.

Datový model nesmí předpokládat bytové atributy jako podlaží, balkon nebo vlastnictví jednotky. Má vycházet ze skutečných polí chat a chalup. Nové či málo stabilní vlastnosti mohou být vedle typovaných polí dočasně uloženy také v JSONB.

#### `listing_observations`

Jedno pozorování nabídky v jednom úspěšném nebo částečném běhu. Obsahuje alespoň:

- listing ID a run ID s unikátním omezením,
- pozorovanou cenu,
- parametry potřebné pro historickou analýzu,
- hash detailu,
- odkaz na raw payload v Cloud Storage, pokud existuje,
- čas pozorování.

Pozorování přítomnosti v každém běhu je nutné pro korektní týdenní medián i zpětnou auditovatelnost.

#### `listing_events`

Události jako `created`, `price_decreased`, `price_increased`, `details_changed`, `deactivated` a `reactivated`. Událost obsahuje čas, starou a novou hodnotu nebo strojově čitelné změny.

#### `listing_images`

Metadata fotografie:

- listing ID,
- zdrojové ID nebo URL,
- pořadí,
- rozměry, pokud jsou známy,
- čas prvního a posledního výskytu,
- volitelný Cloud Storage object key,
- stav stažení a hash souboru.

#### `listing_distances`

- listing ID,
- referenční místo `Praha`,
- přesná verze referenčních souřadnic,
- vzdušná vzdálenost v kilometrech,
- silniční vzdálenost v kilometrech,
- doba jízdy v minutách bez aktuální dopravy,
- použitý poskytovatel a režim,
- čas výpočtu.

Referenční bod Prahy musí být centrálně konfigurovaný a verzovaný, nikoli rozptýlený jako magické souřadnice v kódu. Změna referenčního bodu vyžaduje přepočet nebo novou verzi vzdáleností.

#### `user_listing_data`

Soukromá data jediného uživatele:

- listing ID,
- `is_favorite`,
- soukromá poznámka,
- časy změn.

I při jednom uživateli nemají být poznámky součástí zdrojových dat nabídky.

### 6.3 Raw data

Originální odpovědi API ukládat komprimovaně do Cloud Storage s vazbou na běh a nabídku. Standardní retenční doba je 90 dní a má být vynucena lifecycle pravidlem bucketu.

Raw data slouží k diagnostice, opravě parseru a případnému opakovanému zpracování. PostgreSQL obsahuje trvalou normalizovanou historii, takže smazání raw dat po 90 dnech nesmí odstranit analytický kontext.

## 7. Vzdálenost od Prahy a mapa

### 7.1 Vzdušná vzdálenost

Počítat lokálně z GPS pomocí geodetické/Haversinovy metody. Výpočet nevyžaduje externí placené API.

### 7.2 Silniční vzdálenost a doba jízdy

Použít Google Routes API v režimu bez aktuální dopravní situace. Výsledek ukládat a stejnou trasu bez důvodu nepřepočítávat. Výpočet se provede při prvním získání validních GPS nebo při jejich významné změně.

Je nutné:

- omezit API kvótu tak, aby nebylo možné nekontrolovaně překročit rozpočet,
- sledovat počet výpočtů,
- bezpečně uložit API credential v Secret Manageru,
- při nedostupnosti Routes API zachovat nabídku a vzdálenost dopočítat později,
- nepovažovat dobu jízdy za garantovaný reálný cestovní čas.

Předpoklad ze srpna 2026: Essentials varianta má bezplatný limit 10 000 výpočtů měsíčně. Před nasazením je nutné cenu a limit znovu ověřit v aktuálním ceníku.

### 7.3 Mapa

Preferovat Leaflet s vhodným poskytovatelem OpenStreetMap dlaždic, aby mapa nevytvářela významné fixní náklady. Produkční použití musí respektovat podmínky a limity konkrétního tile providera; provider musí být konfigurovatelný.

## 8. Fotografie

### 8.1 MVP strategie

- Pro všechny nabídky ukládat metadata a zdrojové URL fotografií.
- Fotografie všech nabídek v MVP trvale nekopírovat.
- Do Cloud Storage kopírovat pouze fotografie nabídky označené jako oblíbená.
- Stažení musí být idempotentní a deduplikované podle zdrojového ID nebo hashe.
- Odebrání z oblíbených nesmí fotografie automaticky nevratně smazat; smazání je samostatná explicitní operace nebo pozdější retenční pravidlo.
- UI musí umět zobrazit zdrojové fotografie, ale musí počítat s tím, že URL může přestat fungovat.

### 8.2 Rozpočtový předpoklad

Pilotní měření z 2. srpna 2026 na 10 nabídkách zjistilo medián 26,5 fotografie a 96 708 B pro veřejně renderovanou 800×600 WebP variantu. Při tehdejších 3 583 aktivních nabídkách vychází bodový odhad jedné kopie trhu přibližně na 9,2 GB. Jde o malý nereprezentativní vzorek a originály by byly výrazně větší. Samotné úložiště je relativně levné, ale archiv, počet operací a přenos dat rostou v čase. Před případným zapnutím archivace všech fotografií je nutné udělat nové měření reálného objemu, odhad ročního churnu a kontrolu podmínek použití zdroje.

## 9. Cílová architektura

### 9.1 Aplikační stack

- Python 3.12 nebo aktuální podporovaná stabilní verze,
- FastAPI pro aplikační API,
- React/Next.js pro frontend,
- PostgreSQL,
- SQLAlchemy a Alembic,
- kontejnerizace pomocí Dockeru,
- Terraform pro cloudovou infrastrukturu,
- automatizované testy v CI.

Konkrétní verze závislostí mají být zamčené a průběžně aktualizované. Volba knihovny nesmí zbytečně navyšovat provozní náklady.

### 9.2 Google Cloud komponenty

- Cloud Run service pro FastAPI backend,
- Cloud Run service pro frontend, případně jeden sloučený deployment, pokud prokazatelně sníží složitost a náklady bez zhoršení architektury,
- Cloud Run Job pro scraper a transformační pipeline,
- Cloud Scheduler pro týdenní autorizované spuštění jobu,
- Cloud SQL for PostgreSQL, `db-f1-micro`, bez HA,
- Cloud Storage v jednom regionu pro raw payloady a fotografie oblíbených nabídek,
- Secret Manager pro databázové, OAuth a API credentials,
- Artifact Registry pro kontejnery,
- Cloud Logging a Cloud Monitoring,
- Google OAuth pro přihlášení a aplikační allowlist jednoho e-mailu,
- Google Routes API pro silniční vzdálenost a dobu jízdy.

Všechny podporované prostředky mají být ve `europe-west1`, pokud konkrétní služba nevyžaduje globální prostředek. Je třeba zabránit zbytečným meziregionálním přenosům.

### 9.3 Prostředí

Minimálně rozlišovat:

- lokální vývoj,
- produkci v GCP.

Kvůli rozpočtu není požadováno samostatné permanentní cloudové staging prostředí. Testy mají používat lokální/kontejnerovou databázi a mockované externí služby.

### 9.4 Konfigurace

- Žádné absolutní cesty uživatele v kódu.
- Konfigurace přes environment variables s validací při startu.
- Tajné hodnoty nikdy necommitovat ani nevypisovat do logu.
- Repozitář musí obsahovat bezpečný `.env.example` bez reálných credentials.
- Lokální data, databáze, logy a secrets nesmí být verzované.

## 10. Rozpočet a nákladové mantinely

Cílem je udržet běžný provoz pod 200–300 Kč měsíčně. Pokud se to nepodaří, je přijatelný lokální provoz nebo explicitně schválené zvýšení rozpočtu.

Orientační stav cen ze srpna 2026:

- Cloud SQL `db-f1-micro`: přibližně 0,0105 USD/h, asi 7,67 USD měsíčně za compute bez storage a záloh; instance nemá SLA,
- minimální 10GiB Cloud SQL SSD disk: přibližně 3,40 USD měsíčně; při 2 GiB použitých zálohách přibližně dalších 0,16 USD,
- Cloud Run: při nízkém využití a scale-to-zero pravděpodobně v bezplatném limitu,
- Cloud Scheduler: jeden job v bezplatném limitu tří jobů,
- regionální Standard Cloud Storage: řádově 0,02 USD/GB/měsíc plus operace a přenosy,
- Google Routes Essentials: předpokládaný bezplatný limit 10 000 výpočtů měsíčně.

Reprodukovatelný model v `scripts/calculate_gcp_costs.py` vychází při konzervativním kurzu 24 Kč/USD na přibližně 276 Kč měsíčně bez případné DPH. Konzervativní scénář s větší zálohou a rezervou vychází přibližně na 307 Kč bez případné DPH. Cloud SQL spotřebuje téměř celý rozpočet; podrobný audit je v `docs/discovery/m0-05-gcp-costs.md`.

Ceny jsou pouze pracovní odhad a před nasazením musí být ověřeny v aktuálním Google Cloud Pricing Calculatoru a následně jedním celým fakturačním měsícem. Pokud skutečný run-rate překročí 300 Kč, výchozí rozhodnutí je přejít na lokální PostgreSQL, dokud uživatel explicitně neschválí vyšší rozpočet.

Povinné mantinely:

- Cloud Run `min-instances=0`,
- žádná Cloud SQL HA ani read replica,
- nejmenší ověřená Cloud SQL instance,
- Cloud SQL disk začít na 10 GiB a omezit automatický růst nejvýše na 15 GiB,
- jeden regionální bucket, nikoli multi-region,
- lifecycle pravidlo pro raw data po 90 dnech,
- nepoužívat placený load balancer nebo IAP, pokud není nezbytný,
- vyhnout se Serverless VPC Access connectoru, pokud lze použít bezpečné přímé Cloud SQL připojení,
- nastavit billing budget upozornění na 200 Kč a 300 Kč,
- nastavit kvóty externích API,
- Google Routes výsledek trvale cachovat podle referenčního bodu a souřadnic; po bootstrapu držet denní kvótu nejvýše 300 výpočtů,
- pravidelně kontrolovat náklady podle služby.

Budget alert není tvrdý limit a sám nezastaví účtování. Automatické vypínání produkce se v MVP nepožaduje, ale žádná změna s významným fixním měsíčním nákladem se nesmí zavést bez upozornění uživatele.

## 11. API a frontendové chování

Backend má nabídnout verzované interní endpointy minimálně pro:

- přehled a filtrování nabídek,
- detail nabídky,
- historii ceny,
- týdenní medián ceny,
- mapová data,
- oblíbené a poznámky,
- stav posledního scrapingu,
- autorizované ruční spuštění.

Požadavky na UI:

- české formátování ceny, plochy, data, vzdálenosti a doby jízdy,
- srozumitelný stav chybějících údajů,
- serverové stránkování nebo jiný škálovatelný přístup; nestahovat celý trh do prohlížeče,
- filtry reprezentovatelné v URL, aby bylo možné pohled obnovit nebo uložit,
- loading, empty a error stavy,
- přístupnost klávesnicí a rozumný barevný kontrast,
- žádné zpřístupnění soukromých poznámek bez autentizace.

Frontend nemá vydávat nabídkovou cenu nebo medián za odhad skutečné prodejní ceny.

## 12. Bezpečnost a soukromí

- Přístup pouze po Google OAuth přihlášení.
- Po přihlášení ověřit e-mail proti explicitnímu allowlistu na backendu; kontrola pouze ve frontendu nestačí.
- Všechny zápisové a ruční provozní endpointy vyžadují autentizaci a autorizaci.
- Session cookies musí být `HttpOnly`, `Secure` a s vhodným `SameSite` nastavením.
- Secrets ukládat v Secret Manageru a přidělovat službám nejmenší potřebná IAM oprávnění.
- Databáze ani bucket nesmí být veřejné.
- Zdrojové URL fotografií nepovažovat za důvěryhodný uživatelský vstup.
- Text inzerátu při renderování bezpečně escapovat.
- Logy nesmí obsahovat OAuth tokeny, API klíče, cookies ani celý citlivý request.
- Nastavit zálohování PostgreSQL v nejnižší rozumné konfiguraci, která respektuje rozpočet, a zdokumentovat postup obnovy.

## 13. Monitoring, logování a upozornění

Používat strukturované logy s `run_id`, případně `listing_id`, stavem kroku a typem chyby.

Sledovat minimálně:

- úspěch a délku běhu,
- počet výsledků každé kategorie,
- počet nových, aktualizovaných, deaktivovaných a chybných nabídek,
- počet HTTP chyb a retry,
- počet volání Google Routes,
- velikost raw dat a fotografií,
- náklady a překročení rozpočtových prahů,
- čas posledního úspěšného běhu.

E-mailové upozornění poslat při:

- neúspěšném nebo částečném běhu,
- podezřelém propadu počtu nabídek,
- selhání parseru ve větším rozsahu,
- chybě databáze nebo úložiště,
- překročení rozpočtového upozornění.

Po úspěšném týdenním běhu má být možné zaslat stručný e-mail s novými a zlevněnými objekty. E-mail nesmí obsahovat tajné údaje.

Provozní logy mají standardní retenci 30 dní.

## 14. Kvalita, testování a Definition of Done

### 14.1 Povinné testy

- Unit testy parseru nad verzovanými anonymizovanými fixtures pro chatu i chalupu.
- Testy chybějících, nulových a nových polí API.
- Testy stránkování a kombinace filtrů.
- Testy idempotence opakovaného běhu.
- Testy detekce nové nabídky, změny ceny, deaktivace a reaktivace.
- Test zajišťující, že neúplný běh nedeaktivuje nabídky.
- Testy výpočtu ceny za m² a mediánu s `NULL` a extrémními hodnotami.
- Test výpočtu vzdušné vzdálenosti.
- Integrační test databáze a migrací na PostgreSQL.
- API testy autentizace, autorizace, filtrů a stránkování.
- Základní frontendové testy kritických cest.
- Smoke test kontejnerů.

Živé testy proti Sreality a Google Routes musí být oddělené, šetrné a nesmí běžet při každém lokálním testu.

### 14.2 Akceptační kritéria MVP

MVP je hotové, když:

1. infrastrukturu lze reprodukovatelně vytvořit z repozitáře,
2. týdenní job automaticky stáhne obě potvrzené kategorie pro celou ČR,
3. úspěšný běh vytvoří konzistentní pozorování bez duplicit,
4. historie ceny a stavy nabídky odpovídají uloženým běhům,
5. selhání části zdroje nezpůsobí falešnou hromadnou deaktivaci,
6. vzdálenosti od Prahy jsou vypočtené a cachované,
7. přihlásit se může pouze povolený Google účet,
8. tabulka, mapa, detail, filtry, oblíbené, poznámky a graf ceny fungují na mobilu i desktopu,
9. dashboard zobrazuje korektní medián pro aktuální filtry a historické běhy,
10. fotografie oblíbené nabídky lze archivovat v neveřejném Cloud Storage,
11. neúspěšný běh vytvoří dohledatelný log a e-mailové upozornění,
12. automatické testy procházejí,
13. existuje postup lokálního spuštění, nasazení, migrace a obnovy,
14. odhadovaný běžný účet nepřekračuje 300 Kč měsíčně bez předchozího upozornění.

## 15. Implementační fáze

### Fáze 0 – ověření zdroje a nákladů

- Zachytit aktuální anonymizované vzorky seznamu a detailu pro chatu i chalupu.
- Ověřit filtry, stránkování, limity a dostupná pole.
- Změřit počet a velikost fotografií na reprezentativním vzorku.
- Ověřit přesný GCP odhad v kalkulátoru a dostupnost `db-f1-micro` v regionu.
- Nastavit billing budget a základní API kvóty před produkčním provozem.

### Fáze 1 – datová vrstva a scraper

- Navrhnout PostgreSQL schéma a migrace.
- Implementovat odolného klienta, parser a validaci.
- Implementovat běhy, pozorování, události a stavový automat nabídek.
- Přidat raw storage, strukturované logy a testy.

### Fáze 2 – vzdálenosti a API

- Přidat vzdušnou vzdálenost.
- Integrovat a cachovat Google Routes.
- Vytvořit FastAPI endpointy, filtrování, stránkování a autentizaci.

### Fáze 3 – frontend

- Přehled, historický medián, tabulka, mapa a detail.
- Historie ceny, stavy, oblíbené a poznámky.
- Responzivita, přístupnost a frontendové testy.

### Fáze 4 – cloudový provoz

- Terraform, kontejnery, Cloud Run services a job.
- Cloud Scheduler, secrets, monitoring a upozornění.
- Nasazení, smoke test a kontrola prvního kompletního běhu.
- Ověření reálného měsíčního run-rate nákladů.

## 16. Stav původního repozitáře a pokyny k refaktoringu

Původní implementace je užitečná jako znalost zdrojového API, nikoli jako závazná cílová architektura. Při prvním průzkumu byly zjištěny zejména tyto problémy:

- pevně zadané lokální cesty v `run.py` a `run_scheduled.py`,
- SQLite a souborové mezikroky CSV/JSON,
- datový model orientovaný na byty s mnoha povinnými poli,
- konfigurace obsahuje `33 = chata`, ale ne `43 = chalupa`,
- stránkování filtrovaného dotazu vychází z počtu všech nabídek,
- nová HTTP session se vytváří pro jednotlivé requesty,
- obecné `except` bloky potlačují chyby,
- detail nabídky se po prvním vložení průběžně neaktualizuje,
- nesleduje se bezpečně stažení a návrat nabídky,
- pravděpodobný nesoulad mezi externím kódem nabídky a interním FK v historii cen,
- chybí frontend, API, migrace, cloudová infrastruktura a automatizované testy.

Kód může být výrazně refaktorován. Je vhodnější zachovat ověřené poznatky o datech a napsat testovatelnou modulární pipeline než mechanicky převádět starou strukturu do cloudu.

Staré notebooky a bytová data nejsou zdrojem pro produkční migraci. Mohou zůstat jako archiv, dokud uživatel výslovně nerozhodne jinak.

## 17. Pravidla pro budoucí rozhodování agentů

Při nejasnosti preferovat v tomto pořadí:

1. správnost a neztracení historických dat,
2. bezpečné chování vůči zdroji a ochranu soukromí,
3. provozní náklady pod stanoveným limitem,
4. jednoduchost pro jednoho uživatele,
5. pozorovatelnost a testovatelnost,
6. snadné budoucí rozšíření bez předčasné komplexity.

Agent nesmí bez explicitního souhlasu:

- rozšířit scraping na jiné typy nemovitostí nebo portály,
- zavést službu s významným fixním měsíčním nákladem,
- zveřejnit aplikaci, bucket nebo databázi,
- migrovat stará bytová data,
- začít archivovat všechny fotografie,
- obejít ochrany nebo omezení zdrojové služby,
- smazat historická produkční data,
- změnit význam metriky mediánu.

Pokud se externí API nebo GCP služba změní, agent má nejprve doložit dopad na správnost, cenu a rozsah a teprve poté navrhnout změnu tohoto dokumentu.

## 18. Dosud odložená rozhodnutí

Následující položky nejsou blokátorem MVP a rozhodnou se při implementaci na základě měření:

- přesné souřadnice referenčního bodu Prahy,
- konkrétní poskytovatel mapových dlaždic,
- přesný práh pro upozornění na podezřelý propad počtu výsledků,
- přesná sada typovaných polí po analýze aktuálních payloadů chat a chalup,
- doba uchování fotografií po odebrání nabídky z oblíbených,
- zda budou frontend a backend dva Cloud Run services, nebo jeden úspornější deployment,
- konkrétní CI služba podle hostingu repozitáře.

Tato rozhodnutí musí respektovat cíle, bezpečnost a rozpočtové mantinely výše.

## 19. Údržba dokumentu

Každá významná změna produktu, datového modelu, cloudové architektury, retenční politiky nebo rozpočtu musí být promítnuta sem ve stejném pull requestu či sadě změn jako implementace.

Při aktualizaci se mají potvrzená rozhodnutí měnit přímo v příslušné sekci. Důležité nahrazené rozhodnutí je vhodné stručně zaznamenat v samostatném changelogu nebo ADR, aby bylo zřejmé, proč se architektura změnila.
