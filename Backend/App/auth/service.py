import hashlib
import secrets
import smtplib

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from email.message import EmailMessage

from jose import jwt

from passlib.context import CryptContext

from Backend.App.core.config import settings

from Backend.App.core.database import users_collection


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


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

    return pwd_context.hash(
        password.encode("utf-8")[:72]
    )


def verify_password(
    password: str,
    hashed: str
) -> bool:

    try:

        return pwd_context.verify(
            password.encode("utf-8")[:72],
            hashed
        )

    except Exception:

        return False


# ============================================================
# JWT
# ============================================================

def create_access_token(
    uid: str,
    role: str
) -> str:

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
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
# CLEAN USER
# ============================================================

def clean_user(user: dict) -> dict:

    return {
        "uid": user.get("uid"),

        "name": user.get(
            "name",
            "User"
        ),

        "phone": user.get("phone"),

        "email": user.get("email"),

        "role": user.get(
            "role",
            "Farmer"
        ),

        "village": user.get(
            "village",
            ""
        ),

        "state": user.get(
            "state",
            ""
        ),

        "language": user.get(
            "language",
            "English"
        ),

        "organization_name": user.get(
            "organization_name",
            ""
        ),

        "registration_number": user.get(
            "registration_number",
            ""
        ),

        "business_type": user.get(
            "business_type",
            ""
        ),

        # If no email exists, email verification
        # is automatically considered unnecessary.
        "email_verified": (
            True
            if not user.get("email")
            else bool(
                user.get(
                    "email_verified",
                    False
                )
            )
        ),
    }


# ============================================================
# OTP
# ============================================================

def generate_email_otp() -> str:

    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:

    return hashlib.sha256(
        otp.encode("utf-8")
    ).hexdigest()


