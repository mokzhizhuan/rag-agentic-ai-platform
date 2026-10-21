# RAG Knowledge AI — Phase 1

React + Django REST Framework + Keycloak + PostgreSQL, with configurable Ollama/OpenAI provider metadata. **Development only.** Document ingestion and inference are planned for later phases.

## Requirements
- Docker Desktop running (Windows / PowerShell).
- Ports 5174, 8200, 8180 available.

## Run (PowerShell)
```powershell
Copy-Item .env.example .env
# Edit .env and replace ALL sample passwords/secrets before starting
# Optional: generate a Django secret: python -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose up -d --build
docker compose ps
```

Open **http://localhost:8180/admin/** and sign in with `KEYCLOAK_ADMIN` and `KEYCLOAK_ADMIN_PASSWORD` from `.env`. Select realm `rag-app` (imported at first startup). Under **Users**, create a user, set a non-temporary password under Credentials, and assign realm role `rag-user` under Role mapping. Do not use the initial Keycloak bootstrap admin as the application user.

Open **http://localhost:5174/**, log in as that user, and click **Test authenticated Django API**. You should see profile claims and the currently configured AI provider.

Health check: **http://localhost:8200/api/health/**

> Keycloak might need a little time to start after PostgreSQL becomes ready. If the first attempt fails, refresh once Keycloak is serving requests.

## Provider selection
Edit `.env`:
```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_CHAT_MODEL=llama3.2
```
or
```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_real_key_here
OPENAI_CHAT_MODEL=gpt-4.1-mini
```
Then run `docker compose up -d --force-recreate backend`. **Phase 1 reports configuration only; it does not call either provider.** `OLLAMA_BASE_URL` is suitable for Ollama running on Windows host using Docker Desktop, provided Ollama listens on an interface reachable by Docker.

## Endpoint list
- Public `GET /api/health/`
- Bearer token protected `GET /api/auth/me/`
- Bearer token protected `GET /api/ai/provider/`

## Notes
- The SPA uses Keycloak Authorization Code + PKCE (no client secret in browser).
- Django validates token signature via Keycloak JWKS, issuer, expiry and `rag-api` audience.
- `start-dev`, HTTP, Django `DEBUG=True`, broad development CORS, and demo Vite server **must not be deployed to production**.
- Keycloak realm JSON is imported only when realm does not already exist. To apply later changes, use the admin console or an intentional reimport strategy; avoid deleting volumes with user data.
- PostgreSQL is split into `ragdb` and `keycloak` databases in the same container. pgvector is deferred until Phase 2.
- Tokens are held in Keycloak JS memory; no tokens are manually written to localStorage.
- OpenAI keys stay backend-side in `.env` (never commit that file).
