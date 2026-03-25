"""
main.py — FastAPI application entry point
"""
import os
from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from routes import leads, agents, followups, sales, coordinator, seller, admin

load_dotenv()

app = FastAPI(title="Tigo Leads API", version="2.0.0")

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


# ─── Startup Event ───────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Run migrations on startup."""
    from routes.admin import migrate_admin_schema
    migrate_admin_schema()
    try:
        import migrate_catalog
        migrate_catalog.run()
    except Exception as e:
        print("Error migrating catalog:", e)


# ─── Frontend routes (Jinja2 views) ─────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    """Default redirect to login."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/leaddesk", response_class=HTMLResponse, include_in_schema=False)
async def leaddesk(request: Request):
    """Agent view."""
    return templates.TemplateResponse("leaddesk.html", {"request": request})


@app.get("/coordinator", response_class=HTMLResponse, include_in_schema=False)
async def coordinator_view(request: Request):
    """Coordinator view."""
    return templates.TemplateResponse("coordinator.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_view(request: Request):
    """Administrator view."""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/backoffice", response_class=HTMLResponse, include_in_schema=False)
async def backoffice_view(request: Request):
    """Backoffice management view."""
    return templates.TemplateResponse("backoffice.html", {"request": request})


# ─── Health check ───────────────────────────────────────
@app.get("/health")
async def health():
    """Verify API and Database connectivity."""
    from database import fetchone
    db_ok = False
    try:
        # Simple query to test DB
        fetchone("SELECT 1")
        db_ok = True
    except:
        pass
    
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "version": "2.0.4"
    }


# ─── Global Exception Handler ───────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions to avoid generic 500 HTML pages."""
    # If it's already an HTTPException, let it through
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "error": exc.detail}
        )
    
    # Otherwise, log it and return a 500 JSON
    import logging
    logging.getLogger("uvicorn.error").error(f"Global exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )
