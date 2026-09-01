import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from jose import jwt
from passlib.context import CryptContext

from Backend.App.core.config import settings
from Backend.App.core.database import users_collection


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

OTP_MINUTES = 10

ALLOWED_ROLES = {
    "Farmer",
    "FPO",
    "Bulk Buyer",
}


# ============================================================
# PASSWORD
# ============================================================

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    Bcrypt only supports the first 72 bytes.
    """
    return pwd_context.hash(password.encode("utf-8")[:72])


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(
            password.encode("utf-8")[:72],
            hashed
        )
    except Exception:
        return False


# ============================================================
# JWT ACCESS TOKEN
# ============================================================

def create_access_token(uid: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": uid,
        "role": role,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


# ============================================================
# CLEAN USER RESPONSE
# ============================================================

def clean_user(user: dict) -> dict:
    """
    Removes sensitive information such as password and OTP
    before sending user information to the frontend.
    """

    return {
        "uid": user.get("uid"),
        "name": user.get("name", "User"),
        "phone": user.get("phone"),
        "email": user.get("email"),
        "role": user.get("role", "Farmer"),
        "village": user.get("village", ""),
        "state": user.get("state", ""),
        "language": user.get("language", "English"),

        # Farmer / FPO / Bulk Buyer fields
        "organization_name": user.get("organization_name", ""),
        "registration_number": user.get("registration_number", ""),
        "business_type": user.get("business_type", ""),

        # If there is no email, email verification is not required.
        "email_verified": (
            True
            if not user.get("email")
            else bool(user.get("email_verified", False))
        ),
    }


# ============================================================
# OTP
# ============================================================

def generate_email_otp() -> str:
    """
    Generate a secure 6-digit OTP.
    """
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    """
    Store only a hash of the OTP in MongoDB.
    """
    return hashlib.sha256(
        otp.encode("utf-8")
    ).hexdigest()


def send_email_otp(email: str, otp: str) -> None:
    """
    Send email verification OTP.

    This is only called when the user actually provides
    an email address.
    """

    if not settings.SMTP_HOST:
        raise RuntimeError(
            "Email service is not configured. "
            "Add SMTP_HOST, SMTP_PORT, SMTP_USERNAME, "
            "SMTP_PASSWORD and SMTP_FROM to Render."
        )

    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        raise RuntimeError(
            "Email service is not configured. "
            "Add SMTP_HOST, SMTP_PORT, SMTP_USERNAME, "
            "SMTP_PASSWORD and SMTP_FROM to Render."
        )

    message = EmailMessage()

    message["Subject"] = "KisaanLink - Email Verification OTP"

    message["From"] = (
        settings.SMTP_FROM
        if settings.SMTP_FROM
        else settings.SMTP_USERNAME
    )

    message["To"] = email

    message.set_content(
        "Hello,\n\n"
        "Welcome to KisaanLink.\n\n"
        f"Your email verification OTP is: {otp}\n\n"
        f"This OTP is valid for {OTP_MINUTES} minutes.\n\n"
        "If you did not request this verification, "
        "please ignore this email.\n\n"
        "Regards,\n"
        "KisaanLink Team"
    )

    with smtplib.SMTP(
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        timeout=20
    ) as server:

        server.ehlo()

        server.starttls()

        server.ehlo()

        server.login(
            settings.SMTP_USERNAME,
            settings.SMTP_PASSWORD
        )

        server.send_message(message)


# ============================================================
# PHONE NUMBER NORMALIZATION
# ============================================================

def normalize_phone(phone: str | None):
    """
    Accept all of these:

        9876543210
        +919876543210
        919876543210

    Store consistently as:

        +919876543210
    """

    if not phone:
        return None

    value = phone.strip()

    if not value:
        return None

    digits = "".join(
        ch for ch in value
        if ch.isdigit()
    )

    # Indian 10-digit number
    if len(digits) == 10:
        return "+91" + digits

    # Indian number entered with 91
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits

    # Already international format
    if value.startswith("+") and len(digits) >= 10:
        return "+" + digits

    raise ValueError(
        "Enter a valid mobile number."
    )


# ============================================================
# REGISTER USER
# ============================================================

def register_user(data):

    if users_collection is None:
        raise RuntimeError(
            "MongoDB is not configured. "
            "Add MONGO_URI to Render."
        )

    # --------------------------------------------------------
    # EMAIL IS OPTIONAL
    # --------------------------------------------------------

    if data.email and data.email.strip():
        email = data.email.strip().lower()
    else:
        email = None

    # --------------------------------------------------------
    # ROLE
    # --------------------------------------------------------

    role = (data.role or "Farmer").strip()

    if role not in ALLOWED_ROLES:
        raise ValueError(
            "Invalid account type. Choose Farmer, FPO or Bulk Buyer."
        )

    # --------------------------------------------------------
    # PHONE
    # --------------------------------------------------------

    phone = normalize_phone(data.phone)

    # At least one login identifier must exist.
    if not phone and not email:
        raise ValueError(
            "Please provide a mobile number."
        )

    # --------------------------------------------------------
    # CHECK EXISTING ACCOUNT
    #
    # IMPORTANT:
    # We DO NOT search for email=None.
    #
    # This prevents the MongoDB:
    #
    # E11000 duplicate key error
    # email_1 dup key: { email: null }
    # --------------------------------------------------------

    conditions = []

    if phone:
        conditions.append({
            "phone": phone
        })

    if email:
        conditions.append({
            "email": email
        })

    existing = None

    if conditions:
        existing = users_collection.find_one({
            "$or": conditions
        })

    if existing:

        # If an old unverified email account exists,
        # remove it so registration can be attempted again.
        if (
            email
            and existing.get("email") == email
            and not existing.get("email_verified", False)
        ):
            users_collection.delete_one({
                "uid": existing.get("uid")
            })

        else:
            raise ValueError(
                "An account with this mobile number or email already exists."
            )

    # --------------------------------------------------------
    # BASIC USER DATA
    # --------------------------------------------------------

    now = datetime.now(timezone.utc)

    user = {
        "uid": data.uid,

        "name": data.name.strip(),

        # Phone is normally the primary login method.
        "phone": phone,

        "password": hash_password(data.password),

        "role": role,

        "auth_provider": data.auth_provider,

        "village": (
            data.village.strip()
            if data.village
            else ""
        ),

        "state": (
            data.state.strip()
            if data.state
            else "Andhra Pradesh"
        ),

        "language": (
            data.language
            if data.language
            else "English"
        ),

        # FPO / Bulk Buyer fields.
        "organization_name": (
            getattr(data, "organization_name", "") or ""
        ).strip(),

        "registration_number": (
            getattr(data, "registration_number", "") or ""
        ).strip(),

        "business_type": (
            getattr(data, "business_type", "") or ""
        ).strip(),

        "created_at": now,
    }

    # --------------------------------------------------------
    # EMAIL OPTIONAL LOGIC
    # --------------------------------------------------------

    if email:

        # Email was provided.
        # OTP verification is required.

        otp = generate_email_otp()

        user["email"] = email

        user["email_verified"] = False

        user["email_otp_hash"] = hash_otp(otp)

        user["email_otp_expires_at"] = (
            now + timedelta(minutes=OTP_MINUTES)
        )

        # Send OTP BEFORE inserting the account.
        #
        # If SMTP fails, registration fails instead of creating
        # an unusable unverified account.
        send_email_otp(
            email,
            otp
        )

    else:

        # ----------------------------------------------------
        # NO EMAIL
        #
        # Do NOT store:
        #
        # "email": None
        #
        # This is important because the old MongoDB unique
        # email index was rejecting multiple null values.
        # ----------------------------------------------------

        user["email_verified"] = True

    # --------------------------------------------------------
    # INSERT USER
    # --------------------------------------------------------

    users_collection.insert_one(user)

    return user


# ============================================================
# VERIFY EMAIL OTP
# ============================================================

def verify_email_otp(email: str, otp: str):

    if users_collection is None:
        raise RuntimeError(
            "MongoDB is not configured."
        )

    if not email:
        raise ValueError(
            "Email address is required for email verification."
        )

    email = email.strip().lower()

    otp = otp.strip()

    user = users_collection.find_one({
        "email": email
    })

    if not user:
        raise ValueError(
            "No registration found for this email."
        )

    if user.get("email_verified"):
        return user

    expires_at = user.get(
        "email_otp_expires_at"
    )

    if not expires_at:
        raise ValueError(
            "Verification OTP is unavailable. "
            "Please request a new OTP."
        )

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if datetime.now(timezone.utc) > expires_at:
        raise ValueError(
            "OTP has expired. Please request a new OTP."
        )

    if hash_otp(otp) != user.get(
        "email_otp_hash"
    ):
        raise ValueError(
            "Invalid OTP."
        )

    users_collection.update_one(
        {
            "uid": user["uid"]
        },
        {
            "$set": {
                "email_verified": True
            },
            "$unset": {
                "email_otp_hash": "",
                "email_otp_expires_at": ""
            }
        }
    )

    return users_collection.find_one({
        "uid": user["uid"]
    })


# ============================================================
# RESEND EMAIL OTP
# ============================================================

def resend_email_otp(email: str):

    if users_collection is None:
        raise RuntimeError(
            "MongoDB is not configured."
        )

    if not email:
        raise ValueError(
            "Email address is required."
        )

    email = email.strip().lower()

    user = users_collection.find_one({
        "email": email
    })

    if not user:
        raise ValueError(
            "No account found for this email."
        )

    if user.get("email_verified"):
        raise ValueError(
            "This email is already verified."
        )

    otp = generate_email_otp()

    now = datetime.now(timezone.utc)

    # Send first.
    send_email_otp(
        email,
        otp
    )

    # Save only the new OTP hash.
    users_collection.update_one(
        {
            "uid": user["uid"]
        },
        {
            "$set": {
                "email_otp_hash": hash_otp(otp),
                "email_otp_expires_at": (
                    now + timedelta(minutes=OTP_MINUTES)
                )
            }
        }
    )


# ============================================================
# LOGIN IDENTIFIER NORMALIZATION
# ============================================================

def normalize_identifier(identifier: str) -> str:

    value = identifier.strip()

    if not value:
        return value

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    if "@" in value:
        return value.lower()

    # --------------------------------------------------------
    # PHONE
    # --------------------------------------------------------

    digits = "".join(
        ch for ch in value
        if ch.isdigit()
    )

    # 10-digit Indian number
    if len(digits) == 10:
        return "+91" + digits

    # 91 + 10 digits
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits

    # +91...
    if value.startswith("+"):
        return "+" + digits

    return value


# ============================================================
# AUTHENTICATE USER
# ============================================================

def authenticate_user(
    identifier: str,
    password: str
):

    if users_collection is None:
        raise RuntimeError(
            "MongoDB is not configured. "
            "Add MONGO_URI to Render."
        )

    normalized = normalize_identifier(
        identifier
    )

    # --------------------------------------------------------
    # FIND USER
    # --------------------------------------------------------

    if "@" in normalized:

        # Email login
        user = users_collection.find_one({
            "email": normalized.lower()
        })

    else:

        # Mobile login
        user = users_collection.find_one({
            "phone": normalized
        })

    # --------------------------------------------------------
    # PASSWORD
    # --------------------------------------------------------

    if not user:
        return None

    if not verify_password(
        password,
        user.get("password", "")
    ):
        return None

    # --------------------------------------------------------
    # EMAIL VERIFICATION
    #
    # If email exists, it must be verified.
    #
    # If email does NOT exist, verification is skipped.
    # --------------------------------------------------------

    if (
        user.get("email")
        and not user.get("email_verified", False)
    ):
        raise ValueError(
            "Please verify your email before logging in."
        )

    return user


# ============================================================
# LOGIN RESPONSE
# ============================================================

def login_response(user):

    return {
        "access_token": create_access_token(
            user["uid"],
            user.get("role", "Farmer")
        ),

        "token_type": "bearer",

        "user": clean_user(user),
    }