from nonebot import require
from nonebot.plugin import PluginMetadata

require("amrita.plugins.chat")
from . import core

__plugin_meta__ = PluginMetadata(
    name="DeepSeek DSML补丁包",
    description="针对DeepSeek模型DSML泄露问题的补丁包",
    usage="",
    type="library",
    homepage="https://github.com/AmritaBot/plugin-deepseek",
    supported_adapters={"~onebot.v11"},
)

__all__ = ["core"]
