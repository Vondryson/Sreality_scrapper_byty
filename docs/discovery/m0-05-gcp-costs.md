# M0-05 – GCP náklady a technické předpoklady

Datum ověření: 2026-08-02  
Cílový projekt: `sreality-scrapper-504307`  
Region: `europe-west1` (Belgie)

## Výsledek

Navržená architektura je technicky dostupná, ale s trvale běžícím Cloud SQL je rozpočet 200–300 Kč měsíčně velmi těsný. Kontrolovaný základní scénář vychází přibližně na **276 Kč/měsíc bez případné DPH**. Konzervativní scénář je přibližně **307 Kč/měsíc bez případné DPH**. Cloud SQL tvoří přibližně 98 % základního odhadu.

Doporučení je pokračovat ve vývoji cloudově kompatibilní varianty, ale cloudové prostředky zatím nevytvářet. Před nasazením je nutné potvrdit billing cílového projektu, způsob účtování daně a cenu konfigurace v Google Cloud Pricing Calculatoru. Po nasazení má následovat jeden celý měřený fakturační měsíc; pokud run-rate přesáhne 300 Kč, aplikace přejde na lokální PostgreSQL, nebo uživatel explicitně schválí vyšší rozpočet.

Brána M0 zatím není uzavřena: projekt, billing a aktivované služby nebylo možné read-only ověřit kvůli lokální chybě důvěryhodnosti TLS při obnově OAuth tokenu `gcloud`. Aktivní `gcloud` účet i projekt navíc patří jinému pracovnímu prostředí, proto nebyla jejich konfigurace změněna.

## Předpoklady kalkulace

- 730,5 hodiny v průměrném měsíci.
- Plánovací kurz 24 Kč/USD. Jde o konzervativní interní kurz, nikoli garantovaný kurz faktury.
- Ceny jsou bez daní; případná česká DPH může výslednou částku zvýšit.
- Bez HA, read repliky, load balanceru, IAP a Serverless VPC Access connectoru.
- Cloud Run používá request-based billing, `min-instances=0` a omezený počet maximálních instancí.
- Bezplatné limity nejsou spotřebované jinými projekty na stejném billing accountu.
- PostgreSQL data se v prvních měsících vejdou do 2 GiB; provisionovaný disk má povinné minimum 10 GiB.
- Raw payloady mají lifecycle 90 dní a fotografie se archivují jen u oblíbených nabídek.
- Routes se počítají jen pro novou nebo přemístěnou nabídku a výsledek se trvale cachuje.

## Měsíční model

| Služba | Základ USD | Konzervativně USD | Poznámka |
|---|---:|---:|---|
| Cloud SQL `db-f1-micro` compute | 7,67 | 7,67 | 0,0105 USD/h; shared-core bez SLA |
| Cloud SQL 10 GiB SSD | 3,40 | 3,40 | 0,000465753 USD/GiB/h; minimum 10 GiB |
| Cloud SQL backups | 0,16 | 0,80 | model 2 až 10 GiB skutečně použitých záloh |
| Cloud Storage | 0,20 | 0,40 | raw data, oblíbené fotografie a operace |
| Artifact Registry | 0,05 | 0,15 | po bezplatných 0,5 GB; nutný cleanup images |
| Cloud Run services a job | 0,00 | 0,10 | nízká zátěž se má vejít do free tieru |
| Cloud Scheduler | 0,00 | 0,00 | jeden job z limitu tří bezplatných jobů |
| Google Routes Essentials | 0,00 | 0,00 | pouze při cache a dodržení limitu 10 000/měsíc |
| Logging a Monitoring | 0,00 | 0,00 | hluboko pod 50 GiB logů, retence 30 dní |
| Secret Manager | 0,00 | 0,00 | do 6 aktivních verzí a 10 000 access operací |
| Rezerva na drobné operace/egress | 0,00 | 0,25 | bezpečnostní rezerva |
| **Celkem** | **11,48** | **12,77** | **cca 276 až 307 Kč bez daně** |

Základní výpočet je reprodukovatelný skriptem `scripts/calculate_gcp_costs.py`.

## Největší nákladová rizika

### Routes bez cache

Profil trhu našel 3 583 aktuálních nabídek. Jednorázový bootstrap se vejde pod bezplatných 10 000 výpočtů. Kdyby se však trasa přepočítala pro všechny nabídky každý týden, vzniklo by přibližně 15 514 výpočtů měsíčně. Přibližně 5 514 placených výpočtů by při 5 USD/1 000 znamenalo dalších zhruba 27,57 USD, tedy asi 662 Kč měsíčně.

Povinná ochrana:

- cache podle referenčního bodu a souřadnic nabídky,
- přepočet jen při nových nebo změněných souřadnicích,
- serverová API key restriction,
- jednorázový bootstrap s dočasnou kvótou nejvýše 4 000/den,
- po bootstrapu snížit kvótu na 300/den a sledovat měsíční usage.

