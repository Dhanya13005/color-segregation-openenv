"""
app.py — AI Conveyor Color Segregation System — FastAPI Backend
================================================================
Responsibilities:
  - Serve static frontend files from /static
  - POST /api/login  — mock or real authentication
  - POST /api/scores — persist a score entry
  - GET  /api/scores — return score history (latest first)
  - GET  /api/status — health / state check

Persistence: SQLite via Python's built-in sqlite3 module.
DB file path is configurable via openenv.yaml / environment variable DB_PATH.

Run:
    uvicorn app:app --reload --port 8000

Requirements (see openenv.yaml):
    pip install fastapi uvicorn python-multipart pyyaml
"""

import sqlite3
import json
import os
import secrets
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

import yaml  # PyYAML — pip install pyyaml
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ─── Load Config from openenv.yaml ───────────────────────────────────────────
_config_path = Path(__file__).parent / "openenv.yaml"
_config: dict = {}

if _config_path.exists():
    with open(_config_path, "r") as f:
        _config = yaml.safe_load(f) or {}

def cfg(key: str, default=None):
    """Read from YAML config, then environment variable override, then default."""
    env_val = os.environ.get(key)
    if env_val is not None:
        return env_val
    return _config.get(key, default)

# ─── Settings ─────────────────────────────────────────────────────────────────
PORT       = int(cfg("FASTAPI_PORT", 8000))
DB_PATH    = cfg("DB_PATH", "scores.db")
DEBUG      = cfg("DEBUG", "true").lower() == "true"
SECRET_KEY = cfg("SECRET_KEY", secrets.token_hex(32))

# ─── Mock user store — replace with a real DB/auth in production ──────────────
# Format: { username: hashed_password }
MOCK_USERS = {
    "admin": hashlib.sha256("admin".encode()).hexdigest(),
    "demo":  hashlib.sha256("demo".encode()).hexdigest(),
    "user":  hashlib.sha256("password".encode()).hexdigest(),
}

# ─── Simple in-memory session store (NOT for production use) ─────────────────
_sessions: dict[str, str] = {}   # token → username


# ─── Database setup ───────────────────────────────────────────────────────────
def get_db() -> sqlite3.Connection:
    """Return a new SQLite connection. Called per request for thread safety."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist. Called at startup."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT    NOT NULL,
            score     INTEGER NOT NULL,
            timestamp TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    if DEBUG:
        print(f"[DB] Initialised SQLite at '{DB_PATH}'")


# ─── Lifespan (replaces deprecated @app.on_event) ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    init_db()
    if DEBUG:
        print(f"[APP] AI Conveyor backend running on port {PORT} (debug={DEBUG})")
    yield
    # Shutdown — nothing to clean up for SQLite


# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Conveyor Color Segregation API",
    version="1.0.0",
    description="Backend for the AI Conveyor Color Segregation simulation.",
    lifespan=lifespan,
)

# CORS — allow all origins for local dev; tighten for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class ScoreRequest(BaseModel):
    user: str
    score: int
    timestamp: Optional[str] = None


# ─── Helper: validate session token from cookie ───────────────────────────────
def get_session_user(request: Request) -> Optional[str]:
    token = request.cookies.get("session_token")
    return _sessions.get(token) if token else None


# ─── API Routes ───────────────────────────────────────────────────────────────

@app.post("/api/login", summary="Authenticate user and create a session cookie")
async def login(payload: LoginRequest, response: Response):
    """
    Mock authentication endpoint.
    In production: replace MOCK_USERS with a real user DB query.
    Returns a session cookie on success.
    """
    username = payload.username.strip().lower()
    pw_hash  = hashlib.sha256(payload.password.encode()).hexdigest()

    stored_hash = MOCK_USERS.get(username)
    if not stored_hash or not secrets.compare_digest(pw_hash, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": "Invalid username or password."},
        )

    # Issue a simple session token
    token = secrets.token_hex(24)
    _sessions[token] = username

    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,  # 8-hour session
        secure=False,          # Set True behind HTTPS in production
    )

    return {"success": True, "username": username}


@app.post("/api/scores", summary="Save a score entry to the database")
async def post_score(payload: ScoreRequest):
    """
    Persist a score record.
    Accepts: { user, score, timestamp }
    timestamp should be ISO-8601 string; defaults to now() if omitted.
    """
    ts = payload.timestamp or datetime.now(timezone.utc).isoformat()
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO scores (username, score, timestamp) VALUES (?, ?, ?)",
            (payload.user, payload.score, ts),
        )
        conn.commit()
    finally:
        conn.close()

    return {"success": True, "message": "Score saved."}


@app.get("/api/scores", summary="Retrieve all score history, latest first")
async def get_scores():
    """
    Returns a JSON array of score objects sorted by id DESC (newest first).
    Each object: { user, score, timestamp }
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT username AS user, score, timestamp FROM scores ORDER BY id DESC LIMIT 200"
        ).fetchall()
    finally:
        conn.close()

    return [dict(row) for row in rows]


@app.get("/api/status", summary="Health check / running state")
async def get_status():
    """
    Simple health-check endpoint.
    Extend to return server-side simulation state if needed.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db": DB_PATH,
        "debug": DEBUG,
    }


# ─── Serve Static Frontend ────────────────────────────────────────────────────
# Mount AFTER API routes so /api/* takes precedence.
_static_dir = Path(__file__).parent / "static"

@app.get("/", include_in_schema=False)
async def index():
    """Serve the main SPA page."""
    return FileResponse(_static_dir / "index.html")

# Mount /static for assets (CSS, JS, SVG)
app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")


# ─── Entry point for direct execution ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=DEBUG)