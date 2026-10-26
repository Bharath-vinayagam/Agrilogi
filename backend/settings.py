import os

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    BaseSettings = None
    SettingsConfigDict = None


if BaseSettings:
    class Settings(BaseSettings):
        app_env: str = "development"
        frontend_origin: str = "http://localhost:3000"
        supabase_url: str = ""
        supabase_service_role_key: str = ""
        groq_api_key: str = ""
        twilio_account_sid: str = ""
        twilio_auth_token: str = ""
        twilio_phone_number: str = ""
        ola_maps_api_key: str = ""
        tomtom_api_key: str = ""

        model_config = SettingsConfigDict(env_file=".env", extra="ignore")
else:
    class Settings:
        app_env = os.getenv("APP_ENV", "development")
        frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER", "")
        ola_maps_api_key = os.getenv("OLA_MAPS_API_KEY", "")
        tomtom_api_key = os.getenv("TOMTOM_API_KEY", "")


settings = Settings()
