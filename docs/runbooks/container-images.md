# Produkční kontejnerové images

Tento runbook pokrývá task `M4-01`. Images používají přesné Python/Node base tagy,
zamčené aplikační závislosti a běží jako neprivilegovaný uživatel `10001:10001`.

## Build

Z kořene repozitáře:

```powershell
docker build --file backend/Dockerfile --target api --tag sreality-backend:local .
docker build --file backend/Dockerfile --target scraper --tag sreality-scraper:local .
docker build --file frontend/Dockerfile --tag sreality-frontend:local `
  --build-arg SREALITY_BACKEND_URL=http://backend:8080 frontend
```

`SREALITY_BACKEND_URL` se ukládá do Next.js rewrite manifestu při buildu. Produkční
frontend image proto musí být sestaven až se známým interním URL backend Cloud Run
service. Do argumentu nepatří secret.

## Izolovaný smoke test

Smoke stack používá dočasný PostgreSQL `tmpfs`, port `127.0.0.1:13000` a nesdílí
volume s lokálním vývojovým prostředím:

```powershell
docker compose --file compose.m4-smoke.yaml build
docker compose --file compose.m4-smoke.yaml up --detach postgres backend frontend
docker compose --file compose.m4-smoke.yaml run --rm scraper
Invoke-RestMethod http://127.0.0.1:13000/api/v1/health/live
docker compose --file compose.m4-smoke.yaml ps
```

Kontrola runtime uživatele:

```powershell
docker run --rm --entrypoint id sreality-backend:m4-smoke
docker run --rm --entrypoint id sreality-scraper:m4-smoke
docker run --rm --entrypoint id sreality-frontend:m4-smoke
```

Očekávané UID/GID je `10001`. Úklid smoke stacku:

```powershell
docker compose --file compose.m4-smoke.yaml down
```

Referenční lokální build z 12. srpna 2026 měl velikosti 74,4 MiB pro API,
74,4 MiB pro scraper a 88,2 MiB pro frontend. Smoke ověřil API liveness i
readiness přes frontend proxy a read-only databázový check scraper image.

## Reprodukovatelnost

- Python runtime dependency lock je `requirements-prod.txt`; aktualizuje se přes
  `pip-compile pyproject.toml --output-file requirements-prod.txt --strip-extras`.
- Node dependency graph instaluje `npm ci` z `frontend/package-lock.json`.
- Base images jsou připnuté na patch verzi i multi-arch registry digest.
- Image neobsahují `.env`, Git metadata, testy, lokální data ani vývojové dependency.
