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
```

