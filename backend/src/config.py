from decouple import config

ALLOWED_ORIGINS: list[str] = [
    origin.strip()
    for origin in str(config("ALLOWED_ORIGINS", default="http://localhost:3000")).split(",")
    if origin.strip()
]
ENVIRONMENT: str = str(config("ENVIRONMENT", default="development"))
IS_PRODUCTION: bool = ENVIRONMENT == "production"
