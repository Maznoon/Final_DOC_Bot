from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_USER_IDS: List[int]

    @field_validator("ADMIN_USER_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Union[str, List[int]]) -> List[int]:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    DATABASE_URL: str
    SUPPORT_CONTACT: str
    CARD_OWNER_NAME: str
    CARD_NUMBER: str
    PAYMENT_GATEWAY_ENABLED: bool = False
    PAYMENT_GATEWAY_URL: str = ""
    DEFAULT_PRODUCT_IMAGE: str = "https://via.placeholder.com/300"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
