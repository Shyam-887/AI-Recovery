# AI Revenue Recovery — PostgreSQL + Alembic + Redis/Celery

This version adds:
- PostgreSQL with SQLAlchemy 2.x async ORM
- Alembic migrations
- Redis broker/result backend
- Celery worker
- Persistent organizations, users, customers, payments, recovery cases, actions and audit logs
- Transactional task enqueue pattern (Celery task is queued after DB commit)

## Start infrastructure

```bash
docker compose up -d postgres redis
```

## Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env`.

## Create database schema

```bash
alembic upgrade head
```

## Run API

```bash
uvicorn app.main:app --reload
```

## Run worker

In another terminal:

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

## Demo

POST `/api/v1/events/payment-failed`:

```json
{
  "organization_id": "00000000-0000-0000-0000-000000000001",
  "customer_id": "00000000-0000-0000-0000-000000000002",
  "customer_name": "Rahul Sharma",
  "amount": 4999,
  "currency": "INR",
  "reason": "insufficient_funds",
  "attempt_number": 1,
  "payment_method": "card"
}
```

For a real deployment, create organization/customer rows first and pass their UUIDs.

## Architecture

Webhook -> PostgreSQL transaction -> Celery/Redis task -> Risk/Diagnosis/Recommendation ->
Policy -> Integration -> Recovery Action + Audit Log.

The task updates the same recovery case in PostgreSQL, so state survives API/worker restarts.


## Authentication & RBAC (v2.1)

Register:
```bash
POST /api/v1/auth/register
```

Login:
```bash
POST /api/v1/auth/login
```

Use the returned bearer token on protected recovery APIs.

Roles:
- admin: full access
- manager: recovery operations
- agent: recovery actions
- viewer: read-only

Tenant isolation is enforced using the organization ID carried in the JWT.
Run the new migration with:

```bash
cd backend
alembic upgrade head
```


## Payment Gateway Webhooks (v2.2)

Configure:
```env
STRIPE_WEBHOOK_SECRET=whsec_...
RAZORPAY_WEBHOOK_SECRET=...
```

Endpoints:
- `POST /api/v1/webhooks/stripe`
- `POST /api/v1/webhooks/razorpay`

Both endpoints verify signatures before accepting events and store provider event IDs/hashes
to reject duplicate webhook deliveries.

Run:
```bash
cd backend
alembic upgrade head
```


## Action Execution (v2.3)

Recovery decisions now create persistent `RecoveryAction` records and execute through an
adapter boundary. Notification execution is currently a safe console provider, while
Stripe/Razorpay payment adapters expose the production integration boundary.

High-value/blocked cases require manager/admin approval via:
`POST /api/v1/recovery/cases/{case_id}/execute`.

Configure provider credentials in `.env` before enabling real external API calls.

## Payment History Dashboard (v2.4)

The dashboard now includes a payment ledger with transaction ID, customer, amount, status, provider, payment method, attempt number and timestamp, plus search and status filters.

Payment history API:
`GET /api/v1/payments`

Payment method is stored with each payment. Stripe/Razorpay webhook normalization also attempts to capture the method and masked last four digits when the provider payload exposes them.

Run the migration:
```bash
cd backend
alembic upgrade head
```
