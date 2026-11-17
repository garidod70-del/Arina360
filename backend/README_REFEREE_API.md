# ARENA 360 referee API (phase 2)

All routes are under `/api/v1/referees` and require a valid bearer access token except the verified referee directory.

- `GET /api/v1/referees?sport=Жүдо&region=Улаанбаатар`: verified referee directory with average rating.
- `POST /api/v1/referees/profile/me`: create/update referee profile. Requires an administrator-granted `referee` role. Profile edits reset verification to `pending`.
- `POST /api/v1/referees/requests`: create a real persisted referee booking request.
- `GET /api/v1/referees/requests/me`: list requests created by the current user or assigned to them.
- `POST /api/v1/referees/requests/{id}/assign?referee_user_id={user_id}`: requester or admin assigns a verified referee matching the sport.
- `POST /api/v1/referees/requests/{id}/accept`: assigned referee accepts.
- `POST /api/v1/referees/requests/{id}/complete`: requester, assigned referee, or admin marks accepted work complete.
- `POST /api/v1/referees/requests/{id}/rating`: requester rates a completed booking once (1–5).

## Security boundaries
- Public registration always creates an `athlete` role; no public endpoint grants `referee` or `admin`.
- Referee profile verification defaults to `pending`; only an administrator-controlled process should mark it `verified`.
- Payments are not charged by this API. The request total is an estimate only, not a payment confirmation.
- Production must use database migrations (not `AUTO_CREATE_TABLES`), HTTPS, rate limiting, backups, and a controlled admin role-management process.
