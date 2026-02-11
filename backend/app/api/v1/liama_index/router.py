
import logging
from typing import Any, List, Dict

from llama_index.core import (
    VectorStoreIndex, 
    Document, 
    StorageContext,
    Settings as LlamaSettings,
    SimpleDirectoryReader
)
import os
import tempfile
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks, File, UploadFile, Form
from pydantic import BaseModel, Field

# Pymilvus 2.x attempts to parse MILVUS_URI from environment on import.
# If it's set to an invalid format (e.g. missing http scheme), it crashes.
# We clear it here to ensure safe import; actual connection uses settings.MILVUS_URI.
if "MILVUS_URI" in os.environ:
    del os.environ["MILVUS_URI"]

from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai import OpenAIEmbedding

from app.core.config import settings

# 设置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# 初始化 LlamaIndex 设置 (Lazy Loading 推荐，但在 Demo 中直接初始化)
# ============================================================

def get_milvus_vector_store() -> MilvusVectorStore:
    """获取 Milvus 向量存储实例"""
    # 优先使用 URI (Zilliz Cloud)，其次使用 Host/Port (自建 Milvus)
    if settings.MILVUS_URI:
        return MilvusVectorStore(
            uri=settings.MILVUS_URI,
            token=settings.MILVUS_TOKEN,
            collection_name=settings.MILVUS_COLLECTION,
            dim=settings.LLAMAINDEX_EMBEDDING_DIM
        )
    elif settings.MILVUS_HOST:
        # 自建 Milvus 连接
        return MilvusVectorStore(
            uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}",
            user=settings.MILVUS_USER,
            password=settings.MILVUS_PASSWORD,
            collection_name=settings.MILVUS_COLLECTION,
            dim=settings.LLAMAINDEX_EMBEDDING_DIM,
            overwrite=False # 默认不覆盖，避免误删数据
        )
    else:
        raise HTTPException(status_code=500, detail="未配置 Milvus 连接信息 (URI 或 HOST/PORT)，请检查 .env 文件")

def init_global_settings():
    """初始化 LlamaIndex 全局设置"""
    # 配置 LLM (使用智谱 GLM)
    LlamaSettings.llm = OpenAILike(
        model=settings.LLM_MODEL_ID or "glm-4-flash",
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_BASE_URL,
        is_chat_model=True,
        context_window=32000 # 根据模型调整
    )
    
    # 配置 Embedding (使用智谱 embedding-3)
    # 注意: Zhipu 的 embedding-3 需要兼容 OpenAI 接口
    # 使用 model_name 而不是 model 来绕过 OpenAIEmbeddingModelType 枚举检查
    LlamaSettings.embed_model = OpenAIEmbedding(
        model_name="embedding-3",
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_BASE_URL,
        dimensions=settings.LLAMAINDEX_EMBEDDING_DIM
    )

# 初始化全局配置
try:
    init_global_settings()
except Exception as e:
    logger.error(f"LlamaIndex 全局配置初始化失败: {e}")

# ============================================================
# 请求/响应模型
# ============================================================

