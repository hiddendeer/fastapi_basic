# LangChain 1.2.6 核心技术指南

> 基于 LangChain 1.2.6+ 版本的实战教学，展示最常用、最实用的 AI 应用开发技术。

---

## 📚 目录

- [核心概念](#核心概念)
- [环境配置](#环境配置)
- [API 接口详解](#api-接口详解)
- [关键技术点](#关键技术点)
- [常见陷阱](#常见陷阱)
- [最佳实践](#最佳实践)

---

## 核心概念

### 1. LCEL (LangChain Expression Language)

LangChain 1.0+ 的核心编程范式，使用管道符 `|` 构建链式调用：

```python
chain = prompt | llm | parser
result = await chain.ainvoke({"question": "用户问题"})
```

**优势**：
- 代码简洁直观
- 自动优化执行流程
- 支持流式输出
- 易于调试和维护

### 2. LangGraph

LangChain 1.2+ 引入的新架构，用于构建有状态的 AI 应用：

- **Agent**: 基于 LangGraph 的智能代理
- **State**: 状态管理，支持多轮对话
- **Checkpointer**: 持久化状态（支持 Redis/数据库）

### 3. 核心组件

| 组件 | 作用 | 常用类 |
|------|------|--------|
| **LLM** | 大语言模型接口 | `ChatOpenAI` |
| **Prompt** | 提示词模板 | `ChatPromptTemplate` |
| **Parser** | 输出解析器 | `StrOutputParser`, `PydanticOutputParser` |
| **History** | 对话历史管理 | `RunnableWithMessageHistory` |
| **Agent** | 工具调用代理 | `create_agent` (LangGraph) |

---

## 环境配置

### 1. 安装依赖

```bash
# backend/pyproject.toml
langchain>=1.2.6
langchain-openai>=1.1.7
```

### 2. 配置环境变量

在项目根目录 `.env` 文件中：

```env
# LLM 配置
LLM_MODEL_ID=gpt-4o
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
```

### 3. 启动项目

```bash
cd backend
uv run fastapi dev app/main.py
```

访问 Swagger UI: `http://localhost:8000/docs`

---

## API 接口详解

### 1. 基础对话 `/chat`

**功能**：最简单的 LangChain 用法演示

```python
@router.post("/chat", response_model=ChatResponse)
async def basic_chat(request: ChatRequest):
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个友好的助手，请回答用户的问题"),
        ("user", "{question}")
    ])

    # LCEL 链式调用
    chain = prompt | llm | StrOutputParser()
    result = await chain.ainvoke({"question": request.message})

    return ChatResponse(response=result)
```

**关键点**：
- 使用 `from_messages()` 创建结构化提示词
- `StrOutputParser` 自动提取文本内容
- `ainvoke()` 异步调用（推荐）

---

### 2. 流式响应 `/stream`

**功能**：实时推送 LLM 生成过程

```python
@router.post("/stream")
async def streaming_chat(request: ChatRequest):
    llm = get_llm(streaming=True)
    prompt = ChatPromptTemplate.from_template("{question}")
    chain = prompt | llm | StrOutputParser()

    async def event_generator():
        async for chunk in chain.astream({"question": request.message}):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**关键点**：
- `streaming=True` 启用流式输出
- `astream()` 返回异步生成器
- FastAPI 的 `StreamingResponse` 自动处理 SSE

---

### 3. 翻译功能 `/translate`

**功能**：LCEL 链式调用 + 流式输出

```python
@router.post("/translate")
async def translate_text(request: TranslationRequest):
    llm = get_llm(streaming=True)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一位精通多种语言的翻译官。"),
        ("user", "请将以下内容翻译成{target_language}：\n\n{text}")
    ])

    chain = prompt | llm | StrOutputParser()

    async def event_generator():
        async for chunk in chain.astream({
            "text": request.text,
            "target_language": request.target_language
        }):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**关键点**：
- 支持多参数传递
- 流式返回翻译结果
- 提示词模板中的变量自动替换

---

### 4. 结构化输出 `/extract`

**功能**：强制 LLM 返回 Pydantic 模型数据

```python
@router.post("/extract", response_model=PersonInfo)
async def extract_info(request: ExtractionRequest):
    llm = get_llm()

    # 初始化解析器
    parser = PydanticOutputParser(pydantic_object=PersonInfo)

    # 注入格式化指令
    prompt = ChatPromptTemplate.from_template(
        "从以下文本中提取人物信息。\n{format_instructions}\n文本内容：{text}"
    )
    prompt = prompt.partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser
    return await chain.ainvoke({"text": request.text})
```

**关键点**：
- `PydanticOutputParser` 确保输出格式
- `partial()` 预填充部分变量
- 自动解析为 Pydantic 对象

---

### 5. 文件翻译 `/translate-file`

**功能**：支持 PDF/Word 文件上传并翻译

```python
@router.post("/translate-file")
async def translate_file(
    file: UploadFile = File(...),
    target_language: str = Form("zh-CN")
):
    content = await file.read()
    text = ""

    # PDF 处理
    if file.filename.lower().endswith(".pdf"):
        pdf_reader = pypdf.PdfReader(io.BytesIO(content))
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"

    # DOCX 处理
    elif file.filename.lower().endswith(".docx"):
        doc = docx.Document(io.BytesIO(content))
        for para in doc.paragraphs:
            text += para.text + "\n"

    # 使用 LLM 翻译
    llm = get_llm(streaming=True)
    chain = prompt | llm | StrOutputParser()

    async def event_generator():
        async for chunk in chain.astream({
            "text": text,
            "target_language": target_language
        }):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**关键点**：
- 使用 `pypdf` 提取 PDF 文本
- 使用 `python-docx` 处理 Word 文档
- 流式返回翻译结果

---

### 6. 带记忆的对话 `/langchain-function`

**功能**：多轮对话记忆管理

```python
@router.post("/langchain-function")
async def langchainFunction(request: ChatRequest):
    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个友好的助手，请根据对话历史回答用户的问题"),
        ("placeholder", "{chat_history}"),  # 占位符：历史记录
        ("user", "{input}")  # ⚠️ 注意：不要用 f-string
    ])

    chain = prompt | llm | StrOutputParser()

    # 对话历史存储
    store: Dict[str, list] = {}

    def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = []
        history = InMemoryChatMessageHistory()
        for msg in store.get(session_id, []):
            history.add_message(msg)
        return history

    # 包装链以支持历史记录
    conversational_chain = RunnableWithMessageHistory(
        runnable=chain,
        get_session_history=get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    config = {"configurable": {"session_id": "default_session"}}
    result = await conversational_chain.ainvoke(
        {"input": request.message},
        config=config
    )

    return result
```

**关键点**：
- `placeholder` 用于注入历史记录
- `session_id` 区分不同会话
- 生产环境应使用 Redis/数据库存储历史

---

### 7. Agent 工具调用 `/langchainReact`

**功能**：LangChain 1.2+ 新 API，基于 LangGraph

```python
async def langchainReact(request: ChatRequest):
    from langchain.agents import create_agent

    llm = get_llm()

    # 定义工具
    tools = []  # 添加你的工具

    # 创建 Agent (LangGraph 方式)
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="你是一个友好的助手"
    )

    # 调用 Agent
    result = await agent.ainvoke({
        "messages": [("user", request.message)]
    })

    # 返回最后一条消息
    return result["messages"][-1].content
```

**关键点**：
- LangChain 1.2+ 使用 `create_agent` (LangGraph)
- 不再需要 `AgentExecutor`
- 输入格式：`{"messages": [("user", "文本")]}`
- 输出格式：`{"messages": [...]}`

---

## 关键技术点

### 1. 提示词模板的三种写法

#### 写法一：简单模板
```python
prompt = ChatPromptTemplate.from_template("回答问题：{question}")
```

#### 写法二：消息列表（推荐）
```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个助手"),
    ("user", "{question}")
])
```

#### 写法三：部分预填充
```python
prompt = ChatPromptTemplate.from_template(
    "{format_instructions}\n文本：{text}"
)
prompt = prompt.partial(
    format_instructions="请输出 JSON 格式"
)
```

### 2. 流式 vs 非流式

| 方法 | 用途 | 返回值 |
|------|------|--------|
| `invoke()` | 同步调用 | 完整结果 |
| `ainvoke()` | 异步调用（推荐） | 完整结果 |
| `stream()` | 同步流式 | 生成器 |
| `astream()` | 异步流式（推荐） | 异步生成器 |

### 3. 输出解析器对比

| 解析器 | 用途 | 返回类型 |
|--------|------|----------|
| `StrOutputParser` | 纯文本输出 | `str` |
| `PydanticOutputParser` | 结构化数据 | Pydantic 模型 |

---

## 常见陷阱

### ⚠️ 陷阱 1：f-string 错误使用

**错误代码**：
```python
("user", f"{input}")  # ❌ 会被求值为 "<built-in function input>"
```

**正确写法**：
```python
("user", "{input}")  # ✅ 作为占位符，运行时替换
```

### ⚠️ 陷阱 2：LangChain 1.2 的 Agent API 变化

**旧 API (已废弃)**：
```python
from langchain.agents import create_react_agent, AgentExecutor

agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
executor = AgentExecutor(agent=agent, tools=tools)
result = await executor.ainvoke({"input": message})
```

**新 API (LangChain 1.2+)**：
```python
from langchain.agents import create_agent

agent = create_agent(model=llm, tools=tools, system_prompt=prompt)
result = await agent.ainvoke({"messages": [("user", message)]})
```

### ⚠️ 陷阱 3：对话历史类型错误

**错误代码**：
```python
store: Dict[str, list[BaseChatMessageHistory]] = {}  # ❌ 类型错误
```

**正确写法**：
```python
from langchain_core.messages import BaseMessage
store: Dict[str, list[BaseMessage]] = {}  # ✅ 存储消息列表
```

---

## 最佳实践

### 1. 使用异步方法

```python
# ✅ 推荐
result = await chain.ainvoke({"question": "问题"})

# ❌ 避免
result = chain.invoke({"question": "问题"})
```

### 2. 生产环境状态管理

```python
# 开发环境：内存存储
store = {}

# 生产环境：Redis/数据库
from redis import Redis
redis_client = Redis(host='localhost', port=6379, db=0)
```

### 3. 错误处理

```python
try:
    result = await chain.ainvoke({"question": message})
except Exception as e:
    raise HTTPException(status_code=500, detail=f"LLM 调用失败: {str(e)}")
