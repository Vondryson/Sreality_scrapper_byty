# Progres projektu Sreality Chaty Tracker

## Aktuální stav

- Poslední aktualizace: 2026-08-02
- Aktuální milník: M0 – Ověření zdroje, návrhu a nákladů
- Aktuální hlavní task: `M0-05` – blokováno potvrzením billing stavu cílového projektu
- Následující doporučený task: `M1-01` – Navrhnout finální databázové schéma z profilu dat
- Blokátory: read-only ověření projektu/billingu/API selhává při obnově `gcloud` OAuth tokenu kvůli lokálnímu TLS certifikátu; je potřeba kontrola správným osobním účtem
- Souhrn: 5 dokončeno, 0 rozpracováno, 1 blokováno, 37 čeká

## Legenda

- `[ ]` čeká,
- `[~]` rozpracováno,
- `[x]` dokončeno,
- `[!]` blokováno.

Najednou má být `[~]` označen nejvýše jeden hlavní task. Dílčí paralelní práce se popíše v poznámce hlavního tasku, aby tracker nepůsobil, že existuje více vlastníků kritické cesty.

## Dokumentace a plánování

- [x] `DOC-01` – Prozkoumat původní kód, potvrdit produktová rozhodnutí a vytvořit `specifikace.md`, `roadmap.md` a `progres.md`.

## M0 – Ověření zdroje, návrhu a nákladů

- [x] `M0-01` – Založit cílovou strukturu projektu a vývojové standardy.
- [x] `M0-02` – Ověřit živé filtry a stránkování Sreality.
- [x] `M0-03` – Zachytit anonymizované fixtures chaty a chalupy.
- [x] `M0-04` – Udělat profil polí a fotografií.
- [!] `M0-05` – Ověřit GCP náklady a technické předpoklady.

## M1 – PostgreSQL a spolehlivá datová pipeline

- [ ] `M1-01` – Navrhnout finální databázové schéma z profilu dat.
- [ ] `M1-02` – Přidat lokální PostgreSQL a migrační základ.
- [ ] `M1-03` – Zavést validovanou konfiguraci a strukturované logování.
- [ ] `M1-04` – Implementovat odolného Sreality HTTP klienta.
- [ ] `M1-05` – Implementovat tolerantní parser a doménové modely.
- [ ] `M1-06` – Implementovat raw-storage rozhraní.
- [ ] `M1-07` – Implementovat běh a ukládání pozorování.
- [ ] `M1-08` – Implementovat události a stavový automat nabídek.
- [ ] `M1-09` – Přidat bezpečnostní bránu deaktivace.
- [ ] `M1-10` – Dokončit CLI a testovací pokrytí pipeline.

## M2 – Vzdálenosti, FastAPI a zabezpečené operace

- [ ] `M2-01` – Definovat a verzovat referenční bod Prahy.
- [ ] `M2-02` – Implementovat vzdušnou vzdálenost.
- [ ] `M2-03` – Integrovat Google Routes s cache a kvótou.
- [ ] `M2-04` – Založit FastAPI aplikaci a API kontrakty.
- [ ] `M2-05` – Implementovat seznam, filtry, řazení a stránkování.
- [ ] `M2-06` – Implementovat detail, historii, mapu a medián.
- [ ] `M2-07` – Implementovat oblíbené, poznámky a archivaci fotografií.
- [ ] `M2-08` – Implementovat Google OAuth, allowlist a provozní endpointy.

## M3 – Český responzivní frontend

- [ ] `M3-01` – Založit Next.js frontend a UI základ.
- [ ] `M3-02` – Implementovat přihlášení a chráněný shell.
- [ ] `M3-03` – Implementovat dashboard mediánu.
- [ ] `M3-04` – Implementovat tabulku nabídek a URL filtry.
- [ ] `M3-05` – Implementovat mapu.
- [ ] `M3-06` – Implementovat detail a historii ceny.
- [ ] `M3-07` – Implementovat oblíbené a soukromé poznámky.
- [ ] `M3-08` – Dokončit responzivitu, přístupnost a E2E testy.

## M4 – GCP infrastruktura a automatizovaný provoz

