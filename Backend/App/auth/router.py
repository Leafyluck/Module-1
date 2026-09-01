from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
)

from Backend.App.auth.schemas import (
    UserRegister,
    EmailOTPVerify,
    ResendEmailOTP,
    PasswordLogin,
    ProfileUpdate,
    FarmUpdate,
)

from Backend.App.auth.service import (
    register_user,
    authenticate_user,
    login_response,
    verify_email_otp,
    resend_email_otp,
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


# =========================================================
# REGISTER
# =========================================================

@router.post("/register")
async def register(user: UserRegister):

    try:

        new_user = register_user(user)

        # -----------------------------------------
        # EMAIL PROVIDED
        # -----------------------------------------

        if new_user.get("email"):

            return {
                "success": True,

                "requires_email_verification": True,

                "message": (
                    "Registration successful. "
                    "Check your email for the "
                    "verification OTP."
                ),

                "email": new_user.get(
                    "email"
                ),

                "email_verified": False,
            }

        # -----------------------------------------
        # EMAIL NOT PROVIDED
        # -----------------------------------------

        return {
            "success": True,

            "requires_email_verification": False,

            "message": (
                "Registration successful!"
            ),

            **login_response(
                new_user
            ),
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {exc}"
        )


# =========================================================
# VERIFY EMAIL OTP
# =========================================================

@router.post("/verify-email-otp")
async def verify_email(
    data: EmailOTPVerify
):

    try:

        user = verify_email_otp(
            data.email,
            data.otp
        )

        return {
            "success": True,

            "message": (
                "Email verified successfully!"
            ),

            "email_verified": True,

            "user": {
                "uid": user.get("uid"),
                "name": user.get("name"),
                "email": user.get("email"),
                "phone": user.get("phone"),
                "role": user.get("role"),
            },
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Email verification failed: {exc}"
        )


# =========================================================
# RESEND EMAIL OTP
# =========================================================

@router.post("/resend-email-otp")
async def resend_otp(
    data: ResendEmailOTP
):

    try:

        resend_email_otp(
            data.email
        )

        return {
            "success": True,
            "message": (
                "A new OTP has been sent "
                "to your email."
            ),
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to resend OTP: {exc}"
        )


# =========================================================
# PASSWORD LOGIN
# =========================================================

@router.post("/login-password")
async def login(
    credentials: PasswordLogin
):

    try:

        user = authenticate_user(
            credentials.identifier,
            credentials.password
        )

        if not user:

            raise HTTPException(
                status_code=401,
                detail=(
                    "Invalid mobile/email "
                    "or password."
                )
            )

        return {
            "message": "Login successful",

            **login_response(
                user
            ),
        }

    except HTTPException:
        raise

    except ValueError as exc:

        raise HTTPException(
            status_code=403,
            detail=str(exc)
        )

    except RuntimeError as exc:

        raise HTTPException(
            status_code=503,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {exc}"
        )


# =========================================================
# CURRENT USER
# =========================================================

@router.get("/auth/me")
async def me(
    current_user=Depends(
        get_current_user
    )
):

    return {
        "message": (
            "Authentication successful!"
        ),

        "user": current_user,
    }


# =========================================================
# FARMER PROFILE
# =========================================================

@router.get("/farmers/profile")
async def get_profile(
    current_user=Depends(
        require_farmer
    )
):

    return {
        "profile": current_user
    }


@router.put("/farmers/profile")
async def update_profile(
    data: ProfileUpdate,
    current_user=Depends(
        require_farmer
    )
):

    if users_collection is None:

        raise HTTPException(
            status_code=503,
            detail=(
                "Database is not configured."
            )
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

    from Backend.App.auth.service import clean_user

    return {
        "message": (
            "Profile updated successfully."
        ),

        "profile": clean_user(
            updated
        ),
    }


# =========================================================
# FARMER FARM
# =========================================================

@router.get("/farmers/farm")
async def get_farm(
    current_user=Depends(
        require_farmer
    )
):

    if farms_collection is None:

        raise HTTPException(
            status_code=503,
            detail=(
                "Database is not configured."
            )
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
    current_user=Depends(
        require_farmer
    )
):

    if farms_collection is None:

        raise HTTPException(
            status_code=503,
            detail=(
                "Database is not configured."
            )
        )

    farm = {
        "uid": current_user["uid"],
        **data.model_dump()
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
        "message": (
            "Farm information saved successfully."
        ),

        "farm": farm,
    }