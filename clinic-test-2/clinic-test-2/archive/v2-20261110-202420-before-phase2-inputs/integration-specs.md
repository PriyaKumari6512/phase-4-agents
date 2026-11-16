# Clinic Booking System — Integration Specifications

Based on: architecture v2 · Status: proposed

## 1. API conventions

Shared by every contract (there is one: api-clinic-api-v1).

| Topic | Convention |
|---|---|
| Base path and versioning | Paths start at the root (`/appointments`, `/health`). The major version is carried by the contract file name (`clinic-api-v1`) and `info.version`. A breaking change gets a new file `clinic-api-v2.openapi.yaml` next to v1. Additive changes bump the minor version in place |
| Format | JSON over HTTPS (TLS 1.2+), UTF-8, `snake_case` field names, plural-noun paths |
| Authentication | `Authorization: Bearer <JWT>` on every operation except `POST /auth/register`, `POST /auth/login` and `GET /health`. JWT is signed with `JWT_SIGNING_KEY`, valid 60 minutes, carries account id, role and patient id. The token is never in a URL or a log |
| Authorization | Roles `patient` and `receptionist` (LLD authorization matrix). Deny by default. Patients reach only their own records |
| Pagination | Query parameters `page` (from 1, default 1) and `page_size` (default 50, max 100). Response envelope: `{ "items": [...], "page": 1, "page_size": 50, "total": 123 }`. Every list operation uses it |
| Error envelope | Every 4xx and 5xx body is the `Error` schema: `{ "code", "message", "timestamp", "correlation_id" }`. `code` is one of the 16 codes of LLD section 2.1 (VALIDATION_ERROR 422, UNAUTHENTICATED 401, INVALID_CREDENTIALS 401, ACCOUNT_LOCKED 429, FORBIDDEN 403, NOT_FOUND 404, EMAIL_TAKEN 409, SLOT_NOT_BOOKABLE 422, SLOT_TAKEN 409, LIMIT_REACHED 409, TOO_LATE_TO_CHANGE 409, INVALID_STATE 409, IDEMPOTENCY_CONFLICT 422, RATE_LIMITED 429, DEPENDENCY_UNAVAILABLE 503, INTERNAL_ERROR 500). Messages never contain email, name, mobile or token |
| Correlation id | Request header `X-Correlation-Id` (optional, up to 64 characters). If absent the API generates one. It is returned in the `X-Correlation-Id` response header and in the `Error` body, and written to every log line |
| Idempotency | Header `Idempotency-Key` (required on `POST /appointments`, up to 100 characters). Same patient and key with the same data returns the original appointment, with different data returns 422 IDEMPOTENCY_CONFLICT (BR-012). Keys are kept as long as the appointment row. Reschedule, cancel and no-show are naturally safe to repeat: a repeat gets 409 INVALID_STATE and the client re-reads the list |
| Date and time | ISO 8601 UTC with `Z` for instants (`2026-11-04T09:30:00Z`). Dates are `YYYY-MM-DD` and times of day `HH:MM`, in the clinic time zone (`CLINIC_TIMEZONE`, ASM-007). No money appears in this API |
| Rate limiting | Ingress limit 20 requests/s per client IP, API limit 10 requests/s per account (burst 20), login 5 attempts per 15 minutes per account. Over the limit: 429 RATE_LIMITED or ACCOUNT_LOCKED with `Retry-After` (seconds). Successful responses carry `X-RateLimit-Limit` and `X-RateLimit-Remaining` for the per-account limit |
| Health | `GET /health` is unauthenticated, returns 200 `{ "status": "ok" }` when the database answers a `select 1` within 1000 ms, otherwise 503 |

## 2. Contracts

| Contract id | File | Version | Owner (ctr id) | Consumers (ctr / act ids) | Operations |
|---|---|---|---|---|---|
| api-clinic-api-v1 | contracts/clinic-api-v1.openapi.yaml | 1.1.0 | ctr-clinic-api | ctr-web-app (for act-patient and act-receptionist) | 17: getHealth, registerPatient, login, getPatient, updatePatientContact, erasePatient, listDentists, listOpenSlots, listWorkingHours, setWorkingHours, blockPeriod, bookAppointment, listAppointments, cancelAppointment, rescheduleAppointment, markNoShow, getDaySchedule |

