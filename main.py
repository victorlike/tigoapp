"""
main.py — FastAPI application entry point
"""
import os
from fastapi import FastAPI, Request, Depends, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from routes import leads, agents, followups, sales, coordinator

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


# ─── Health check ───────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