- [ ] `M4-01` – Připravit produkční Docker images.
- [ ] `M4-02` – Založit Terraform state a základ projektu.
- [ ] `M4-03` – Vytvořit Cloud SQL, Storage a lifecycle.
- [ ] `M4-04` – Vytvořit IAM, service accounts a secrets.
- [ ] `M4-05` – Nasadit Cloud Run services a scraper job.
- [ ] `M4-06` – Přidat Scheduler, ruční běh a CI/CD.
- [ ] `M4-07` – Přidat monitoring, e-mail a obnovu.
- [ ] `M4-08` – Nastavit a ověřit rozpočtové pojistky.

## M5 – End-to-end validace a předání MVP

- [ ] `M5-01` – Ověřit první kompletní produkční běh.
- [ ] `M5-02` – Provést failure, security a restore drill.
- [ ] `M5-03` – Uzavřít MVP checklist a provozní dokumentaci.

## Pracovní poznámky k aktivnímu tasku

### 2026-08-02 – `M0-05`

- Ověřeny oficiální ceníky Cloud SQL, Cloud Run, Storage, Scheduler, Routes, Logging a Secret Manager; regionální dostupnost je pro navržené komponenty vyhovující.
- Reprodukovatelný model vychází na 275,58 Kč bez daně v základním a 306,55 Kč v konzervativním scénáři. Cloud SQL tvoří přibližně 98 % základního odhadu.
- Zdokumentováno kritické riziko Routes: bez cache by týdenní přepočet celého trhu přidal asi 662 Kč/měsíc. Navržena cache, bootstrap kvóta a následný limit 300/den.
- Přidán report `docs/discovery/m0-05-gcp-costs.md`, kalkulační skript a unit testy.
- Lokálně je Google Cloud SDK 549.0.0, ale Terraform chybí. Aktivní `gcloud` účet/projekt patří jinému pracovnímu prostředí a nebyl změněn.
- Zbývá: správným osobním účtem potvrdit billing, daňový režim, aktivovatelnost API a finální Cloud SQL cenu v Calculatoru; potom zaznamenat uživatelovo cloud/local rozhodnutí.

Při zahájení tasku sem zapsat:

- datum a ID tasku,
- stručný plán,
- soubory nebo komponenty v rozsahu,
- rizika a předpoklady,
- provedené testy,
- co zbývá před označením `[x]`.

Po dokončení stručnou poznámku přesunout do historie níže.

## Blokátory a otevřené otázky

### `M0-05` – potvrzení cílového GCP projektu

- Blokující podmínka: nelze potvrdit billing a API stav projektu `sreality-scrapper-504307`.
- Ověřeno: veřejné ceny a regionální dostupnost, lokální SDK, explicitní read-only pokusy bez změny aktivního pracovního projektu.
- Příčina: `gcloud` selže při obnově OAuth tokenu na lokální chybě důvěryhodnosti TLS; dostupný aktivní účet navíc není osobní účet vlastníka cílového projektu.
- Chybí: kontrola v Cloud Console správným účtem, daňový režim billing accountu a uživatelovo potvrzení podmíněného cloudového pokračování při odhadu kolem horního rozpočtového limitu.
- Dopad: blokuje uzavření brány M0 a cloudové tasky závislé na M0-05 (`M2-03`, `M4-02`); neblokuje lokální návrh databáze od `M1-01`.

Položka označená `[!]` musí zde uvést:

- konkrétní blokující podmínku,
- co již bylo ověřeno,
- jaké rozhodnutí nebo přístup chybí,
- které další tasky blokuje.

## Historie dokončené práce

### 2026-08-02 – `M0-04`

- Profilováno 5 aktuálních chat a 5 chalup bez uložení textů, ID, lokalit, URL nebo image bytes.
- Potvrzena struktura 29 top-level polí a přibližně 70 parametrů, přičemž mnoho hodnot je nullable.
- Zjištěno, že cena může být `0`; specifikace ji nově vyřazuje z mediánu a normalizuje jako neuvedenou.
- Medián počtu fotografií je 26,5; medián veřejné 800×600 WebP varianty je 96 708 B.
- Bodový odhad jedné kopie aktuálního trhu je přibližně 9,2 GB; strategie archivovat jen oblíbené nabídky zůstává správná.
- Přidán opakovatelný agregovaný profiler, JSON report a interpretace v `docs/discovery/m0-04-data-profile.md`.
- Ověření: 22 read-only requestů s prodlevou; všech 10 image měření úspěšných; předchozí unit sada procházela.