Version 1.1.0 (request 2) is additive: optional `reminder_channel` (`sms` or `whatsapp`, default `sms`) on the `bookAppointment` request and the `Appointment` response. No operation was added, removed or renamed, so existing clients keep working. Consumer ctr-web-app adds the channel choice. A `whatsapp` value while WHATSAPP_ENABLED is false returns 422 VALIDATION_ERROR.

Operation to component map: `registerPatient`, `login` → cmp-identity. `getPatient`, `updatePatientContact`, `erasePatient` → cmp-patient-registry (erase also cmp-booking, cmp-identity). `listDentists`, `listOpenSlots`, `listWorkingHours`, `setWorkingHours`, `blockPeriod` → cmp-scheduling. `bookAppointment`, `listAppointments`, `cancelAppointment`, `rescheduleAppointment` → cmp-booking. `markNoShow`, `getDaySchedule` → cmp-day-schedule.

## 3. Integrations

### rel-001: act-patient → ctr-web-app
| Aspect | Specification |
|---|---|
| Purpose | Patient's browser loads the static web app |
| Protocol and style | HTTPS GET of static files (HTML, JS, CSS) from static hosting behind a CDN |
| Operations | None. No contract and no data: static assets only |
| Authentication | None, public static files. Accepted because the files hold no data or secret. The app calls the API with a token (rel-003) |
| Timeout | 10000 ms (browser) |
| Retry | none by design, the user reloads the page. Static files are cached at the CDN edge |
| Circuit breaker | none, the CDN is the failure isolation and there is no caller service |
| Fallback | CDN serves the last cached version when the origin is down |
| Idempotency | read-only |
| Error mapping | CDN 5xx → browser shows a static "try again later" page |
| Rate limits / quotas | CDN default per-IP limits, no application limit |

### rel-002: act-receptionist → ctr-web-app
| Aspect | Specification |
|---|---|
| Purpose | Receptionist's browser loads the static web app |
| Protocol and style | HTTPS GET of static files from static hosting behind a CDN |
| Operations | None. No contract and no data: static assets only |
| Authentication | None, public static files (same reasoning as rel-001). Receptionist screens only show data after login through rel-003 |
| Timeout | 10000 ms (browser) |
| Retry | none by design, the user reloads the page |
| Circuit breaker | none, the CDN is the failure isolation and there is no caller service |
| Fallback | CDN serves the last cached version when the origin is down |
| Idempotency | read-only |
| Error mapping | CDN 5xx → browser shows a static "try again later" page |
| Rate limits / quotas | CDN default per-IP limits, no application limit |

### rel-003: ctr-web-app → ctr-clinic-api
| Aspect | Specification |
|---|---|
| Purpose | All business operations of patients and receptionists |
| Protocol and style | REST/JSON over HTTPS, synchronous |
| Operations | All 17 operations of api-clinic-api-v1 (section 2) |
| Authentication | JWT bearer in `Authorization`, obtained from `POST /auth/login`, 60 minutes. The signing key is `JWT_SIGNING_KEY` from the secret store. The web app keeps the token in memory only (not in local storage). CORS allows only `CORS_ALLOWED_ORIGINS` |
| Timeout | 10000 ms per request in the browser. Server side, the ingress timeout is 15000 ms |
| Retry | Idempotent reads (GET): 2 retries, backoff 500 ms then 1500 ms, only on network error, 429, 502, 503, 504. `POST /appointments`: up to 2 retries with the **same** Idempotency-Key, same backoff, on network error and 503. Reschedule, cancel, no-show, erase: no automatic retry |
| Circuit breaker | none: one backend, a human is the caller and sees the message. The ingress health check removes a failing instance |
| Fallback | The user sees "Something went wrong, please retry" with the correlation id, and the form data stays on screen. For SLOT_TAKEN the app reloads the open slots |
| Idempotency | `Idempotency-Key` on `POST /appointments` (BR-012). All GETs are read-only. Other writes are state-guarded (409 INVALID_STATE on a repeat) |
| Error mapping | The app shows a message by `code`: SLOT_TAKEN and SLOT_NOT_BOOKABLE → pick another slot. TOO_LATE_TO_CHANGE → call the clinic. LIMIT_REACHED → cancel one first. UNAUTHENTICATED → login screen. RATE_LIMITED and ACCOUNT_LOCKED → wait `Retry-After` seconds. DEPENDENCY_UNAVAILABLE and INTERNAL_ERROR → retry message |
| Rate limits / quotas | 10 requests/s per account, burst 20. Ingress 20 requests/s per IP. Login 5 attempts per 15 minutes per account |

