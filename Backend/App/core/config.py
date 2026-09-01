import os

try:
    from dotenv import load_dotenv

    load_dotenv()

except ImportError:
    pass


class Settings:

    MONGO_URI = os.getenv(
        "MONGO_URI",
        ""
    )

    JWT_SECRET = os.getenv(
        "JWT_SECRET",
        "change-this-secret"
    )

    JWT_ALGORITHM = os.getenv(
        "JWT_ALGORITHM",
        "HS256"
    )

    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "1440"
        )
    )

    # =========================================================
    # EMAIL SMTP
    # =========================================================

    SMTP_HOST = os.getenv(
        "SMTP_HOST",
        "smtp.gmail.com"
    )

    SMTP_PORT = int(
        os.getenv(
            "SMTP_PORT",
            "587"
        )
    )

    SMTP_USERNAME = os.getenv(
        "SMTP_USERNAME",
        ""
    )

    SMTP_PASSWORD = os.getenv(
        "SMTP_PASSWORD",
        ""
    )

    SMTP_FROM = os.getenv(
        "SMTP_FROM",
        ""
    )


settings = Settings()