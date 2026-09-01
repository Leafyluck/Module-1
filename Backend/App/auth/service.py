import hashlib
import secrets
import smtplib

from datetime import datetime, timedelta, timezone
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


# =========================================================
# PASSWORD
# =========================================================

def hash_password(password: str) -> str:
    return pwd_context.hash(
        password.encode("utf-8")[:72]
    )


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(
            password.encode("utf-8")[:72],
            hashed
        )
    except Exception:
        return False


# =========================================================
# JWT
# =========================================================

def create_access_token(uid: str, role: str) -> str:

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


# =========================================================
# CLEAN USER
# =========================================================

def clean_user(user: dict) -> dict:

    return {
        "uid": user.get("uid"),
        "name": user.get("name", "User"),
        "phone": user.get("phone"),
        "email": user.get("email"),
        "role": user.get("role", "Farmer"),
        "village": user.get("village", ""),
        "state": user.get("state", ""),
        "language": user.get("language", "English"),

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

        "email_verified": bool(
            user.get("email_verified", False)
        ),
    }


# =========================================================
# OTP HELPERS
# =========================================================

def generate_email_otp() -> str:

    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:

    return hashlib.sha256(
        otp.encode("utf-8")
    ).hexdigest()


# =========================================================
# SEND EMAIL OTP
# =========================================================

def send_email_otp(email: str, otp: str):

    smtp_host = getattr(
        settings,
        "SMTP_HOST",
        ""
    )

    smtp_port = getattr(
        settings,
        "SMTP_PORT",
        587
    )

    smtp_username = getattr(
        settings,
        "SMTP_USERNAME",
        ""
    )

    smtp_password = getattr(
        settings,
        "SMTP_PASSWORD",
        ""
    )

    smtp_from = getattr(
        settings,
        "SMTP_FROM",
        smtp_username
    )

    if (
        not smtp_host
        or not smtp_username
        or not smtp_password
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

    message["From"] = smtp_from
    message["To"] = email

    message.set_content(
        f"""
Hello,

Welcome to KisaanLink.

Your email verification OTP is:

{otp}

This OTP is valid for {OTP_MINUTES} minutes.

If you did not request this verification,
please ignore this email.

Regards,
KisaanLink Team
"""
    )

    with smtplib.SMTP(
        smtp_host,
        int(smtp_port),
        timeout=20
    ) as server:

        server.ehlo()
        server.starttls()
        server.ehlo()

        server.login(
            smtp_username,
            smtp_password
        )

        server.send_message(message)


# =========================================================
# PHONE NORMALIZATION
# =========================================================

def normalize_phone(phone: str | None):

    if not phone:
        return None

    value = str(phone).strip()

    digits = "".join(
        ch for ch in value
        if ch.isdigit()
    )

    if len(digits) == 10:
        return "+91" + digits

    if (
        len(digits) == 12
        and digits.startswith("91")
    ):
        return "+" + digits

    if value.startswith("+") and len(digits) >= 10:
        return "+" + digits

    raise ValueError(
        "Enter a valid 10-digit Indian mobile number."
    )


# =========================================================
# REGISTER USER
# =========================================================

def register_user(data):

    if users_collection is None:
        raise RuntimeError(
            "MongoDB is not configured. "
            "Add MONGO_URI to Render."
        )

    # -----------------------------------------
    # NAME
    # -----------------------------------------

    name = data.name.strip()

    if len(name) < 2:
        raise ValueError(
            "Enter a valid name."
        )

    # -----------------------------------------
    # ROLE
    # -----------------------------------------

    role = data.role.strip()

    if role not in ALLOWED_ROLES:
        raise ValueError(
            "Invalid account type."
        )

    # -----------------------------------------
    # PHONE
    # -----------------------------------------

    phone = normalize_phone(
        data.phone
    )

    # -----------------------------------------
    # EMAIL - OPTIONAL
    # -----------------------------------------

    email = None

    if data.email:

        email = (
            str(data.email)
            .strip()
            .lower()
        )

        if "@" not in email:
            raise ValueError(
                "Enter a valid email address."
            )

    # -----------------------------------------
    # AT LEAST ONE LOGIN IDENTIFIER
    # -----------------------------------------

    if not phone and not email:
        raise ValueError(
            "Please provide a mobile number or email."
        )

    # -----------------------------------------
    # DUPLICATE CHECK
    # -----------------------------------------

    conditions = []

    if phone:
        conditions.append(
            {"phone": phone}
        )

    if email:
        conditions.append(
            {"email": email}
        )

    existing = None

    if conditions:
        existing = users_collection.find_one(
            {"$or": conditions}
        )

    if existing:

        # Allow re-registration of an
        # unverified email account.
        if (
            email
            and existing.get("email") == email
            and not existing.get(
                "email_verified",
                False
            )
        ):

            users_collection.delete_one(
                {
                    "uid": existing.get("uid")
                }
            )

        else:

            raise ValueError(
                "An account with this mobile number "
                "or email already exists."
            )

    # -----------------------------------------
    # EMAIL VERIFICATION STATUS
    # -----------------------------------------

    email_verified = False

    otp = None
    now = datetime.now(timezone.utc)

    if email:

        # Email supplied:
        # verification required.

        otp = generate_email_otp()
        email_verified = False

    else:

        # No email:
        # no email verification required.

        email_verified = True

    # -----------------------------------------
    # USER DOCUMENT
    # -----------------------------------------

    user = {
        "uid": data.uid,

        "name": name,

        "phone": phone,

        "email": email,

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

        "language": data.language,

        "organization_name": (
            data.organization_name.strip()
            if getattr(
                data,
                "organization_name",
                None
            )
            else ""
        ),

        "registration_number": (
            data.registration_number.strip()
            if getattr(
                data,
                "registration_number",
                None
            )
            else ""
        ),

        "business_type": (
            data.business_type.strip()
            if getattr(
                data,
                "business_type",
                None
            )
            else ""
        ),

        "email_verified": email_verified,

        "created_at": now,
    }

    # -----------------------------------------
    # ADD OTP ONLY WHEN EMAIL EXISTS
    # -----------------------------------------

    if email and otp:

        user["email_otp_hash"] = hash_otp(
            otp
        )

        user["email_otp_expires_at"] = (
            now
            + timedelta(
                minutes=OTP_MINUTES
            )
        )

        # Send email BEFORE saving user.
        send_email_otp(
            email,
            otp
        )

    # -----------------------------------------
    # SAVE USER
    # -----------------------------------------

    users_collection.insert_one(
        user
    )

    return user


# =========================================================
# VERIFY EMAIL OTP
# =========================================================

def verify_email_otp(
    email: str,
    otp: str
):

    if users_collection is None:
        raise RuntimeError(
            "MongoDB is not configured."
        )

    if not email:
        raise ValueError(
            "No email address was provided."
        )

    email = (
        str(email)
        .strip()
        .lower()
    )

    user = users_collection.find_one(
        {
            "email": email
        }
    )

    if not user:
        raise ValueError(
            "No registration found for this email."
        )

    if user.get(
        "email_verified",
        False
    ):
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

    if datetime.now(
        timezone.utc
    ) > expires_at:

        raise ValueError(
            "OTP has expired. "
            "Please request a new OTP."
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
                "email_otp_expires_at": "",
            },
        }
    )

    return users_collection.find_one(
        {
            "uid": user["uid"]
        }
    )


