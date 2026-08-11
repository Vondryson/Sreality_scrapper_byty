# Live checks

Explicitně spouštěné, nízkofrekvenční kontroly Sreality a později Google Routes. Nesmějí být součástí výchozího `python -m pytest` ani běžného CI běhu.

Každá live kontrola musí mít vlastní opt-in marker nebo samostatný příkaz, omezený počet requestů a bezpečné zacházení s odpověďmi.

Živý smoke test nového HTTP klienta provede dva sekvenční requesty (jednu chatu
a jednu chalupu) s prodlevou nejméně 0,75 s:

```powershell
$env:SREALITY_RUN_LIVE_TESTS = "1"
python -m pytest -m live backend/tests/live/test_sreality_client_live.py
```
