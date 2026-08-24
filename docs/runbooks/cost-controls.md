# Rozpočtové pojistky a kontrola nákladů

Tento runbook pokrývá produkční projekt `sreality-scrapper-504307` a osobní billing
account `019FD9-252204-7DCB11`. ID billing účtu není credential; žádný token,
secret ani fakturační údaj se do repozitáře neukládá.

## Aktivní mantinely

- Měsíční budget je 300 Kč a používá `CURRENT_SPEND` prahy 200 a 300 Kč.
- Upozornění míří na ověřený Cloud Monitoring e-mailový kanál vlastníka.
- `ComputeRoutes` má projektový limit 300 požadavků za den. Aplikace navíc stejný
  limit vynucuje lokálně a výsledky trvale cachuje.
- Log bucket `_Default` uchovává data 30 dní.
- Cloud Run služby mají `min_instance_count=0`, nejvýše jednu instanci; scraper má
  jeden task, nulový retry a běží jednou týdně.
- Cloud SQL zůstává single-zone `db-f1-micro`, 10 GiB SSD, nejvýše 15 GiB, bez HA
  a read repliky. Raw objekty expirují po 90 dnech a Artifact Registry maže staré
  neoznačené images.

Budget alert není tvrdý limit a nezastaví Cloud SQL ani jinou službu. Překročení
300 Kč vyžaduje analýzu podle služby; výchozí reakce je zastavit další placené
změny a připravit návrat PostgreSQL do lokálního provozu, dokud vlastník neschválí
vyšší rozpočet.

## První převzetí existujících guardrailů do state

Před importem musí být aktivní osobní gcloud konfigurace a inicializovaný produkční
GCS backend. Tyto dva importy nemění cloudové nastavení, pouze převezmou již
existující prostředky do Terraform state:

```powershell
terraform -chdir=infra/terraform import `
  'google_logging_project_bucket_config.default' `
  'projects/sreality-scrapper-504307/locations/global/buckets/_Default'

terraform -chdir=infra/terraform import `
  'google_service_usage_consumer_quota_override.routes_daily_requests' `
  'projects/545468906541/services/routes.googleapis.com/consumerQuotaMetrics/routes.googleapis.com%2Fcompute_routes_requests/limits/%2Fd%2Fproject/consumerOverrides/Cg1RdW90YU92ZXJyaWRl'
```

Před vytvořením budgetu nejprve zapnout deklarovanou API a zkontrolovat, zda na
účtu nevznikl mezitím ekvivalentní budget mimo Terraform:

```powershell
gcloud services enable billingbudgets.googleapis.com `
  --project=sreality-scrapper-504307

gcloud billing budgets list `
  --billing-account=019FD9-252204-7DCB11
```

Pokud existuje budget pro tento projekt se stejnými prahy, apply se zastaví a
existující budget se nejprve importuje. Nevytváří se duplicitní upozornění.

## Bezpečný plán a apply

```powershell
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform test
terraform -chdir=infra/terraform plan -out production.tfplan
terraform -chdir=infra/terraform show production.tfplan
```

Povolené M4-08 změny jsou zapnutí Billing Budget API, vytvoření jediného budgetu
a případná in-place normalizace dvou importovaných guardrailů. Jakýkoli destroy,
replace, druhý budget nebo změna runtime infrastruktury znamená zastavit. Uložený
plán se aplikuje až po výslovném schválení vlastníka.

## Produkční ověření

```powershell
gcloud billing budgets list `
  --billing-account=019FD9-252204-7DCB11 `
  --format='table(displayName,amount.specifiedAmount.currencyCode,amount.specifiedAmount.units)'

gcloud logging buckets describe _Default `
  --location=global `
  --project=sreality-scrapper-504307 `
  --format='value(retentionDays)'
```

V Google Cloud Console se u Routes API ověří limit
`Directions - ComputeRoutes per request quota` pro jednotku `1/d/{project}`;
effective limit musí být `300`. Budget musí být omezen jen na projekt
`sreality-scrapper-504307`, v CZK, s prahy 66,67 % a 100 %, což odpovídá přesně
200 a 300 Kč.

## Aktuální měsíční run-rate podle služby

Stav k 24. srpnu 2026 vychází z reálně nasazené konfigurace a reprodukovatelného
modelu `scripts/calculate_gcp_costs.py`. Jde o očekávaný run-rate bez případné DPH,
nikoli o již uzavřenou fakturu. První úplný fakturační měsíc jej musí nahradit
skutečnými hodnotami z Billing reportu.

| Služba | Běžný odhad USD | Běžný odhad Kč | Důvod |
|---|---:|---:|---|
| Cloud SQL compute | 7,67 | 184,09 | `db-f1-micro` běží nepřetržitě |
| Cloud SQL SSD | 3,40 | 81,66 | provisionovaných 10 GiB |
| Cloud SQL backups | 0,16 | 3,84 | model 2 GiB a sedm denních záloh |
| Cloud Storage | 0,20 | 4,80 | raw payloady a oblíbené fotografie |
| Artifact Registry | 0,05 | 1,20 | images nad případný free tier |
| Cloud Run | 0,00 | 0,00 | nízká zátěž, scale-to-zero |
| Scheduler, Routes, Logging/Monitoring, Secrets | 0,00 | 0,00 | očekáváno v bezplatných limitech |
| **Celkem** | **11,48** | **275,58** | plánovací kurz 24 Kč/USD |

Konzervativní scénář je 12,77 USD, přibližně 306,55 Kč. Největší riziko je Cloud
SQL; Routes se při cache a limitu 300/den nemají stát placenou položkou.

## Pravidelný audit

První měsíc kontrolovat Billing report týdně, poté jednou měsíčně:

1. Nastavit scope pouze na projekt `sreality-scrapper-504307`.
2. Období nastavit na aktuální kalendářní měsíc, kredity zahrnout stejně jako
   budget a seskupit náklady podle služby.
3. Zapsat skutečné CZK pro Cloud SQL, Storage, Artifact Registry, Cloud Run,
   Routes, Logging/Monitoring, Scheduler a Secret Manager.
4. Porovnat skutečnost s tabulkou výše a vysvětlit každou novou placenou službu
   nebo odchylku větší než 20 %.
5. Při překročení 200 Kč zkontrolovat forecast. Při dosažení 300 Kč zastavit nové
   placené změny a rozhodnout o lokálním PostgreSQL nebo explicitně novém budgetu.

Billing API bez zapnutého BigQuery exportu neposkytuje spolehlivý detail skutečných
nákladů po službách pro automatický skript. Kvůli rozpočtu se samostatný exportní
dataset v MVP nezavádí; důkazem je Billing report po celém fakturačním měsíci.
