# Frontend

České responzivní rozhraní Sreality Chaty Trackeru postavené na Next.js App Routeru a strict TypeScriptu.

## Lokální spuštění

Backend musí běžet na `http://localhost:8000`. Frontend všechny požadavky na `/api/v1/*` serverově přeposílá na backend, takže autentizační cookies zůstávají same-origin. Pro OAuth používejte v obou službách přesně host `localhost`, nikoli kombinaci s `127.0.0.1`.

```powershell
cd frontend
npm install
npm run dev
```

Aplikace bude dostupná na `http://localhost:3000`.

Volitelně lze backend změnit pouze serverovou proměnnou, například `SREALITY_BACKEND_URL=http://localhost:8000`. Hodnota se neposílá do browserového JavaScriptu.

Mapové dlaždice používají bezpečný konfigurovatelný preset `NEXT_PUBLIC_MAP_TILE_PROVIDER=osm` nebo `carto`; odpovídající atribuce je součástí presetu a nelze ji omylem vynechat. Před produkčním nasazením je nutné zvolenému providerovi potvrdit podmínky a očekávaný provoz.

## Kontroly kvality

```powershell
npm run lint
npm run typecheck
npm test
npm run test:e2e
npm run build
```

Playwright E2E automaticky vytvoří produkční Next server a ověří kritické cesty v desktopovém Chromiu i mobilním Pixel 7 viewportu. Backend a živé OAuth se při těchto testech nepoužívají; API je deterministicky mockované v browserové vrstvě.

`src/lib/api/contracts.ts` je ručně udržovaná TypeScript reprezentace stabilního FastAPI kontraktu. Při změně backendového response modelu musí být změněna a otestována ve stejném pull requestu.
