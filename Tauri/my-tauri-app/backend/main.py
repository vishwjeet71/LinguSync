from fastapi import FastAPI
import uvicorn, os, signal
import multiprocessing
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="BackendServer",
    description="testing",
    version="1.0",
)

origins = [
    "http://localhost:1420",
    "tauri://localhost",
    "http://tauri.localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/shutdown")
def shutdown_server():
    os.kill(os.getpid(), signal.SIGTERM)
    return {"message": "Server shutting down..."}

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }

if __name__ == "__main__":
    multiprocessing.freeze_support()
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)