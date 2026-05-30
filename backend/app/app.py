# backend/app/app.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes.radar import router as radar_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="AEGIS API",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5175",
            "http://localhost:5175",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(
        radar_router,
        prefix="/api/radar",
        tags=["radar"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()