from collections.abc import Callable
from pathlib import Path
from typing import Any
import json
import mysql.connector

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from backend.errors import ApiError
from backend.admin import install_admin_routes
from backend.customers import install_customer_routes
from backend.knowledge import install_knowledge_routes
from backend.reports import install_report_routes
from backend.auth import install_auth_routes
from backend.chats import install_chat_routes
from backend.ai import AIProvider
from backend.ai import mask_display
from backend.config import Settings
from backend.tickets import install_ticket_routes
from backend.support import install_support_routes
from backend.system_admin import install_system_admin_routes
from backend.automation import install_automation_routes
from backend.db import Database
from starlette.concurrency import run_in_threadpool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_FILES = {
    "script.js",
    "auth.js",
    "account.js",
    "tickets.js",
    "tickets.css",
    "style.css",
    "pages.css",
    "landing-vi.css",
    "account.css",
    "workspace.css",
    "workspace.js",
    "chat.js",
    "chat.css",
    "knowledge.js",
    "knowledge.css",
    "ticket-ai.css",
    "report.css",
    "admin.css",
    "acceptance.js",
}


def create_app(
    db_probe: Callable[[], None] | None = None,
    *,
    origin: str = "http://localhost:3000",
    serve_static: bool = False,
    database: Any | None = None,
    settings: Settings | None = None,
    ai: AIProvider | None = None,
    sms_sender: Any | None = None,
) -> FastAPI:
    if settings is not None:
        origin = settings.origin
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def secure_requests(request: Request, call_next: Callable) -> JSONResponse:
        response = None
        if request.url.path.startswith("/api/") and request.method not in {
            "GET",
            "HEAD",
            "OPTIONS",
        }:
            if (
                request.headers.get("origin") != origin
                or request.headers.get("x-vietincare-request") != "1"
            ):
                response = JSONResponse({"error": "ORIGIN_REJECTED"}, status_code=403)
            elif (
                "application/json"
                not in request.headers.get("content-type", "").lower()
            ):
                response = JSONResponse({"error": "JSON_REQUIRED"}, status_code=415)
            else:
                try:
                    length = int(request.headers.get("content-length", "0") or 0)
                except ValueError:
                    length = -1
                if length < 0:
                    response = JSONResponse({"error": "INVALID_INPUT"}, status_code=400)
                elif length > 65536 or len(await request.body()) > 65536:
                    response = JSONResponse(
                        {"error": "BODY_TOO_LARGE"}, status_code=413
                    )
        if response is None:
            response = await call_next(request)
        if (
            isinstance(database, Database)
            and request.method == "GET"
            and response.status_code == 200
            and request.url.path.startswith("/api/")
            and request.url.path not in {"/api/health", "/api/auth/me"}
        ):

            def audit_read() -> None:
                actor = getattr(request.state, "authenticated_user", None)
                if actor is None:
                    return
                database.execute(
                    "INSERT INTO AuditLog(MaUser,HanhDong,DoiTuong,DiaChiIP) VALUES(?,'ACCESS_READ',?,?)",
                    (
                        actor["MaUser"],
                        request.url.path[:100],
                        request.client.host if request.client else None,
                    ),
                )

            await run_in_threadpool(audit_read)
        if request.url.path.startswith(
            "/api/"
        ) and "application/json" in response.headers.get("content-type", ""):

            def masked(value: Any, field: str = "") -> Any:
                if isinstance(value, str):
                    if field in {"phone", "email", "actorEmail"}:
                        return value  # Authorized contact fields remain editable; free-text secrets are masked.
                    return mask_display(value)
                if isinstance(value, list):
                    return [masked(item) for item in value]
                if isinstance(value, dict):
                    return {key: masked(item, key) for key, item in value.items()}
                return value

            if hasattr(response, "body_iterator"):
                body = b"".join([chunk async for chunk in response.body_iterator])
                sanitized = JSONResponse(
                    masked(json.loads(body)), status_code=response.status_code
                )
                # Retain all headers, including repeated Set-Cookie values.
                sanitized.raw_headers += [
                    (k, v)
                    for k, v in response.raw_headers
                    if k not in {b"content-length", b"content-type"}
                ]
                response = sanitized
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
        return JSONResponse({"error": error.code}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse({"error": "INVALID_INPUT"}, status_code=400)

    @app.exception_handler(mysql.connector.Error)
    async def handle_database_error(
        request: Request, error: mysql.connector.Error
    ) -> JSONResponse:
        if error.errno in {1205, 1213}:
            return JSONResponse({"error": "CONCURRENT_UPDATE"}, status_code=409)
        return JSONResponse({"error": "DATABASE_UNAVAILABLE"}, status_code=503)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        if db_probe is None and database is None:
            raise ApiError(503, "SERVICE_UNAVAILABLE")
        try:
            if database is not None:
                database.fetch_one("SELECT 1 AS ready")
            else:
                db_probe()
        except Exception as error:
            raise ApiError(503, "SERVICE_UNAVAILABLE") from error
        return {"status": "ok"}

    if database is not None and settings is not None:
        ai = ai or AIProvider(settings)
        install_auth_routes(app, database, settings, sms_sender)
        install_admin_routes(app, database)
        install_customer_routes(app, database)
        install_ticket_routes(
            app, database, ai, settings.ai_provider, settings.ai_chat_model
        )
        install_chat_routes(app, database, ai, settings.ai_threshold)
        install_knowledge_routes(app, database, ai, settings.ai_threshold)
        install_report_routes(app, database)
        install_support_routes(app, database, ai)
        install_system_admin_routes(app, database, ai)
        install_automation_routes(app, database, ai)

    if serve_static:

        @app.get("/")
        def home() -> RedirectResponse:
            return RedirectResponse("/VI/index-vi.html", status_code=307)

        @app.get("/{asset_path:path}")
        def public_asset(asset_path: str) -> FileResponse:
            asset = Path(asset_path)
            allowed_page = (
                len(asset.parts) == 2
                and asset.parts[0] in {"VI", "EN"}
                and asset.name
                in {
                    f"{page}-{language}.html"
                    for page in (
                        "index",
                        "login",
                        "register",
                        "account",
                        "account-profile",
                        "tickets",
                        "chat",
                        "knowledge",
                    )
                    for language in ("vi", "en")
                }
            )
            if asset_path not in PUBLIC_FILES and not allowed_page:
                raise ApiError(404, "NOT_FOUND")
            path = (PROJECT_ROOT / asset).resolve()
            if PROJECT_ROOT not in path.parents or not path.is_file():
                raise ApiError(404, "NOT_FOUND")
            return FileResponse(path)

    return app
