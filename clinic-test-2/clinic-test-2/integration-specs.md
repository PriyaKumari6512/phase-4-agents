# BrightSmile Booking — Integration Specifications

Based on: architecture v1 · Status: proposed

## 1. API conventions

Shared by the one contract, `api-clinic-api-v1`.

| Topic | Convention |
|---|---|
| Base path and versioning | All operations are under `/api` (the edge routes `/api` to ctr-clinic-api). The major version is in the contract id and file name (`clinic-api-v1`), not in the path. `GET /health` is at `/health`, outside `/api`, for the platform probe. Additive changes bump the minor `info.version`; a breaking change gets a new file `clinic-api-v2.openapi.yaml` next to v1. |
| Authentication | Users: a signed JWT in the `session` cookie (`HttpOnly`, `Secure`, `SameSite=Strict`, 7 days for patients, 8 hours or 30 minutes idle for staff). Role, clinic and active flag are re-read from the database on every request. Writes also need the `X-CSRF-Token` header (returned by the sign-in and `GET /me` responses) and an `Origin` that matches the site. Provider webhooks: `X-Signature` (HMAC-SHA256) and `X-Timestamp`, no cookie. |
| Pagination | Every list takes `page` (default 1) and `page_size` (default 50, maximum 200). The response is `{items, page, page_size, total}`. A list that has natural groups (the day view) pages over the groups. |
| Error envelope | Every 4xx and 5xx body is the `Error` schema: `{code, message, timestamp, correlation_id}` with a stable `code` from the LLD Errors table, a plain-English `message` and an ISO timestamp. `SLOT_TAKEN` adds `next_slots` (up to 10), `CUTOFF_PASSED` and `ONLINE_BOOKING_BLOCKED` add `clinic_phone`. |
| Status mapping | 422 VALIDATION_ERROR, OUTSIDE_HORIZON, TREATMENT_NOT_ONLINE, HOURS_OVERLAP · 401 AUTH_REQUIRED, AUTH_CODE_INVALID, AUTH_CODE_EXPIRED, AUTH_BAD_CREDENTIALS, WEBHOOK_SIGNATURE_INVALID · 403 FORBIDDEN, AUTH_ACCOUNT_INACTIVE, CSRF_FAILED, ONLINE_BOOKING_BLOCKED · 404 NOT_FOUND · 409 CONFLICT, FAMILY_LIMIT, SLOT_UNAVAILABLE, SLOT_TAKEN, CUTOFF_PASSED, NOSHOW_TOO_EARLY, NOSHOW_UNDO_EXPIRED, INVALID_TRANSITION · 429 RATE_LIMITED, AUTH_LOCKED · 503 PROVIDER_UNAVAILABLE · 500 INTERNAL_ERROR. |
| Correlation id | The `X-Request-Id` request header is used if present (maximum 64 characters), otherwise generated. It is returned in the `X-Request-Id` response header and in `Error.correlation_id`, and written to every log line and provider call. |
| Idempotency | `POST /appointments` requires `Idempotency-Key` (a UUID). A repeat with the same key and body returns the first response (stored 48 hours in `idempotency_key`); the same key with another body is 422 VALIDATION_ERROR. Other writes are naturally safe to repeat: a second cancel or arrived answers 409 INVALID_TRANSITION and changes nothing. Webhooks are idempotent on provider message id. The web app never retries a write automatically. |
| Date, time, money | Instants are ISO 8601 UTC with `Z` (`2027-03-01T04:30:00Z`); the web app shows IST. Day parameters (`date`, `date_from`) are IST calendar days `YYYY-MM-DD`; clock times in working hours are IST `HH:MM`; months are `YYYY-MM` in IST. Phones are E.164. No money is exchanged (CON-006). |
| Rate limiting | The edge (WAF) limits 300 requests per minute per IP. Code requests: per phone 10 a day and 1 every 30 seconds, per IP 30 an hour (thr-008). Limited responses are 429 with `Retry-After` (seconds), `X-RateLimit-Limit` and `X-RateLimit-Remaining`. Webhooks: 600 requests per minute per provider at the edge. |
| PII | Phone numbers, names and codes are never in URLs or logs. Search by phone or name uses a query parameter on `GET /patients` over HTTPS only; access logs of the edge drop the query string of that route. |

