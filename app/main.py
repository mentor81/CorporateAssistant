from fastapi import FastAPI
from app.api.routes import auth, hr, general

app = FastAPI(title="AI HR Service")

app.include_router(auth.router)
app.include_router(hr.router)
app.include_router(general.router)