### rel-004: ctr-clinic-api → ctr-clinic-db
| Aspect | Specification |
|---|---|
| Purpose | Persist and read all entities (data-model.md) |
| Protocol and style | SQL over TLS (PostgreSQL wire protocol), synchronous, through an ORM with parameterised queries |
| Operations | The access patterns AP-001 to AP-019 of data-model.md. No contract file (internal) |
| Authentication | Database role `clinic_api` (least privilege, no DDL). The password is in `DATABASE_URL` from the secret store. Migrations run with a separate migration role, only in the deploy pipeline |
| Timeout | Connection acquire 2000 ms, connect 3000 ms, statement timeout 3000 ms (`statement_timeout`), lock wait 2000 ms |
| Retry | 2 retries, backoff 50 ms then 200 ms, of the whole transaction, only on serialization failure (SQLSTATE 40001) and deadlock (40P01). Not on unique violation (that is SLOT_TAKEN) and not on timeout in a write (the client retries with the Idempotency-Key). Reads may retry once on connection loss |
| Circuit breaker | none: the database is the single system of record with no alternative path. The pool fails fast after 2000 ms and `/health` reports 503 so the ingress stops routing |
| Fallback | None. The caller returns 503 DEPENDENCY_UNAVAILABLE. Failover to the standby is done by the database platform (≤ 5 min, QA-003) |
| Idempotency | Booking writes: `ux_appointments_idem` (patient_id, idempotency_key). Reminder claim: `FOR UPDATE SKIP LOCKED` plus status. Other writes are guarded by status and `version` |
| Error mapping | Unique violation on `ux_appointments_active_slot` → SLOT_TAKEN. Unique violation on `ux_user_accounts_email_lower` → EMAIL_TAKEN. Unique violation on `ux_appointments_idem` → return the original appointment (or IDEMPOTENCY_CONFLICT if data differ). Connection or statement timeout, pool exhausted → DEPENDENCY_UNAVAILABLE. Any other error → INTERNAL_ERROR |
| Rate limits / quotas | Pool of 10 connections per instance (at most 40 at 4 instances), below the database limit of 100 connections |