## 2. Contracts

| Contract id | File | Version | Owner (ctr id) | Consumers (ctr / act ids) | Operations |
|---|---|---|---|---|---|
| api-clinic-api-v1 | contracts/clinic-api-v1.openapi.yaml | 1.0.0 | ctr-clinic-api | ctr-web (all roles), act-sms-provider (webhook), act-whatsapp-provider (webhook) | 50: `GET /health`; auth (5): patient code, patient verify, staff login, logout, `GET /me`; staff (3); patients (7): family list and add, search, create, reminder preference, block status, lift block; erasure (1); catalogue (9): clinics, dentists and treatments, each list, create, update; schedules (6): working hours list and set, leave list and add, to-move list, free slots; appointments (6): list, book, get, reschedule, cancel, history; reception (6): book, reschedule, cancel, arrived, no-show, undo; day view, dentist's own day, failed reminders, no-show report (4); webhooks (2): SMS and WhatsApp |

## 3. Integrations

### rel-001: act-patient → ctr-web
| Aspect | Specification |
|---|---|
| Purpose | Patient screens in a phone browser |
| Protocol and style | HTTPS, static files from the CDN |
| Operations | none (browser); files are versioned by name |
| Authentication | none until sign-in (public static files; no data in them) |
| Timeout | 30000 ms in the browser |
| Retry | none by the system; the user reloads. The CDN retries its origin once after 1000 ms |
| Circuit breaker | none: static files, no dynamic dependency |
| Fallback | The CDN serves the last good build if the origin is down |
| Idempotency | read-only |
| Error mapping | CDN 5xx → the browser's offline page |
| Rate limits / quotas | WAF 300 requests per minute per IP |

### rel-002: act-receptionist → ctr-web
| Aspect | Specification |
|---|---|
| Purpose | Reception screens in a desktop browser |
| Protocol and style | HTTPS, static files from the CDN |
| Operations | none (browser) |
| Authentication | none until sign-in |
| Timeout | 30000 ms |
| Retry | none; as rel-001 |
| Circuit breaker | none: static files |
| Fallback | As rel-001; reception phones are the manual fallback |
| Idempotency | read-only |
| Error mapping | as rel-001 |
| Rate limits / quotas | as rel-001 |

### rel-003: act-dentist → ctr-web
| Aspect | Specification |
|---|---|
| Purpose | The dentist's day screen on a phone or clinic PC |
| Protocol and style | HTTPS, static files from the CDN |
| Operations | none (browser) |
| Authentication | none until sign-in |
| Timeout | 30000 ms |
| Retry | none; as rel-001 |
| Circuit breaker | none: static files |
| Fallback | As rel-001 |
| Idempotency | read-only |
| Error mapping | as rel-001 |
| Rate limits / quotas | as rel-001 |

### rel-004: act-practice-manager → ctr-web
| Aspect | Specification |
|---|---|
| Purpose | Manager screens: hours, leave, treatments, staff, report |
| Protocol and style | HTTPS, static files from the CDN |
| Operations | none (browser) |
| Authentication | none until sign-in |
| Timeout | 30000 ms |
| Retry | none; as rel-001 |
| Circuit breaker | none: static files |
| Fallback | As rel-001 |
| Idempotency | read-only |
| Error mapping | as rel-001 |
| Rate limits / quotas | as rel-001 |

