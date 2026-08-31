from pydantic import BaseModel, Field
from typing import Optional


class UserRegister(BaseModel):
    uid: str
    name: str = Field(min_length=2, max_length=100)
    phone: Optional[str] = None
    email: Optional[str] = None
    password: str = Field(min_length=6, max_length=128)
    role: str = "Farmer"
    auth_provider: str = "password"
    village: str = ""
    state: str = "Andhra Pradesh"
    language: str = "English"


class PasswordLogin(BaseModel):
    identifier: str
    password: str


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    village: str = ""
    state: str = "Andhra Pradesh"
    language: str = "English"


class FarmUpdate(BaseModel):
    land_acres: float = Field(ge=0)
    primary_crop: str = "Rice"
    soil_type: str = "Loamy"
    irrigation: str = "Borewell"
