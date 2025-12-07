from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import SQLModel

from backend.database import engine
from backend.routers import volunteers, books, stalls, reports


# -------------------------------
# Lifespan: Startup + Shutdown
# -------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables
    SQLModel.metadata.create_all(engine)
    print("🚀 Database initialized")

    yield   # ← application runs here

    # Shutdown (optional)
    print("🛑 Application shutting down")


# -------------------------------
# Create FastAPI App
# -------------------------------
app = FastAPI(
    title="Book Stall Management API",
    version="1.0",
    lifespan=lifespan
)


# -------------------------------
# Include Routers
# -------------------------------

app.include_router(books.router,  tags=["Books"])
app.include_router(volunteers.router, tags=["Volunteers"])
app.include_router(stalls.router,  tags=["Stalls"])
app.include_router(reports.router,  tags=["Reports"])


# -------------------------------
# Root Endpoint
# -------------------------------
@app.get("/")
def root():
    return {"message": "Book Stall API running!"}