def send_email_otp(
    email: str,
    otp: str
) -> None:

    if (
        not settings.SMTP_HOST
        or not settings.SMTP_USERNAME
        or not settings.SMTP_PASSWORD
    ):

        raise RuntimeError(
            "Email service is not configured. "
            "Add SMTP_HOST, SMTP_PORT, SMTP_USERNAME, "
            "SMTP_PASSWORD and SMTP_FROM to Render."
        )

    message = EmailMessage()

    message["Subject"] = (
        "KisaanLink - Email Verification OTP"
    )

    message["From"] = (
        settings.SMTP_FROM
        or settings.SMTP_USERNAME
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
# PHONE NORMALIZATION
# ============================================================

def normalize_phone(
    phone: str | None
):

    if not phone:
        return None

    value = phone.strip()

    if not value:
        return None

    digits = "".join(
        ch
        for ch in value
        if ch.isdigit()
    )

    if len(digits) == 10:

        return "+91" + digits

    if (
        len(digits) == 12
        and digits.startswith("91")
    ):

        return "+" + digits

    if (
        value.startswith("+")
        and len(digits) >= 10
    ):

        return "+" + digits

    raise ValueError(
        "Enter a valid mobile number."
    )


# ============================================================
# REGISTER
# ============================================================

def register_user(data):

    if users_collection is None:

        raise RuntimeError(
            "MongoDB is not configured. "
            "Add MONGO_URI to Render."
        )

    # --------------------------------------------------------
    # OPTIONAL EMAIL
    # --------------------------------------------------------

    if data.email and data.email.strip():

        email = (
            data.email
            .strip()
            .lower()
        )

    else:

        email = None

    # --------------------------------------------------------
    # ROLE
    # --------------------------------------------------------

    role = (
        data.role or "Farmer"
    ).strip()

    if role not in ALLOWED_ROLES:

        raise ValueError(
            "Invalid account type. "
            "Choose Farmer, FPO or Bulk Buyer."
        )

    # --------------------------------------------------------
    # PHONE
    # --------------------------------------------------------

    phone = normalize_phone(
        data.phone
    )

    if not phone and not email:

        raise ValueError(
            "Please provide a mobile number."
        )

    # --------------------------------------------------------
    # DUPLICATE CHECK
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

        # Allow retrying an unverified email registration.
        if (
            email
            and existing.get("email") == email
            and not existing.get(
                "email_verified",
                False
            )
        ):

            users_collection.delete_one({
                "uid": existing.get("uid")
            })

        else:

            raise ValueError(
                "An account with this mobile number "
                "or email already exists."
            )

    now = datetime.now(
        timezone.utc
    )

    # --------------------------------------------------------
    # BASE USER
    # --------------------------------------------------------

    user = {
        "uid": data.uid,

        "name": data.name.strip(),

        "phone": phone,

        "password": hash_password(
            data.password
        ),

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

        "organization_name": (
            data.organization_name or ""
        ).strip(),

        "registration_number": (
            data.registration_number or ""
        ).strip(),

        "business_type": (
            data.business_type or ""
        ).strip(),

        "created_at": now,
    }

    # --------------------------------------------------------
    # EMAIL PROVIDED
    # --------------------------------------------------------

    if email:

        otp = generate_email_otp()

        user["email"] = email

        user["email_verified"] = False

        user["email_otp_hash"] = hash_otp(
            otp
        )

        user["email_otp_expires_at"] = (
            now
            + timedelta(
                minutes=OTP_MINUTES
            )
        )

        # Email verification required.
        send_email_otp(
            email,
            otp
        )

    # --------------------------------------------------------
    # NO EMAIL
    # --------------------------------------------------------

    else:

        # IMPORTANT:
        # Do NOT insert email=None.
        #
        # The sparse unique index we configured in
        # MongoDB will therefore ignore this user.
        user["email_verified"] = True

    # --------------------------------------------------------
    # CREATE ACCOUNT
    # --------------------------------------------------------

    users_collection.insert_one(
        user
    )

    return user


# ============================================================
# VERIFY EMAIL OTP
# ============================================================

def verify_email_otp(
    email: str,
    otp: str
):

    if users_collection is None:

        raise RuntimeError(
            "MongoDB is not configured."
        )

    email = (
        email
        .strip()
        .lower()
    )

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

    if (
        datetime.now(timezone.utc)
        > expires_at
    ):

        raise ValueError(
            "OTP has expired. "
            "Please request a new OTP."
        )

    if (
        hash_otp(otp)
        != user.get("email_otp_hash")
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
# RESEND OTP
# ============================================================

def resend_email_otp(
    email: str
):

    if users_collection is None:

        raise RuntimeError(
            "MongoDB is not configured."
        )

    if not email:

        raise ValueError(
            "Email address is required."
        )

    email = (
        email
        .strip()
        .lower()
    )

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

    now = datetime.now(
        timezone.utc
    )

    send_email_otp(
        email,
        otp
    )

    users_collection.update_one(
        {
            "uid": user["uid"]
        },
        {
            "$set": {
                "email_otp_hash": hash_otp(otp),
                "email_otp_expires_at": (
                    now
                    + timedelta(
                        minutes=OTP_MINUTES
                    )
                )
            }
        }
    )


# ============================================================
# LOGIN IDENTIFIER
# ============================================================

def normalize_identifier(
    identifier: str
) -> str:

    value = identifier.strip()

    if not value:
        return value

    # Email
    if "@" in value:

        return value.lower()

    # Mobile
    digits = "".join(
        ch
        for ch in value
        if ch.isdigit()
    )

    if len(digits) == 10:

        return "+91" + digits

    if (
        len(digits) == 12
        and digits.startswith("91")
    ):

        return "+" + digits

    if value.startswith("+"):

        return "+" + digits

    return value


# ============================================================
# LOGIN
# ============================================================

def authenticate_user(
    identifier: str,
    password: str
):

    if users_collection is None:

        raise RuntimeError(
            "MongoDB is not configured."
        )

    normalized = normalize_identifier(
        identifier
    )

    if "@" in normalized:

        user = users_collection.find_one({
            "email": normalized.lower()
        })

    else:

        user = users_collection.find_one({
            "phone": normalized
        })

    if not user:

        return None

    if not verify_password(
        password,
        user.get("password", "")
    ):

        return None

    # Only users who actually supplied an email
    # need email verification.
    if (
        user.get("email")
        and not user.get(
            "email_verified",
            False
        )
    ):

        raise ValueError(
            "Please verify your email before logging in."
        )

    return user


# ============================================================
# LOGIN RESPONSE
# ============================================================

def login_response(
    user
):

    return {
        "access_token": create_access_token(
            user["uid"],
            user.get(
                "role",
                "Farmer"
            )
        ),

        "token_type": "bearer",

        "user": clean_user(user),
    }