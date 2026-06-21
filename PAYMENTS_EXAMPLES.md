# Payment API Examples

These examples show backend structure for Stripe and PayPal integration. Keep secrets in `.env`.

## Stripe Environment

```env
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_PRICE_ID=price_xxxxx
APP_URL=http://127.0.0.1:8000
```

## Stripe Route

```agi
fn create_stripe_checkout(request):
    if STRIPE_SECRET_KEY == "":
        return json_response({"ok": False, "error": "stripe_not_configured"}, status=500)

    return json_response({
        "ok": True,
        "provider": "stripe",
        "success_url": APP_URL + "/payments/success",
        "cancel_url": APP_URL + "/payments/cancel"
    })

app.post("/api/payments/stripe", create_stripe_checkout)
```

## PayPal Environment

```env
PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-client-secret
PAYPAL_ENV=sandbox
```

## PayPal Route

```agi
fn paypal_base_url() -> string:
    if PAYPAL_ENV == "live":
        return "https://api-m.paypal.com"
    return "https://api-m.sandbox.paypal.com"

fn create_paypal_order(request):
    if PAYPAL_CLIENT_ID == "" or PAYPAL_CLIENT_SECRET == "":
        return json_response({"ok": False, "error": "paypal_not_configured"}, status=500)

    return json_response({
        "ok": True,
        "provider": "paypal",
        "api_base": paypal_base_url()
    })

app.post("/api/payments/paypal", create_paypal_order)
```
