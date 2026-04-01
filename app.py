from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from environment.env import ColorSortingEnv

app = FastAPI()
env = ColorSortingEnv()

@app.get("/api")
def home():
    return {"message": "Color Segregation Running 🚀"}

@app.get("/reset")
def reset():
    return env.reset()

@app.post("/step")
def step(action: str):
    return env.step(action)

@app.get("/state")
def state():
    return env.state()
app.mount("/", StaticFiles(directory="static", html=True), name="static")