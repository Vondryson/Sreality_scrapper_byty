# Terraform pro GCP

Terraform spravuje výhradně osobní projekt `sreality-scrapper-504307`. Pracovní
projekt `maiven-lab-dev` je mimo rozsah. Kořenový modul záměrně odmítne jiné project
ID i region než `europe-west1`.

## 1. Bootstrap remote state

GCS backend vyžaduje existující bucket, proto je state bucket izolovaný v modulu
`bootstrap`. Modul používá lokální state pouze pro tento jeden bucket; lokální state
je ignorovaný Gitem a neobsahuje aplikační secrets.

```powershell
cd infra/terraform/bootstrap
terraform init
terraform plan -out bootstrap.tfplan
terraform apply bootstrap.tfplan
```

Bucket má uniform bucket-level access, public access prevention, versioning a
`prevent_destroy`. Jeho jméno je `sreality-scrapper-504307-tfstate`.

## 2. Inicializace hlavního modulu

Po vytvoření bucketu:

```powershell
cd ..
Copy-Item backend.hcl.example backend.hcl
terraform init -backend-config=backend.hcl
terraform plan -out production.tfplan
```

`backend.hcl` neobsahuje secret, ale je lokální provozní konfigurace a není verzovaný.
Plán před aplikací musí být ručně zkontrolovaný; neočekávané `destroy` nebo `replace`
akce znamenají zastavit a zjistit příčinu.

Produkční alerty se zapnou pouze při explicitně zadaném příjemci. E-mail není
secret, ale není natvrdo uložený v repozitáři:

```powershell
terraform plan -var 'monitoring_email=owner@example.com' -out production.tfplan
```

Po prvním apply musí příjemce potvrdit ověřovací zprávu Google Cloud Monitoring.
Bez potvrzení může být kanál vytvořený, ale upozornění nemusí dorazit.

## Datový základ

Kořenový modul vytváří jednu zonální PostgreSQL 16 instanci a jeden regionální
aplikační bucket:

- Cloud SQL používá `db-f1-micro`, Enterprise edition, 10GiB SSD s automatickým
  růstem omezeným na 15 GiB, denní zálohy a sedm uložených backupů bez PITR;
- Terraform i Cloud SQL API chrání instanci před smazáním, přímá databázová
  spojení mimo Cloud SQL Auth Proxy/connector jsou odmítnutá;
- aplikační bucket má uniform bucket-level access, vynucenou prevenci veřejného
  přístupu a sedmidenní soft-delete ochranu;
- objekty pod `raw/` se po 90 dnech lifecycle pravidlem odstraní, zatímco
  `favorite-images/` nemá automatickou expiraci.

Databázový uživatel ani heslo se zde nevytvářejí, protože by se citlivá hodnota
dostala do Terraform state. Service accounts, IAM a Secret Manager postup doplní
`M4-04`; produkční migrace se ověří až s touto identitou.

## Runtime identity a secrets

API, frontend a scraper používají tři samostatné service accounts. API a scraper
smějí připojit pouze Cloud SQL connector; k aplikačnímu bucketu mají pouze kombinaci
`objectCreator` + `objectViewer`, takže runtime nemůže objekty mazat ani přepisovat.
Scraper navíc smí spotřebovávat projektovou API kvótu pro Google Routes. Frontend
nemá přístup k databázi, bucketu ani aplikačním secretům.

Terraform vytváří prázdné, regionálně replikované Secret Manager kontejnery pro
databázové URL, Google OAuth konfiguraci, owner e-mail a session secret. Záměrně
nevytváří `google_secret_manager_secret_version`: hodnoty se naplní mimo Terraform
a nikdy se proto neobjeví v konfiguraci, plánu ani state. API získá pouze svých pět
secretů, scraper pouze databázové URL.

## Autentizace

Lokálně Terraform používá Application Default Credentials osobního účtu. Doporučený
postup je samostatná gcloud konfigurace `sreality-tracker`:

```powershell
gcloud config configurations activate sreality-tracker
gcloud auth application-default login
gcloud auth application-default set-quota-project sreality-scrapper-504307
```

Do `.tf`, `.tfvars`, backend konfigurace ani state se nevkládají access tokeny,
OAuth client secret nebo databázová hesla.

## Kontroly bez změny cloudu

```powershell
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
terraform test
```

Produkční build, promotion immutable digestů, plán, rollback a ověření popisuje
[deployment runbook](../../docs/runbooks/production-deployment.md).
Zálohy, izolovanou obnovu a důkazní checklist popisuje
[Cloud SQL restore runbook](../../docs/runbooks/cloud-sql-restore.md).
