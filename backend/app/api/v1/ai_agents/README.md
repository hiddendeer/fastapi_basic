# LangChain 基础教学演示项目

本模块展示了 LangChain (v0.1+) 的核心用法，并集成在 FastAPI 框架中。

## 核心概念说明

1. **Chat Models (聊天模型)**:
    - 位于 `app/core/ai/llm.py`。
    - 使用封装好的 `ChatOpenAI` 客户端，支持流式和非流式输出。

2. **Prompt Templates (提示词模板)**:
    - 位于 `router.py`。
    - 使用 `ChatPromptTemplate` 管理对话上下文，让 Prompt 结构化且易于维护。

3. **LCEL (LangChain 表达式语言)**:
    - 演示了 `prompt | llm | parser` 这种简洁的链式写法。
    - 这是 LangChain 1.0 后的核心推荐写法。

4. **Output Parsers (输出解析器)**:
    - 演示了 `StrOutputParser`（提取纯文本）和 `PydanticOutputParser`（强类型结构化输出）。

## 如何运行

1. **配置环境变量**:
    确保项目根目录下的 `.env` 文件中有以下配置：

    ```env
    LLM_MODEL_ID=your_model_id
    LLM_API_KEY=your_api_key
    LLM_BASE_URL=your_api_url
    ```

2. **启动后端**:

    ```bash
    cd backend
    uv run fastapi dev app/main.py
    ```

3. **测试接口**:
    打开 Swagger UI: `http://localhost:8000/docs` 并查找 `ai-agents` 分组。

## 学习建议

- **官方文档**: 访问 [LangChain Documentation](https://python.langchain.com/) 了解最新特性。
- **LCEL 深入**: 理解管道符 `|` 的原理，它是构建复杂 Agent 的基础。
- **LangSmith**: 当你的链路变复杂时，建议集成 LangSmith 进行调试和监控。
