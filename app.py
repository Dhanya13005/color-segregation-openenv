"""
app.py — AI Conveyor Color Segregation System
==============================================
Backend: FastAPI + MongoDB Atlas (Motor async)
Auth:    JWT Bearer tokens
Hashing: hashlib.sha256 (Python 3.14 safe — no bcrypt/passlib)
TLS Fix: certifi for MongoDB Atlas SSL

OpenEnv Hackathon endpoints:
  POST /openenv/reset    — reset environment state
  GET  /openenv/validate — return capabilities

Install:
  pip install -r requirements.txt

Run:
  uvicorn app:app --reload --port 8000
"""

import os, re, secrets, hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

import certifi
import yaml
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from jose import JWTError, jwt

# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════
_cfg_path = Path(__file__).parent / "openenv.yaml"
_cfg_file: dict = {}
if _cfg_path.exists():
    with open(_cfg_path) as f:
        _cfg_file = yaml.safe_load(f) or {}

def cfg(key: str, default=None):
    return os.environ.get(key, _cfg_file.get(key, default))

PORT             = int(cfg("FASTAPI_PORT", 8000))
DEBUG            = str(cfg("DEBUG", "true")).lower() == "true"
MONGO_URI        = cfg("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB         = cfg("MONGO_DB", "conveyor_db")
SECRET_KEY       = cfg("SECRET_KEY", secrets.token_hex(32))
JWT_ALGO         = "HS256"
JWT_EXPIRE_HOURS = int(cfg("JWT_EXPIRE_HOURS", 8))

# ══════════════════════════════════════════════════════════════
#  PASSWORD HASHING (sha256 — works on all Python versions)
# ══════════════════════════════════════════════════════════════
def hash_password(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return secrets.compare_digest(
        hashlib.sha256(plain.encode("utf-8")).hexdigest(), hashed
    )

# ══════════════════════════════════════════════════════════════
#  JWT
# ══════════════════════════════════════════════════════════════
def create_token(username: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": exp}, SECRET_KEY, algorithm=JWT_ALGO)

def decode_token(token: str) -> Optional[str]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGO]).get("sub")
    except JWTError:
        return None

# ══════════════════════════════════════════════════════════════
#  SEED USERS
# ══════════════════════════════════════════════════════════════
SEED_USERS = [
    {"username": "admin", "pw_hash": hash_password("admin123"),
     "email": "admin@conveyor.local", "role": "admin"},
    {"username": "demo",  "pw_hash": hash_password("demo"),
     "email": "demo@conveyor.local",  "role": "user"},
]

# ══════════════════════════════════════════════════════════════
#  MONGODB GLOBALS
# ══════════════════════════════════════════════════════════════
mongo_client: Optional[AsyncIOMotorClient] = None
db = None

# ══════════════════════════════════════════════════════════════
#  ENVIRONMENT STATE  (for OpenEnv reset/validate)
# ══════════════════════════════════════════════════════════════
env_state = {
    "running":     False,
    "step":        0,
    "score":       0,
    "reset_count": 0,
    "last_reset":  None,
}

# ══════════════════════════════════════════════════════════════
#  LIFESPAN
# ══════════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_client, db

    # Strip stray tls params from URI
    _uri = MONGO_URI
    if "mongodb+srv://" in _uri and "tls=" in _uri:
        import urllib.parse as _up
        _p  = _up.urlparse(_uri)
        _qs = _up.parse_qs(_p.query, keep_blank_values=True)
        for _k in ("tls", "ssl"):
            _qs.pop(_k, None)
        _uri = _up.urlunparse(
            _p._replace(query=_up.urlencode({k: v[0] for k, v in _qs.items()}))
        )

    mongo_client = AsyncIOMotorClient(
        _uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=20000,
        socketTimeoutMS=20000,
    )
    db = mongo_client[MONGO_DB]

    try:
        await mongo_client.admin.command("ping")
        print(f"✅ MongoDB Connected → database='{MONGO_DB}'")
    except Exception as e:
        print(f"❌ MongoDB Error: {e}")

    for seed in SEED_USERS:
        if not await db["users"].find_one({"username": seed["username"]}):
            doc = {**seed, "created_at": datetime.now(timezone.utc).isoformat()}
            await db["users"].insert_one(doc)
            print(f"   Seeded user: {seed['username']}")

    await db["users"].create_index("username", unique=True)
    await db["scores"].create_index([("saved_at", -1)])

    print(f"🚀 Server ready → http://127.0.0.1:{PORT}")
    print(f"   Admin: username=admin  password=admin123")
    print(f"   Docs:  http://127.0.0.1:{PORT}/docs")

    yield
    mongo_client.close()
    print("MongoDB connection closed.")

# ══════════════════════════════════════════════════════════════
#  FASTAPI APP
# ══════════════════════════════════════════════════════════════
app = FastAPI(
    title="AI Conveyor API",
    version="3.0.0",
    description="FastAPI + MongoDB backend for AI Conveyor Color Segregation.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ══════════════════════════════════════════════════════════════
#  AUTH DEPENDENCY
# ══════════════════════════════════════════════════════════════
bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer)
) -> str:
    if not creds:
        raise HTTPException(401, detail="Missing authentication token.")
    username = decode_token(creds.credentials)
    if not username:
        raise HTTPException(401, detail="Invalid or expired token.")
    return username

