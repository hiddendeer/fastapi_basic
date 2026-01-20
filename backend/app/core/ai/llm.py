import os
from langchain_openai import ChatOpenAI
from app.core.config import settings

def get_llm(streaming: bool = False) -> ChatOpenAI:
    """
    获取初始化后的 LangChain LLM 客户端。
    
    Args:
        streaming: 是否启用流式输出。默认为 False。
        
    Returns:
        ChatOpenAI: 配置好的 LangChain 聊天模型实例。
    """
    return ChatOpenAI(
        model=settings.LLM_MODEL_ID,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL,
        streaming=streaming,
        temperature=0.1,  # 默认采样温度
    )
