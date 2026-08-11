# Verzovaný referenční bod Prahy

- Stav: přijato
- Datum: 2026-08-11

## Kontext

Vzdušná i silniční vzdálenost musí používat jeden srozumitelný počátek. Skrytá
souřadnice rozptýlená v kalkulátorech by znemožnila spolehlivě poznat, podle
které definice Prahy byl historický výsledek vypočten.

Specifikace požaduje město Praha, nikoli soukromou adresu uživatele. Proto je
vhodný veřejný, dlouhodobě identifikovatelný bod v centru města. Oficiální web
hlavního města uvádí Magistrát hl. m. Prahy na adrese Mariánské náměstí 2,
Praha 1. Adresní místo RÚIAN 21714746 má publikované WGS84 souřadnice přibližně
50.0871072 N, 14.4178281 E.

Zdroje:

- https://praha.eu/informacni-stredisko-magistratu-hl-m-prahy
- https://vdp.cuzk.gov.cz/vdp/ruian/adresnimista/21714746

## Rozhodnutí

Výchozí reference verze 1 je:

- klíč `praha_marianske_namesti`,
- verze `1`,
- WGS84 `50.0871072, 14.4178281`,
- popisek `Praha – Mariánské náměstí`.

Jediným zdrojem aplikační konfigurace je neměnný registr v
`sreality_tracker.domain.reference_points`. Cache identita obsahuje klíč,
kladnou celočíselnou verzi a SHA-256 normalizovaných souřadnic na sedm
desetinných míst.

Souřadnice se pod existující verzí nesmějí měnit. Nový referenční bod nebo
úprava souřadnic musí dostat vyšší verzi a historické výsledky zůstanou
rozlišitelné v `listing_distances`.

## Důsledky

- Všechny kalkulátory a poskytovatelé tras dostanou stejný explicitní objekt.
- Změna reference automaticky změní cache identitu a vyžádá nový výpočet.
- Bod reprezentuje administrativní centrum, nikoli individuální místo odjezdu;
  uživatelsky konfigurovatelný domov není součást MVP.
- Mariánské náměstí může mít dopravní omezení. Při integraci Routes se bude
  ověřovat, zda provider bod bezpečně přichytí k dostupné komunikaci; případná
  změna bude verze 2, nikoli tichá oprava verze 1.
