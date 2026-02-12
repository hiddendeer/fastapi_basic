"""
报警 Agent 路由
实现观察-思考-行动的智能体循环，自动处理系统报警
"""
import os
import logging
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain.agents import create_agent

# Milvus 环境变量清理（与 llamaindex/router.py 保持一致）
if "MILVUS_URI" in os.environ:
    del os.environ["MILVUS_URI"]

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.milvus import MilvusVectorStore

from app.core.ai.llm import get_llm
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# Milvus 辅助函数
# ============================================================

def get_milvus_vector_store() -> MilvusVectorStore:
    """获取 Milvus 向量存储实例"""
    if settings.MILVUS_URI:
        return MilvusVectorStore(
            uri=settings.MILVUS_URI,
            token=settings.MILVUS_TOKEN,
            collection_name=settings.MILVUS_COLLECTION,
            dim=settings.LLAMAINDEX_EMBEDDING_DIM
        )
    elif settings.MILVUS_HOST:
        return MilvusVectorStore(
            uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}",
            user=settings.MILVUS_USER,
            password=settings.MILVUS_PASSWORD,
            collection_name=settings.MILVUS_COLLECTION,
            dim=settings.LLAMAINDEX_EMBEDDING_DIM,
            overwrite=False
        )
    else:
        raise HTTPException(status_code=500, detail="未配置 Milvus 连接信息")

# ============================================================
# 工具函数定义
# ============================================================

# 负责人手机号映射表
CONTACT_PHONE_MAP = {
    "仓库": "13800138001",
    "办公室": "13800138002",
    "换衣间": "13800138003",
    "生产车间": "13800138004",
    "机房": "13800138005",
    "食堂": "13800138006",
    "会议室": "13800138007",
}

# 同义词映射，支持更多变体
LOCATION_SYNONYMS = {
    "仓库": ["仓库", "仓储", "库房", "货仓"],
    "办公室": ["办公室", "写字楼", "办公楼", "办公区"],
    "换衣间": ["换衣间", "更衣室", "更衣间"],
    "生产车间": ["生产车间", "车间", "生产区", "制造车间"],
    "机房": ["机房", "服务器机房", "数据中心", "IDC机房"],
    "食堂": ["食堂", "餐厅", "饭堂"],
    "会议室": ["会议室", "会议厅", "洽谈室"],
}


@tool
def get_contact_phone(location: str) -> str:
    """
    根据地点名称查询负责人手机号。

    Args:
        location: 地点名称，如"仓库"、"办公室"、"换衣间"等

    Returns:
        负责人手机号字符串

    Examples:
        >>> get_contact_phone("仓库")
        "13800138001"
    """
    # 首先精确匹配
    if location in CONTACT_PHONE_MAP:
        return CONTACT_PHONE_MAP[location]

    # 尝试同义词匹配
    for standard_name, synonyms in LOCATION_SYNONYMS.items():
        if location in synonyms:
            return CONTACT_PHONE_MAP[standard_name]

    # 未找到对应负责人
    available_locations = ", ".join(CONTACT_PHONE_MAP.keys())
    return f"未找到地点 '{location}' 的负责人信息。可用地点: {available_locations}"


@tool
def search_emergency_manuals(query: str, top_k: int = 3) -> str:
    """
    从 Milvus 向量数据库中搜索相关的应急处理手册。

    当收到报警信息（如火灾、漏水等）时，使用此工具查询相关的应急处理文档，
    获取专业的处理步骤和注意事项。

    Args:
        query: 查询内容，如"仓库着火"、"机房漏水"等
        top_k: 返回的最相关文档数量，默认为3

    Returns:
        相关应急手册内容的文本摘要

    Examples:
        >>> search_emergency_manuals("仓库着火")
        "找到以下相关应急文档：..."
    """
    try:
        # 获取向量存储
        vector_store = get_milvus_vector_store()

        # 创建索引
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

        # 使用 retriever 检索相关文档
        retriever = index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)

        if not nodes:
            return "未找到相关的应急处理文档。"

        # 整合检索结果
        results = []
        for i, node in enumerate(nodes, 1):
            content = node.node.get_content()
            metadata = node.node.metadata
            score = node.score if hasattr(node, 'score') else 0

            # 提取文档来源
            source = metadata.get('file_name', metadata.get('source', '未知来源'))

            result_text = f"[文档{i}] 来源: {source} (相关度: {score:.4f})\n{content}"
            results.append(result_text)

        return f"找到 {len(nodes)} 条相关应急处理文档：\n\n" + "\n\n".join(results)

    except Exception as e:
        logger.error(f"Milvus 查询失败: {e}")
        return f"查询应急手册时出错: {str(e)}"


# ============================================================
# 请求/响应模型
# ============================================================

class AlertRequest(BaseModel):
    """报警信息请求"""
    alert_message: str = Field(..., description="报警文本信息，如：仓库着火了")

    class Config:
        json_schema_extra = {
            "example": {
                "alert_message": "仓库着火了"
            }
        }


class ToolCallResult(BaseModel):
    """工具调用结果"""
    tool_name: str = Field(..., description="调用的工具名称")
    tool_input: dict[str, Any] = Field(..., description="工具输入参数")
    tool_output: str = Field(..., description="工具返回结果")


class AlertResponse(BaseModel):
    """报警处理响应"""
    original_alert: str = Field(..., description="原始报警信息")
    tool_calls: list[ToolCallResult] = Field(default_factory=list, description="工具调用记录")
    maintenance_suggestion: str = Field(..., description="检修建议")
    contact_info: str = Field(default="", description="负责人联系信息")
    emergency_manuals: str = Field(default="", description="应急手册查询结果")


