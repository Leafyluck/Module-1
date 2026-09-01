from fastapi import APIRouter, HTTPException, Depends

from Backend.App.auth.schemas import (
    UserRegister,
    PasswordLogin,
    ProfileUpdate,
    FarmUpdate,
)

from Backend.App.auth.service import (
    register_user,
    authenticate_user,
    login_response,
    clean_user,
)

from Backend.App.auth.dependencies import (
    get_current_user,
    require_farmer,
)

from Backend.App.core.database import (
    users_collection,
    farms_collection,
)


router = APIRouter(
    prefix="/api",
    tags=["Authentication"]
)


# ============================================================
# REGISTER
# ============================================================

@router.post("/register")
async def register(user: UserRegister):

    try:

        if not user.phone and not user.email:
            raise ValueError(
                "Please provide a mobile number."
            )

        new_user = register_user(user)

        return {
            "message": "User registered successfully!",
            **login_response(new_user),
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {exc}"
        )


# ============================================================
# PASSWORD LOGIN
# ============================================================

@router.post("/login-password")
async def login(credentials: PasswordLogin):

    try:

        user = authenticate_user(
            credentials.identifier,
            credentials.password
        )

        if not user:

            raise HTTPException(
                status_code=401,
                detail="Invalid mobile/email or password."
            )

        return {
            "message": "Login successful",
            **login_response(user),
        }

    except HTTPException:
        raise

    except ValueError as exc:

        raise HTTPException(
            status_code=403,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {exc}"
        )


# ============================================================
# CURRENT USER
# ============================================================

@router.get("/auth/me")
async def me(
    current_user=Depends(get_current_user)
):

    return {
        "message": "Authentication successful!",
        "user": current_user,
    }


# ============================================================
# PROFILE
#
# ALL THREE ACCOUNT TYPES CAN ACCESS THIS:
#
# Farmer
# FPO
# Bulk Buyer
# ============================================================

@router.get("/profile")
async def get_profile(
    current_user=Depends(get_current_user)
):

    return {
        "profile": current_user
    }


@router.put("/profile")
async def update_profile(
    data: ProfileUpdate,
    current_user=Depends(get_current_user)
):

    if users_collection is None:

        raise HTTPException(
            status_code=503,
            detail="Database is not configured."
        )

    users_collection.update_one(
        {
            "uid": current_user["uid"]
        },
        {
            "$set": data.model_dump()
        }
    )

    updated = users_collection.find_one(
        {
            "uid": current_user["uid"]
        }
    )

    return {
        "message": "Profile updated successfully.",
        "profile": clean_user(updated),
    }


# ============================================================
# FARM PROFILE
#
# Only Farmers need farm information.
# ============================================================

@router.get("/farmers/profile")
async def get_farmer_profile(
    current_user=Depends(require_farmer)
):

    return {
        "profile": current_user
    }


@router.put("/farmers/profile")
async def update_farmer_profile(
    data: ProfileUpdate,
    current_user=Depends(require_farmer)
):

    if users_collection is None:

        raise HTTPException(
            status_code=503,
            detail="Database is not configured."
        )

    users_collection.update_one(
        {
            "uid": current_user["uid"]
        },
        {
            "$set": data.model_dump()
        }
    )

    updated = users_collection.find_one(
        {
            "uid": current_user["uid"]
        }
    )

    return {
        "message": "Profile updated successfully.",
        "profile": clean_user(updated),
    }


# ============================================================
# FARM
# ============================================================

@router.get("/farmers/farm")
async def get_farm(
    current_user=Depends(require_farmer)
):

    if farms_collection is None:

        raise HTTPException(
            status_code=503,
            detail="Database is not configured."
        )

    farm = farms_collection.find_one(
        {
            "uid": current_user["uid"]
        },
        {
            "_id": 0
        }
    )

    return {
        "farm": farm or {
            "uid": current_user["uid"],
            "land_acres": 0,
            "primary_crop": "Rice",
            "soil_type": "Loamy",
            "irrigation": "Borewell",
        }
    }


@router.put("/farmers/farm")
async def update_farm(
    data: FarmUpdate,
    current_user=Depends(require_farmer)
):

    if farms_collection is None:

        raise HTTPException(
            status_code=503,
            detail="Database is not configured."
        )

    farm = {
        "uid": current_user["uid"],
        **data.model_dump(),
    }

    farms_collection.update_one(
        {
            "uid": current_user["uid"]
        },
        {
            "$set": farm
        },
        upsert=True
    )

    return {
        "message": "Farm information saved successfully.",
        "farm": farm,
    }