```

### 4. 监控和调试

集成 [LangSmith](https://smith.langchain.com/) 进行链路追踪：

```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your_langsmith_key"
```

---

## 附录：FastAPI + Redis 核心用法

> 在生产环境中，使用 Redis 存储对话历史、缓存数据是最常见的做法。以下是核心用法总结。

### 1. 安装依赖

```bash
# backend/pyproject.toml
redis>=5.0.0
```

### 2. 基础配置

```python
# app/core/redis.py
import redis
from typing import Optional
from contextlib import contextmanager

class RedisClient:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True  # 自动解码为字符串
        )

    @contextmanager
    def get_connection(self):
        """获取 Redis 连接（上下文管理器）"""
        yield self.client

# 全局实例
redis_client = RedisClient(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0))
)
```

### 3. 核心操作

#### 3.1 字符串操作

```python
from app.core.redis import redis_client

# 设置值（永久）
redis_client.client.set("key", "value")

# 设置值（带过期时间，单位：秒）
redis_client.client.setex("key", 3600, "value")  # 1小时后过期

# 获取值
value = redis_client.client.get("key")

# 删除
redis_client.client.delete("key")

# 检查是否存在
exists = redis_client.client.exists("key")
```

#### 3.2 哈希表操作（适合存储结构化数据）

```python
# 设置哈希字段
redis_client.client.hset("user:123", mapping={
    "name": "张三",
    "email": "zhang@example.com",
    "age": "25"
})

# 获取单个字段
name = redis_client.client.hget("user:123", "name")

# 获取所有字段
user_data = redis_client.client.hgetall("user:123")