### rel-005: ctr-web → ctr-clinic-api
| Aspect | Specification |
|---|---|
| Purpose | Every application operation of the screens |
| Protocol and style | REST over HTTPS, JSON, under `/api` |
| Operations | All 48 user operations of `api-clinic-api-v1` (everything except the two webhooks) and `GET /health` |
| Authentication | JWT in the `session` cookie plus `X-CSRF-Token` on writes and an Origin check; patient code sign-in and staff login are public operations |
| Timeout | 10000 ms per request (slot list and booking are expected inside 2000 and 3000 ms for 95%, QA-001, QA-002) |
| Retry | Reads (GET): 1 retry after 500 ms on network error or 503. Writes: none automatic; the user presses again, and `POST /appointments` is then safe through its `Idempotency-Key` |
| Circuit breaker | none: the browser is the only caller and the user sees the error at once; the edge health check removes a failing replica |
| Fallback | Screen shows "Something went wrong, try again" with the correlation id; for CUTOFF_PASSED and ONLINE_BOOKING_BLOCKED it shows the clinic phone from the response |
| Idempotency | `Idempotency-Key` on `POST /appointments`; other writes by status checks (INVALID_TRANSITION) |
| Error mapping | The `Error.code` to a screen message from one English catalogue; 401 AUTH_REQUIRED → sign-in screen; 429 → wait message using `Retry-After`; 409 SLOT_TAKEN → show `next_slots` |
| Rate limits / quotas | 300 requests per minute per IP at the edge; code limits as section 1 |

### rel-006: ctr-clinic-api → ctr-db
| Aspect | Specification |
|---|---|
| Purpose | All reads and writes of the 15 tables in `data-model.md` |
| Protocol and style | SQL over TLS, PostgreSQL wire protocol, SQLAlchemy sessions, one transaction per request |
| Operations | The access patterns AP-001 to AP-031 |
| Authentication | Database user and password from the secret store as environment variables (`DATABASE_URL`); the application user has no DDL rights; network access only from the container service |
| Timeout | Connect 3000 ms; statement timeout 5000 ms; pool wait 3000 ms |
| Retry | Read-only statements: 1 retry after 200 ms on connection error. A write transaction rolled back by the database for a deadlock or serialisation failure (SQLSTATE 40001, 40P01) is retried once as a whole, because nothing was committed. Never retry after a commit is in doubt |
| Circuit breaker | none: the pool (20 connections per replica, 40 in total against a limit of 100) bounds the load; HA failover to the standby takes about 60 seconds |
| Fallback | During failover requests fail with 503 INTERNAL_ERROR and the web app shows the retry message; the queued messages are untouched |
| Idempotency | Booking by `Idempotency-Key`; dispatcher claims by `FOR UPDATE SKIP LOCKED` |
| Error mapping | SQLSTATE 23P01 (exclusion violation on `ex_appointment_no_overlap`) → SLOT_TAKEN; 23P01 on `ex_working_hours_no_overlap` → HOURS_OVERLAP; 23505 (unique) → CONFLICT, FAMILY_LIMIT when from the family insert; 57014 (statement timeout) and connection errors → INTERNAL_ERROR (500) |
| Rate limits / quotas | Pool of 20 per replica; statement timeout 5000 ms |

### rel-007: ctr-clinic-api → act-sms-provider
| Aspect | Specification |
|---|---|
| Purpose | Send sign-in codes, confirmations, notices and reminders by SMS through DLT-registered templates |
| Protocol and style | REST over HTTPS, JSON, called by `cmp-channel-adapters`. Codes are sent inside the request; every other message is sent asynchronously by the dispatcher (JOB-001) |
| Operations | Provider "send message" call: template id, recipient phone, template values, client reference = `message.id`. Not a contract operation of ours |
| Authentication | Provider API key (`SMS_API_KEY`) from the secret store, sent in the provider's authorisation header over TLS |
| Timeout | 5000 ms (connect 2000 ms) |
| Retry | Dispatcher messages: 3 attempts in all, backoff 5 s then 30 s (the `next_attempt_at` column), retried on timeout, 5xx and 429 only; a 4xx rejection is final (REJECTED). Safe because the client reference is the message id. Sign-in code: no retry in the request; the patient asks for a new code |
| Circuit breaker | Opens after 5 failures within 60 seconds; stays open 60 seconds, then one probe call. While open, queued messages wait (they are not marked failed) and a code request answers 503 PROVIDER_UNAVAILABLE |
| Fallback | Dispatcher: the row returns to `queued` with the next attempt time; after 3 attempts it is `failed`, and reception sees it in "Reminders failed" (FR-033). Code: PROVIDER_UNAVAILABLE, the patient can ask again, reception books by phone (RSK-002) |
| Idempotency | Client reference = `message.id`; the provider is asked not to deliver a repeated reference twice. If the provider cannot guarantee this (to confirm, ASM-009), a retry after a timeout is only made when no provider message id was received |
| Error mapping | Timeout, connection error, 5xx, 429 → RETRYABLE; 400, 403 (bad template, bad number) → REJECTED (final); unknown 4xx → REJECTED; breaker open → PROVIDER_UNAVAILABLE |
| Rate limits / quotas | Our dispatcher sends at most 50 messages per cycle every 30 seconds (about 1.7 a second); the clinic's account quota and sender ID are set with the provider (CON-007); about 4,000 messages a week expected |

