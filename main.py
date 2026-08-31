import os
import random
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from Backend.App.auth.router import router as auth_router
from Backend.App.core.database import users_collection, orders_collection

app = FastAPI(title="KisaanLink Farmer Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")


def template(name: str):
    path = os.path.join(TEMPLATES_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found.")
    return FileResponse(path)


@app.get("/")
async def root():
    return template("index.html")


@app.get("/index.html")
async def index():
    return template("index.html")


@app.get("/forecast.html")
async def forecast_page():
    return template("forecast.html")


@app.get("/health")
async def health():
    return {"status": "ok", "database_configured": users_collection is not None}


@app.get("/api/dashboard-stats")
async def dashboard_stats():
    if users_collection is None or orders_collection is None:
        return {"fpos": 0, "farmers": 0, "totalOrders": 0, "revenue": 0}

    def fetch():
        return (
            users_collection.count_documents({"role": "FPO"}),
            users_collection.count_documents({"role": "Farmer"}),
            orders_collection.count_documents({}),
            sum((o.get("amount", 0) or 0) for o in orders_collection.find({}, {"amount": 1, "_id": 0})),
        )

    fpos, farmers, orders, revenue = await asyncio.to_thread(fetch)
    return {"fpos": fpos, "farmers": farmers, "totalOrders": orders, "revenue": revenue}


class ForecastRequest(BaseModel):
    crop: str
    land_acres: float = Field(gt=0)
    region: str


@app.post("/api/forecast")
async def forecast(req: ForecastRequest):
    crop = req.crop.strip().title()
    recommended = round(req.land_acres * 0.7, 1)
    return {
        "recommendation": {
            "acres": recommended,
            "plant_date": "Next suitable window",
            "profit_margin": "Estimated 38–45%",
            "rain_forecast": "Check local weather before field work",
            "crop": crop,
            "region": req.region,
        },
        "chart_data": {
            "demand": [100 + i * 2 + random.randint(-5, 5) for i in range(30)],
            "supply": [110 + random.randint(-10, 10) for _ in range(30)],
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
