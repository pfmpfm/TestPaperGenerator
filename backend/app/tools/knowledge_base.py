"""
历史题库RAG工具 - 基于Qdrant的题目向量检索/入库

实现PRD 5.2.2:
- 向量检索(语义相似)
- 元数据过滤(年级/科目/题型/难度)
- 检索相似题作为生成参考
- 题目入库供后续检索
"""
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import models

from app.core.database import get_qdrant_async_client
from app.core.llm_client import get_embedding_client
from app.core.logging import logger

# 历史题库collection名称
COLLECTION_QUESTIONS = "history_questions"


class KnowledgeBase:
    """历史题库RAG"""

    def __init__(self):
        self.embedding = get_embedding_client()
        self.client = get_qdrant_async_client()
        self._dimension: Optional[int] = None
        self._initialized = False

    async def _ensure_collection(self):
        """确保collection存在，维度按实际embedding探测(规避配置维度不匹配)"""
        if self._initialized:
            return

        # 探测真实维度(配置维度可能与实际provider返回不符)
        if self._dimension is None:
            probe = await self.embedding.async_create_embedding("维度探测")
            self._dimension = len(probe)
            logger.info(f"[RAG] embedding实际维度: {self._dimension}")

        collections = await self.client.get_collections()
        names = {c.name for c in collections.collections}
        if COLLECTION_QUESTIONS not in names:
            await self.client.create_collection(
                collection_name=COLLECTION_QUESTIONS,
                vectors_config=models.VectorParams(
                    size=self._dimension,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(f"[RAG] 创建collection: {COLLECTION_QUESTIONS} (dim={self._dimension})")
        self._initialized = True

    @staticmethod
    def _embed_text(question: Dict[str, Any]) -> str:
        """用于embedding的文本：知识点+题型+题干"""
        kps = " ".join(question.get("knowledge_points", []) or [])
        return f"{question.get('subject','')} {kps} {question.get('content','')}"

    def _build_filter(
        self,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        question_type: Optional[str] = None,
    ) -> Optional[models.Filter]:
        """构建元数据过滤条件"""
        conditions = []
        for field, value in (
            ("grade", grade),
            ("subject", subject),
            ("question_type", question_type),
        ):
            if value:
                conditions.append(
                    models.FieldCondition(
                        key=field, match=models.MatchValue(value=value)
                    )
                )
        return models.Filter(must=conditions) if conditions else None

    async def search_similar(
        self,
        question: Dict[str, Any],
        top_k: int = 3,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        question_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        检索语义相似的历史题目

        Returns:
            [{"score": float, "content": str, "answer": str, ...}, ...]
        """
        try:
            await self._ensure_collection()
            vector = await self.embedding.async_create_embedding(
                self._embed_text(question)
            )
            results = await self.client.search(
                collection_name=COLLECTION_QUESTIONS,
                query_vector=vector,
                query_filter=self._build_filter(grade, subject, question_type),
                limit=top_k,
                with_payload=True,
            )
            return [
                {"score": r.score, **(r.payload or {})} for r in results
            ]
        except Exception as e:  # noqa: BLE001 - RAG失败不应阻断生成
            logger.warning(f"[RAG] 相似检索失败(降级为无参考): {e}")
            return []

    async def add_question(self, question: Dict[str, Any]) -> Optional[str]:
        """
        将题目存入历史题库(计算向量+payload)

        Returns:
            Qdrant point id，失败返回None
        """
        try:
            await self._ensure_collection()
            vector = await self.embedding.async_create_embedding(
                self._embed_text(question)
            )
            point_id = str(uuid.uuid4())
            payload = {
                "content": question.get("content", ""),
                "answer": question.get("answer", ""),
                "question_type": question.get("question_type", ""),
                "difficulty": question.get("difficulty", ""),
                "grade": question.get("grade", ""),
                "subject": question.get("subject", ""),
                "knowledge_points": question.get("knowledge_points", []),
            }
            await self.client.upsert(
                collection_name=COLLECTION_QUESTIONS,
                points=[
                    models.PointStruct(
                        id=point_id, vector=vector, payload=payload
                    )
                ],
            )
            return point_id
        except Exception as e:  # noqa: BLE001 - 入库失败不应阻断主流程
            logger.warning(f"[RAG] 题目入库失败: {e}")
            return None

    async def add_questions_batch(self, questions: List[Dict[str, Any]]) -> List[Optional[str]]:
        """
        批量将题目存入历史题库（并发embedding加速）

        Args:
            questions: 题目列表

        Returns:
            point_id列表，失败的为None
        """
        if not questions:
            return []

        try:
            await self._ensure_collection()

            # 并发embedding
            import asyncio
            embedding_tasks = [
                self.embedding.async_create_embedding(self._embed_text(q))
                for q in questions
            ]
            vectors = await asyncio.gather(*embedding_tasks, return_exceptions=True)

            # 构建points（跳过embedding失败的）
            points = []
            point_ids = []
            for q, vector in zip(questions, vectors):
                if isinstance(vector, Exception):
                    logger.warning(f"[RAG] embedding失败: {vector}")
                    point_ids.append(None)
                    continue

                point_id = str(uuid.uuid4())
                payload = {
                    "content": q.get("content", ""),
                    "answer": q.get("answer", ""),
                    "question_type": q.get("question_type", ""),
                    "difficulty": q.get("difficulty", ""),
                    "grade": q.get("grade", ""),
                    "subject": q.get("subject", ""),
                    "knowledge_points": q.get("knowledge_points", []),
                }
                points.append(
                    models.PointStruct(
                        id=point_id, vector=vector, payload=payload
                    )
                )
                point_ids.append(point_id)

            # 批量upsert
            if points:
                await self.client.upsert(
                    collection_name=COLLECTION_QUESTIONS,
                    points=points,
                )

            return point_ids

        except Exception as e:
            logger.warning(f"[RAG] 批量题目入库失败: {e}")
            return [None] * len(questions)

    async def list_questions(
        self,
        limit: int = 20,
        offset: int = 0,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        列出历史题库中的题目（用于预览）

        Args:
            limit: 返回数量
            offset: 偏移量
            grade: 筛选年级（可选）
            subject: 筛选科目（可选）

        Returns:
            {"questions": [...], "total": int}
        """
        try:
            await self._ensure_collection()

            # 构建filter
            must_conditions = []
            if grade:
                must_conditions.append(
                    models.FieldCondition(
                        key="grade",
                        match=models.MatchValue(value=grade)
                    )
                )
            if subject:
                must_conditions.append(
                    models.FieldCondition(
                        key="subject",
                        match=models.MatchValue(value=subject)
                    )
                )

            filter_condition = (
                models.Filter(must=must_conditions) if must_conditions else None
            )

            # 方案：用scroll多次获取实现offset
            # Qdrant的scroll offset是point_id而非数字，需手动跳过前面的数据
            current_offset = 0
            collected = []
            next_page_offset = None

            while current_offset < offset + limit:
                points, next_page_offset = await self.client.scroll(
                    collection_name=COLLECTION_QUESTIONS,
                    scroll_filter=filter_condition,
                    limit=min(100, offset + limit - current_offset),  # 每批最多100
                    offset=next_page_offset,
                    with_payload=True,
                    with_vectors=False,
                )

                if not points:
                    break

                collected.extend(points)
                current_offset += len(points)

                # 已收集足够数据
                if current_offset >= offset + limit:
                    break

                # 没有更多数据
                if next_page_offset is None:
                    break

            # 截取所需范围
            start_idx = min(offset, len(collected))
            end_idx = min(offset + limit, len(collected))
            result_points = collected[start_idx:end_idx]

            # 提取payload
            questions = []
            for point in result_points:
                if point.payload:
                    questions.append(point.payload)

            # 获取总数
            count_result = await self.client.count(
                collection_name=COLLECTION_QUESTIONS,
                count_filter=filter_condition,
                exact=False,
            )
            total = count_result.count

            return {
                "questions": questions,
                "total": total,
            }

        except Exception as e:
            logger.warning(f"[RAG] 列出题目失败: {e}")
            return {"questions": [], "total": 0}


# 全局单例
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """获取历史题库实例(单例)"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
