# M0-04 – Profil polí a fotografií

- Datum měření: 2026-08-02
- Zdroj: veřejný Next.js `__NEXT_DATA__` SSR payload
- Vzorek: 5 nejnovějších chat a 5 nejnovějších chalup
- Requesty: 2 vyhledávací stránky, 10 detailů a 10 obrázků
- Strojový report: `sreality-data-profile-2026-08-02.json`

## Omezení vzorku

Jde o malý nereprezentativní vzorek nejnovějších nabídek, nikoli populační statistiku. Hodnoty slouží k návrhu schématu a řádovému odhadu úložiště. Nejsou podkladem pro tržní analýzu ani rozhodnutí o koupi.

## Zjištění pro datový model

- Detail má 29 stabilně přítomných top-level polí. Všech deset detailů obsahovalo samostatný objekt `params` se zhruba 70 známými klíči.
- Mnoho parametrů je vždy přítomných jako klíč, ale často mají hodnotu `NULL`. Databáze proto nesmí používat plošné `NOT NULL` ani náhradní text `"-"`.
- `estateArea` bylo numerické ve všech 10 případech a reprezentuje plochu pozemku.
- `params.usableArea` bylo numerické ve všech 10 případech.
- `params.buildingArea` bylo vyplněné jen v 5 z 10 případů. Musí být nullable a nesmí nahrazovat užitnou plochu.
- `priceCzk` i `priceCzkPerSqM` mohou mít hodnotu `0`. Nula se musí interpretovat jako neuvedená/cena na vyžádání podle doprovodných polí, nikoli jako běžná cena. Do mediánu nesmí vstupovat jako nula.
- Codebook hodnoty mají tvar objektu `{"name": ..., "value": ...}`, nikoli prostého integeru.
- Doporučený model: typované sloupce pro identitu, kategorie, stav, cenu, klíčové plochy, lokalitu a analytické filtry; vedle nich JSONB snapshot pro úplný a proměnlivý parametrický kontext.

## Číselné varianty ve vzorku

| Pole | Vyplněno | Minimum | Medián | Maximum |
| --- | ---: | ---: | ---: | ---: |
| `priceCzk` | 10/10 | 0 | 2 785 000 | 6 990 000 |
| `priceCzkPerSqM` | 10/10 | 0 | 46 335,5 | 72 812 |
| `estateArea` | 10/10 | 68 | 1 159 | 36 850 |
| `params.usableArea` | 10/10 | 35 | 87 | 503 |
| `params.buildingArea` | 5/10 | 65 | 160 | 254 |

Hodnoty jsou uvedené pouze jako agregáty. Jednotlivé ceny, ID ani lokality se neukládají.

## Fotografie

| Metrika | Minimum | Medián | Maximum |
| --- | ---: | ---: | ---: |
| Počet fotografií na nabídku | 5 | 26,5 | 39 |
| Deklarovaná šířka originálu | 515 px | 1 600 px | 5 712 px |
| Deklarovaná výška originálu | 409 px | 1 066 px | 4 284 px |
| 800×600 WebP, quality 60 | 28 110 B | 96 708 B | 242 196 B |

Všech 10 měření veřejné 800×600 WebP varianty proběhlo úspěšně. Soubory byly po změření zahozeny.

Při 2 409 chatách, 1 174 chalupách, mediánu 26,5 fotografie a 96 708 B vychází hrubý bodový odhad jedné kompletní kopie trhu přibližně na 9,2 GB. Nezahrnuje verze, nové a stažené nabídky ani provozní přenosy. Plná archivace originálů by byla výrazně větší.

## Rozhodnutí

- Strategie MVP se nemění: pro všechny nabídky ukládat metadata a zdrojové URL, do Cloud Storage kopírovat pouze fotografie oblíbených nabídek.
- Pro archiv oblíbených preferovat explicitně zvolenou normalizovanou variantu, například 800×600 WebP, pokud není potřeba originální rozlišení.
- Metadata musí uchovat pořadí, deklarované rozměry, zdrojové ID/URL, stav archivace a hash.
- Budoucí plošná archivace vyžaduje nové měření churnu, egressu, operací a právních podmínek.

