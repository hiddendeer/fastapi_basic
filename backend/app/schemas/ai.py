from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    """基础对话请求"""
    message: str = Field(..., description="用户发送的消息内容")

class ChatResponse(BaseModel):
    """基础对话响应"""
    response: str = Field(..., description="AI 返回的消息内容")

class TranslationRequest(BaseModel):
    """翻译请求"""
    text: str = Field(..., description="需要翻译的文本")
    target_language: str = Field(default="中文", description="目标语言")

class TranslationResponse(BaseModel):
    """翻译响应"""
    original_text: str
    translated_text: str
    target_language: str

class ExtractionRequest(BaseModel):
    """信息提取请求"""
    text: str = Field(..., description="包含信息的文本数据")

class PersonInfo(BaseModel):
    """从文本中提取的人物信息结构"""
    name: str = Field(..., description="人物姓名")
    age: Optional[int] = Field(None, description="人物年龄")
    occupation: Optional[str] = Field(None, description="职业")
