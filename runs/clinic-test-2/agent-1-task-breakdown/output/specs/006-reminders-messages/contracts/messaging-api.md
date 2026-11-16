# Contracts: 006-reminders-messages

Added operations for `contracts/clinic-api-v1.openapi.yaml` (api-clinic-api-v1). Errors use the API's standard error body.

## Patient preferences (cmp-identity), auth: patient session cookie

### GET /api/me/preferences
- 200: `{ "preferredChannel": "sms" | "whatsapp" }`

### Booking request addition (owned by feature 003, listed here for the field)
- `POST /api/appointments` body gains `channel`: `"sms" | "whatsapp"` (required). 422 if missing or other value. The saved booking sets the account's `preferredChannel`.

## Reception opt-out (cmp-identity), auth: receptionist or practice manager session, CSRF header

### PUT /api/patient-accounts/{accountId}/reminders
- Body: `{ "enabled": true | false }`
- 200: `{ "remindersEnabled": bool, "changedAt": datetime, "changedBy": staffId }`
- `enabled=false` cancels the account's pending reminders in the same transaction.
- 403 for dentist; 404 if the account is unknown. Receptionist access follows ASM-011 (patients searchable by all reception; the change is audited).
- GET `/api/patient-accounts/{accountId}` (existing patient record) gains `remindersEnabled`, `remindersOptOutSource`, `remindersOptOutAt`.

## Provider webhooks (cmp-messaging / cmp-channel-adapters), auth: HMAC signature

### POST /api/webhooks/sms  (rel-009)
- Header carries the HMAC-SHA256 signature of the raw body (header name set by the provider adapter).
- Body kinds (normalised by the adapter): delivery receipt `{providerMessageId, state: delivered|failed, errorCode?}` or inbound reply `{from, text}`.
- 200 `{}` for accepted, repeated or unknown ids; 401 for missing/bad signature; 429 rate limited; 400 malformed.

### POST /api/webhooks/whatsapp  (rel-010)
- Same, delivery receipts only; inbound text is ignored (STOP through WhatsApp is not in scope of this release).

## Internal ports (not HTTP)

```python
class ChannelPort(Protocol):
    channel: Literal["sms", "whatsapp"]
    async def send(self, msg: OutboundMessage) -> SendResult: ...      # template_id + values only
    def verify(self, headers: Mapping[str, str], body: bytes) -> bool: ...
    def parse_webhook(self, body: bytes) -> list[Receipt | InboundReply]: ...

class MessagingService:
    def on_booked(self, session, appointment) -> None                  # confirmation + reminder rows
    def on_cancelled(self, session, appointment, actor) -> None        # cancel reminder + change notice
    def on_rescheduled(self, session, appointment, old_start, actor) -> None
    async def send_code(self, phone: str, code: str) -> bool           # in the sign-in request
    def set_reminders(self, session, account_id, enabled, source, actor) -> None
```

`OutboundMessage` carries `template_id`, `to` (phone) and `values` (clinic, dentist, treatment, date, time, link, code); nothing else is passed.
