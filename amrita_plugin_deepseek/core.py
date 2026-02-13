import contextlib
import random
import typing

from amrita.API import send_to_admin
from amrita.plugins.chat.API import ToolsManager, on_before_chat, on_chat
from amrita.plugins.chat.config import config_manager
from amrita.plugins.chat.event import ChatEvent
from amrita.plugins.chat.utils.models import Message
from nonebot import get_bot, logger

from .dsml import (
    DSMLFunctionCall,
    DSMLParameter,
    DSMLParseError,
    DSMLParser,
)
from .utils import Checker


@on_before_chat(priority=5, block=False).handle()
async def security_check(event: ChatEvent):
    has_bad_msg = False
    with contextlib.suppress(DSMLParseError):
        if DSMLParser.parse(
            event.message.user_query
            if isinstance(event.message.user_query, str)
            else event.message.user_query.content
        ):
            logger.warning(
                "User query contains DSML, which is not allowed for security reasons."
            )
    if Checker.check_by_rule(
        event.message.user_query
        if isinstance(event.message.user_query, str)
        else event.message.user_query.content
    ):
        logger.warning(
            "User query contains potentially harmful content, which is not allowed for security reasons."
        )

        has_bad_msg = True
    if has_bad_msg:
        with contextlib.suppress(Exception):
            await send_to_admin(
                f"Security Alert: User query contains potentially harmful content.\nUser ID: {event.get_user_id()}\nQuery: {event.message.user_query}\nPowered by Amrita DeepSeek增强包"
            )
            await get_bot().send(
                event.get_nonebot_event(),
                random.choice(config_manager.config.llm_config.block_msg),
            )
        event._send_message.user_query.content = "[因为安全原因，此消息并没有被解析。]"


@on_chat(priority=5, block=False).handle()
async def checker(event: ChatEvent):
    matches: list[DSMLFunctionCall] = []
    with contextlib.suppress(DSMLParseError):
        event.model_response, matches = DSMLParser.find_and_clean(event.model_response)
    if not matches:
        return
    event.model_response = (
        event.model_response.strip() or "(发生了一些错误，想要休息一下......)"
    )
    results: list[str] = []
    logger.warning("Find DSML in response！")
    for call in matches:
        tool_name: str = call.name
        params: list[DSMLParameter] = call.parameters
        if (tool := ToolsManager().get_tool(tool_name)) is None or tool.custom_run:
            logger.warning(f"Tool {tool_name} not found")
            continue
        try:
            result: str = await typing.cast(
                typing.Callable[[dict[str, typing.Any]], typing.Awaitable[str]],
                tool.func,
            )({param.name: param.value for param in params})
            results.append(
                f"Called Tool: {tool_name}\n\nResult: \n```text\n{result}\n```\n"
            )
        except Exception as e:
            logger.error(f"Error running tool {tool_name}: {e}\n")
            results.append(f"Error running tool {tool_name}: {e}\n")
            continue
    final_result = "\n".join(results)
    event.get_send_message().memory.append(Message(role="user", content=final_result))
