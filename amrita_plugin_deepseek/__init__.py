from nonebot import require
from nonebot.plugin import PluginMetadata

require("amrita.plugins.chat")
from . import config, core

__plugin_meta__ = PluginMetadata(
    name="DeepSeek 模型安全增强包",
    description="针对DeepSeek模型DSML泄露与安全问题的补丁包",
    usage="",
    type="library",
    homepage="https://github.com/AmritaBot/plugin-deepseek",
    supported_adapters={"~onebot.v11"},
    config=config.Config
)

__all__ = ["config", "core"]
