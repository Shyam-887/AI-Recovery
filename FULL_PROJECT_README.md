# AI Revenue Recovery — Full Stack

Includes the existing FastAPI/PostgreSQL/Redis/Celery/JWT/RBAC/payment-webhook backend and a React/Vite frontend dashboard.

## Backend
cd backend
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload

Celery:
celery -A app.core.celery_app.celery_app worker --loglevel=info

## Frontend
cd frontend
npm install
npm run dev

Set VITE_API_URL when the API is not localhost:8000.

## Infrastructure
PostgreSQL and Redis can be started with:
docker compose up -d postgres redis

The frontend preview container can be built with:
docker compose -f docker-compose.full.yml up --build
