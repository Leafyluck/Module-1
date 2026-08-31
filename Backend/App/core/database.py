from pymongo import MongoClient
from Backend.App.core.config import settings


if settings.MONGO_URI:
    client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database("KisaanLink")
    users_collection = db["users"]
    orders_collection = db["orders"]
    farms_collection = db["farms"]
    print(f"Connected to Database: '{db.name}'")
else:
    client = None
    db = None
    users_collection = None
    orders_collection = None
    farms_collection = None
    print("WARNING: MONGO_URI is not configured. Database features are unavailable.")
