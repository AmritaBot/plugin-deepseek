from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class DSMLParseError(Exception):
    """DSML解析错误"""


class ParamType(str, Enum):
    """参数类型枚举"""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NULL = "null"
    UNKNOWN = "unknown"

    def __str__(self):
        return self.value


class DSMLParameter(BaseModel):
    """DSML参数"""

    name: str
    value: Any
    type: ParamType
    raw_value: str  # 原始字符串值
    attributes: dict[str, str] = Field(default_factory=dict)


class DSMLFunctionCall(BaseModel):
    """DSML函数调用"""

    name: str
    parameters: list[DSMLParameter] = Field(default_factory=list)
    nested_calls: list[DSMLFunctionCall] = Field(default_factory=list)
    raw_xml: str = ""  # 原始XML片段


class DSMLParser:
    """DSML解析器 - 处理DeepSeek工具调用标签"""

    # 编译正则表达式
    # 匹配整个DSML块
    DSML_BLOCK_PATTERN = re.compile(
        r"<｜DSML｜function_calls>(.*?)</｜DSML｜function_calls>",
        re.DOTALL,  # 使.匹配换行符
    )

    # 匹配单个函数调用
    INVOKE_PATTERN = re.compile(
        r'<｜DSML｜invoke\s+name="([^"]+)">(.*?)</｜DSML｜invoke>', re.DOTALL
    )

    # 匹配参数
    PARAMETER_PATTERN = re.compile(
        r'<｜DSML｜parameter\s+name="([^"]+)"(?:\s+([^>]*))?>(.*?)</｜DSML｜parameter>',
        re.DOTALL,
    )

    # 匹配属性（如 string="true"）
    ATTR_PATTERN = re.compile(r'(\w+)="([^"]*)"')

    # 特殊字符转义映射
    ESCAPE_MAP: ClassVar[dict[str, str]] = {
        "&lt;": "<",
        "&gt;": ">",
        "&amp;": "&",
        "&quot;": '"',
        "&apos;": "'",
    }

    @classmethod
    def _unescape_xml(cls, text: str) -> str:
        """反转义XML实体"""
        for escaped, unescaped in cls.ESCAPE_MAP.items():
            text = text.replace(escaped, unescaped)
        return text

    @classmethod
    def _escape_xml(cls, text: str) -> str:
        """转义XML特殊字符"""
        # 反向映射
        unescape_to_escape = {v: k for k, v in cls.ESCAPE_MAP.items()}
        for unescaped, escaped in unescape_to_escape.items():
            text = text.replace(unescaped, escaped)
        return text

    @classmethod
    def _parse_parameter_value(cls, raw_value: str, param_type: str) -> Any:
        """解析参数值"""
        raw_value = raw_value.strip()

        # 处理类型转换
        if param_type == "string" or param_type == "true":
            # string="true" 通常表示值是字符串类型
            return cls._unescape_xml(raw_value)

        elif param_type == "number":
            try:
                # 尝试解析为浮点数或整数
                if "." in raw_value:
                    return float(raw_value)
                return int(raw_value)
            except ValueError:
                # 如果失败，返回原始字符串
                return raw_value

        elif param_type == "boolean":
            return raw_value.lower() in ("true", "1", "yes")

        elif param_type in ("object", "array"):
            try:
                return json.loads(raw_value)
            except json.JSONDecodeError:
                # 如果不是合法JSON，返回原始字符串
                return raw_value

        elif param_type == "null":
            return None

        else:
            # 未知类型，尝试智能解析
            if raw_value.lower() in ("true", "false"):
                return raw_value.lower() == "true"
            elif raw_value.isdigit():
                return int(raw_value)
            elif re.match(r"^\d+\.\d+$", raw_value):
                return float(raw_value)
            elif raw_value == "null":
                return None
            else:
                return cls._unescape_xml(raw_value)

    @classmethod
    def _parse_parameter(cls, param_match: re.Match[str]) -> DSMLParameter:
        """解析单个参数"""
        name = param_match.group(1)
        attrs_text = param_match.group(2) or ""
        raw_value = param_match.group(3)

        # 解析属性
        attrs = {}
        param_type = ParamType.STRING  # 默认类型

        for attr_match in cls.ATTR_PATTERN.finditer(attrs_text):
            attr_name = attr_match.group(1)
            attr_value = attr_match.group(2)
            attrs[attr_name] = attr_value

            if attr_name == "type" or attr_name == "string":
                # 尝试确定参数类型
                try:
                    param_type = ParamType(attr_value.lower())
                except ValueError:
                    param_type = ParamType.UNKNOWN

        # 解析参数值
        type_str: str = attrs.get("type", attrs.get("string", "string"))
        value = cls._parse_parameter_value(raw_value, type_str)

        return DSMLParameter(
            name=name,
            value=value,
            type=param_type,
            raw_value=raw_value,
            attributes=attrs,
        )

    @classmethod
    def _parse_invoke(
        cls, invoke_match: re.Match[str], parent_xml: str = ""
    ) -> DSMLFunctionCall:
        """解析单个函数调用"""
        name: str = invoke_match.group(1)
        inner_xml: str = invoke_match.group(2)
        full_xml: str = invoke_match.group(0)

        # 查找嵌套的函数调用
        nested_calls = []
        nested_invokes: list[re.Match[str]] = list(
            cls.INVOKE_PATTERN.finditer(inner_xml)
        )

        if nested_invokes:
            # 有嵌套调用，需要先处理嵌套
            for nested_match in nested_invokes:
                nested_call: DSMLFunctionCall = cls._parse_invoke(
                    nested_match, inner_xml
                )
                nested_calls.append(nested_call)

        # 解析当前层的参数（排除嵌套调用的部分）
        parameters = []
        param_matches: list[re.Match[str]] = list(
            cls.PARAMETER_PATTERN.finditer(inner_xml)
        )

        for param_match in param_matches:
            # 检查这个参数是否在嵌套调用内部
            param_start, _ = param_match.span()

            # 如果参数在任何一个嵌套调用内部，则跳过
            inside_nested = False
            for nested_call in nested_calls:
                nested_start: int = inner_xml.find(nested_call.raw_xml)
                nested_end: int = nested_start + len(nested_call.raw_xml)
                if nested_start <= param_start < nested_end:
                    inside_nested = True
                    break

            if not inside_nested:
                parameter: DSMLParameter = cls._parse_parameter(param_match)
                parameters.append(parameter)

        return DSMLFunctionCall(
            name=name,
            parameters=parameters,
            nested_calls=nested_calls,
            raw_xml=full_xml,
        )

    @classmethod
    def extract_dsml_blocks(cls, text: str) -> list[str]:
        """从文本中提取所有DSML块"""
        blocks = [match.group(0) for match in cls.DSML_BLOCK_PATTERN.finditer(text)]
        return blocks

    @classmethod
    def parse(cls, text: str) -> list[DSMLFunctionCall]:
        """
        解析包含DSML的文本

        Args:
            text: 包含DSML的文本

        Returns:
            解析出的函数调用列表

        Raises:
            DSMLParseError: 解析失败时抛出
        """
        try:
            # 提取所有DSML块
            dsml_blocks = cls.extract_dsml_blocks(text)

            if not dsml_blocks:
                return []

            function_calls = []

            for block in dsml_blocks:
                # 解析块内的所有函数调用
                invoke_matches: list[re.Match[str]] = list(
                    cls.INVOKE_PATTERN.finditer(block)
                )

                for invoke_match in invoke_matches:
                    function_call: DSMLFunctionCall = cls._parse_invoke(
                        invoke_match, block
                    )
                    function_calls.append(function_call)

            return function_calls

        except Exception as e:
            raise DSMLParseError(f"Failed to parse DSML: {e!s}") from e

    @classmethod
    def find_and_clean(
        cls, text: str, remove: bool = True
    ) -> tuple[str, list[DSMLFunctionCall]]:
        """
        查找并清理文本中的DSML

        Args:
            text: 原始文本
            remove: 是否从文本中移除DSML

        Returns:
            (清理后的文本, 解析出的函数调用列表)
        """
        # 解析DSML
        function_calls = cls.parse(text)

        if remove and function_calls:
            # 移除所有DSML块
            cleaned_text = cls.DSML_BLOCK_PATTERN.sub("", text).strip()
        else:
            cleaned_text = text

        return cleaned_text, function_calls

    @classmethod
    def to_dict(cls, function_calls: list[DSMLFunctionCall]) -> list[dict[str, Any]]:
        """将函数调用列表转换为字典（便于序列化）"""
        return [call.model_dump() for call in function_calls]


