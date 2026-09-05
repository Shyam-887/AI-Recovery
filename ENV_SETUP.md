# .env configuration

## Backend
Edit `backend/.env`.

Local defaults are already filled in for PostgreSQL, Redis and Celery.
Put your real Stripe/Razorpay credentials in this file when you have them.

## Frontend
The frontend reads `VITE_API_URL` at build time. For local development:
`http://localhost:8000/api/v1`

## Production
Do not commit real secrets. Replace `JWT_SECRET` with a long random secret and
inject provider credentials through your deployment platform's secret manager.
