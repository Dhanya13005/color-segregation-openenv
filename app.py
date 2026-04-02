import os, secrets, hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path


from contextlib import asynccontextmanager

import yaml

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from jose import jwt

# ================= CONFIG =================
_cfg_path = Path(__file__).parent / "openenv.yaml"
_cfg_file = {}

if _cfg_path.exists():
    with open(_cfg_path) as f:
        _cfg_file = yaml.safe_load(f) or {}

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"status": "reset successful"} 

@app.get("/api/scores")
async def get_scores():
    data = await db["scores"].find().to_list(100)
    for d in data:
        d.pop("_id", None)
    return data

@app.get("/api/status")
async def status():
    return {"status": "ok"}

# ================= STATIC =================
static_dir = Path(__file__).parent / "static"

@app.get("/")
async def home():
    return FileResponse(static_dir / "index.html")

app.mount("/", StaticFiles(directory=static_dir), name="static")