# 运行示例


def example_print() -> None:
    # 示例文本（包含DSML和普通文本）
    sample_text = """
    这是普通文本。

    <｜DSML｜function_calls>
    <｜DSML｜invoke name="webscraper">
    <｜DSML｜parameter name="url" string="true">https://amrita.suggar.top/docs</｜DSML｜parameter>
    <｜DSML｜parameter name="depth" type="number">2</｜DSML｜parameter>
    <｜DSML｜parameter name="extract_links" string="true">true</｜DSML｜parameter>
    </｜DSML｜invoke>
    </｜DSML｜function_calls>

    更多文本内容。

    <｜DSML｜function_calls>
    <｜DSML｜invoke name="think_and_reason">
    <｜DSML｜parameter name="content" string="true">需要分析文档结构</｜DSML｜parameter>
    </｜DSML｜invoke>
    </｜DSML｜function_calls>
    """

    parser = DSMLParser()

    try:
        # 1. 解析DSML
        print("=== 解析DSML ===")
        function_calls = parser.parse(sample_text)

        for i, call in enumerate(function_calls):
            print(f"\n调用 {i + 1}: {call.name}")
            for param in call.parameters:
                print(f"  - {param.name}: {param.value} (类型: {param.type.value})")

        # 2. 清理文本
        print("\n=== 清理文本 ===")
        cleaned_text, _extracted_calls = parser.find_and_clean(sample_text, remove=True)
        print("清理后文本:")
        print(f'"{cleaned_text}"')

        # 3. 转换为字典
        print("\n=== 转换为字典 ===")
        dict_data = parser.to_dict(function_calls)
        print(json.dumps(dict_data, indent=2, ensure_ascii=False))

    except DSMLParseError as e:
        print(f"解析错误: {e}")


if __name__ == "__main__":
    example_print()
