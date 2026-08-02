# Test layout

- `unit/` – rychlé izolované testy bez sítě a databáze,
- `integration/` – PostgreSQL a další adaptéry,
- `live/` – explicitní šetrné kontroly externích služeb.

Pytest test discovery je omezený na tento adresář. Původní notebooky a legacy skripty nejsou součástí nové testovací sady.

