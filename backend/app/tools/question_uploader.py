"""
历史题库题目上传工具

用户上传优质题目文档(PDF/Word/TXT/Markdown) → MarkItDown解析 → LLM提取结构化题目 → 存入Qdrant
"""
from typing import Any, Dict, List

from markitdown import MarkItDown

from app.core.llm_client import get_llm_client
from app.core.logging import logger
from app.tools.knowledge_base import get_knowledge_base

EXTRACTION_SYSTEM_PROMPT = """你是题目结构化提取专家。
用户会给你一段包含试题的文本，你需要从中提取题目并输出JSON数组。

输出格式：严格JSON数组，每个元素包含：
- content: 题目内容（字符串，对于选择题需包含题干+选项）
- answer: 答案（字符串）
- explanation: 解析（字符串，可选）
- question_type: 题型，必须是 "选择题"、"填空题" 或 "应用题" 之一
- difficulty: 难度，必须是 "简单"、"中等" 或 "困难" 之一
- knowledge_points: 知识点（字符串数组）

注意：
1. 只提取完整的题目（有题干+答案），不完整的跳过
2. 选择题的content必须包含题干和A/B/C/D选项
3. 如果文本中没有明确标注难度，根据题目复杂度推断
4. 如果没有明确标注知识点，根据题目内容推断1-2个相关知识点
5. 输出纯JSON数组，不要任何额外说明文字
"""

EXTRACTION_USER_PROMPT = """请从以下文本中提取题目：

年级: {grade}
科目: {subject}

文本内容：
{text}

请提取所有题目并输出JSON数组。"""


class QuestionUploader:
    """题目上传解析器"""

    def __init__(self):
        self.markitdown = MarkItDown()
        self.llm = get_llm_client()
        self.kb = get_knowledge_base()

    async def parse_and_upload(
        self,
        file_path: str,
        grade: str,
        subject: str,
    ) -> Dict[str, Any]:
        """
        解析文档并上传题目到历史题库

        Args:
            file_path: 文档路径
            grade: 年级
            subject: 科目

        Returns:
            {"success": bool, "uploaded": int, "failed": int, "errors": [str]}
        """
        try:
            # 1. MarkItDown解析文档
            logger.info(f"[QuestionUpload] 解析文档: {file_path}")
            result = self.markitdown.convert(file_path)
            text = result.text_content

            if not text or len(text) < 50:
                return {
                    "success": False,
                    "uploaded": 0,
                    "failed": 0,
                    "errors": ["文档内容为空或过短"]
                }

            # 限制文档长度，避免超大文档导致LLM超时
            MAX_TEXT_LENGTH = 20000  # 约10页PDF的文本量
            if len(text) > MAX_TEXT_LENGTH:
                logger.warning(
                    f"[QuestionUpload] 文档过长({len(text)}字符)，截取前{MAX_TEXT_LENGTH}字符"
                )
                text = text[:MAX_TEXT_LENGTH]

            # 2. LLM提取结构化题目
            logger.info(f"[QuestionUpload] LLM提取题目中(文本长度: {len(text)})...")
            questions = await self._extract_questions(text, grade, subject)

            if not questions:
                return {
                    "success": False,
                    "uploaded": 0,
                    "failed": 0,
                    "errors": ["未能从文档中提取到有效题目"]
                }

            # 3. 上传到历史题库(Qdrant)
            uploaded = 0
            failed = 0
            errors = []

            # 补全必需字段
            for q in questions:
                q["grade"] = grade
                q["subject"] = subject

            # 批量入库（并发embedding加速）
            logger.info(f"[QuestionUpload] 开始批量入库 {len(questions)} 道题目...")
            point_ids = await self.kb.add_questions_batch(questions)

            for q, point_id in zip(questions, point_ids):
                if point_id:
                    uploaded += 1
                else:
                    failed += 1
                    errors.append(f"入库失败: {q.get('content', '')[:40]}")

            logger.info(
                f"[QuestionUpload] 上传完成 | 成功: {uploaded} | 失败: {failed}"
            )
            return {
                "success": True,
                "uploaded": uploaded,
                "failed": failed,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"[QuestionUpload] 解析上传失败: {e}")
            return {
                "success": False,
                "uploaded": 0,
                "failed": 0,
                "errors": [f"解析失败: {str(e)}"]
            }

    async def _extract_questions(
        self, text: str, grade: str, subject: str
    ) -> List[Dict[str, Any]]:
        """用LLM从文本中提取结构化题目"""
        user_prompt = EXTRACTION_USER_PROMPT.format(
            grade=grade, subject=subject, text=text[:8000]  # 限制长度避免超token
        )

        try:
            messages = [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            response = await self.llm.async_chat_completion(
                messages=messages,
                temperature=0.3,  # 低温度保证结构化输出稳定
            )

            content = response.choices[0].message.content.strip()

            # 解析JSON
            import json
            import re

            # 提取JSON数组（去掉markdown代码块）
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if not match:
                logger.warning(f"[QuestionUpload] LLM未返回有效JSON: {content[:200]}")
                return []

            questions = json.loads(match.group(0))

            if not isinstance(questions, list):
                logger.warning(f"[QuestionUpload] LLM返回非数组: {type(questions)}")
                return []

            # 过滤无效题目
            valid = []
            for q in questions:
                if (
                    isinstance(q, dict)
                    and q.get("content")
                    and q.get("answer")
                    and q.get("question_type")
                ):
                    valid.append(q)

            logger.info(f"[QuestionUpload] LLM提取 {len(valid)} 道有效题目")
            return valid

        except Exception as e:
            logger.error(f"[QuestionUpload] LLM提取失败: {e}")
            return []


# 全局单例
_uploader = None


def get_question_uploader() -> QuestionUploader:
    """获取题目上传器实例(单例)"""
    global _uploader
    if _uploader is None:
        _uploader = QuestionUploader()
    return _uploader