# ══════════════════════════════════════════════════════════════
#  SCHEMAS
# ══════════════════════════════════════════════════════════════
class RegisterReq(BaseModel):
    username: str
    password: str
    email:    Optional[str] = ""

class LoginReq(BaseModel):
    username: str
    password: str

class ScoreReq(BaseModel):
    score:     int
    user:      Optional[str] = None
    timestamp: Optional[str] = None

# ══════════════════════════════════════════════════════════════
#  ✅  OPENENV ROUTES  — must come BEFORE StaticFiles mount
#      These are the routes the hackathon checker calls.
# ══════════════════════════════════════════════════════════════

@app.post("/openenv/reset", tags=["openenv"],
          summary="Reset environment — required by OpenEnv checker (POST OK)")
async def openenv_reset_post():
    """
    OpenEnv hackathon POST /openenv/reset endpoint.
    Resets simulation environment state and returns HTTP 200.
    """
    env_state["running"]     = False
    env_state["step"]        = 0
    env_state["score"]       = 0
    env_state["reset_count"] += 1
    env_state["last_reset"]  = datetime.now(timezone.utc).isoformat()

    return {
        "success": True,
        "message": "Environment reset successful",
        "state":   env_state.copy(),
    }


@app.get("/openenv/reset", tags=["openenv"],
         summary="Reset environment (GET — probed by some checkers)")
async def openenv_reset_get():
    """GET version — some checkers probe with GET before POST."""
    return await openenv_reset_post()


@app.get("/openenv/validate", tags=["openenv"],
         summary="Validate environment capabilities")
