# Kontrolovaný produkční deployment

Tento runbook pokrývá M4-06 pro osobní projekt `sreality-scrapper-504307`.
Automatický deployment z pull requestu není povolený: CI pouze testuje a každá
produkční změna vyžaduje immutable image digest, uložený Terraform plán a ruční
kontrolu akcí před aplikací.

## Předpoklady

- aktivní osobní `gcloud` konfigurace a ADC pro projekt,
- Docker Desktop a přihlášení k `europe-west1-docker.pkg.dev`,
- čisté CI pro commit, který se nasazuje,
- lokální `infra/terraform/backend.hcl` a `workloads.auto.tfvars`; oba soubory
  ignoruje Git.

## Testovací brána

Z kořene repozitáře spusťte stejné kontroly jako CI:

```powershell
python -m ruff check backend scripts
python -m ruff format --check backend scripts
python -m mypy
python -m pytest -m "not live"
Push-Location frontend
npm ci
npm run lint
npm run typecheck
npm test
npm run build
Pop-Location
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform test
```

## Build a promotion images

Pro každý deployment vytvořte nový tag odvozený z commitu; immutable tag nikdy
nepřepisujte. API a scraper sdílejí vrstvy, ale mají rozdílný target. Frontend musí
být sestaven se stabilní produkční API URL.

```powershell
$Tag = "deploy-$(git rev-parse --short=12 HEAD)-$(Get-Date -Format yyyyMMddHHmmss)"
$Registry = "europe-west1-docker.pkg.dev/sreality-scrapper-504307/sreality-tracker"
gcloud auth configure-docker europe-west1-docker.pkg.dev --quiet
docker buildx build --file backend/Dockerfile --target api --tag "$Registry/api:$Tag" --push .
docker buildx build --file backend/Dockerfile --target scraper --tag "$Registry/scraper:$Tag" --push .
docker buildx build --file frontend/Dockerfile `
  --build-arg SREALITY_BACKEND_URL=https://sreality-tracker-api-4ao6c5entq-ew.a.run.app `
  --tag "$Registry/frontend:$Tag" --push frontend
```

Získejte registry digesty přes `gcloud artifacts docker images list --include-tags`
a vložte plné `...@sha256:...` reference do ignorovaného
`infra/terraform/workloads.auto.tfvars`. Terraform validace odmítne tag nebo image
z jiného projektu/repository.

## Plán, migrace a apply

```powershell
terraform -chdir=infra/terraform plan -input=false -out=production.tfplan
terraform -chdir=infra/terraform show -no-color production.tfplan
terraform -chdir=infra/terraform apply production.tfplan
```

Plán s neočekávaným `destroy`, `replace`, změnou regionu, veřejného Storage nebo
identity se neaplikuje. Databázovou migraci spusťte před předáním provozu nové API
revizi přes Cloud SQL Auth Proxy podle databázového runbooku; downgrade schématu se
neprovádí automaticky.

## Ověření a rollback

Po deploymentu ověřte frontend, `/api/v1/health/live`, `/api/v1/health/ready`,
anonymní `401` na `/api/v1/listings`, owner login a read-only scraper `check`.
Terraform následně musí hlásit `No changes`.

Rollback aplikace znamená vrátit předchozí známé image digesty do lokálního tfvars,
zkontrolovat plán se změnou pouze příslušné Cloud Run revize a aplikovat jej.
Artifact Registry drží nejméně deset posledních verzí. Pokud nová migrace není
zpětně kompatibilní, zastavte rollback aplikace a použijte schválený DB restore
postup z M4-07.

## Scheduler a ruční běh

Scheduler `sreality-tracker-weekly` volá job každé pondělí v `03:00`
`Europe/Prague` přes vlastní service account. Nemá retry, aby nevyvolal dva drahé
scrapingové běhy při nejasné HTTP odpovědi. Owner-only API ručního běhu používá
unikátní logical key a pouze job-level custom roli pro `run` s execution override.

Před produkčním plným během lze připojení ověřit jednorázovým execution override
na argument `check`; tato kontrola nečte Sreality a nezapisuje aplikační data.
