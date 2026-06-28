from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "Financial Analysis Dashboard API"
    api_version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )


settings = Settings()