### rel-005: ctr-clinic-api → act-sms-gateway
| Aspect | Specification |
|---|---|
| Purpose | Send the reminder text for one appointment (FR-3) |
| Protocol and style | REST/JSON over HTTPS, synchronous call made by the background job JOB-001 through cmp-sms-adapter. Never called in a user request |
| Operations | `POST {SMS_API_URL}/messages` with body `{ "to": "<E.164>", "text": "<message>" }`. Provider not chosen yet (ASM-009), so this is our adapter's canonical shape and the adapter maps it to the chosen provider |
| Authentication | API key in header `X-Api-Key` from `SMS_API_KEY` (secret store, environment variable). Rotated every 90 days (thr-008) |
| Timeout | 5000 ms (`SMS_TIMEOUT_SECONDS`) for connect plus response |
| Retry | Done by the job, not in the call: up to 5 attempts per reminder (`REMINDER_MAX_ATTEMPTS`), delay 5 min, 15 min, 60 min, then 60 min. No attempt after 2 h before the visit (BR-010). Safe because the provider `Idempotency-Key` is the reminder id (BR-011) |
| Circuit breaker | Opens after 5 consecutive failures, stays open 300 s, then one probe call (half-open). While open, `send` fails at once with BreakerOpen and the reminder goes back to Pending without using an attempt |
| Fallback | The reminder stays Pending or becomes Failed or Expired. The booking is never blocked. Alert on `breaker_opened` and on `reminders_overdue` above 0 for 1 h. No second channel for SMS itself (no email fallback). SMS is the fallback target of rel-006 (BR-019); this breaker is independent of the WhatsApp one |
| Idempotency | Header `Idempotency-Key: <reminder id>`. A duplicate is detected by the provider (ASM-009). A 409 with the same key is treated as success. Residual risk of a duplicate SMS after a crash is accepted (RSK-002) |
| Error mapping | Timeout, network error, 429, 5xx → SmsTransientError (retry with backoff). 401 or 403 → SmsTransientError plus an alert "gateway credentials" (a rotated key must not fail every reminder permanently). 400 or 422 (invalid number or text) → SmsPermanentError, reminder Failed. 409 with the same key → success. Open breaker → BreakerOpen |
| Rate limits / quotas | Our volume is about 200 messages per day, at most 50 per job run (one run per 60 s). Provider limits are unknown until the provider is chosen. A provider 429 honours `Retry-After` |

### rel-006: ctr-clinic-api → act-whatsapp-provider
| Aspect | Specification |
|---|---|
| Purpose | Send the reminder for one appointment on WhatsApp when the patient chose it (FR-4) |
| Protocol and style | REST/JSON over HTTPS, synchronous call made by the background job JOB-001 through cmp-whatsapp-adapter. Never called in a user request |
| Operations | `POST {WHATSAPP_API_URL}/messages` with body `{ "to": "<E.164>", "template": "<WHATSAPP_TEMPLATE_NAME>", "language": "en", "parameters": ["<first name>", "<dentist name>", "<local date and time>"] }`. Provider not chosen yet (ASM-013), so this is our adapter's canonical shape and the adapter maps it to the chosen provider. No free text is ever sent (BR-018, CON-003) |
| Authentication | API key in header `X-Api-Key` from `WHATSAPP_API_KEY` (secret store, environment variable). Rotated every 90 days (thr-010) |
| Timeout | 5000 ms (`WHATSAPP_TIMEOUT_SECONDS`) for connect plus response |
| Retry | Done by the job, not in the call: up to 5 attempts per reminder, delay 5 min, 15 min, 60 min, then 60 min, no attempt after 2 h before the visit (BR-010), the same as rel-005. Only transient errors are retried |
| Circuit breaker | Own breaker, independent of rel-005: opens after 5 consecutive failures, stays open 300 s, then one probe call (half-open). While open, `send` fails at once with BreakerOpen |
| Fallback | A permanent error or an open breaker switches the reminder once to SMS (rel-005): `channel` = 'sms', `fallback_used` = true, attempts reset, back to Pending (BR-019, ADR-0007), only if `REMINDER_SMS_FALLBACK` is true and the cutoff has not passed. Otherwise the reminder becomes Failed. A reminder is claimed and sent on one channel at a time, never both. Bookings are never blocked. Alerts on `breaker_opened`, `reminder_channel_fallback` and `reminders_overdue` |
| Idempotency | Header `Idempotency-Key: <reminder id>`, per provider (the SMS gateway receives the same id after a fallback, which is a different system). A duplicate is detected by the provider (ASM-013). A 409 with the same key is treated as success. After an ambiguous failure (timeout after the request was sent) the job retries WhatsApp with the same key and does not fall back until a definite permanent error or an open breaker (RSK-009) |
| Error mapping | Timeout, network error, 429, 5xx → WhatsAppTransientError (retry with backoff). 401 or 403 → WhatsAppTransientError plus an alert "provider credentials". 400 or 422 with recipient not on WhatsApp, recipient not opted in, or template rejected, paused or unapproved → WhatsAppPermanentError, fallback to SMS (BR-019). 409 with the same key → success. Open breaker → BreakerOpen, handled as the fallback case |
| Rate limits / quotas | About 200 messages per day at most, at most 50 per job run. Provider limits and template quotas are unknown until the provider is chosen. A provider 429 honours `Retry-After` |

