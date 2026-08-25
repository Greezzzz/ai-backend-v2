from pydantic import BaseModel


class JwtSettings(BaseModel):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int


class ApiKeySettings(BaseModel):
    key: str