### 2026-08-02 – `M0-03`

- Ověřena detailní SSR query `estate` pro jednu chatu a jednu chalupu.
- Přidány sanitizované search/detail fixtures pro oba podtypy a syntetický případ s chybějícími volitelnými poli.
- Sanitizace nahrazuje původní texty, ID, ceny, plochy, souřadnice a mediální URL; fixtures neobsahují známé zdrojové domény ani původní vzorová ID/lokality.
- Přidán explicitní generátor `scripts/capture_sreality_fixtures.py` se čtyřmi pomalými read-only requesty a bezpečnostní kontrolou před zápisem.
- Dokumentována struktura a proces aktualizace fixtures.
- Ověření: pytest hlásí `7 passed`; `compileall` a kontrola zakázaných vzorů prošly.

### 2026-08-02 – `M0-02`

- Zjištěno, že původní `/api/cs/v2/estates` a `/count` endpointy vracejí HTTP 404 a nejsou použitelným základem nové pipeline.
- Ověřen aktuální strukturovaný Next.js `__NEXT_DATA__` SSR payload veřejných vyhledávacích stránek.
- Potvrzeny slugy `chaty`/`chalupy`, podtypy 33/43, prodej, domy, celá ČR a stránkování `?strana=N`.
- Při měření nalezeno 2 409 chat a 1 174 chalup; pozorovaný limit je 22 výsledků na stránku.
- Opakovaná první stránka měla pro oba podtypy shodná ID a stránky 1/2 se nepřekrývaly.
- Přidán read-only skript `scripts/validate_sreality_api.py`, agregovaný report v `docs/discovery/` a tři regresní testy parseru.
- Specifikace byla aktualizována tak, aby budoucí agent nepoužil nefunkční REST endpointy bez nového ověření.
- Ověření: živá validace prošla 6 requesty s prodlevou 0,75 s; pytest hlásí `4 passed`; `compileall` a TOML parsing prošly.

### 2026-08-02 – `M0-01`

- Vytvořen cílový scaffold pro Python backend/scraper, testy, budoucí Next.js frontend, Terraform, ADR a pomocné skripty.
- Standardizován Python 3.13 a Node.js 24 LTS; přidán `pyproject.toml`, EditorConfig a runtime version files.
- Zavedeny a zdokumentovány příkazy pro Ruff, mypy, pytest a základní syntaktickou kontrolu.
- Původní scraper zůstal beze změn na původních cestách a je označen jako referenční legacy implementace.
- Ověření: `pyproject.toml` načten přes `tomllib`, `compileall` prošel a pytest hlásí `1 passed`.
- Ruff a mypy nebyly spuštěny, protože zatím nejsou lokálně nainstalované; jejich konfigurace a instalační postup jsou připravené.

### 2026-08-02 – `DOC-01`

- Prozkoumán původní Python scraper, SQLite vrstva, transformace a konfigurace.
- Sepsána cílová produktová a technická specifikace.
- Potvrzen rozsah: chaty a chalupy na prodej v celé ČR, jeden uživatel, Praha jako referenční bod, týdenní běh a GCP rozpočet 200–300 Kč.
- Vytvořena roadmapa s milníky, závislostmi, branami a akceptačními kritérii.

## Pravidla aktualizace

Při každé změně stavu tasku je nutné současně:

1. změnit checkbox,
2. aktualizovat datum, aktuální task, následující task a souhrn nahoře,
3. zaznamenat testy a významná zjištění,
4. přidat nebo odstranit blokátor,
5. po dokončení přidat krátký záznam do historie,
6. při změně rozsahu aktualizovat také `specifikace.md`,
7. při změně pořadí, závislosti nebo akceptace aktualizovat také `roadmap.md`.

Task lze označit `[x]` pouze po splnění sloupce „Hotovo, když“ v `roadmap.md`.