# ============================================================
# Agent 实现（观察-思考-行动循环）
# ============================================================

async def process_alert_with_agent(alert_message: str) -> AlertResponse:
    """
    使用 Agent 处理报警信息

    流程：
    1. 观察(Observation): 接收报警文本
    2. 思考(Thought): LLM 判断是否需要调用工具
    3. 行动(Action): 执行工具调用获取负责人信息和应急手册
    4. 综合: 结合原始报警和工具结果生成检修建议
    """
    llm = get_llm(streaming=False)

    # 定义工具列表
    tools = [get_contact_phone, search_emergency_manuals]

    # 定义系统提示
    system_prompt = """你是一个智能报警处理助手，负责处理系统报警并生成检修建议。

当收到报警信息时：
1. 分析报警中涉及的地点（如仓库、办公室、换衣间等）
2. 如果识别出具体地点，调用 get_contact_phone 工具获取负责人电话
3. 分析报警类型（如火灾、漏水等），调用 search_emergency_manuals 工具查询相关的应急处理手册
4. 综合所有信息，生成详细的检修建议

检修建议应包括：
- 问题的紧急程度评估
- 可能的原因分析
- 具体的检修步骤（参考应急手册内容）
- 安全注意事项
- 需要联系的人员（如果已获取）

请用专业但易懂的语言回复。"""

    # 使用 langchain 的 create_agent API (通常返回 CompiledGraph)
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        debug=False
    )

    tool_results = []
    contact_info = ""
    emergency_manuals_result = ""
    final_suggestion = ""

    try:
        # 调用 agent (自动执行工具)
        inputs = {"messages": [HumanMessage(content=alert_message)]}
        result = await agent.ainvoke(inputs)

        # 解析消息历史，提取工具调用和最终回复
        messages = result.get("messages", [])
        
        # 临时映射：tool_call_id -> {name, args}
        tool_calls_map = {}

        for msg in messages:
            # 1. 记录 AI 发出的工具调用请求 (AIMessage)
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    call_id = tool_call.get("id")
                    if call_id:
                        tool_calls_map[call_id] = {
                            "name": tool_call.get("name"),
                            "args": tool_call.get("args")
                        }

            # 2. 记录工具执行结果 (ToolMessage)
            if isinstance(msg, ToolMessage):
                call_id = msg.tool_call_id
                content = msg.content
                
                if call_id and call_id in tool_calls_map:
                    call_info = tool_calls_map[call_id]
                    tool_name = call_info["name"]
                    tool_args = call_info["args"]
                    
                    tool_results.append(ToolCallResult(
                        tool_name=tool_name,
                        tool_input=tool_args,
                        tool_output=str(content)
                    ))

                    # 提取联系信息
                    if tool_name == "get_contact_phone":
                        location = tool_args.get("location", "未知地点")
                        contact_info = f"{location}负责人: {content}"
                    
                    # 提取应急手册结果
                    elif tool_name == "search_emergency_manuals":
                        emergency_manuals_result = str(content)
                        # 如果内容太长，工具输出只展示一部分
                        short_output = emergency_manuals_result[:200] + "..." if len(emergency_manuals_result) > 200 else emergency_manuals_result
                        tool_results[-1].tool_output = short_output

            # 3. 获取最终回复 (AIMessage)
            if isinstance(msg, AIMessage) and not msg.tool_calls:
                if msg.content and isinstance(msg.content, str):
                    final_suggestion = msg.content

    except Exception as e:
        logger.error(f"Agent 执行异常: {e}", exc_info=True)

    # 如果 Agent 没有生成完整结果，补充生成检修建议
    if not final_suggestion:
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个专业的运维检修顾问。请根据报警信息提供详细的检修建议。

你的响应应该包括：
1. 问题的紧急程度评估
2. 可能的原因分析
3. 具体的检修步骤和建议
4. 安全注意事项

请用专业但易懂的语言回复。"""),
            ("user", """报警信息：{alert_message}
{contact_section}
{manuals_section}

请根据以上信息提供检修建议。""")
        ])

        contact_section = f"\n负责人信息：{contact_info}" if contact_info else ""
        manuals_section = f"\n应急手册参考：{emergency_manuals_result}" if emergency_manuals_result else ""
        
        analysis_chain = analysis_prompt | llm | StrOutputParser()

        final_suggestion = await analysis_chain.ainvoke({
            "alert_message": alert_message,
            "contact_section": contact_section,
            "manuals_section": manuals_section
        })

    return AlertResponse(
        original_alert=alert_message,
        tool_calls=tool_results,
        maintenance_suggestion=final_suggestion,
        contact_info=contact_info,
        emergency_manuals=emergency_manuals_result
    )


# ============================================================
# API 路由
# ============================================================

@router.post("/alert", response_model=AlertResponse)
async def handle_alert(request: AlertRequest) -> Any:
    """
    处理系统报警信息，自动检索手册并生成检修建议

    工作流程：
    1. 接收报警文本（如"仓库着火了"）
    2. Agent 分析报警内容，识别涉及的地点
    3. 如有具体地点，自动调用工具查询负责人手机号
    4. 综合报警信息和负责人信息，生成详细的检修建议

    Args:
        request: 包含报警信息的请求体

    Returns:
        AlertResponse: 包含工具调用记录和检修建议的响应
    """
    try:
        logger.info(f"收到报警信息: {request.alert_message}")

        # 处理报警
        response = await process_alert_with_agent(request.alert_message)

        logger.info(f"报警处理完成，调用了 {len(response.tool_calls)} 个工具")
        return response

    except Exception as e:
        logger.error(f"报警处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"报警处理失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "alert-agent"}
