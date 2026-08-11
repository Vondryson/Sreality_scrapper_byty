# Discovery reports

Technické reporty z validační fáze M0. Reporty smějí obsahovat pouze agregované hodnoty, schéma, hashe externích ID a jiné informace nezbytné pro návrh systému.

Nesmějí obsahovat:

- credentials nebo interní tokeny,
- celé texty inzerátů,
- osobní údaje prodejců,
- stažené fotografie,
- raw API payloady.

Původní JSON endpointy používané scraperem z roku 2024 nyní vracejí HTTP 404. Validace proto kontroluje veřejný strukturovaný `__NEXT_DATA__` payload serverově renderovaných vyhledávacích stránek. Spouští se explicitně:

```powershell
python scripts/validate_sreality_api.py --output docs/discovery/sreality-api-validation-YYYY-MM-DD.json
```

Skript provede šest read-only požadavků pomocí systémového `curl` s TLS validací a prodlevou. Uloží pouze technický souhrn a hashe externích ID.

Agregovaný profil polí a fotografií:

```powershell
python -m scripts.profile_sreality_data --output docs/discovery/sreality-data-profile-YYYY-MM-DD.json --sample-per-category 5
```

Výchozí profil načte pět detailů z každé kategorie a jednu veřejnou 800×600 WebP variantu obrázku na nabídku. Popisy, kontakty, ID, lokality, URL ani image bytes neukládá.
