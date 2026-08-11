# Live checks

Explicitně spouštěné, nízkofrekvenční kontroly Sreality a Google Routes. Nesmějí být součástí výchozího `python -m pytest` ani běžného CI běhu.

Každá live kontrola musí mít vlastní opt-in marker nebo samostatný příkaz, omezený počet requestů a bezpečné zacházení s odpověďmi.

Živý smoke test nového HTTP klienta provede dva sekvenční requesty (jednu chatu
a jednu chalupu) s prodlevou nejméně 0,75 s:

```powershell
$env:SREALITY_RUN_LIVE_TESTS = "1"
python -m pytest -m live backend/tests/live/test_sreality_client_live.py
```

Google Routes live test provede přesně jeden `TRAFFIC_UNAWARE` Essentials
request Praha–Brno. Token musí být krátkodobý a po testu odstraněný z procesu:

```powershell
$env:SREALITY_ROUTES_PROJECT_ID = "sreality-scrapper-504307"
$env:SREALITY_ROUTES_ACCESS_TOKEN = gcloud auth print-access-token --configuration=sreality-tracker
$env:SREALITY_RUN_ROUTES_LIVE_TESTS = "1"
python -m pytest -m live backend/tests/live/test_google_routes_live.py
Remove-Item Env:SREALITY_ROUTES_ACCESS_TOKEN
Remove-Item Env:SREALITY_RUN_ROUTES_LIVE_TESTS
```
