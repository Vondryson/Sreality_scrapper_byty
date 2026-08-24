# Cloud SQL záloha a izolovaná obnova

Tento postup obnovuje produkční automatickou zálohu do **nové dočasné instance**.
Nikdy nepoužívá `sreality-tracker-postgres` jako cíl obnovy. Skutečný restore drill
vytváří placenou Cloud SQL instanci a její vytvoření i pozdější smazání proto
vyžaduje samostatné schválení vlastníka. Provedení drillu patří do `M5-02`.

## Garantovaný základ

Terraform u produkční PostgreSQL 16 instance v `europe-west1` vynucuje:

- denní automatickou zálohu od `00:00` UTC;
- sedm uložených záloh;
- ochranu instance proti smazání v Terraformu i Cloud SQL API;
- maximální automatický růst disku na 15 GiB;
- bez PITR, protože MVP používá úsporný backup režim.

RPO je proto nejvýše přibližně 24 hodin plus doba dokončení zálohy. RTO není pro
MVP garantované; při drillu se změří od vytvoření cílové instance po dokončení
datové kontroly.

## 1. Předpoklady a read-only kontrola

Použij osobní gcloud konfiguraci a vždy uveď cílový projekt explicitně:

```powershell
gcloud config configurations activate sreality-tracker
gcloud config get-value account
gcloud config get-value project
gcloud sql instances describe sreality-tracker-postgres `
  --project sreality-scrapper-504307 `
  --format='yaml(name,region,databaseVersion,state,settings.backupConfiguration)'
gcloud sql backups list `
  --instance sreality-tracker-postgres `
  --project sreality-scrapper-504307 `
  --limit 7 `
  --format='table(id,status,startTime,endTime,location)'
```

Zastav se, pokud účet/projekt nesouhlasí, instance není `RUNNABLE`, poslední
záloha nemá stav `SUCCESSFUL`, je starší než 48 hodin nebo není v očekávaném
regionu. Zapiš ID vybrané zálohy, její `endTime` a čas začátku drillu do protokolu.

## 2. Vytvoření izolovaného cíle

V Google Cloud Console otevři **Cloud SQL → Create instance → PostgreSQL** a
vytvoř jednorázovou instanci s přesným jménem schváleným v protokolu, například
`sreality-tracker-restore-drill-20260823`. Musí mít:

- projekt `sreality-scrapper-504307`, region `europe-west1` a PostgreSQL 16;
- Enterprise, zonální `db-f1-micro`, 10 GiB SSD;
- Cloud SQL connector enforcement a žádné aplikační Cloud Run napojení;
- vypnutou deletion protection pouze proto, aby šel schválený dočasný cíl uklidit;
- žádný Scheduler, veřejnou aplikaci ani produkční DNS/IAM vazbu.

Před obnovou znovu spusť `gcloud sql instances describe <RESTORE_INSTANCE>` a
zkontroluj název, project, region a verzi. Produkční název nesmí být použit jako
`--restore-instance`.

## 3. Obnova vybrané zálohy

Po explicitním schválení placeného drillu nahraď pouze dva zástupné údaje:

```powershell
gcloud sql backups restore <BACKUP_ID> `
  --backup-instance sreality-tracker-postgres `
  --restore-instance <RESTORE_INSTANCE> `
  --project sreality-scrapper-504307
```

Příkaz nech interaktivně zobrazit cílovou instanci; potvrď ho až po poslední
kontrole, že cílem není produkce. Sleduj dokončení:

```powershell
gcloud sql operations list `
  --instance <RESTORE_INSTANCE> `
  --project sreality-scrapper-504307 `
  --limit 10 `
  --format='table(name,operationType,status,startTime,endTime,error.errors.message)'
```

Při chybě restore nepokračuj silnějším nebo jiným cílem. Ulož výstup operace a
nejdřív zjisti příčinu.

## 4. Datová kontrola bez zápisu

Připoj Cloud SQL Auth Proxy pouze k dočasné connection name na lokální port
`55432`. Databázové heslo načti ze svého lokálního správce secretů; nevypisuj ho
do terminálu, dokumentace ani protokolu.

V `psql` nejprve vynucuj read-only transakci a proveď:

```sql
BEGIN READ ONLY;
SELECT version_num FROM alembic_version;
SELECT count(*) AS listings FROM listings;
SELECT count(*) AS scrape_runs FROM scrape_runs;
SELECT id, status, finished_at
FROM scrape_runs
ORDER BY started_at DESC
LIMIT 5;
ROLLBACK;
```

Drill je úspěšný pouze pokud:

- připojení míří na connection name dočasné instance;
- schéma obsahuje očekávanou Alembic revizi;
- počty tabulek jsou nenulové a odpovídají času vybrané zálohy;
- poslední běhy lze přečíst bez databázové nebo storage chyby;
- produkční Cloud Run revize, job, secret a DB instance nebyly změněny.

Zapiš čas dokončení a vypočtené RPO/RTO. Neukládej řádky s osobními poznámkami,
OAuth údaje ani databázové heslo.

## 5. Úklid

Nejdřív vypni lokální proxy. V Console otevři přesnou dočasnou instanci, ověř její
název i connection name proti protokolu a vyžádej si schválení smazání. Smazání
je nevratné a nesmí se použít glob, prefix ani proměnná, která může být prázdná.

Po schváleném smazání ověř:

```powershell
gcloud sql instances list `
  --project sreality-scrapper-504307 `
  --format='table(name,region,state)'
terraform plan -var 'monitoring_email=<MONITORING_EMAIL>' -detailed-exitcode
```

Výsledný Terraform exit code musí být `0` (žádný drift). Protokol drillu obsahuje
backup ID a časy, název dočasné instance, výsledek čtyř read-only kontrol, RPO,
RTO, potvrzení úklidu a odkaz na incident, pokud některý krok selhal.
