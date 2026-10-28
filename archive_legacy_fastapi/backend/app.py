from collections.abc import Callable
from pathlib import Path
from typing import Any

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
from backend.config import Settings
from backend.tickets import install_ticket_routes
from backend.support import install_support_routes
from backend.system_admin import install_system_admin_routes


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PUBLIC_FILES = {
    "script.js", "auth.js", "account.js", "tickets.js", "tickets.css", "style.css",
    "pages.css", "landing-vi.css", "account.css", "workspace.css", "workspace.js",
    "chat.js", "chat.css", "knowledge.js", "knowledge.css", "ticket-ai.css", "report.css", "admin.css",
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
        if request.url.path.startswith("/api/") and request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("origin") != origin or request.headers.get("x-vietincare-request") != "1":
                response = JSONResponse({"error": "ORIGIN_REJECTED"}, status_code=403)
            elif "application/json" not in request.headers.get("content-type", "").lower():
                response = JSONResponse({"error": "JSON_REQUIRED"}, status_code=415)
            elif int(request.headers.get("content-length", "0") or 0) > 65536:
                response = JSONResponse({"error": "BODY_TOO_LARGE"}, status_code=413)
        if response is None:
            response = await call_next(request)
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
    async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse({"error": "INVALID_INPUT"}, status_code=400)

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
        install_ticket_routes(app, database, ai, settings.ai_provider, settings.ai_chat_model)
        install_chat_routes(app, database, ai, settings.ai_threshold)
        install_knowledge_routes(app, database, ai, settings.ai_threshold)
        install_report_routes(app, database)
        install_support_routes(app, database, ai)
        install_system_admin_routes(app, database, ai)

    if serve_static:
        @app.get("/")
        def home() -> RedirectResponse:
            return RedirectResponse("/VI/index-vi.html", status_code=307)

        @app.get("/{asset_path:path}")
        def public_asset(asset_path: str) -> FileResponse:
            asset = Path(asset_path)
            allowed_page = len(asset.parts) == 2 and asset.parts[0] in {"VI", "EN"} and asset.name in {
                f"{page}-{language}.html"
                for page in ("index", "login", "register", "account", "account-profile", "tickets", "chat", "knowledge")
                for language in ("vi", "en")
            }
            if asset_path not in PUBLIC_FILES and not allowed_page:
                raise ApiError(404, "NOT_FOUND")
            path = (PROJECT_ROOT / asset).resolve()
            if PROJECT_ROOT not in path.parents or not path.is_file():
                raise ApiError(404, "NOT_FOUND")
            return FileResponse(path)

    return app
