from pydantic import BaseModel


class JwtSettings(BaseModel):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_minutes: int = 60


class ApiKeySettings(BaseModel):
    key: str
