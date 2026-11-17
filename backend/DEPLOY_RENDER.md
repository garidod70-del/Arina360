# ARENA 360 API — HTTPS deployment

This repository includes a Render Blueprint at the repository root. Import the repository in Render and apply `render.yaml`. Render provisions a web service and PostgreSQL; the web service receives a managed HTTPS URL and generated secrets.

## Database migration
After the first deployment, run from the service Shell:
```sh
cd /srv/arena360
alembic upgrade head
```
Then confirm `https://YOUR-SERVICE.onrender.com/health` returns `{"status":"ok","service":"arena360-api"}`.

## First administrator
1. Register a normal ARENA 360 account with the phone number that will become the administrator.
2. In Render Environment, copy the generated `ADMIN_BOOTSTRAP_KEY` value.
3. Send one POST request to `/api/v1/admin/bootstrap` with JSON `{"phone":"+976XXXXXXXX"}` and header `X-Admin-Bootstrap-Key: <key>`.
4. Remove `ADMIN_BOOTSTRAP_KEY` from the Render service environment and redeploy. The bootstrap route then becomes unusable. Only the first admin can be created this way.

## Grant and verify referees
Use an admin access token:
- POST `/api/v1/admin/referees/grant` with phone, sport, rank, region, base_fee. This grants referee role but profile remains pending.
- POST `/api/v1/admin/referees/{user_id}/verify` with `{"approved":true,"note":"Лицензийн дугаар ... шалгасан"}` only after the real federation licence has been checked. Rejection uses approved=false.

## Flutter APK
Set the GitHub repository variable `ARENA_API_BASE_URL` to the exact service origin, e.g. `https://arena360-api.onrender.com` (no `/api/v1` suffix), then run the Android APK workflow. The workflow passes this value to Flutter as `ARENA_API_BASE_URL`.

## Important
A Render service and URL cannot be created by repository code alone. A repository owner must import and approve the Blueprint in Render. Free database plans may expire or have limited availability; choose a persistent paid database before production launch. CORS is permissive for this mobile-only API; restrict it if a web frontend is introduced. Real-world licence validation is an administrator's responsibility; this API records the decision, it does not query a federation registry.
