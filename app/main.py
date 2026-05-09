from fastapi import FastAPI
from app.api.routes import auth, hr, general, rnd
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_origins=r"^https?://192\.168\.\d{1,3}\.\d{1,3}(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(hr.router)
app.include_router(general.router)
app.include_router(rnd.router)

