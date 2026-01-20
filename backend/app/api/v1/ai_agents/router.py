from typing import Any
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.core.ai.llm import get_llm
from app.schemas.ai import (
    ChatRequest, 
    ChatResponse, 
    TranslationRequest, 
    TranslationResponse,
    ExtractionRequest,
    PersonInfo
)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def basic_chat(request: ChatRequest) -> Any:
    """
    1. 基础对话演示
    展示最简单的 LangChain 用法：Prompt -> LLM -> String
    """
    # llm = get_llm()
    llm = get_llm()
    # 定义提示词模板
    # prompt = ChatPromptTemplate.from_template("你是一个友好的助手，请回答用户的问题：{question}")
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个友好的助手，请回答用户的问题"),
        ("user", "{question}")
    ])
    
    # 使用 LCEL (LangChain Expression Language) 构建链
    # 逻辑：提示词 -> 模型 -> 解析为字符串
    # chain = prompt | llm | StrOutputParser()
    chain = prompt | llm | StrOutputParser()
    
    # result = await chain.ainvoke({"question": request.message})
    # return ChatResponse(response=result)
    result = await chain.ainvoke({"question": request.message})
    return ChatResponse(response=result)

@router.post("/stream")
async def streaming_chat(request: ChatRequest):
    """
    2. 流式响应演示
    展示如何通过控制器将 LLM 的生成过程实时推送给前端。
    """
    llm = get_llm(streaming=True)
    prompt = ChatPromptTemplate.from_template("{question}")
    chain = prompt | llm | StrOutputParser()

    async def event_generator():
        async for chunk in chain.astream({"question": request.message}):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/translate")
async def translate_text(request: TranslationRequest) -> StreamingResponse:
    """
    3. LCEL 链式调用演示 (流式输出)
    展示如何构建一个稍微复杂的、带有固定逻辑的链，并以流式输出结果。
    """
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

@router.post("/extract", response_model=PersonInfo)
async def extract_info(request: ExtractionRequest) -> Any:
    """
    4. 结构化输出演示 (Output Parser)
    展示如何强制 LLM 返回符合 Pydantic 模型的数据格式。
    """
    llm = get_llm()
    # 初始化解析器
    parser = PydanticOutputParser(pydantic_object=PersonInfo)
    
    # 在提示词中注入格式化指令
    prompt = ChatPromptTemplate.from_template(
        "从以下文本中提取人物信息。\n{format_instructions}\n文本内容：{text}"
    )
    # 注入解析器要求的指令
    prompt = prompt.partial(format_instructions=parser.get_format_instructions())
    
    chain = prompt | llm | parser
    
    return await chain.ainvoke({"text": request.text})
