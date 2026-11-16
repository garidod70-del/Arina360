# ARENA 360 Backend

Initial ASP.NET Core 8 API foundation.

## Run locally

Install the .NET 8 SDK, then:

```bash
cd backend/ARENA360.Api
dotnet restore
dotnet run
```

Open the Swagger URL printed by the app. Initial endpoints:

- `GET /api/health` — API health
- `GET /api/modules` — ARENA 360 module catalogue

This is a foundation only. Authentication, PostgreSQL persistence, payments, notifications and production deployment are not implemented yet. Never commit real secrets.
