# ARENA 360 authentication foundation

## Included
- ASP.NET Core Identity user storage with PostgreSQL.
- Password hashing through Identity (plain-text passwords are never stored).
- JWT access tokens (12-hour expiry).
- Public roles: `Organizer` and `Referee`. Public registration cannot create an `Admin`.
- Protected example endpoint: `GET /api/account/me`.

## Configuration
Set these environment variables in the hosting environment; do not commit secrets:

- `ConnectionStrings__ArenaDb`: PostgreSQL connection string.
- `Jwt__Secret`: random secret with at least 32 UTF-8 bytes.
- Optional: `Jwt__Issuer`, `Jwt__Audience`.

For local development, use user-secrets or environment variables. Never put production passwords or JWT secrets in appsettings.json.

## Database
Install the EF Core tool, then from `backend/ARENA360.Api` run:

```bash
dotnet tool install --global dotnet-ef
dotnet ef migrations add InitialIdentity
dotnet ef database update
```

The API does not automatically create or migrate a production database at startup.

## Endpoints
- `POST /api/auth/register` — create Organizer or Referee account.
- `POST /api/auth/login` — receive JWT.
- `GET /api/account/me` — current account (Bearer token required).
