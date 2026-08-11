# Sanitized Sreality SSR fixtures

Fixtures byly vytvořeny 2. srpna 2026 z veřejného Next.js `__NEXT_DATA__` payloadu. Obsahují pouze strukturu a datové typy potřebné pro vývoj parseru.

Sanitizace nahrazuje:

- všechny původní textové hodnoty,
- externí a interní identifikátory,
- ceny a plochy,
- přesné souřadnice,
- URL obrázků a dalších médií.

Soubory `search_chata.json`, `search_chalupa.json`, `detail_chata.json` a `detail_chalupa.json` reprezentují oba cílové podtypy. `detail_missing_optional.json` je syntetický okrajový případ odvozený ze skutečné struktury, ale s odstraněnými volitelnými poli a hodnotami `NULL`.

Fixtures se negenerují během běžných testů. Explicitní aktualizace:

```powershell
python -m scripts.capture_sreality_fixtures --output-dir backend/tests/fixtures/sreality
```

Před commitem musí projít test `test_sreality_fixtures.py`, který ověřuje sanitizační metadata, cílové kategorie a absenci známých zdrojových domén.