# =========================================================
# RESEND EMAIL OTP
# =========================================================

def resend_email_otp(email: str):

    if users_collection is None:
        raise RuntimeError(
            "MongoDB is not configured."
        )

    if not email:
        raise ValueError(
            "No email address was provided."
        )

    email = (
        str(email)
        .strip()
        .lower()
    )

    user = users_collection.find_one(
        {
            "email": email
        }
    )

    if not user:
        raise ValueError(
            "No account found for this email."
        )

    if user.get(
        "email_verified",
        False
    ):
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
                "email_otp_hash": hash_otp(
                    otp
                ),

                "email_otp_expires_at": (
                    now
                    + timedelta(
                        minutes=OTP_MINUTES
                    )
                ),
            }
        }
    )


# =========================================================
# IDENTIFIER NORMALIZATION
# =========================================================

def normalize_identifier(
    identifier: str
):

    value = identifier.strip()

    digits = "".join(
        ch for ch in value
        if ch.isdigit()
    )

    # 10-digit Indian number
    if len(digits) == 10:
        return "+91" + digits

    # 91XXXXXXXXXX
    if (
        len(digits) == 12
        and digits.startswith("91")
    ):
        return "+" + digits

    # Already +91...
    if (
        value.startswith("+")
        and digits
    ):
        return "+" + digits

    # Otherwise treat it as email
    return value


# =========================================================
# AUTHENTICATE USER
# =========================================================

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

    # -----------------------------------------
    # SEARCH PHONE OR EMAIL
    # -----------------------------------------

    if normalized.startswith("+"):

        user = users_collection.find_one(
            {
                "phone": normalized
            }
        )

    else:

        user = users_collection.find_one(
            {
                "email": normalized.lower()
            }
        )

    # -----------------------------------------
    # USER NOT FOUND
    # -----------------------------------------

    if not user:
        return None

    # -----------------------------------------
    # PASSWORD
    # -----------------------------------------

    if not verify_password(
        password,
        user.get(
            "password",
            ""
        )
    ):
        return None

    # -----------------------------------------
    # EMAIL VERIFICATION
    # -----------------------------------------
    #
    # IMPORTANT:
    # No email = no verification required.
    #
    # Email exists but isn't verified =
    # login blocked.
    #

    email = user.get("email")

    if email and not user.get(
        "email_verified",
        False
    ):

        raise ValueError(
            "Please verify your email "
            "before logging in."
        )

    return user


# =========================================================
# LOGIN RESPONSE
# =========================================================

def login_response(user):

    return {
        "access_token": create_access_token(
            user["uid"],
            user.get(
                "role",
                "Farmer"
            )
        ),

        "token_type": "bearer",

        "user": clean_user(
            user
        ),
    }