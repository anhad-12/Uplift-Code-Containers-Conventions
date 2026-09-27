from pydantic import BaseSettings


class Settings(BaseSettings):
    sender: str = "shop@example.com"
    smtp_host: str = "localhost"


def get_settings() -> Settings:
    return Settings()
