# M2-03 – Google Routes live validace

Datum ověření: 2026-08-11

## Projekt a bezpečnostní pojistky

- Google Cloud projekt: `sreality-scrapper-504307`
- Project number: `545468906541`
- Ověřený osobní účet: `vondryswow@gmail.com`
- Billing: aktivní
- API: `routes.googleapis.com` zapnuté
- Compute Routes denní consumer override: `300` požadavků na projekt
- Pracovní projekt `maiven-lab-dev` nebyl použit ani změněn.

## Kontrolovaný request

Byl proveden jediný request `directions/v2:computeRoutes` s krátkodobým OAuth
tokenem. Token ani jiné credentials nejsou v repozitáři zaznamenané.

- Počátek: Praha, Mariánské náměstí v1 (`50.0871072, 14.4178281`)
- Cíl: veřejný testovací bod Brno (`49.1951, 16.6068`)
- Režim: `DRIVE`
- Routing preference: `TRAFFIC_UNAWARE`
- Field mask: `routes.distanceMeters,routes.duration`
- Výsledek: `207588` metrů, `8233s` (přibližně `137,2` minuty)
- Lokální Haversinova vzdálenost Praha–Brno: `186,221 km`

Request potvrdil funkční projekt, billing, OAuth autorizaci a tvar minimální
odpovědi. Produkční implementace musí zachovat minimální field mask, trvalou
cache podle verze reference a cílových souřadnic a nesmí při chybě externího
API znepřístupnit nabídku.
