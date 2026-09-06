# API Docs

Two developer-facing references for the Soccer Club API
(`https://soccer-api.athlongoapp.com`):

- **`../API_REFERENCE.md`** — human-readable reference: every endpoint with its
  request body and example responses, grouped by module, plus a role→endpoint
  matrix.
- **`openapi.yaml`** — the OpenAPI 3.0 spec (all 30 paths, request/response
  schemas, Bearer-JWT security, roles noted per endpoint).
- **`swagger.html`** — a browser viewer for `openapi.yaml`.

## Viewing the Swagger UI

The browser blocks `swagger.html` from reading `openapi.yaml` over `file://`,
so serve this folder over HTTP (any one of these):

```bash
# from the repo root
cd docs && python3 -m http.server 8080
# then open http://localhost:8080/swagger.html
```

Alternatives that need no local server:
- Go to <https://editor.swagger.io> → File → Import file → choose `openapi.yaml`.
- Import `openapi.yaml` directly into Postman or Insomnia to generate a request
  collection.

## Trying requests

1. In Swagger UI click **Authorize**, paste an access token from
   `POST /auth/login`, and Authorize.
2. All protected endpoints will then send `Authorization: Bearer <token>`.
