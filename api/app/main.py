from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

#important change 
from .routes.analyze import router as analyze_router
####

from .config import settings
from .routes.session import router as session_router
from .routes.chat import router as chat_router

from .routes.report import router as report_router

app = FastAPI(title="CopyCat-AI", version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",")] if settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
####
app.include_router(analyze_router)
#####
app.include_router(session_router)
app.include_router(chat_router)

app.include_router(report_router)

@app.get("/health")
def health():
    return {"ok": True, "env": settings.app_env}
