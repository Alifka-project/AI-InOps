"""FastAPI application entrypoint.

Wires routers, CORS, structured exception handling, and request logging.
"""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .models import HealthResponse
from .routers import (
    data,
    datasets,
    forecast,
    report,
    simulate,
    transport,
    warehouse,
)

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("digital_twin")

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Digital Twin for Electrolux UAE supply-chain & warehouse operations — "
        "sensitive-material supply resilience under the 2026 Strait of Hormuz crisis."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# --------------------------------------------------------------------------
# Structured exception handlers
# --------------------------------------------------------------------------
def _clean_errors(errors: list) -> list:
    """Strip non-serialisable objects (e.g. ValueError in ctx) from errors."""
    cleaned = []
    for err in errors:
        item = {k: v for k, v in err.items() if k != "ctx"}
        ctx = err.get("ctx")
        if ctx:
            item["ctx"] = {k: str(v) for k, v in ctx.items()}
        cleaned.append(item)
    return cleaned


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "validation_error",
                "message": "Request validation failed.",
                "details": _clean_errors(exc.errors()),
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"type": "http_error", "message": str(exc.detail)}},
    )


@app.exception_handler(KeyError)
async def key_error_handler(request: Request, exc: KeyError):
    return JSONResponse(
        status_code=400,
        content={"error": {"type": "bad_request", "message": str(exc).strip("'\"")}},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"error": {"type": "value_error", "message": str(exc)}},
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "internal_error",
                "message": "An unexpected error occurred.",
            }
        },
    )


# --------------------------------------------------------------------------
# Health + routers
# --------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok", app_env=settings.app_env, version=settings.version
    )


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
    }


app.include_router(datasets.router)
app.include_router(data.router)
app.include_router(forecast.router)
app.include_router(transport.router)
app.include_router(warehouse.router)
app.include_router(simulate.router)
app.include_router(report.router)
