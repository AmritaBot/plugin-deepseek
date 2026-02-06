# amrita_plugin_deepseek

这是一个针对 Amrita 框架的插件，专门用于处理 DeepSeek 模型生成的 DSML (DeepSeek Markup Language) 函数调用标签。该插件能够解析和执行 AI 模型生成的工具调用指令。

## 功能特点

- **DSML 解析**: 解析 DeepSeek 模型错误生成的 `<｜DSML｜function_calls>` 标签
- **工具调用执行**: 自动识别并执行模型建议的工具调用
- **参数处理**: 正确解析各种类型的参数（字符串、数字、布尔值等）
- **错误处理**: 当工具调用出现异常时，优雅地处理错误
- **响应整合**: 将工具调用结果重新整合到对话流程中

## 工作原理

插件通过以下步骤处理包含 DSML 的响应：

1. **检测**: 在 AI 响应中查找 DSML 标签
2. **解析**: 解析函数调用和参数
3. **执行**: 执行对应的工具
4. **反馈**: 将执行结果添加回对话上下文中

## DSML 标签格式

DSML 使用特定格式的 XML 风格标签来表示函数调用：

```xml
<｜DSML｜function_calls>
<｜DSML｜invoke name="tool_name">
<｜DSML｜parameter name="param1" type="string">value1</｜DSML｜parameter>
<｜DSML｜parameter name="param2" type="number">42</｜DSML｜parameter>
</｜DSML｜invoke>
</｜DSML｜function_calls>
```

## 安装方法

使用 uv 安装（推荐）：

```bash
uv add amrita_plugin_deepseek
```

或者将此插件加入到你的项目依赖中：

```toml
[project]
dependencies = [
    "amrita_plugin_deepseek",
]
```

或者使用 `Amrita-CLI` 安装

```bash
amrita plugin install amrita_plugin_deepseek
```

## 配置

此插件不需要额外配置。安装后会自动注册到 Amrita 框架中。

## 使用示例

当 DeepSeek 模型生成包含 DSML 标签的响应时，插件会自动解析并执行相应的工具调用。例如，如果模型建议使用网络爬虫工具获取信息：

```text
我需要获取 https://amrita.suggar.top/docs 的内容。

<｜DSML｜function_calls>
<｜DSML｜invoke name="webscraper">
<｜DSML｜parameter name="url" string="true">https://amrita.suggar.top/docs</｜DSML｜parameter>
</｜DSML｜invoke>
</｜DSML｜function_calls>
```

插件会自动执行 webscraper 工具，并将结果返回给模型，然后模型可以基于这些结果继续对话。

## 支持的适配器

- OneBot V11

## 依赖项

- Python >= 3.10
- amrita[full] >= 0.7.3.2

## 开发

### 环境设置

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 同步依赖
uv sync
```

## 许可证

请参阅项目仓库中的许可证文件。