# 删除哈希字段
redis_client.client.hdel("user:123", "email")

# 获取所有字段名
fields = redis_client.client.hkeys("user:123")
```

#### 3.3 列表操作（适合存储历史记录）

```python
# 左侧插入（最新的在前面）
redis_client.client.lpush("chat:history:user123", '{"role": "user", "content": "你好"}')
redis_client.client.lpush("chat:history:user123", '{"role": "assistant", "content": "你好！"}')

# 获取列表（指定范围）
history = redis_client.client.lrange("chat:history:user123", 0, 9)  # 获取前10条

# 获取列表长度
length = redis_client.client.llen("chat:history:user123")

# 保留指定范围（删除其他）
redis_client.client.ltrim("chat:history:user123", 0, 19)  # 只保留前20条

# 删除列表
redis_client.client.delete("chat:history:user123")
```

#### 3.4 JSON 操作（需要 RedisJSON 模块）

```python
import json

# 存储 JSON（字符串方式）
data = {"name": "张三", "age": 25}
redis_client.client.set("user:123", json.dumps(data))

# 读取 JSON
value = redis_client.client.get("user:123")
user_data = json.loads(value) if value else None
```

### 4. 实战：对话历史存储

#### 方案一：使用列表存储

```python
from app.core.redis import redis_client
import json

async def save_chat_message(session_id: str, role: str, content: str):
    """保存单条消息"""
    key = f"chat:history:{session_id}"
    message = {"role": role, "content": content, "timestamp": time.time()}

    # 添加到列表头部
    redis_client.client.lpush(key, json.dumps(message))

    # 只保留最近 100 条
    redis_client.client.ltrim(key, 0, 99)

    # 设置过期时间（7天）
    redis_client.client.expire(key, 604800)

async def get_chat_history(session_id: str, limit: int = 20) -> list:
    """获取历史记录"""
    key = f"chat:history:{session_id}"

    # 获取最近的 N 条
    messages = redis_client.client.lrange(key, 0, limit - 1)

    # 反转（因为 lpush 是倒序存储的）
    messages.reverse()

    return [json.loads(msg) for msg in messages]

async def clear_chat_history(session_id: str):
    """清空历史记录"""
    key = f"chat:history:{session_id}"
    redis_client.client.delete(key)
```

#### 方案二：集成到 LangChain

```python
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
from app.core.redis import redis_client
import json

class RedisChatMessageHistory(BaseChatMessageHistory):
    """基于 Redis 的对话历史管理"""

    def __init__(self, session_id: str, ttl: int = 604800):
        self.session_id = session_id
        self.key = f"chat:history:{session_id}"
        self.ttl = ttl  # 默认7天过期

    @property
    def messages(self) -> list[BaseMessage]:
        """获取所有消息"""
        data = redis_client.client.lrange(self.key, 0, -1)
        messages = []

        for item in reversed(data):  # Redis 是倒序的
            msg = json.loads(item)
            if msg["type"] == "human":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["type"] == "ai":
                messages.append(AIMessage(content=msg["content"]))

        return messages

    def add_message(self, message: BaseMessage) -> None:
        """添加消息"""
        msg_data = {
            "type": "human" if isinstance(message, HumanMessage) else "ai",
            "content": message.content
        }

        redis_client.client.lpush(self.key, json.dumps(msg_data))
        redis_client.client.expire(self.key, self.ttl)

    def clear(self) -> None:
        """清空消息"""
        redis_client.client.delete(self.key)

# 使用示例
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    return RedisChatMessageHistory(session_id)

conversational_chain = RunnableWithMessageHistory(
    runnable=chain,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)
```

### 5. 缓存装饰器

```python
from functools import wraps
import hashlib
import json

