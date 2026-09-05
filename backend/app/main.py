from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.auth import router as auth_router
from app.api.webhooks import router as webhook_router
from app.api.actions import router as action_router

app = FastAPI(
    title="AI Revenue Recovery Platform",
    version="2.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://[::1]:5173",
        "http://[::1]:4173",
        "http://[::1]:3000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/api/v1")
app.include_router(action_router, prefix="/api/v1")

@app.get("/")
async def health():
    return {"service": "ai-revenue-recovery", "status": "ok"}
