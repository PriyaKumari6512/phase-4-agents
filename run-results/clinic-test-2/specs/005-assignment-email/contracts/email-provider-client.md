# Contract: Email provider client (internal)

Module: `app/services/email_client.py` in acme/taskflow-api. The provider is not named in architecture.md (open question Q2); this is the provider-agnostic interface.

```text
EmailMessage: to_address, to_name, subject, text_body, html_body (optional), idempotency_key
SendResult:   provider_message_id
EmailClient.send(message: EmailMessage) -> SendResult
```

Errors:
- `TransientEmailError`: timeout, connection error, HTTP 429 or 5xx from the provider. The caller retries.
- `PermanentEmailError`: other 4xx (invalid address, rejected content, authentication failure). The caller marks the notification failed.

Rules:
- Settings from environment via `app/core/config.py`: `EMAIL_PROVIDER_API_KEY` (secret, from External Secrets), `EMAIL_PROVIDER_BASE_URL`, `EMAIL_FROM_ADDRESS`; request timeout 10 s (A).
- `idempotency_key` is sent to the provider in the form the provider supports; if it does not support one, the key is ignored.
- The client never logs the API key or the message body.
- A fake implementation `tests/fakes/fake_email_client.py` records messages and can be told to fail.
