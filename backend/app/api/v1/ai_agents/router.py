from typing import Any
import io
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough
import pypdf
import docx
import os
import tempfile

win32com_client = None
pythoncom_module = None

if os.name == 'nt':
    try:
        import win32com.client as win32com_client
        import pythoncom as pythoncom_module
    except ImportError:
        pass

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

@router.post("/translate-file")
async def translate_file(
    file: UploadFile = File(...),
    target_language: str = Form("zh-CN")
) -> StreamingResponse:
    """
    5. 文件翻译演示
    支持 PDF 和 Word 文件上传，提取文本后进行流式翻译。
    """
    content = await file.read()
    text = ""
    
    try:
        if file.filename.lower().endswith(".pdf"):
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        elif file.filename.lower().endswith(".docx"):
            doc = docx.Document(io.BytesIO(content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif file.filename.lower().endswith(".doc"):
            # 使用 pywin32 处理 .doc (仅限 Windows)
            if os.name != 'nt':
                raise HTTPException(status_code=400, detail="当前系统不支持 .doc 格式，请在 Windows 环境下运行或使用 .docx 格式。")
            
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as tmp:
                tmp.write(content)
                tmp_path = tmp.name
                # 重要：必须关闭文件，否则 Word 无法打开
                tmp.close()
            
            try:
                # 检查模块是否存在
                if not pythoncom_module or not win32com_client:
                    raise HTTPException(status_code=500, detail="Word 解析引擎 (pywin32) 未能正确加载，请联系管理员。")

                # 初始化 COM 组件
                pythoncom_module.CoInitialize()
                word = None
                try:
                    word = win32com_client.Dispatch("Word.Application")
                    word.Visible = False
                    abs_path = os.path.abspath(tmp_path)
                    doc = word.Documents.Open(abs_path)
                    try:
                        text = doc.Content.Text
                    finally:
                        doc.Close()
                finally:
                    if word:
                        word.Quit()
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                raise HTTPException(status_code=500, detail=f"Word 解析失败 (请确保已安装 Microsoft Word): {str(e)}")
            finally:
                if pythoncom_module:
                    pythoncom_module.CoUninitialize()
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式。请上传 PDF, Word (.docx) 或 Word (.doc) 文件。")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="未能从文件中提取到有效文本。")

    llm = get_llm(streaming=True)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一位精通多种语言的翻译官。"),
        ("user", "请将以下内容翻译成{target_language}：\n\n{text}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    async def event_generator():
        # 先发送文件名作为确认消息（可选）
        # yield f"--- 文件: {file.filename} ---\n\n"
        async for chunk in chain.astream({
            "text": text,
            "target_language": target_language
        }):
            yield chunk

    return StreamingResponse(event_generator(), media_type="text/event-stream")
