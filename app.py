<<<<<<< HEAD
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
=======
import os, secrets, hashlib
>>>>>>> a963d2b (added openenv reset endpoint)
from datetime import datetime, timedelta, timezone
from pathlib import Path


from contextlib import asynccontextmanager

<<<<<<< HEAD
import certifi
import yaml
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
=======
import yaml

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import FileResponse
>>>>>>> a963d2b (added openenv reset endpoint)
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
<<<<<<< HEAD
from jose import JWTError, jwt

# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════
_cfg_path = Path(__file__).parent / "openenv.yaml"
_cfg_file: dict = {}
=======
from jose import jwt

# ================= CONFIG =================
_cfg_path = Path(__file__).parent / "openenv.yaml"
_cfg_file = {}

>>>>>>> a963d2b (added openenv reset endpoint)
if _cfg_path.exists():
    with open(_cfg_path) as f:
        _cfg_file = yaml.safe_load(f) or {}

<<<<<<< HEAD
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
=======
def cfg(key, default=None):
    return os.environ.get(key, _cfg_file.get(key, default))

PORT = int(cfg("FASTAPI_PORT", 8000))
MONGO_URI = cfg("MONGO_URI")
MONGO_DB = cfg("MONGO_DB", "conveyor_db")
SECRET_KEY = cfg("SECRET_KEY", secrets.token_hex(32))
JWT_ALGO = "HS256"

# ================= HASH =================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

def create_token(username):
    exp = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({"sub": username, "exp": exp}, SECRET_KEY, algorithm=JWT_ALGO)

def decode_token(token):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGO]).get("sub")
    except:
        return None

# ================= DB =================
client = None
db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db

    # ✅ FIXED CONNECTION
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[MONGO_DB]

    try:
        await client.admin.command("ping")
        print("✅ MongoDB Connected")
    except Exception as e:
        print("❌ MongoDB Error:", e)

    # Seed users
    for u in ["admin", "demo"]:
        if not await db["users"].find_one({"username": u}):
            await db["users"].insert_one({
                "username": u,
                "pw_hash": hash_password("admin123" if u == "admin" else "demo")
            })
            print("Seeded:", u)

    yield
    client.close()

# ================= APP =================
app = FastAPI(lifespan=lifespan)
>>>>>>> a963d2b (added openenv reset endpoint)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
<<<<<<< HEAD
    allow_credentials=True,
=======
>>>>>>> a963d2b (added openenv reset endpoint)
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
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
=======
# ================= AUTH =================
bearer = HTTPBearer()

async def get_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    user = decode_token(creds.credentials)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user

# ================= SCHEMAS =================
class Register(BaseModel):
    username: str
    password: str

class Login(BaseModel):
    username: str
    password: str

class Score(BaseModel):
    score: int

# ================= ROUTES =================

@app.post("/api/register")
async def register(data: Register):
    if await db["users"].find_one({"username": data.username}):
        raise HTTPException(400, "User already exists")

    await db["users"].insert_one({
        "username": data.username,
        "pw_hash": hash_password(data.password)
    })

    return {"success": True}

@app.post("/api/login")
async def login(data: Login):
    user = await db["users"].find_one({"username": data.username})

    if not user or not verify_password(data.password, user["pw_hash"]):
        raise HTTPException(401, "Invalid login")

    token = create_token(data.username)

    return {
        "success": True,
        "token": token,
        "username": data.username
    }


@app.post("/api/scores")
async def save_score(data: Score, user: str = Depends(get_user)):
    await db["scores"].insert_one({
        "user": user,
        "score": data.score,
        "time": datetime.now().isoformat()
    })
    return {"success": True} 

@app.post("/openenv/reset")
async def openenv_reset():
    return {
        "success": True,
        "message": "Environment reset successful"
    }

@app.get("/api/scores")
async def get_scores():
    data = await db["scores"].find().to_list(100)
    for d in data:
        d.pop("_id", None)
    return data
>>>>>>> a963d2b (added openenv reset endpoint)

@app.get("/api/status")
async def status():
    return {"status": "ok"}

<<<<<<< HEAD
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
=======
# ================= STATIC =================
static_dir = Path(__file__).parent / "static"

@app.get("/")
async def home():
    return FileResponse(static_dir / "index.html")

app.mount("/", StaticFiles(directory=static_dir), name="static")
>>>>>>> a963d2b (added openenv reset endpoint)
