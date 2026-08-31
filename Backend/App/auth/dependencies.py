from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from Backend.App.core.config import settings
from Backend.App.core.database import users_collection
from Backend.App.auth.service import clean_user

security = HTTPBearer(auto_error=True)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        uid = payload.get("sub")
        if not uid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired authentication token.")

    if users_collection is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")
    user = users_collection.find_one({"uid": uid})
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return clean_user(user)


def require_farmer(current_user=Depends(get_current_user)):
    if current_user.get("role") != "Farmer":
        raise HTTPException(status_code=403, detail="Farmer access required.")
    return current_user


def require_fpo(current_user=Depends(get_current_user)):
    if current_user.get("role") != "FPO":
        raise HTTPException(status_code=403, detail="FPO access required.")
    return current_user


def require_bulk_buyer(current_user=Depends(get_current_user)):
    if current_user.get("role") != "Bulk Buyer":
        raise HTTPException(status_code=403, detail="Bulk Buyer access required.")
    return current_user


def require_admin(current_user=Depends(get_current_user)):
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user
