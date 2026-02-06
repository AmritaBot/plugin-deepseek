import contextlib
import typing

from amrita.plugins.chat.API import ToolsManager, on_chat
from amrita.plugins.chat.event import ChatEvent
from amrita.plugins.chat.utils.models import Message
from nonebot import logger

from .dsml import (
    DSMLFunctionCall,
    DSMLParameter,
    DSMLParseError,
    DSMLParser,
)


@on_chat(priority=5,block=False).handle()
async def checker(event: ChatEvent):
    matches:list[DSMLFunctionCall] = []
    with contextlib.suppress(DSMLParseError):
        event.model_response,matches = DSMLParser.find_and_clean(event.model_response)
    if not matches:
        return
    event.model_response = event.model_response.strip() or "(发生了一些错误，想要休息一下......)"
    results:list[str] = []
    logger.warning("Find DSML in response！")
    for call in matches:
        tool_name: str = call.name
        params: list[DSMLParameter] = call.parameters
        if (tool := ToolsManager().get_tool(tool_name)) is None or tool.custom_run:
            logger.warning(f"Tool {tool_name} not found")
            continue
        try:
            result: str = await typing.cast(typing.Callable[[dict[str, typing.Any]], typing.Awaitable[str]],tool.func)({param.name: param.value for param in params})
            results.append(f"Called Tool: {tool_name}\n\nResult: \n```text\n{result}\n```\n")
        except Exception as e:
            logger.error(f"Error running tool {tool_name}: {e}\n")
            results.append(f"Error running tool {tool_name}: {e}\n")
            continue
    final_result = "\n".join(results)
    event.get_send_message().memory.append(Message(role="user", content=final_result))