async def openenv_validate():
    """Return system capabilities for OpenEnv validation."""
    db_ok = False
    try:
        await mongo_client.admin.command("ping")
        db_ok = True
    except Exception:
        pass

    return {
        "success":      True,
        "project":      "AI Conveyor Color Segregation System",
        "version":      "3.0.0",
        "db_connected": db_ok,
        "env_state":    env_state.copy(),
        "features": [
            "user_registration",
            "user_login_jwt",
            "color_segregation_game",
            "score_tracking",
            "leaderboard",
            "openai_inference",
        ],
        "endpoints": {
            "POST /openenv/reset":    "Reset environment",
            "GET  /openenv/validate": "Validate capabilities",
            "POST /api/register":     "Register user",
            "POST /api/login":        "Login (JWT)",
            "GET  /api/me":           "Current user",
            "POST /api/scores":       "Save score",
            "GET  /api/scores":       "Score history",
            "GET  /api/status":       "Health check",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/openenv/validate", tags=["openenv"])
async def openenv_validate_post():
    """POST version of validate."""
    return await openenv_validate()


# ══════════════════════════════════════════════════════════════
#  API ROUTES
# ══════════════════════════════════════════════════════════════

@app.post("/api/register", status_code=201, tags=["auth"])
async def register(data: RegisterReq):
    username = data.username.strip()
    if len(username) < 3 or len(username) > 30:
        raise HTTPException(400, detail={"success": False,
            "message": "Username must be 3–30 characters."})
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise HTTPException(400, detail={"success": False,
            "message": "Only letters, numbers, underscores allowed."})
    if len(data.password) < 4:
        raise HTTPException(400, detail={"success": False,
            "message": "Password must be at least 4 characters."})

    existing = await db["users"].find_one(
        {"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}}
    )
    if existing:
        raise HTTPException(400, detail={"success": False,
            "message": "Username already taken. Please choose another."})

    await db["users"].insert_one({
        "username":   username,
        "pw_hash":    hash_password(data.password),
        "email":      (data.email or "").strip(),
        "role":       "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"success": True, "message": f"Account '{username}' created."}


@app.post("/api/login", tags=["auth"])
async def login(data: LoginReq):
    user = await db["users"].find_one(
        {"username": {"$regex": f"^{re.escape(data.username.strip())}$",
                      "$options": "i"}}
    )
    if not user or not verify_password(data.password, user["pw_hash"]):
        raise HTTPException(401, detail={"success": False,
            "message": "Invalid username or password."})

    token = create_token(user["username"])
    return {
        "success":  True,
        "token":    token,
        "username": user["username"],
        "role":     user.get("role", "user"),
    }


@app.get("/api/me", tags=["auth"])
async def get_me(current_user: str = Depends(get_current_user)):
    user = await db["users"].find_one(
        {"username": current_user}, {"pw_hash": 0, "_id": 0}
    )
    if not user:
        raise HTTPException(404, detail="User not found.")
    return {"success": True, "user": user}


@app.post("/api/scores", tags=["scores"])
async def save_score(data: ScoreReq,
                     current_user: str = Depends(get_current_user)):
    doc = {
        "user":     data.user or current_user,
        "score":    data.score,
        "saved_at": data.timestamp or datetime.now(timezone.utc).isoformat(),
    }
    await db["scores"].insert_one(doc)
    return {"success": True, "message": "Score saved."}


@app.get("/api/scores", tags=["scores"])
async def get_scores():
    cursor = db["scores"].find({}, {"_id": 0}).sort("saved_at", -1).limit(200)
    rows = await cursor.to_list(length=200)
    for r in rows:
        if "saved_at" in r and "timestamp" not in r:
            r["timestamp"] = r.pop("saved_at")
    return rows


@app.get("/api/status", tags=["system"])
async def get_status():
    db_ok = False
    try:
        await mongo_client.admin.command("ping")
        db_ok = True
    except Exception:
        pass
    return {
        "status":    "ok" if db_ok else "degraded",
        "db":        "mongodb_atlas",
        "db_ok":     db_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
#  STATIC FILES
#  Mount on "/static" prefix so openenv routes are never shadowed.
#  The root "/" and "/{path}" routes serve index.html manually.
# ══════════════════════════════════════════════════════════════
_static = Path(__file__).parent / "static"

# Mount CSS/JS/SVG assets under /static
app.mount("/static", StaticFiles(directory=str(_static)), name="static_assets")


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(_static / "index.html")


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    """
    SPA fallback — serve index.html for any unknown path
    EXCEPT routes already handled above (api/*, openenv/*).
    """
    # Let FastAPI handle known prefixes — only catch unknown paths
    if full_path.startswith(("api/", "openenv/", "docs", "redoc", "openapi")):
        raise HTTPException(404)

    # Serve actual static file if it exists
    file_path = _static / full_path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # Otherwise serve SPA shell
    return FileResponse(_static / "index.html")


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=DEBUG)