### rel-008: ctr-clinic-api → act-whatsapp-provider
| Aspect | Specification |
|---|---|
| Purpose | Send confirmations, notices and reminders by WhatsApp approved templates |
| Protocol and style | REST over HTTPS, JSON, called by `cmp-channel-adapters`, always by the dispatcher |
| Operations | Provider "send template message" call: template name, language `en`, recipient phone, parameters, client reference = `message.id` |
| Authentication | Provider API key (`WHATSAPP_API_KEY`) from the secret store |
| Timeout | 5000 ms (connect 2000 ms) |
| Retry | As rel-007: 3 attempts, backoff 5 s then 30 s, on timeout, 5xx and 429 only |
| Circuit breaker | Opens after 5 failures within 60 seconds, open 60 seconds, then one probe. While open the rows stay queued |
| Fallback | After 3 failed attempts, or a failed receipt, one SMS row is created with `fallback_of_message_id` (unique key) when `FALLBACK_WHATSAPP_TO_SMS` is true (ASM-005); the SMS then follows rel-007. If the switch is off or the SMS fails, the chain ends `failed` and appears in "Reminders failed" |
| Idempotency | Client reference = `message.id`; one fallback per message by the unique key on `fallback_of_message_id` (thr-018) |
| Error mapping | As rel-007; additionally "recipient not on WhatsApp" or "template not approved" → REJECTED, which starts the fallback at once without further attempts |
| Rate limits / quotas | As rel-007; the WhatsApp provider's per-number messaging tier is set with the provider |

### rel-009: act-sms-provider → ctr-clinic-api
| Aspect | Specification |
|---|---|
| Purpose | Delivery receipts for sent SMS, and inbound STOP replies |
| Protocol and style | HTTPS webhook (provider pushes JSON) |
| Operations | `POST /webhooks/sms` of `api-clinic-api-v1` |
| Authentication | HMAC-SHA256 signature over `X-Timestamp + "." + raw body` with `WEBHOOK_SECRET_SMS`, in `X-Signature`; timestamp older than 5 minutes is rejected (replay protection) |
| Timeout | The handler answers within 2000 ms (signature check, one indexed update); the provider's own delivery timeout applies on its side |
| Retry | Done by the provider (assumed: several retries over about 1 hour, to confirm under ASM-009). The handler is idempotent so a repeat changes nothing |
| Circuit breaker | none: an inbound call; the edge rate limit of 600 requests per minute protects the API |
| Fallback | If our API is down the provider retries; a missed STOP is the risk accepted in thr-017 and reconciled by the provider's retry; a missed receipt leaves the row `sent`, which is not shown as failed |
| Idempotency | Key is provider message id plus status; a receipt never moves a row backwards (`delivered` and `failed` are final); unknown ids are ignored with 200; a STOP sets the opt-out flag and skips queued reminders, and repeating it changes nothing |
| Error mapping | Bad or missing signature, or old timestamp → 401 WEBHOOK_SIGNATURE_INVALID; malformed body → 422 VALIDATION_ERROR; unknown message id → 200 (ignored); unexpected fault → 500 INTERNAL_ERROR (the provider retries) |
| Rate limits / quotas | 600 requests per minute at the edge; batch of at most 100 events per call |