def cache_result(ttl: int = 3600):
    """Redis 缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            key_data = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = f"cache:{hashlib.md5(key_data.encode()).hexdigest()}"

            # 尝试从缓存获取
            cached = redis_client.client.get(cache_key)
            if cached:
                return json.loads(cached)

            # 执行函数
            result = await func(*args, **kwargs)

            # 存入缓存
            redis_client.client.setex(
                cache_key,
                ttl,
                json.dumps(result, ensure_ascii=False)
            )

            return result
        return wrapper
    return decorator

# 使用示例
@cache_result(ttl=1800)  # 缓存30分钟
async def expensive_operation(param: str):
    # 耗时操作
    return {"result": f"处理结果: {param}"}
```

### 6. 环境变量配置

```env
# .env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password  # 可选
```

### 7. 连接池配置（生产环境推荐）

```python
from redis import ConnectionPool

class RedisClient:
    def __init__(self):
        self.pool = ConnectionPool(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
            max_connections=50  # 最大连接数
        )
        self.client = redis.Redis(connection_pool=self.pool)
```

### 8. 常见操作速查表

| 操作 | 命令 | 说明 |
|------|------|------|
| **字符串** | `set(key, value)` | 设置值 |
| | `get(key)` | 获取值 |
| | `setex(key, ttl, value)` | 设置值+过期时间 |
| | `delete(key)` | 删除 |
| **哈希** | `hset(key, field, value)` | 设置字段 |
| | `hget(key, field)` | 获取字段 |
| | `hgetall(key)` | 获取所有字段 |
| | `hdel(key, field)` | 删除字段 |
| **列表** | `lpush(key, value)` | 左侧插入 |
| | `rpush(key, value)` | 右侧插入 |
| | `lrange(key, start, stop)` | 获取范围 |
| | `ltrim(key, start, stop)` | 保留范围 |
| **通用** | `expire(key, ttl)` | 设置过期时间 |
| | `ttl(key)` | 获取剩余时间 |
| | `exists(key)` | 检查是否存在 |

### 9. 最佳实践

1. **设置过期时间**：避免内存泄漏
   ```python
   redis_client.client.setex("key", 3600, "value")  # 推荐
   redis_client.client.expire("key", 3600)  # 也可以
   ```

2. **使用连接池**：生产环境必须使用
   ```python
   pool = ConnectionPool(max_connections=50)
   client = redis.Redis(connection_pool=pool)
   ```

3. **批量操作**：使用 Pipeline 提高性能
   ```python
   pipe = redis_client.client.pipeline()
   for i in range(100):
       pipe.set(f"key:{i}", f"value:{i}")
   pipe.execute()  # 一次性执行
   ```

4. **错误处理**：
   ```python
   try:
       value = redis_client.client.get("key")
   except redis.ConnectionError:
       # 降级处理：使用内存缓存或直接返回
       value = None
   ```

---

## 附录：FastAPI 多环境配置最佳实践

> 在实际项目中，需要区分开发、测试、生产环境。以下是多环境配置的完整方案。

### 1. 环境文件结构

```
backend/
├── .env                 # 开发环境（默认，不提交到 Git）
├── .env.test            # 测试环境（不提交到 Git）
├── .env.production      # 生产环境（不提交到 Git）
├── .env.example         # 示例配置（提交到 Git）
└── app/
    └── core/
        └── config.py    # 配置加载模块
```

### 2. 环境配置文件示例

#### `.env.example`（提交到 Git）

```env
# ================================
# 环境配置示例文件
# 复制此文件为 .env 并填写真实值
# ================================

# 环境标识
ENVIRONMENT=development
DEBUG=true

# ================================
# API 配置
# ================================
API_V1_STR=/api/v1
PROJECT_NAME="FastAPI AI Agents"
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# ================================
# LLM 配置
# ================================
LLM_MODEL_ID=gpt-4o
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# ================================
# Redis 配置
# ================================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# ================================
# 数据库配置
# ================================
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# ================================
# 安全配置
# ================================
SECRET_KEY=your-secret-key-here-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ================================
# 日志配置
# ================================
LOG_LEVEL=INFO
```

#### `.env`（开发环境）

```env
# 开发环境配置
ENVIRONMENT=development
DEBUG=true

# LLM - 开发环境
LLM_MODEL_ID=gpt-4o
LLM_API_KEY=sk-dev-xxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000

# Redis - 本地
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# 日志 - 详细输出
LOG_LEVEL=DEBUG
```

#### `.env.test`（测试环境）

```env
# 测试环境配置
ENVIRONMENT=test
DEBUG=false

# LLM - 测试环境（可以使用 Mock 或更便宜的模型）
LLM_MODEL_ID=gpt-3.5-turbo
LLM_API_KEY=sk-test-xxx
LLM_BASE_URL=https://api.openai.com/v1
LLM_TEMPERATURE=0.5
LLM_MAX_TOKENS=1000

# Redis - 测试服务器
REDIS_HOST=redis.test.local
REDIS_PORT=6379
REDIS_DB=1  # 使用不同的 DB

# 数据库 - 测试库
DATABASE_URL=postgresql://test_user:test_pass@test-db:5432/test_db

# 日志
LOG_LEVEL=WARNING
```

#### `.env.production`（生产环境）

```env
# 生产环境配置
ENVIRONMENT=production
DEBUG=false

# LLM - 生产环境
LLM_MODEL_ID=gpt-4o
LLM_API_KEY=sk-prod-xxx  # 使用生产环境专用密钥
LLM_BASE_URL=https://api.openai.com/v1
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4000

# Redis - 生产集群
REDIS_HOST=redis.production.internal
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-strong-password-here
REDIS_SSL=true
REDIS_MAX_CONNECTIONS=50

# 数据库 - 生产库（使用连接池）
DATABASE_URL=postgresql://prod_user:strong_pass@prod-db:5432/prod_db?pool_size=20&max_overflow=10

# 安全 - 生产环境密钥（使用随机生成的强密钥）
SECRET_KEY=your-super-secure-random-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS - 仅允许生产域名
BACKEND_CORS_ORIGINS=["https://your-domain.com"]

# 日志
LOG_LEVEL=ERROR

# 监控
SENTRY_DSN=https://xxx@sentry.io/xxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_xxx
```

### 3. 配置加载模块

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    """应用配置类"""

    # 环境标识
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # API 配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FastAPI AI Agents"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # LLM 配置
    LLM_MODEL_ID: str = "gpt-4o"
    LLM_API_KEY: str
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_MAX_CONNECTIONS: int = 50

    # 数据库配置
    DATABASE_URL: str

    # 安全配置
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 日志配置
    LOG_LEVEL: str = "INFO"

    # 监控配置
    SENTRY_DSN: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# 根据环境变量加载不同的配置文件
def get_settings() -> Settings:
    """获取当前环境的配置"""
    env = os.getenv("ENVIRONMENT", "development")

    env_file_map = {
        "development": ".env",
        "test": ".env.test",
        "production": ".env.production",
    }

    env_file = env_file_map.get(env, ".env")

    return Settings(_env_file=env_file)

# 全局配置实例
settings = get_settings()
```

### 4. 运行命令

#### 开发环境

```bash
# 方式一：使用 uv（推荐）
cd backend
uv run fastapi dev app/main.py

# 方式二：明确指定环境
ENVIRONMENT=development uv run fastapi dev app/main.py

# Windows PowerShell
$ENV:ENVIRONMENT="development"; uv run fastapi dev app/main.py
```

#### 测试环境

```bash
# 运行测试
cd backend
ENVIRONMENT=test uv run pytest

# 使用测试环境启动服务
ENVIRONMENT=test uv run fastapi dev app/main.py

# Windows PowerShell
$ENV:ENVIRONMENT="test"; uv run fastapi dev app/main.py
```

#### 生产环境

```bash
# 方式一：使用 uvicorn（推荐）
cd backend
ENVIRONMENT=production uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 方式二：使用 Docker
docker run -d \
  --name fastapi-app \
  --env-file .env.production \
  -p 8000:8000 \
  your-image-name

# 方式三：使用 systemd（Linux 服务）
sudo systemctl start fastapi
```

### 5. Docker 多环境配置

#### `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# 复制代码
COPY ./app ./app

# 暴露端口
EXPOSE 8000

# 启动命令（支持环境变量）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `docker-compose.yml`

```yaml
version: '3.8'

services:
  # 开发环境
  app-dev:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./app:/app/app  # 热重载
    environment:
      - ENVIRONMENT=development
    command: uvicorn app.main:app --host 0.0.0.0 --reload

  # 测试环境
  app-test:
    build: .
    ports:
      - "8001:8000"
    env_file:
      - .env.test
    environment:
      - ENVIRONMENT=test
    command: uv run pytest

  # 生产环境
  app-prod:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    environment:
      - ENVIRONMENT=production
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

#### 使用 Docker Compose

```bash
# 开发环境
docker-compose up app-dev

# 测试环境
docker-compose up app-test

# 生产环境
docker-compose up -d app-prod

# 后台运行
docker-compose up -d

# 查看日志
docker-compose logs -f app-prod
```

### 6. Git 配置

#### `.gitignore`

```gitignore
# 环境配置文件
.env
.env.test
.env.production
.env.local

# 但保留示例文件
!.env.example
```

### 7. 环境切换的最佳实践

#### 方案一：使用启动脚本

```bash
#!/bin/bash
# start.sh

ENV=${1:-development}

case $ENV in
  "dev"|"development")
    export ENVIRONMENT=development
    uv run fastapi dev app/main.py
    ;;
  "test")
    export ENVIRONMENT=test
    uv run pytest
    ;;
  "prod"|"production")
    export ENVIRONMENT=production
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    ;;
  *)
    echo "Usage: ./start.sh [dev|test|prod]"
    exit 1
    ;;
esac
```

使用：

```bash
./start.sh dev      # 开发环境
./start.sh test     # 测试环境
./start.sh prod     # 生产环境
```

#### 方案二：使用 Makefile

```makefile
# Makefile
.PHONY: dev test prod

dev:
	ENVIRONMENT=development uv run fastapi dev app/main.py

test:
	ENVIRONMENT=test uv run pytest

prod:
	ENVIRONMENT=production uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

docker-dev:
	docker-compose up app-dev

docker-test:
	docker-compose up app-test

docker-prod:
	docker-compose up -d app-prod
```

使用：

```bash
make dev          # 开发环境
make test         # 测试环境
make prod         # 生产环境
make docker-prod  # Docker 生产环境
```

### 8. 环境配置检查清单

| 检查项 | 开发环境 | 测试环境 | 生产环境 |
|--------|----------|----------|----------|
| `DEBUG` | `true` | `false` | `false` |
| `ENVIRONMENT` | `development` | `test` | `production` |
| CORS | 允许所有本地 | 允许测试域名 | 仅允许生产域名 |
| 日志级别 | `DEBUG` | `WARNING` | `ERROR` |
| 数据库 | 本地或开发库 | 独立测试库 | 生产主库 + 从库 |
| Redis | 本地 | 测试服务器 | 生产集群 |
| API 密钥 | 开发密钥 | 测试密钥 | 生产密钥（独立） |
| 连接池 | 小（10） | 中（20） | 大（50+） |
| Workers | 1（热重载） | 2 | 4+ |
| 监控 | 可选 | 可选 | 必须（Sentry + LangSmith） |

### 9. 安全建议

1. **永远不要提交敏感信息到 Git**
   ```bash
   # 检查是否已意外提交
   git log --all --full-history -- "*.env"
   ```

2. **使用密钥管理服务**
   - 开发/测试：`.env` 文件
   - 生产：AWS Secrets Manager / Azure Key Vault / HashiCorp Vault

3. **生产环境强制检查**
   ```python
   # app/main.py
   if settings.ENVIRONMENT == "production" and settings.DEBUG:
       raise ValueError("生产环境必须关闭 DEBUG 模式！")

   if settings.ENVIRONMENT == "production" and not settings.SECRET_KEY:
       raise ValueError("生产环境必须设置 SECRET_KEY！")
   ```

---

## 学习资源

- [LangChain 官方文档](https://python.langchain.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

---

## 更新日志

- **v1.2.6**: 更新至 LangChain 1.2.6 API，使用 LangGraph 架构
- **v1.0**: 采用 LCEL 表达式语言
- **v0.1**: 初始版本

---

> 💡 **提示**: 建议配合 Swagger UI (`/docs`) 进行接口测试，快速理解每个功能的效果。
