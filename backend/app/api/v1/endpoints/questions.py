"""
题目管理API
"""
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.schemas.schemas import Question, QuestionCreate, ResponseBase
from app.services.question_service import QuestionService
from app.tools.question_uploader import get_question_uploader

router = APIRouter()

# 支持的题目文档格式
ALLOWED_QUESTION_FORMATS = {".pdf", ".docx", ".doc", ".txt", ".md"}
# 题目文档临时上传目录
QUESTION_UPLOAD_DIR = Path("data/uploads/questions")
QUESTION_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/", response_model=ResponseBase)
async def list_questions(
    grade: Optional[str] = Query(None, description="年级"),
    subject: Optional[str] = Query(None, description="科目"),
    difficulty: Optional[str] = Query(None, description="难度"),
    question_type: Optional[str] = Query(None, description="题型"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    查询题目列表
    """
    try:
        service = QuestionService(db)
        questions, total = await service.list_questions(
            grade=grade,
            subject=subject,
            difficulty=difficulty,
            question_type=question_type,
            skip=skip,
            limit=limit,
        )

        return ResponseBase(
            success=True,
            message="查询成功",
            data={
                "questions": questions,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        )

    except Exception as e:
        logger.exception(f"查询题目列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag-preview", response_model=ResponseBase)
async def preview_rag_questions(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    grade: Optional[str] = Query(None, description="筛选年级"),
    subject: Optional[str] = Query(None, description="筛选科目"),
):
    """
    预览历史题库（Qdrant RAG存储）

    返回存储在向量数据库中的题目，用于查看RAG数据
    """
    try:
        uploader = get_question_uploader()
        result = await uploader.kb.list_questions(
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
        logger.error(f"[QuestionAPI] RAG预览失败: {e}")
        raise HTTPException(status_code=500, detail=f"RAG预览失败: {str(e)}")


@router.get("/{question_id}", response_model=ResponseBase)
async def get_question(
    question_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取单个题目详情
    """
    try:
        service = QuestionService(db)
        question = await service.get_question(question_id)

        if not question:
            raise HTTPException(status_code=404, detail="题目不存在")

        return ResponseBase(
            success=True,
            message="查询成功",
            data=question
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取题目详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=ResponseBase)
async def create_question(
    question: QuestionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    创建题目（手动添加）
    """
    try:
        service = QuestionService(db)
        created = await service.create_question(question)

        return ResponseBase(
            success=True,
            message="题目创建成功",
            data=created
        )

    except Exception as e:
        logger.exception(f"创建题目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{question_id}", response_model=ResponseBase)
async def delete_question(
    question_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    删除题目
    """
    try:
        service = QuestionService(db)
        success = await service.delete_question(question_id)

        if not success:
            raise HTTPException(status_code=404, detail="题目不存在")

        return ResponseBase(
            success=True,
            message="题目已删除"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"删除题目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_questions(
    file: UploadFile = File(..., description="题目文档文件"),
    grade: str = Form(..., description="年级，如'小学五年级'"),
    subject: str = Form(..., description="科目，如'数学'"),
):
    """
    上传题目文档到历史题库

    支持格式: PDF, Word(docx/doc), TXT, Markdown
    文档内容会用LLM提取结构化题目，然后存入历史题库供生成时参考
    """
    # 1. 校验文件格式
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_QUESTION_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {suffix}。支持的格式: {', '.join(ALLOWED_QUESTION_FORMATS)}"
        )

    # 2. 保存上传文件到临时目录
    file_path = QUESTION_UPLOAD_DIR / file.filename
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"[QuestionAPI] 上传文件: {file.filename} ({len(content)} bytes)")
    except Exception as e:
        logger.error(f"[QuestionAPI] 保存文件失败: {e}")
        raise HTTPException(status_code=500, detail="文件保存失败")

    # 3. 解析并上传到历史题库
    try:
        uploader = get_question_uploader()
        result = await uploader.parse_and_upload(
            file_path=str(file_path),
            grade=grade,
            subject=subject,
        )

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"题目提取失败: {'; '.join(result['errors'])}"
            )

        return ResponseBase(
            success=True,
            message=f"上传成功！已添加 {result['uploaded']} 道题目到历史题库",
            data={
                "file_name": file.filename,
                "grade": grade,
                "subject": subject,
                "uploaded": result["uploaded"],
                "failed": result["failed"],
                "errors": result["errors"],
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QuestionAPI] 解析上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"解析上传失败: {str(e)}")


@router.post("/upload-text")
async def upload_questions_text(
    text: str = Form(..., description="题目文本内容"),
    grade: str = Form(..., description="年级，如'小学五年级'"),
    subject: str = Form(..., description="科目，如'数学'"),
):
    """
    上传题目文本到历史题库（无需文件，直接粘贴文本）

    支持直接粘贴题目文本，LLM会提取结构化题目并存入历史题库
    """
    # 校验文本长度
    if not text or len(text.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="文本内容过短，至少需要50个字符"
        )

    if len(text) > 50000:
        raise HTTPException(
            status_code=400,
            detail="文本内容过长（最大50000字符），请分段上传"
        )

    try:
        uploader = get_question_uploader()
        # 直接调用LLM提取题目（跳过文件解析步骤）
        questions = await uploader._extract_questions(text, grade, subject)

        if not questions:
            raise HTTPException(
                status_code=400,
                detail="未能从文本中提取到有效题目"
            )

        # 上传到历史题库(Qdrant)
        uploaded = 0
        failed = 0
        errors = []

        for q in questions:
            # 补全必需字段
            q["grade"] = grade
            q["subject"] = subject

            point_id = await uploader.kb.add_question(q)
            if point_id:
                uploaded += 1
            else:
                failed += 1
                errors.append(f"入库失败: {q.get('content', '')[:40]}")

        logger.info(
            f"[QuestionAPI] 文本上传完成 | 成功: {uploaded} | 失败: {failed}"
        )

        return ResponseBase(
            success=True,
            message=f"上传成功！已添加 {uploaded} 道题目到历史题库",
            data={
                "text_length": len(text),
                "grade": grade,
                "subject": subject,
                "uploaded": uploaded,
                "failed": failed,
                "errors": errors,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QuestionAPI] 文本上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文本上传失败: {str(e)}")