### rel-010: act-whatsapp-provider → ctr-clinic-api
| Aspect | Specification |
|---|---|
| Purpose | Delivery receipts for WhatsApp messages (a failed receipt starts the SMS fallback) |
| Protocol and style | HTTPS webhook (provider pushes JSON) |
| Operations | `POST /webhooks/whatsapp` of `api-clinic-api-v1` |
| Authentication | As rel-009 with `WEBHOOK_SECRET_WHATSAPP` |
| Timeout | The handler answers within 2000 ms |
| Retry | Done by the provider; the handler is idempotent |
| Circuit breaker | none: an inbound call |
| Fallback | A lost "failed" receipt is caught after 3 attempts only when the provider call itself failed; if no receipt ever arrives the row stays `sent` and the nightly JOB-005 does not change it (a known gap, RSK-004) |
| Idempotency | As rel-009; a replayed failed receipt cannot create a second SMS because `fallback_of_message_id` is unique (thr-018) |
| Error mapping | As rel-009 |
| Rate limits / quotas | As rel-009 |

## 4. External partner integrations

Both providers are not yet chosen (ASM-002, ASM-009). The adapter component isolates them (ADR-0006); the table is the shape the adapters must be able to meet. The names below are placeholders until the choice.

| Item | SMS provider (act-sms-provider) | WhatsApp provider (act-whatsapp-provider) |
|---|---|---|
| Adapter component | cmp-channel-adapters, `sms.py` and `webhooks.py` | cmp-channel-adapters, `whatsapp.py` and `webhooks.py` |
| Sandbox / test environment | Provider test account with a test sender ID and a test number list, available in week 1–2 (DEP-001); staging uses it | Provider sandbox or test number with test templates (DEP-002); staging uses it |
| Credentials and rotation | `SMS_API_KEY`, `WEBHOOK_SECRET_SMS` in the cloud secret store, passed as environment variables; rotated every 180 days and at once if leaked; a rotation overlaps old and new webhook secret for 24 hours | `WHATSAPP_API_KEY`, `WEBHOOK_SECRET_WHATSAPP`, same rules |
| Webhooks: endpoint | `POST /api/webhooks/sms` | `POST /api/webhooks/whatsapp` |
| Webhooks: signature | HMAC-SHA256 hex in `X-Signature` over `X-Timestamp.rawBody`; if the provider signs differently, the adapter verifies the provider's scheme and the contract header stays | Same |
| Webhooks: replay protection | Timestamp within 5 minutes, and idempotency on provider message id and status | Same |
| Webhooks: retries | By the provider; we answer 200 fast so it stops | Same |
| Data sent | Phone, template id, template values (clinic, dentist, date, time, link, first name). Nothing clinical (thr-013) | Phone, approved template name, language `en`, the same values |
| Template rules (CON-003, NFR-011) | Every kind has a DLT-registered template id in `TEMPLATE_IDS`; free text is never sent (BR-025) | Every kind has an approved template; messages outside the 24-hour window use templates only |
| Data mapping: send | `message.kind` and `message.channel` pick the `template_id`; `message.params` → provider variables in order; `message.id` → client reference | Same, `params` → template components |
| Data mapping: receipt | Provider status "delivered" → `message.status = delivered`; "failed", "undelivered", "rejected" → `failed` with `last_error_code = RECEIPT_FAILED`; anything else is ignored | Same ("read" also counts as delivered) |
| Data mapping: inbound | A reply whose trimmed upper-case text is `STOP` (also `STOP ALL`, `UNSUBSCRIBE`) from a phone → `patient_account.reminders_opt_out = true`; other text is ignored and not stored | none (WhatsApp STOP is not specified in the PRD; to confirm with the provider) |
| Data mapping: errors | Provider error codes → RETRYABLE or REJECTED (rel-007) | Provider error codes → RETRYABLE or REJECTED (rel-008) |
| Who registers | The clinic owns DLT registration and the WhatsApp business account, with our help (A-005, CON-007) | Same |

## 5. Events

No asynchronous messaging. The `message` table is a work list inside the one database (ADR-0002), not an event stream, and the webhooks are request-response calls on the contract.
