# ARENA 360 API — HTTPS deployment

Import the repository into Render and apply the root `render.yaml` Blueprint. Render provisions the Docker web service and PostgreSQL database and assigns a managed HTTPS URL. The container applies Alembic migrations before starting the API.

## Verify deployment
Open `https://YOUR-SERVICE.onrender.com/health`; expected response:
```json
{"status":"ok","service":"arena360-api"}
```
API docs: `https://YOUR-SERVICE.onrender.com/docs`.

## First administrator (one time)
1. Register an ordinary ARENA 360 account with the phone number that will own admin access.
2. In Render Environment, copy the generated `ADMIN_BOOTSTRAP_KEY`.
3. POST `/api/v1/admin/bootstrap` with JSON `{"phone":"+976XXXXXXXX"}` and header `X-Admin-Bootstrap-Key: <key>`.
4. Remove `ADMIN_BOOTSTRAP_KEY` from Render Environment and redeploy. The first-admin bootstrap route will then be disabled. Only the first admin can be created this way.

## Grant a referee role and register licence
Use the admin account's bearer token:
- POST `/api/v1/admin/referees/grant` with JSON containing `phone`, `sport`, `rank`, `region`, `base_fee`, `license_number`, `license_issuer`, and optional ISO `license_expires_at`.
- This grants the referee role but leaves the licence in `pending` state.
- After checking the physical/original licence with the issuing federation, POST `/api/v1/admin/referees/{user_id}/verify` with `{"approved":true,"note":"..."}`. The API records verifier, timestamp and note. Rejection uses `approved:false`.
- Only verified referees appear in the public directory and can be assigned.

## Build the live API APK
Set GitHub repository variable `ARENA_API_BASE_URL` to the exact HTTPS origin, e.g. `https://arena360-api.onrender.com` (no `/api/v1` suffix), then run the `ARENA 360 Android APK` workflow. The build injects this value into Flutter. If the variable is empty, the APK deliberately stays in local prototype mode.

## Deployment boundary
Repository code cannot create a Render account, accept its terms, select a paid plan, or approve the service on the owner's behalf. The owner must import/apply the Blueprint once. The included free database is for initial smoke testing only and may expire; use a persistent database plan before public production. The API records an administrator's licence check; it does not independently query the federation registry.