### Cloud SQL

Cloud SQL se neumí škálovat na nulu. Disk nelze běžně zmenšit a automatické navýšení je trvalé. Produkční konfigurace proto musí být single-zone `db-f1-micro`, bez HA a replik, s 10GiB diskem a s limitem automatického růstu nejvýše 15 GiB. Pro MVP stačí denní automatická záloha s krátkou retencí; PITR se zapne až po změření jeho storage dopadu.

### Daně a sdílené free tiery

Google uvádí ceny bez garance lokální fakturační částky. Je nutné ověřit, zda je billing account veden jako osobní nebo podnikatelský a zda se přičítá DPH. Free tiery Cloud Run, Scheduler a Secret Manager se mohou sdílet přes billing account; odhad předpokládá, že je nespotřebuje jiný projekt.

## Rozpočtové pojistky pro M4

- běžný budget s upozorněními při 200 Kč, 250 Kč a 300 Kč,
- Cloud Run spend cap v Preview jen pokud bude pro účet dostupný; nechrání Cloud SQL,
- `min-instances=0`, maximálně 2 instance pro každý webový service a maximálně 1 task scraperu,
- Routes key pouze na serveru, API restriction a výše popsané kvóty,
- 90denní lifecycle raw bucketu a archivace fotografií jen pro oblíbené,
- Artifact Registry cleanup policy ponechávající jen několik posledních images,
- logy bez raw payloadů a s 30denní retencí,
- týdenní kontrola nákladů první měsíc a potom měsíční kontrola podle služby.

Budget alert sám o sobě není tvrdý limit. Nové GCP spend caps jsou v Preview a vztahují se jen na vybrané služby; persistentní compute a storage, zejména Cloud SQL, se jejich dosažením nezastaví.

## Stav technických předpokladů

| Kontrola | Stav | Důkaz / další krok |
|---|---|---|
| Cloud Run v `europe-west1` | potvrzeno | region je uveden v aktuálním ceníku Cloud Run |
| Cloud SQL a `db-f1-micro` v `europe-west1` | potvrzeno ceníkem | před tvorbou ještě potvrdit volbu v Calculatoru/Console |
| Regionální Cloud Storage | potvrzeno | Standard storage je pro Belgii dostupné |
| Scheduler, Logging, Secret Manager, Routes | potvrzeno veřejnou dokumentací | globální/regionálně nezávislé dle služby |
| lokální Google Cloud SDK | potvrzeno | nainstalovaná verze 549.0.0 |
| lokální Terraform | nepotvrzeno | Terraform není nainstalován; řeší M4-02 |
| existence cílového projektu | uživatelský vstup | read-only `gcloud` kontrola selhala před přístupem k API |
| billing připojený k projektu | **nepotvrzeno** | ověřit v Console po přihlášení osobním účtem |
| aktivované API a kvóty | **nepotvrzeno** | ověřit až po bezpečném přihlášení k cílovému projektu |
| daňový režim a fakturační měna | **nepotvrzeno** | zkontrolovat profil billing accountu |

## Kroky nutné k uzavření M0-05

Po přihlášení správným osobním Google účtem ověřit bez vytváření prostředků:

1. projekt ID je přesně `sreality-scrapper-504307`,
2. projekt má aktivní billing account a je znám jeho daňový režim,
3. v Pricing Calculatoru je stále dostupná single-zone konfigurace `db-f1-micro`, 10 GiB bez HA v Belgii,
4. jsou dostupné nebo aktivovatelné Cloud Run, Cloud Run Admin, Cloud SQL Admin, Cloud Storage, Scheduler, Secret Manager, Artifact Registry, Logging a Routes API,
5. Routes billing/free cap se nesdílí s jiným významným projektem,
6. uživatel potvrdí podmíněné cloudové pokračování s očekáváním přibližně 276 Kč bez daně a s fallbackem na lokální provoz.

## Oficiální zdroje

- [Cloud SQL pricing](https://cloud.google.com/sql/pricing)
- [Cloud SQL minimum disk size](https://cloud.google.com/sql/docs/postgres/admin-api/rest/v1/instances)
- [Cloud Run pricing](https://cloud.google.com/run/pricing)
- [Cloud Storage pricing](https://cloud.google.com/storage/pricing)
- [Cloud Scheduler pricing](https://cloud.google.com/scheduler/pricing)
- [Google Maps Platform pricing](https://developers.google.com/maps/billing-and-pricing/pricing)
- [Google Cloud Observability pricing](https://cloud.google.com/products/observability/pricing)
- [Secret Manager pricing](https://cloud.google.com/secret-manager/pricing)
- [Cloud Billing budgets](https://cloud.google.com/billing/docs/how-to/budgets)
- [Cloud Billing spend caps (Preview)](https://cloud.google.com/billing/docs/how-to/budgets-spend-caps)
