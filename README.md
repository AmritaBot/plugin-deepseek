# amrita_plugin_deepseek

`amrita_plugin_deepseek` 是 Amrita 框架官方提供的 DeepSeek 模型扩展，用于**解析、拦截并安全执行 DeepSeek DSML（DeepSeek Markup Language）工具调用**。

## 什么是 DSML？

DSML（DeepSeek Markup Language）是 DeepSeek 模型内部用于描述 **Tool Calling（工具调用）** 的底层标记语言。当模型需要调用外部工具时，会生成类似下面的内容：

### DeepSeek V3/R1

```xml
<｜DSML｜function_calls>
<｜DSML｜invoke name="webscraper">
<｜DSML｜parameter name="url">https://example.com</｜DSML｜parameter>
</｜DSML｜invoke>
</｜DSML｜function_calls>
```

### DeepSeek V4

```xml
<｜｜DSML｜｜tool_calls>
<｜｜DSML｜｜invoke name="execute_command">
<｜｜DSML｜｜parameter name="command" string="true">uname -a</｜｜DSML｜｜parameter>
</｜｜DSML｜｜invoke>
</｜｜DSML｜｜tool_calls>
```

在正常情况下，这些标记会由模型运行时自动解析，最终用户**不会看到任何 DSML 内容**。

然而，在消息链中断、工具调用流程异常、适配器未正确处理 Tool Calling，或直接与模型 API 交互等场景下，DeepSeek 可能会将这些底层标记直接输出给用户，不仅影响对话体验，也无法真正完成工具调用。

`amrita_plugin_deepseek` 正是为了解决这一问题而设计。

插件会自动识别模型输出中的 DSML 标签，将其解析为工具调用，并在安全校验通过后执行对应工具，最后把执行结果返回给模型继续生成自然语言回复，使整个 Tool Calling 流程恢复正常，对最终用户保持透明。

除了完成 DSML 的解析与执行外，插件还提供了一套完整的安全防护机制，用于检测恶意 DSML、提示注入（Prompt Injection）以及其他潜在风险，保障 AI 对话系统的安全性与可靠性。

## ✨ 功能特点

### DSML 解析

- 自动识别 DeepSeek 输出的 DSML 标签
- 解析函数调用及参数
- 安全执行对应工具
- 自动将执行结果回写至模型上下文
- 全流程对最终用户透明

### 安全防护

- 双向安全检测（用户输入 / AI 输出）
- Prompt Injection 防护
- MinHash 相似度关键词检测
- 恶意 DSML 标签拦截
- 实时管理员安全警报

### 开箱即用

- 零配置安装
- 自动注册至 Amrita
- 自动启用全部安全策略
- 支持通过 `.env` 调整安全检测敏感度

## 快速开始

```shell
ambot plugin install amrita_plugin_deepseek
```

## .env 配置项

虽然本插件采用零配置设计，但您可以通过 `.env` 文件自定义安全检测的敏感度。在项目根目录创建 `.env` 文件并添加以下配置：

```env
# DeepSeek安全扩展包配置
SECURITY_INVOKE=0.65
```

### 配置项说明

- **`SECURITY_INVOKE`**:
  - **类型**: 浮点数 (0.0 - 1.0)
  - **默认值**: `0.65`
  - **说明**: 设置安全检测的MinHash相似度阈值。值越高，检测越严格（更少的误报，但可能漏检）；值越低，检测越敏感（更多的检测，但可能增加误报）。
  - **建议范围**: `0.5` - `0.8`
    - `0.5` - `0.6`: 低敏感度，适合宽松环境
    - `0.65` - `0.7`: 中等敏感度，推荐默认值
    - `0.75` - `0.8`: 高敏感度，适合高安全要求环境

- **`APPEND_TOOL`**:
  - **类型**: 布尔值 (true/false)
  - **默认值**: `false`
  - **说明**: 是否将工具调用结果追加到模型上下文中。
  - **建议**: 默认关闭

> **注意**: 修改配置后需要重启应用才能生效。
