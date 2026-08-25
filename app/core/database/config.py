from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):

    host: str
    port: int
    user: str
    password: str
    name: str

    model_config = SettingsConfigDict(
        env_prefix="DB_", 
        env_file=".env",
        extra="ignore"
    )

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"