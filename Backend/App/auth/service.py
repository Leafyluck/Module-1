from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt
from Backend.App.core.config import settings
from Backend.App.core.database import users_collection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password.encode("utf-8")[:72])


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password.encode("utf-8")[:72], hashed)
    except Exception:
        return False


def create_access_token(uid: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": uid, "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def clean_user(user: dict) -> dict:
    return {
        "uid": user.get("uid"),
        "name": user.get("name", "Farmer"),
        "phone": user.get("phone"),
        "email": user.get("email"),
        "role": user.get("role", "Farmer"),
        "village": user.get("village", ""),
        "state": user.get("state", ""),
        "language": user.get("language", "English"),
    }


def register_user(data):
    if users_collection is None:
        raise RuntimeError("MongoDB is not configured. Add MONGO_URI to .env.")

    conditions = []
    if data.phone:
        conditions.append({"phone": data.phone})
    if data.email:
        conditions.append({"email": data.email.lower()})

    if conditions and users_collection.find_one({"$or": conditions}):
        raise ValueError("An account with this mobile number or email already exists.")

    user = {
        "uid": data.uid,
        "name": data.name.strip(),
        "phone": data.phone,
        "email": data.email.lower() if data.email else None,
        "password": hash_password(data.password),
        "role": "Farmer",
        "auth_provider": data.auth_provider,
        "village": data.village.strip(),
        "state": data.state.strip(),
        "language": data.language,
        "created_at": datetime.now(timezone.utc),
    }
    users_collection.insert_one(user)
    return user


def authenticate_user(identifier: str, password: str):
    if users_collection is None:
        raise RuntimeError("MongoDB is not configured. Add MONGO_URI to .env.")
    identifier = identifier.strip()
    user = users_collection.find_one({
        "$or": [{"phone": identifier}, {"email": identifier.lower()}]
    })
    if not user or not verify_password(password, user.get("password", "")):
        return None
    return user


def login_response(user):
    return {
        "access_token": create_access_token(user["uid"], user.get("role", "Farmer")),
        "token_type": "bearer",
        "user": clean_user(user),
    }
