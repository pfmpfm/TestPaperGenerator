"""
教材知识库RAG - 基于Qdrant + MarkItDown

实现PRD 5.2.1:
- 多格式文档上传(PDF/Word/PPT/Excel/HTML/TXT)
- MarkItDown统一转Markdown
- 语义切分+Embedding
- 存入Qdrant textbook_knowledge collection
- 按年级/科目/章节查询
"""
import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from markitdown import MarkItDown
from qdrant_client import models

from app.core.database import get_qdrant_async_client
from app.core.llm_client import get_embedding_client
from app.core.logging import logger

# 教材知识库collection名称
COLLECTION_TEXTBOOK = "textbook_knowledge"
# 每个文档块的目标长度(字符)
CHUNK_SIZE = 500
# 块之间的重叠(字符)
CHUNK_OVERLAP = 100


class TextbookKnowledgeBase:
    """教材知识库"""

    def __init__(self):
        self.embedding = get_embedding_client()
        self.client = get_qdrant_async_client()
        self.markitdown = MarkItDown()
        self._dimension: Optional[int] = None
        self._initialized = False

    async def _ensure_collection(self):
        """确保教材知识库collection存在"""
        if self._initialized:
            return

        # 探测真实embedding维度
        if self._dimension is None:
            probe = await self.embedding.async_create_embedding("维度探测")
            self._dimension = len(probe)
            logger.info(f"[TextbookKB] embedding实际维度: {self._dimension}")

        collections = await self.client.get_collections()
        names = {c.name for c in collections.collections}
        if COLLECTION_TEXTBOOK not in names:
            await self.client.create_collection(
                collection_name=COLLECTION_TEXTBOOK,
                vectors_config=models.VectorParams(
                    size=self._dimension,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(f"[TextbookKB] 创建collection: {COLLECTION_TEXTBOOK}")
        self._initialized = True

    def _semantic_chunking(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
        """
        简单的语义切分：按段落+句子边界切分，保留重叠。

        真实场景可用 llama-index 的 SemanticSplitterNodeParser，
        但需要额外依赖和调优，这里用轻量方案。
        """
        # 按段落分割
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 2 <= chunk_size:
                current += para + "\n\n"
            else:
                if current:
                    chunks.append(current.strip())
                current = para + "\n\n"

        if current:
            chunks.append(current.strip())

        # 处理重叠：如果块之间间隔太大，添加overlap
        if overlap > 0 and len(chunks) > 1:
            overlapped = [chunks[0]]
            for i in range(1, len(chunks)):
                prev_tail = chunks[i - 1][-overlap:]
                overlapped.append(prev_tail + "\n" + chunks[i])
            chunks = overlapped

        return chunks

    async def index_document(
        self,
        file_path: str,
        grade: str,
        subject: str,
        chapter: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        索引一个文档到教材知识库

        Args:
            file_path: 文档路径
            grade: 年级
            subject: 科目
            chapter: 章节(可选)
            metadata: 额外元数据(可选)

        Returns:
            索引的块数量
        """
        try:
            await self._ensure_collection()

            # 1. MarkItDown转换为Markdown
            logger.info(f"[TextbookKB] 解析文档: {file_path}")
            result = self.markitdown.convert(file_path)
            markdown_text = result.text_content

            if not markdown_text or len(markdown_text) < 50:
                logger.warning(f"[TextbookKB] 文档内容过短或解析失败: {file_path}")
                return 0

            # 2. 语义切分
            chunks = self._semantic_chunking(markdown_text)
            logger.info(f"[TextbookKB] 切分为 {len(chunks)} 个块")

            if not chunks:
                return 0

            # 3. 批量embedding（并发加速）
            logger.info(f"[TextbookKB] 开始批量embedding...")
            import asyncio
            embedding_tasks = [
                self.embedding.async_create_embedding(chunk)
                for chunk in chunks
            ]
            vectors = await asyncio.gather(*embedding_tasks)
            logger.info(f"[TextbookKB] embedding完成")

            # 4. 构建points并批量入库
            doc_hash = hashlib.md5(markdown_text.encode()).hexdigest()
            file_name = Path(file_path).name

            points = []
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                point_id = str(uuid.uuid4())

                payload = {
                    "content": chunk,
                    "grade": grade,
                    "subject": subject,
                    "chapter": chapter or "",
                    "file_name": file_name,
                    "doc_hash": doc_hash,
                    "chunk_index": i,
                    **(metadata or {}),
                }

                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                )

            # 批量upsert
            logger.info(f"[TextbookKB] 写入Qdrant {len(points)} 个向量...")
            await self.client.upsert(
                collection_name=COLLECTION_TEXTBOOK,
                points=points,
            )

            logger.info(
                f"[TextbookKB] 索引完成: {file_name} | {len(points)} 块 | "
                f"{grade}/{subject}/{chapter or '无章节'}"
            )
            return len(points)

        except Exception as e:
            logger.error(f"[TextbookKB] 索引文档失败: {file_path} | {e}")
            return 0

    async def search_knowledge(
        self,
        query: str,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        检索教材知识

        Args:
            query: 查询文本(如知识点名称、问题描述)
            grade: 年级过滤(可选)
            subject: 科目过滤(可选)
            chapter: 章节过滤(可选)
            top_k: 返回结果数

        Returns:
            [{"score": float, "content": str, "grade": str, ...}, ...]
        """
        try:
            await self._ensure_collection()

            vector = await self.embedding.async_create_embedding(query)

            # 构建元数据过滤
            conditions = []
            for field, value in (
                ("grade", grade),
                ("subject", subject),
                ("chapter", chapter),
            ):
                if value:
                    conditions.append(
                        models.FieldCondition(
                            key=field, match=models.MatchValue(value=value)
                        )
                    )
            query_filter = models.Filter(must=conditions) if conditions else None

            results = await self.client.search(
                collection_name=COLLECTION_TEXTBOOK,
                query_vector=vector,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )

            return [
                {"score": r.score, **(r.payload or {})} for r in results
            ]

        except Exception as e:
            logger.warning(f"[TextbookKB] 知识检索失败: {e}")
            return []

    async def delete_by_file(self, file_name: str) -> int:
        """
        删除指定文件的所有索引块

        Returns:
            删除的点数量
        """
        try:
            await self._ensure_collection()

            # Qdrant delete by filter
            await self.client.delete(
                collection_name=COLLECTION_TEXTBOOK,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="file_name",
                                match=models.MatchValue(value=file_name),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"[TextbookKB] 已删除文件索引: {file_name}")
            return 1  # Qdrant delete返回操作状态，无法精确计数，返回1表示成功
        except Exception as e:
            logger.error(f"[TextbookKB] 删除文件索引失败: {file_name} | {e}")
            return 0

    async def list_chunks(
        self,
        limit: int = 20,
        offset: int = 0,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        列出教材知识库中的知识块（用于预览）

        Args:
            limit: 返回数量
            offset: 偏移量
            grade: 筛选年级（可选）
            subject: 筛选科目（可选）

        Returns:
            {"chunks": [...], "total": int}
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

            # 用scroll多次获取实现offset
            current_offset = 0
            collected = []
            next_page_offset = None

            while current_offset < offset + limit:
                points, next_page_offset = await self.client.scroll(
                    collection_name=COLLECTION_TEXTBOOK,
                    scroll_filter=filter_condition,
                    limit=min(100, offset + limit - current_offset),
                    offset=next_page_offset,
                    with_payload=True,
                    with_vectors=False,
                )

                if not points:
                    break

                collected.extend(points)
                current_offset += len(points)

                if current_offset >= offset + limit:
                    break

                if next_page_offset is None:
                    break

            # 截取所需范围
            start_idx = min(offset, len(collected))
            end_idx = min(offset + limit, len(collected))
            result_points = collected[start_idx:end_idx]

            # 提取payload
            chunks = []
            for point in result_points:
                if point.payload:
                    chunks.append(point.payload)

            # 获取总数
            count_result = await self.client.count(
                collection_name=COLLECTION_TEXTBOOK,
                count_filter=filter_condition,
                exact=False,
            )
            total = count_result.count

            return {
                "chunks": chunks,
                "total": total,
            }

        except Exception as e:
            logger.warning(f"[TextbookKB] 列出知识块失败: {e}")
            return {"chunks": [], "total": 0}


# 全局单例
_textbook_kb: Optional[TextbookKnowledgeBase] = None


def get_textbook_kb() -> TextbookKnowledgeBase:
    """获取教材知识库实例(单例)"""
    global _textbook_kb
    if _textbook_kb is None:
        _textbook_kb = TextbookKnowledgeBase()
    return _textbook_kb