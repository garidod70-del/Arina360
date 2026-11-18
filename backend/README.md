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
- Run and validate Alembic migrations during deployment; keep AUTO_CREATE_TABLES disabled in production.
- Add rate limiting, SMS/OTP phone ownership verification, password reset and refresh-token/session revocation.
- Add admin-controlled role grants and audit logs. Clients cannot assign privileged roles.
- Set a unique random JWT_SECRET (32+ characters) and restrict CORS origins.
- Configure managed PostgreSQL, HTTPS, backups, monitoring and secrets outside source control.
- Add automated integration/security tests and deploy the API to a real HTTPS host.
- Verify payment-provider webhooks before recording payment success.

The first registered account is only an athlete. Organizer, referee, coach, club and provider permissions must be granted through a trusted admin workflow.


## QPay Merchant V2 integration

Configure these server-side environment variables before enabling checkout:

- `QPAY_BASE_URL`: sandbox `https://merchant-sandbox.qpay.mn` for testing; production `https://merchant.qpay.mn` after merchant activation.
- `QPAY_CLIENT_ID`, `QPAY_CLIENT_SECRET`: QPay Merchant V2 API credentials.
- `QPAY_INVOICE_CODE`: invoice code issued for the merchant.
- `QPAY_CALLBACK_URL`: public HTTPS origin of this API (for example `https://api.example.mn`).

Never place QPay credentials in Flutter, commit them to Git, or share them in chat. Use deployment secrets. Run `alembic upgrade head` before deploying; the current schema includes payment-state and optional referee-phone migrations through `0012_referee_phone_optional`.

The app creates invoices at `POST /api/v1/payments/qpay/invoice` for store orders, assigned referee bookings, approved venue bookings, accepted provider service requests, and paid club memberships. The API returns QPay QR/deeplink data. The callback and the authenticated `POST /api/v1/payments/qpay/invoices/{id}/check` endpoint both verify the invoice against QPay `POST /v2/payment/check` before settling the order and recording the 5% commission.

QPay Merchant V2 officially documents sandbox/production hosts, Basic-auth token acquisition, Bearer-token API calls, invoice creation, and server-side payment checking. See https://developer.qpay.mn/mn/docs/merchant?version=2.0.0.

The platform commission is fixed at 5% of verified paid amounts, rounded down to the nearest whole MNT. For example, 50,000₮ produces 2,500₮ commission and 47,500₮ provider net. Duplicate payment events are idempotent; partial/full refund events reverse the commission proportionally. The admin dashboard reports gross, commission, provider net, refunds and unpaid orders; providers can see their own net earnings and transaction history.\n\nThe provider net amounts are currently recorded in the ARENA 360 settlement ledger. Actual automatic transfers to individual sellers/referees/clubs are not enabled by a standard single-merchant invoice; a separate payout/settlement arrangement with QPay/banks is required.