class IndexRequest(BaseModel):
    text: str = Field(..., description="要索引的文本内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="可选的元数据")

class QueryRequest(BaseModel):
    query: str = Field(..., description="查询问题")
    top_k: int = Field(default=3, description="返回的最相关结果数量")

class SearchRequest(BaseModel):
    query: str = Field(..., description="搜索关键词")
    top_k: int = Field(default=3, description="返回的最相似文档数量")

class BaseResponse(BaseModel):
    success: bool
    message: str
    data: Any = None

# ============================================================
# API 路由
# ============================================================

@router.get("/health", response_model=BaseResponse)
async def health_check():
    """LlamaIndex 与 Milvus 连接状态检查"""
    status_data = {
        "llm": "unknown",
        "milvus": "unknown"
    }
    
    # 检查 LLM
    try:
        resp = LlamaSettings.llm.complete("Hello")
        status_data["llm"] = "connected"
    except Exception as e:
        status_data["llm"] = f"error: {str(e)}"
        
    # 检查 Milvus (通过尝试连接)
    try:
        store = get_milvus_vector_store()
        # 简单检查 collection 是否存在并不是直接 API，但初始化 store 通常会尝试连接
        # 我们这里假设能初始化成功即代表基本参数正确，真正的连接在操作时触发
        # 为了更严谨，可以尝试 client.has_collection (在 store.client 中)
        # 但 MilvusVectorStore 封装了 client，这里简单返回配置检查
        if settings.MILVUS_URI:
            status_data["milvus"] = "configured"
        else:
            status_data["milvus"] = "not_configured"
    except Exception as e:
        status_data["milvus"] = f"error: {str(e)}"

    return BaseResponse(
        success=True,
        message="Health check completed",
        data=status_data
    )

def _index_documents(documents: List[Document]):
    """将文档列表索引到 Milvus 的通用逻辑"""
    try:
        # 1. 获取向量存储
        vector_store = get_milvus_vector_store()
        
        # 2. 创建存储上下文
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # 3. 构建索引 (会自动计算 embedding 并存入 Milvus)
        VectorStoreIndex.from_documents(
            documents, 
            storage_context=storage_context
        )
    except Exception as e:
        error_msg = f"索引失败 (类型: {type(e).__name__}): {str(e)}"
        logger.error(error_msg)
        # 确保 detail 是纯字符串，避免编码问题
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/index", response_model=BaseResponse)
async def index_document(request: IndexRequest):
    """索引文本到 Milvus"""
    # 1. 创建文档对象
    doc = Document(text=request.text, extra_info=request.metadata)
    
    # 2. 执行索引
    _index_documents([doc])
    
    return BaseResponse(
        success=True,
        message="文本内容已成功索引并存入 Milvus"
    )

@router.post("/index/file", response_model=BaseResponse)
async def index_file(
    file: UploadFile = File(...),
    metadata: str = Form(None, description="可选的元数据，JSON 字符串格式")
):
    """上传 PDF 或 Word 文档并进行索引"""
    filename = file.filename
    ext = Path(filename).suffix.lower()
    
    if ext not in [".pdf", ".docx"]:
        raise HTTPException(status_code=400, detail="目前仅支持 .pdf 和 .docx 格式的文件")
    
    # 解析元数据
    extra_info = {}
    if metadata:
        try:
            extra_info = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="metadata 必须是有效的 JSON 字符串")
    
    # 确保元数据中有文件名
    extra_info.setdefault("file_name", filename)
    
    # 使用临时文件保存上传内容
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file_path = Path(temp_dir) / filename
        try:
            with open(temp_file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # 使用 SimpleDirectoryReader 加载文档
            loader = SimpleDirectoryReader(input_files=[str(temp_file_path)])
            documents = loader.load_data()
            
            # 为加载的文档添加元数据，并确保所有字段都是 JSON 序列化的 (防止出现 bytes)
            for doc in documents:
                # 清理 llama-index 自动提取的元数据中可能存在的 bytes
                clean_doc_metadata = {}
                for k, v in doc.metadata.items():
                    if isinstance(v, bytes):
                        clean_doc_metadata[k] = v.decode("utf-8", errors="replace")
                    else:
                        clean_doc_metadata[k] = v
                doc.metadata = clean_doc_metadata
                # 合并用户提供的元数据
                doc.metadata.update(extra_info)
            
            logger.info(f"正在索引文件: {filename}, 解析出 {len(documents)} 个片段")
            
            # 执行索引
            _index_documents(documents)
            
            return BaseResponse(
                success=True,
                message=f"文件 '{filename}' 已成功解析并索引到 Milvus (共 {len(documents)} 个片段)"
            )
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"文件处理失败 ({filename}): {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

@router.post("/query", response_model=BaseResponse)
async def query_index(request: QueryRequest):
    """语义查询 (RAG)"""
    try:
        # 1. 连接现有索引
        vector_store = get_milvus_vector_store()
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        
        # 2. 创建查询引擎
        query_engine = index.as_query_engine(similarity_top_k=request.top_k)
        
        # 3. 执行查询
        response = query_engine.query(request.query)
        
        return BaseResponse(
            success=True,
            message="查询成功",
            data={
                "response": str(response),
                "source_nodes": [
                    {
                        "score": node.score,
                        "text": node.node.get_content()[:200] + "..." # 截断展示
                    }
                    for node in response.source_nodes
                ]
            }
        )
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@router.post("/search", response_model=BaseResponse)
async def search_vector(request: SearchRequest):
    """纯向量搜索 (Retriever 模式)"""
    try:
        vector_store = get_milvus_vector_store()
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        
        # 使用 retriever 只做检索，不生成回答
        retriever = index.as_retriever(similarity_top_k=request.top_k)
        nodes = retriever.retrieve(request.query)
        
        results = [
            {
                "score": node.score,
                "text": node.node.get_content(),
                "metadata": node.node.metadata
            }
            for node in nodes
        ]
        
        return BaseResponse(
            success=True,
            message=f"找到 {len(results)} 个相关文档",
            data=results
        )
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.delete("/delete", response_model=BaseResponse)
async def delete_collection():
    """删除索引数据 (Drop Collection)"""
    try:
        # 注意: MilvusVectorStore 目前没有直接的 drop 方法暴露在顶层接口
        # 但可以通过 client 属性访问
        vector_store = get_milvus_vector_store()
        
        # 尝试清理数据
        # 警告: 这会删除整个 collection
        if hasattr(vector_store, "client"):
            # pymilvus client
            if vector_store.client.has_collection(settings.MILVUS_COLLECTION):
                vector_store.client.drop_collection(settings.MILVUS_COLLECTION)
                
        return BaseResponse(
            success=True,
            message=f"集合 {settings.MILVUS_COLLECTION} 已删除"
        )
    except Exception as e:
        logger.error(f"删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
