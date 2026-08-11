# M2-08 – Google OAuth live validace

Datum ověření: 2026-08-11

## Konfigurace

- Google Cloud projekt: `sreality-scrapper-504307`
- OAuth audience: External, stav Testing
- Testovací a povolený účet: `vondryswow@gmail.com`
- Typ klienta: Web application
- Lokální callback: `http://localhost:8000/api/v1/auth/google/callback`
- Scopes: `openid email profile`

OAuth client secret, session secret, authorization code, ID/access token a session
cookie nejsou v repozitáři zaznamenané. Lokální secrets jsou pouze v ignorovaném
`.env`; produkční uložení bude řešit Secret Manager.

## Výsledek

Ručně spuštěný login přes `/api/v1/auth/google/login` dokončil Google callback
a backend vrátil `authenticated: true`. Tím bylo ověřeno:

- authorization-code flow se state, nonce a PKCE,
- serverová výměna kódu a ověření Google ID tokenu,
- ověřený e-mail a backendový allowlist vlastníka,
- vydání HMAC podepsané session cookie,
- lokální redirect URI a OAuth test-user konfigurace.

Automatizované testy navíc pokrývají cizí účet, pozměněnou/expirovanou session,
CSRF zákaz, nepřihlášený přístup a idempotentní ruční scraper trigger.
