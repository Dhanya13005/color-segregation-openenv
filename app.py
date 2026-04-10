
"""
app.py — AI Conveyor Color Segregation System
FastAPI + MongoDB + OpenEnv Ready
"""

import os, re, secrets, hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

# Load .env locally
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except:
    pass

import certifi
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from jose import JWTError, jwt

# ================= CONFIG =================
PORT = int(os.getenv("FASTAPI_PORT", 7860))
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB = os.getenv("MONGO_DB", "conveyor_db")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
JWT_ALGO = "HS256"

# ================= HASH =================
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def verify_password(p, h): return secrets.compare_digest(hash_password(p), h)

# ================= JWT =================
def create_token(u):
    return jwt.encode({"sub": u}, SECRET_KEY, algorithm=JWT_ALGO)

def decode_token(t):
    try:
        return jwt.decode(t, SECRET_KEY, algorithms=[JWT_ALGO]).get("sub")
    except JWTError:
        return None

# ================= DB =================
mongo_client = None
db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_client, db
    if MONGO_URI:
        mongo_client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
        db = mongo_client[MONGO_DB]
        try:
            await mongo_client.admin.command("ping")
            print("✅ MongoDB Connected")
        except Exception as e:
            print("❌ Mongo error:", e)
    yield
    if mongo_client:
        mongo_client.close()

# ================= APP =================
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= AUTH =================
bearer = HTTPBearer(auto_error=False)

async def get_user(c: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if not c: raise HTTPException(401, "No token")
    u = decode_token(c.credentials)
    if not u: raise HTTPException(401, "Invalid token")
    return u

# ================= SCHEMAS =================
class Login(BaseModel):
    username: str
    password: str

class Score(BaseModel):
    score: int

# ================= OPENENV =================
env = {"step":0,"score":0}

@app.post("/openenv/reset")
async def reset():
    env["step"]=0
    env["score"]=0
    return {"success":True}

@app.get("/openenv/validate")
async def validate():
    return {"success":True,"env":env}

# ================= API =================
@app.post("/api/login")
async def login(d: Login):
    if d.username=="admin" and d.password=="admin123":
        return {"token": create_token("admin")}
    raise HTTPException(401,"Invalid")

@app.post("/api/scores")
async def save(s: Score, u=Depends(get_user)):
    if db:
        await db["scores"].insert_one({"user":u,"score":s.score})
    return {"ok":True}

@app.get("/api/scores")
async def get():
    if not db: return []
    return await db["scores"].find({},{"_id":0}).to_list(100)

# ================= STATIC =================
_static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static)), name="static")

@app.get("/")
async def home():
    return FileResponse(_static/"index.html")