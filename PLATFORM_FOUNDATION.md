# ARENA 360 Platform Foundation

This branch adds a separate platform foundation without replacing the existing Flutter app.

## Current repository areas

- `apps/mobile` — existing Flutter Android application
- `backend/ARENA360.Api` — new ASP.NET Core 8 API starter
- `web/admin` — new React admin dashboard starter

## First endpoints

- `GET /api/health`
- `GET /api/modules`

## Next implementation stages

1. PostgreSQL schema, migrations and repository/service layer.
2. Authentication, role-based access (administrator, organizer, referee, club, coach, venue, fitness provider, customer).
3. Referee requests and approvals.
4. Competition registration, draw generation, brackets, scoring and results.
5. Club/training, venue booking, course, fitness and sports marketplace modules.
6. QR verification, notifications, reporting and audit logs.
7. Connect Flutter app and admin web to the same API.
8. CI checks, deployment and Android release build.

The new API and web dashboard are starter foundations, not production-ready services yet. No third-party project code has been copied into this repository.
