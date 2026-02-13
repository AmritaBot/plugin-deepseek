from nonebot import get_plugin_config
from pydantic import BaseModel, Field


class Config(BaseModel):
    security_invoke: float = Field(
        0.65,
    )


CONFIG = get_plugin_config(Config)
