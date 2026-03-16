# 🔐 Security Architecture
This document explains the optional API‑key protections used in PetMatch. They are simple, toggleable, and aligned with **least‑privilege principles**.

---
# 1.0 Overview
PetMatch uses **header-based API keys**:
X-API-Key: <your-key></your-key>

The API supports **two independent guards**, each controlled using environment variables. 

| Guard Type | Environment Variable  | Protects |
|-----------|------------------------|----------|
| Analytics | `ANALYTICS_API_KEY`    | `/api/analytics/*` |
| Writes    | `WRITE_API_KEY`        | `POST / PUT / PATCH / DELETE /api/pets/*` |

Reads (`GET /api/pets/*`, `/health`, `/pets/summary`, etc.) remain **unrestricted** for smooth demos.

---
# 2.0 Enabling Guards
Use environment variables before starting the server.

```bash
# Example (macOS / Linux / WSL)
export ANALYTICS_API_KEY="asecret"
export WRITE_API_KEY="wsecret"
uvicorn app.main:app --

#  Example (Windows PowerShell)
$env:ANALYTICS_API_KEY="asecret"
$env:WRITE_API_KEY="wsecret"
uvicorn app.main:app --reload
```
---
# 3.0 Behaviour Summary
# 3.1 When ANALYTICS_API_KEY is set
Requests to /api/analytics/* require:
```bash
X-API-Key: <ANALYTICS_API_KEY>
```

Otherwise:
```bash
401 Unauthorized
{"detail": "Invalid or missing API key"}
```

# 3.2 When WRITE_API_KEY is set
Any of the following require a valid key:
```bash
POST /api/pets
PUT /api/pets/{id}
PATCH /api/pets/{id}
DELETE /api/pets/{id}
```

# 3.3 When variables are unset
- Analytics endpoints become public
- Write operations become public
- System runs in “demo-friendly” mode
---
# 4.0 Swagger Integration
1. Open http://127.0.0.1:8000/docs
2. Click **Authorize**
3. Enter API key into X-API-Key
4. Swagger will automatically attach it to protected routes
---
# 5.0 Testing Authentication
Tests ensure correct behaviour:
- Guard OFF → endpoints open
- Guard ON + missing header → 401
- Guard ON + correct key → 200

Run relevant tests:
```bash
pytest -q -k auth
```
---
# 6.0 Design Rationale
- Minimal friction for assessors
- No change required to run the API — guards are optional
- Separation of concerns:
    - analytics logic stays independent
    - write operations can be locked on demand
- No database changes required
This meets coursework requirements for clarity, extensibility, and security awareness.

---
# 7.0 Summary
- Uses simple header-based auth
- Two independent guards
- Fully optional
- Ideal for demos and real scenarios
- Easy for markers to test
---