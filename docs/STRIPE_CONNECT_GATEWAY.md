# AGILANG Stripe Connect Gateway v1

This module adds a complete Stripe Connect gateway boundary to the AGILANG runtime. It is intentionally limited to Stripe Connect and does not introduce other payment providers.

## Included capabilities

- Express connected-account creation
- Stripe-hosted onboarding links
- Embedded Connect account sessions
- Account requirement, capability, charge and payout monitoring
- Destination-charge PaymentIntents with application fees
- Refunds with optional application-fee refund and transfer reversal
- Transfers and connected-account payouts
- Dispute listing
- HMAC-SHA256 webhook verification against the raw body
- Timestamp tolerance and duplicate-event rejection
- SQLite operational state, WAL mode, audit history and alerts
- Account reconciliation
- Merchant HTTP endpoints
- Administrator monitoring and reconciliation endpoints
- Zero mandatory third-party Python dependencies

## Production boundary

Stripe remains the payment processor and verification authority. AGILANG supplies orchestration, merchant and administrator APIs, monitoring state, idempotency, webhook processing, audit logs and alerts.

The included HTTP server must run behind a production TLS reverse proxy. Merchant identity headers must be injected by a trusted authenticated application or gateway. Do not expose the service directly to the public internet except for the Stripe webhook route through controlled routing.

## Configuration

Copy `examples/stripe-connect/.env.example` into your secret-management system. Do not commit credentials.

Required values:

```text
STRIPE_SECRET_KEY
STRIPE_CONNECT_WEBHOOK_SECRET
AGILANG_STRIPE_ADMIN_TOKEN
```

Optional values include `STRIPE_PUBLISHABLE_KEY`, `STRIPE_API_VERSION`, `STRIPE_CONNECT_DATABASE`, host, port, timeout and webhook tolerance.

## Install and test

```bash
pip install -e .
python -m pytest tests/test_stripe_connect.py -q
```

## Start the service

Load the environment through your process supervisor or secret manager, then run:

```bash
agi-stripe-connect --host 127.0.0.1 --port 8787
```

Equivalent command:

```bash
python -m agilang.stripe_connect_server --host 127.0.0.1 --port 8787
```

## Endpoints

### Public health

```text
GET /health
```

### Stripe webhook

```text
POST /webhooks/stripe/connect
Stripe-Signature: ...
```

The exact raw request body is verified before parsing.

### Merchant onboarding

Authenticated upstream applications must inject:

```text
X-AGILANG-Merchant-ID: merchant-123
```

Create an Express account:

```http
POST /merchant/onboarding/account
Content-Type: application/json
X-AGILANG-Merchant-ID: merchant-123

{
  "email": "merchant@example.com",
  "country": "US",
  "business_type": "company"
}
```

Create a hosted onboarding link:

```http
POST /merchant/onboarding/link
X-AGILANG-Merchant-ID: merchant-123

{
  "account_id": "acct_...",
  "refresh_url": "https://platform.example/connect/refresh",
  "return_url": "https://platform.example/connect/complete"
}
```

Create an embedded-component account session:

```http
POST /merchant/onboarding/session
X-AGILANG-Merchant-ID: merchant-123

{
  "account_id": "acct_..."
}
```

Only return the short-lived `client_secret` to the authenticated browser session that requested it. Never store it in logs or persistent browser storage.

### Destination payment

Amounts use integer minor units.

```http
POST /merchant/payments
X-AGILANG-Merchant-ID: merchant-123

{
  "connected_account_id": "acct_...",
  "amount": 10000,
  "currency": "usd",
  "application_fee_amount": 500,
  "payment_reference": "order-2026-0001",
  "metadata": {
    "order_id": "2026-0001"
  }
}
```

The stable payment reference becomes part of the idempotency key. Repeating the same operation with the same reference does not intentionally create another payment.

### Refund

```http
POST /merchant/refunds
X-AGILANG-Merchant-ID: merchant-123

{
  "payment_intent_id": "pi_...",
  "refund_reference": "refund-2026-0001",
  "amount": 2500,
  "refund_application_fee": true,
  "reverse_transfer": true
}
```

### Administrator API

Supply:

```text
Authorization: Bearer <AGILANG_STRIPE_ADMIN_TOKEN>
```

Available endpoints:

```text
GET  /admin/summary
GET  /admin/accounts/acct_...
GET  /admin/disputes
POST /admin/reconcile/accounts
```

Reconciliation body:

```json
{
  "account_ids": ["acct_1", "acct_2"]
}
```

The administrator summary contains onboarding states, Stripe object counts and amounts, webhook processing status, open alerts and oldest unprocessed webhook age.

## Events handled

The event dispatcher persists and monitors account, payment, charge, refund, transfer, payout and dispute objects. Important events such as failed payouts, failed payments and new disputes create administrator alerts.

Recommended Connect webhook subscriptions include:

```text
account.updated
account.application.deauthorized
capability.updated
person.updated
payment_intent.created
payment_intent.processing
payment_intent.succeeded
payment_intent.payment_failed
charge.succeeded
charge.refunded
refund.updated
transfer.created
transfer.updated
transfer.reversed
payout.created
payout.updated
payout.paid
payout.failed
payout.canceled
charge.dispute.created
charge.dispute.updated
charge.dispute.closed
```

## Security requirements before deployment

1. Put the service behind HTTPS and an authenticated reverse proxy.
2. Keep Stripe and admin secrets in a vault or protected environment variables.
3. Separate test and live deployments and databases.
4. Permit the webhook route without merchant authentication, but require valid Stripe signatures.
5. Inject merchant identity only after your application authenticates and authorizes the merchant.
6. Restrict the administrator routes by network policy in addition to the bearer token.
7. Rotate credentials and admin tokens periodically.
8. Back up the SQLite database or replace the store with a transactional production database when scaling horizontally.
9. Run webhook delivery retry monitoring and alert on failed or delayed events.
10. Never store card numbers, CVC values, secret keys or account-session client secrets.

## AGILANG application surface

AGILANG `.agi` applications can import and invoke the hosted runtime capability through the existing AGILANG runtime bridge. The underlying implementation remains part of the AGILANG runtime, while application code remains AGILANG-native. A future parser-level `stripe.connect` namespace can lower directly to this gateway without changing its security and persistence contracts.
