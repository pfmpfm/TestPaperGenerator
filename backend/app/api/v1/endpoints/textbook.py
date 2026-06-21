"""
教材知识库管理API
"""
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.core.logging import logger
from app.schemas.schemas import ResponseBase
from app.tools.textbook_kb import get_textbook_kb

router = APIRouter()

# 支持的文档格式
ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt",
    ".xlsx", ".xls", ".html", ".htm", ".txt", ".md"
}
# 文档临时上传目录
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_textbook(
    file: UploadFile = File(..., description="文档文件"),
    grade: str = Form(..., description="年级，如'小学五年级'"),
    subject: str = Form(..., description="科目，如'数学'"),
    chapter: Optional[str] = Form(None, description="章节，可选"),
):
    """
    上传教材文档到知识库

    支持格式: PDF, Word(docx/doc), PowerPoint(pptx/ppt), Excel(xlsx/xls), HTML, TXT, Markdown
    """
    # 1. 校验文件格式
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {suffix}。支持的格式: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 2. 保存上传文件到临时目录
    file_path = UPLOAD_DIR / file.filename
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"[TextbookAPI] 上传文件: {file.filename} ({len(content)} bytes)")
    except Exception as e:
        logger.error(f"[TextbookAPI] 保存文件失败: {e}")
        raise HTTPException(status_code=500, detail="文件保存失败")

    # 3. 索引到教材知识库
    try:
        kb = get_textbook_kb()
        chunk_count = await kb.index_document(
            file_path=str(file_path),
            grade=grade,
            subject=subject,
            chapter=chapter,
        )

        if chunk_count == 0:
            raise HTTPException(status_code=400, detail="文档解析失败或内容为空")

        return ResponseBase(
            success=True,
            message="文档索引成功",
            data={
                "file_name": file.filename,
                "grade": grade,
                "subject": subject,
                "chapter": chapter,
                "chunk_count": chunk_count,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TextbookAPI] 索引文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"文档索引失败: {str(e)}")


@router.post("/search")
async def search_textbook(
    query: str = Form(..., description="查询文本，如'平行四边形的定义'"),
    grade: Optional[str] = Form(None, description="年级过滤"),
    subject: Optional[str] = Form(None, description="科目过滤"),
    chapter: Optional[str] = Form(None, description="章节过滤"),
    top_k: int = Form(5, description="返回结果数", ge=1, le=20),
):
    """
    检索教材知识库

    返回最相关的文档片段
    """
    try:
        kb = get_textbook_kb()
        results = await kb.search_knowledge(
            query=query,
            grade=grade,
            subject=subject,
            chapter=chapter,
            top_k=top_k,
        )

        return ResponseBase(
            success=True,
            message=f"检索到 {len(results)} 条结果",
            data=results,
        )
    except Exception as e:
        logger.error(f"[TextbookAPI] 检索失败: {e}")
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.delete("/document/{file_name}")
async def delete_textbook_document(file_name: str):
    """
    删除教材知识库中指定文件的所有索引
    """
    try:
        kb = get_textbook_kb()
        count = await kb.delete_by_file(file_name)

        # 同时删除本地上传的文件
        file_path = UPLOAD_DIR / file_name
        if file_path.exists():
            file_path.unlink()

        return ResponseBase(
            success=True,
            message="文档已删除",
            data={"file_name": file_name, "deleted": count > 0}
        )
    except Exception as e:
        logger.error(f"[TextbookAPI] 删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/list")
async def list_uploaded_files():
    """
    列出所有已上传的文档文件
    """
    try:
        files = [
            {
                "name": f.name,
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
            }
            for f in UPLOAD_DIR.iterdir()
            if f.is_file()
        ]
        return ResponseBase(
            success=True,
            message=f"共 {len(files)} 个文件",
            data=files,
        )
    except Exception as e:
        logger.error(f"[TextbookAPI] 列出文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出文件失败: {str(e)}")

@router.get("/rag-preview")
async def preview_rag_chunks(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    grade: Optional[str] = Query(None, description="筛选年级"),
    subject: Optional[str] = Query(None, description="筛选科目"),
):
    """
    预览教材知识库（Qdrant RAG存储）

    返回存储在向量数据库中的知识块，用于查看RAG数据
    """
    try:
        kb = get_textbook_kb()
        result = await kb.list_chunks(
            limit=limit,
            offset=offset,
            grade=grade,
            subject=subject,
        )

        return ResponseBase(
            success=True,
            message="查询成功",
            data=result
        )

    except Exception as e:
        logger.error(f"[TextbookAPI] RAG预览失败: {e}")
        raise HTTPException(status_code=500, detail=f"RAG预览失败: {str(e)}")
