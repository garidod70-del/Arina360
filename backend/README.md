# ARENA 360 API — authentication foundation

## Local run (Python 3.12+)

    cd backend
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    uvicorn app.main:app --reload

Windows activation: .venv\\Scripts\\activate

API docs: http://127.0.0.1:8000/docs
Health check: http://127.0.0.1:8000/health

## Docker run

    cd backend
    docker compose up --build

## Endpoints

- POST /api/v1/auth/register — phone + password; new account gets athlete role.
- POST /api/v1/auth/login — returns a JWT access token.
- GET /api/v1/auth/me — current account; requires Authorization: Bearer token.

Phone input is normalized for spaces, dashes and brackets. Password minimum is 8 characters. Passwords are Argon2-hashed and never returned.

## Production work still required

This is a foundation, not a production launch. Before public use:
- Add Alembic migrations; do not use AUTO_CREATE_TABLES in production.
- Add rate limiting, SMS/OTP phone ownership verification, password reset and refresh-token/session revocation.
- Add admin-controlled role grants and audit logs. Clients cannot assign privileged roles.
- Set a unique random JWT_SECRET (32+ characters) and restrict CORS origins.
- Configure managed PostgreSQL, HTTPS, backups, monitoring and secrets outside source control.
- Add automated integration/security tests and deploy the API to a real HTTPS host.
- Verify payment-provider webhooks before recording payment success.

The first registered account is only an athlete. Organizer, referee, coach, club and provider permissions must be granted through a trusted admin workflow.
