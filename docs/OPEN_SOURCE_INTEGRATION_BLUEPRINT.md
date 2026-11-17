# ARENA 360 — Open-source review and integration blueprint

Date: 2026-11-17
Target app: existing Flutter Android app in `apps/mobile`
Working branch: `feature/unified-sports-services`

## 1. Current repository baseline

- The mobile client is a Flutter app.
- The current app's service list has 11 categories, but most category destinations are prototype/generic screens.
- Login currently accepts any non-empty phone/password and navigates locally. It is not server authentication.
- Profile information is stored locally with SharedPreferences.
- No production API, central user database, booking backend, payment gateway, or QR verification service is connected.
- The current pull request is still open and unmerged. Do not describe this branch as a production release.

## 2. Open-source projects reviewed

| Project | Relevant capabilities | License | ARENA 360 decision |
|---|---|---|---|
| FastBooking (predictivelabsai/FastBooking) | Multi-tenant sport/recreation facility bookings, memberships, attendance, check-in, hosted checkout, notifications, clinic appointment scheduling; FastAPI + PostgreSQL | Apache-2.0 | Best initial backend reference/candidate. Review security, maturity, API contracts and deployment before adopting code. Apache-2.0 is permissive; retain required notices and review dependencies. |
| Dojo (DojoUK/Dojo) | Club members, classes, coach assignment, attendance, grades, invoices, payments, member portal | AGPL-3.0 | Strong judo/club workflow reference. Do not copy into a closed/proprietary combined product without understanding AGPL network-source obligations. |
| Bracket (evroon/bracket) | Swiss, single-elimination, round-robin, match scheduling, scores, public standings; FastAPI + TypeScript frontend | AGPL-3.0 | Strong tournament workflow reference. Prefer implementing compatible tournament domain/API in ARENA 360 unless the whole affected server is intentionally AGPL-compliant. |
| OpenAthlete (openathleteorg/openathlete) | Training plans, training load, recovery/performance analytics, coach-athlete workflows | AGPL-3.0 | Useful training/analytics reference, not a drop-in Flutter module. Do not incorporate code until licensing strategy is decided. |
| Clubnetz (sleepwalkerffs/Clubnetz) | Club membership, seasons, court bookings, events, invoices, push/email notifications, public API | AGPL-3.0 | Useful club and facility workflow reference. Same AGPL caution; it is a Blazor/.NET web app, not Flutter code. |
| Easy!Appointments | Practitioner appointment calendars and online booking | GPL-3.0 | Reference for appointment scheduling only. Not a sports medicine record system. Review GPL obligations before incorporating code. |
| Coachfolio (kapoordeepanshu/coachfolio) | Workout plans, coach/client tracking and progress; Next.js + Supabase | MIT | Possible training-plan UI/data-model reference. Project is still growing; inspect security and API boundaries before reuse. |

## 3. Recommended approach

Keep one Flutter Android application. Do not bundle several unrelated web apps inside the APK. Use a single backend API and shared identity, with separate domain modules behind it.

### Proposed architecture

- Mobile: existing Flutter app, reorganized into feature folders and API repositories.
- Backend: modular REST API. FastBooking is the first candidate to audit for booking primitives; do not adopt it blindly.
- Database: PostgreSQL with tenant-aware records and migrations.
- Authentication: one phone-number account, secure password hashing, SMS/OTP verification when an SMS provider is selected, refresh-token/session management, role-based permissions.
- Payments: payment-provider adapter. Select a Mongolia-supported provider only after merchant/API requirements are verified. Never store card details in ARENA 360.
- Notifications: server-triggered push notifications plus in-app notification history.
- QR: server-signed, short-lived, single-use tokens; server validates token, booking/event status and staff permissions. A static QR image alone is not proof of payment or attendance.

### Shared identity and roles

One account can have multiple roles: athlete/parent, organizer, referee, coach, club admin, provider, medical professional, venue operator and platform admin. Permissions must be checked by the backend on every protected action; hiding a button in Flutter is not authorization.

### Core data domains

- users, user_roles, profiles, organizations, organization_members
- service_providers, provider_qualifications, service_categories
- venues, facilities, availability_slots, bookings, booking_status_history
- clubs, memberships, classes, training_sessions, attendance
- competitions, divisions, registrations, draws, brackets, matches, results
- invoices, payment_intents, payment_transactions, refunds
- qr_tokens, check_ins
- notifications, notification_preferences, audit_logs

Medical/rehabilitation records must be a separately permissioned domain. Start with provider discovery and appointment booking; do not expose diagnosis, injury notes or medical documents to general club/organizer roles. Collect only necessary data and establish consent, retention, access logging and Mongolian legal/privacy review before storing health records.

## 4. Delivery sequence

1. **Foundation:** split the single large Flutter file into feature modules; define API contracts, error handling and environment configuration.
2. **Identity:** replace test-mode login with real server-side phone account registration/login and role permissions.
3. **Booking core:** provider profiles, availability, booking lifecycle, cancellations and conflict prevention.
4. **Club and coaching:** membership, classes, attendance, training plans and athlete progress.
5. **Tournament:** registration, divisions, draw generation, bracket formats, mat/court schedule, scores and results.
6. **Payments and QR:** Mongolia-ready payment adapter, signed webhook processing, refunds, QR check-in and anti-replay checks.
7. **Medical and specialist services:** appointment scheduling first; clinical data only after strict privacy/security design.
8. **Notifications and analytics:** push/in-app notices, provider dashboard and audit trail.
9. **QA and release:** automated tests, security review, Android build, device testing and release notes.

## 5. Non-negotiable acceptance checks

- A user account works across all modules and devices.
- Users cannot read or modify another club/provider's private records.
- Double booking is blocked by database-level transaction/constraint logic.
- Payment success is confirmed only by a verified server webhook, never by a client screen.
- QR codes expire, are single-use and are validated online.
- Medical information is inaccessible to unrelated roles.
- Every third-party component has a recorded license, version, attribution and dependency review.
- Build/test results are reported honestly; no APK is called ready until an actual build and device test succeed.

## 6. Explicit limitations

This document records the first source review and proposed integration plan. It does not mean any third-party application has been installed, deployed, or connected to the current app. FastBooking is a candidate for deeper technical review, not yet an approved production dependency. AGPL/GPL projects are workflow references until the project's distribution and source-publication strategy is decided.
