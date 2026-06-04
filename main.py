"""
main.py — FastAPI application entry point
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

from routes import leads, agents, followups, sales, coordinator, seller, admin
from auth import create_session_token, decode_session_token

load_dotenv()

# ─── Startup / Shutdown ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    from routes.admin import migrate_admin_schema
    migrate_admin_schema()
    try:
        import migrate_catalog
        migrate_catalog.run()
    except Exception as e:
        print("Error migrating catalog:", e)
    yield


app = FastAPI(title="Tigo Leads API", version="2.0.4", lifespan=lifespan)

# ─── Session middleware (protect HTML views) ─────────────
PROTECTED_PATHS = {"/leaddesk", "/coordinator", "/admin", "/backoffice"}

class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PROTECTED_PATHS:
            session = request.cookies.get("session")
            payload = decode_session_token(session) if session else None
            if not payload:
                return RedirectResponse(url="/", status_code=302)
        return await call_next(request)

app.add_middleware(SessionMiddleware)

# ─── Static files & templates ───────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ─── API Routers ────────────────────────────────────────
app.include_router(leads.router,        prefix="/api/leads",       tags=["leads"])
app.include_router(agents.router,       prefix="/api/agent",       tags=["agents"])
app.include_router(followups.router,    prefix="/api/followups",   tags=["followups"])
app.include_router(sales.router,        prefix="/api/sales",       tags=["sales"])
app.include_router(coordinator.router,  prefix="/api/coordinator", tags=["coordinator"])
app.include_router(seller.router,       prefix="/api/seller",      tags=["seller"])
app.include_router(admin.router,        prefix="/api/admin",       tags=["admin"])


# ─── Session endpoint ────────────────────────────────────
from pydantic import BaseModel

class SessionRequest(BaseModel):
    email: str
    role: str = "AGENT"

@app.post("/api/auth/session", include_in_schema=False)
async def create_session(data: SessionRequest, response: JSONResponse = None):
    """Issue a session cookie after successful login verification."""
    from fastapi.responses import JSONResponse as JR
    token = create_session_token(data.email.lower().strip(), data.role.upper())
    resp = JR(content={"success": True})
    resp.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite="strict",
        secure=False,  # set True behind HTTPS in production
        max_age=10 * 3600
    )
    return resp


@app.post("/api/auth/logout", include_in_schema=False)
async def logout():
    """Clear the session cookie."""
    from fastapi.responses import JSONResponse as JR
    resp = JR(content={"success": True})
    resp.delete_cookie("session")
    return resp


# ─── Frontend routes (Jinja2 views) ─────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/leaddesk", response_class=HTMLResponse, include_in_schema=False)
async def leaddesk(request: Request):
    return templates.TemplateResponse("leaddesk.html", {"request": request})


@app.get("/coordinator", response_class=HTMLResponse, include_in_schema=False)
async def coordinator_view(request: Request):
    return templates.TemplateResponse("coordinator.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_view(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/backoffice", response_class=HTMLResponse, include_in_schema=False)
async def backoffice_view(request: Request):
    return templates.TemplateResponse("backoffice.html", {"request": request})


# ─── Health check ───────────────────────────────────────
@app.get("/health")
async def health():
    from database import fetchone
    db_ok = False
    try:
        fetchone("SELECT 1")
        db_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "version": app.version
    }


# ─── Global Exception Handler ───────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.detail},
            headers=getattr(exc, "headers", None)
        )
    logging.getLogger("uvicorn.error").error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal Server Error"}
    )