## 4. External partner integrations

Two external systems: act-sms-gateway and act-whatsapp-provider.

| Item | Specification |
|---|---|
| Adapter component | cmp-sms-adapter (`app/sms`: client, breaker, errors). It is the only code that knows the provider. cmp-reminders sees only `send(msisdn, text, idempotency_key)` and the three error types |
| Sandbox / test environment | The provider's test mode or sandbox key, selected by `SMS_API_URL` and `SMS_API_KEY` in dev and staging. A local stub server with the same shape runs in CI. Production keys are never used outside production |
| Credentials and rotation | `SMS_API_KEY` in the platform secret store, delivered as an environment variable, never in images or documents. Rotated every 90 days: the new key is added, the deployment restarted, the old key revoked. Spend alert on the provider account (thr-008) |
| Webhooks | None. The gateway gives no delivery receipts (ASM-009), so there is no inbound endpoint, signature check or replay protection. "Sent" means the gateway accepted the message. If a receipt webhook is added later, it needs a new operation (additive minor version), HMAC signature verification and replay protection on message id |
| Data mapping | Our reminder (`reminders`) and patient mobile → request `to` (E.164 mobile), `text` (built at send time: "Hi <first name>, reminder of your dental appointment with <dentist name> on <date> at <local time>"), `Idempotency-Key` (reminder id). Response `id` or message reference → `reminders.provider_ref`. The text is never stored or logged. No treatment data is sent (thr-009) |
| Open points | Provider choice, SMS consent and sender id rules (ASM-008, ASM-009, RSK-006). Whether SMS consent covers the WhatsApp fallback (ASM-015, RSK-009) |

### act-whatsapp-provider

| Item | Specification |
|---|---|
| Adapter component | cmp-whatsapp-adapter (`app/whatsapp`: client, template, breaker, errors). The only code that knows the provider. cmp-reminders sees only `send(msisdn, template_params, idempotency_key)` and the three error types |
| Sandbox / test environment | The provider's test number or sandbox key, selected by `WHATSAPP_API_URL` and `WHATSAPP_API_KEY` in dev and staging. A local stub server with the same shape runs in CI. Production keys and the production sender number are never used outside production |
| Credentials and rotation | `WHATSAPP_API_KEY` in the platform secret store, delivered as an environment variable, never in images or documents. Rotated every 90 days: add the new key, restart, revoke the old one. Spend and volume alert on the provider account (thr-010) |
| Message template | One pre-approved English reminder template named by `WHATSAPP_TEMPLATE_NAME`, with 3 parameters (first name, dentist name, local date and time). Business-initiated WhatsApp messages need an approved template and an opted-in recipient (CON-003). If the template is rejected or paused, the provider answers a permanent error and reminders fall back to SMS (RSK-008) |
| Opt-in | Choosing `whatsapp` at booking is the opt-in (ASM-014), stored as `appointments.reminder_channel`. The API offers `whatsapp` only while `WHATSAPP_ENABLED` is true |
| Webhooks | None. Delivery receipts are not used (ASM-013), so there is no inbound endpoint, signature check or replay protection. "Sent" means the provider accepted the message. If receipts or reply handling are added later, they need a new operation (additive minor version), HMAC signature verification and replay protection on message id |
| Data mapping | Our reminder and patient mobile → request `to` (E.164, the same number as the SMS), `template` (name), `parameters` (first name, dentist name, local date and time, built at send time), `Idempotency-Key` (reminder id). Response message id → `reminders.provider_ref`. Parameters are never stored or logged. No treatment data is sent (thr-011) |
| Open points | Provider choice and template approval (ASM-013, RSK-008), opt-in wording and that the mobile number is the WhatsApp number (ASM-014), consent for SMS fallback (ASM-015, RSK-009) |

## 5. Events

No asynchronous messaging.
