# Live checks

Explicitně spouštěné, nízkofrekvenční kontroly Sreality a později Google Routes. Nesmějí být součástí výchozího `python -m pytest` ani běžného CI běhu.

Každá live kontrola musí mít vlastní opt-in marker nebo samostatný příkaz, omezený počet requestů a bezpečné zacházení s odpověďmi.

