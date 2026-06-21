"""
试卷生成Workflow - 使用LangGraph编排生成流程

流程: parse_requirement -> generate_questions -> assemble_paper
"""
import asyncio
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.generator_agent import GeneratorAgent
from app.agents.quality_review_group import QualityReviewGroup
from app.core.config import settings
from app.core.logging import logger
from app.core.llm_client import get_embedding_client
from app.tools.knowledge_base import get_knowledge_base


class GenerationState(TypedDict, total=False):
    """Workflow运行状态"""
    requirement: Dict[str, Any]      # 试卷需求(dict)
    generation_tasks: List[Dict[str, Any]]  # 待生成的题目任务
    questions: List[Dict[str, Any]]  # 已生成的题目
    paper: Dict[str, Any]            # 组装好的试卷
    current_step: str
    errors: List[str]
    enable_review: bool              # 是否启用质量审核
    enable_rag: bool                 # 是否启用RAG(检索参考+去重+入库)


def _build_tasks(requirement: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    根据需求拆解生成任务

    将每个题型的题目数量分配到(知识点, 难度)组合，保证：
    1. 题目总数超额50%（抵消审核和去重损失）
    2. 知识点尽可能全覆盖(知识点数<=题目数时全部覆盖)
    3. 难度按分布比例分配(最大余数法取整)
    """
    knowledge_points: List[str] = requirement.get("knowledge_points", [])
    question_types: Dict[str, int] = requirement.get("question_types", {})
    difficulty_dist: Dict[str, float] = requirement.get(
        "difficulty_distribution", {"简单": 0.4, "中等": 0.4, "困难": 0.2}
    )

    if not knowledge_points:
        knowledge_points = ["综合"]

    tasks: List[Dict[str, Any]] = []
    for q_type, target in question_types.items():
        if target <= 0:
            continue

        # 超额50%生成，抵消审核和去重损失
        total = int(target * 1.5)

        # 1. 为该题型的 total 道题逐题分配知识点(round-robin保证全覆盖)
        kp_slots = [
            knowledge_points[i % len(knowledge_points)] for i in range(total)
        ]
        # 2. 按难度分布分配 total 道题(最大余数法，数量守恒)
        difficulty_slots = _allocate_by_distribution(total, difficulty_dist)

        # 3. 将知识点槽位与难度槽位配对，聚合成任务
        bucket: Dict[tuple, int] = {}
        idx = 0
        for difficulty, d_count in difficulty_slots.items():
            for _ in range(d_count):
                kp = kp_slots[idx]
                bucket[(kp, difficulty)] = bucket.get((kp, difficulty), 0) + 1
                idx += 1

        for (kp, difficulty), count in bucket.items():
            tasks.append({
                "knowledge_point": kp,
                "question_type": q_type,
                "difficulty": difficulty,
                "count": count,
            })
    return tasks


def _allocate_by_distribution(total: int, distribution: Dict[str, float]) -> Dict[str, int]:
    """
    按比例将total分配到各类别，使用最大余数法保证总和严格等于total。
    """
    if not distribution:
        return {"中等": total}

    # 归一化权重
    weight_sum = sum(distribution.values()) or 1.0
    exact = {k: total * v / weight_sum for k, v in distribution.items()}
    floored = {k: int(v) for k, v in exact.items()}
    remainder = total - sum(floored.values())

    # 余数按小数部分从大到小依次+1
    if remainder > 0:
        order = sorted(
            distribution.keys(),
            key=lambda k: exact[k] - floored[k],
            reverse=True,
        )
        for i in range(remainder):
            floored[order[i % len(order)]] += 1
    return floored


def _count_by_type(questions: List[Dict[str, Any]]) -> Dict[str, int]:
    """统计各题型的题目数量"""
    counts: Dict[str, int] = {}
    for q in questions:
        qt = q.get("question_type", "其他")
        counts[qt] = counts.get(qt, 0) + 1
    return counts


def _trim_to_target(
    questions: List[Dict[str, Any]], target: Dict[str, int]
) -> List[Dict[str, Any]]:
    """每个题型最多保留 target 指定的数量，超出部分裁剪"""
    kept: List[Dict[str, Any]] = []
    seen: Dict[str, int] = {}
    for q in questions:
        qt = q.get("question_type", "其他")
        limit = target.get(qt)
        if limit is None:
            kept.append(q)  # 不在目标内的题型不裁剪
            continue
        if seen.get(qt, 0) < limit:
            kept.append(q)
            seen[qt] = seen.get(qt, 0) + 1
    return kept


def _build_compensation_tasks(
    shortfall: Dict[str, int],
    existing: List[Dict[str, Any]],
    knowledge_points: List[str],
    difficulty_dist: Dict[str, float],
) -> List[Dict[str, Any]]:
    """
    为缺口构建补偿生成任务，优先补未覆盖的知识点。
    """
    covered = {kp for q in existing for kp in q.get("knowledge_points", [])}
    # 未覆盖的知识点排前面，优先补齐
    ordered_kps = [kp for kp in knowledge_points if kp not in covered] + [
        kp for kp in knowledge_points if kp in covered
    ]
    if not ordered_kps:
        ordered_kps = knowledge_points or ["综合"]

    tasks: List[Dict[str, Any]] = []
    for qt, need in shortfall.items():
        kp_slots = [ordered_kps[i % len(ordered_kps)] for i in range(need)]
        difficulty_slots = _allocate_by_distribution(need, difficulty_dist)
        bucket: Dict[tuple, int] = {}
        idx = 0
        for difficulty, d_count in difficulty_slots.items():
            for _ in range(d_count):
                kp = kp_slots[idx]
                bucket[(kp, difficulty)] = bucket.get((kp, difficulty), 0) + 1
                idx += 1
        for (kp, difficulty), count in bucket.items():
            tasks.append({
                "knowledge_point": kp,
                "question_type": qt,
                "difficulty": difficulty,
                "count": count,
            })
    return tasks


class GenerationWorkflow:
    """试卷生成Workflow"""

    def __init__(self):
        self.generator = GeneratorAgent()
        self.quality_review = QualityReviewGroup()
        self.knowledge_base = get_knowledge_base()
        self.embedding = get_embedding_client()
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(GenerationState)
        graph.add_node("parse_requirement", self._parse_requirement)
        graph.add_node("generate_questions", self._generate_questions)
        graph.add_node("review_questions", self._review_questions)
        graph.add_node("deduplicate_questions", self._deduplicate_questions)
        graph.add_node("compensate", self._compensate)
        graph.add_node("assemble_paper", self._assemble_paper)

        graph.set_entry_point("parse_requirement")
        graph.add_edge("parse_requirement", "generate_questions")
        graph.add_edge("generate_questions", "review_questions")
        graph.add_edge("review_questions", "deduplicate_questions")
        graph.add_edge("deduplicate_questions", "compensate")
        graph.add_edge("compensate", "assemble_paper")
        graph.add_edge("assemble_paper", END)
        return graph.compile()

    # ==================== 节点 ====================
    async def _parse_requirement(self, state: GenerationState) -> GenerationState:
        """解析需求，拆解生成任务"""
        requirement = state["requirement"]
        tasks = _build_tasks(requirement)
        logger.info(f"[workflow] 解析需求完成 | 共 {len(tasks)} 个生成任务")
        return {
            "generation_tasks": tasks,
            "current_step": "parse_requirement",
            "errors": [],
        }

    async def _run_generation_tasks(
        self,
        tasks: List[Dict[str, Any]],
        grade: str,
        subject: str,
        errors: List[str],
        enable_rag: bool = True,
    ) -> List[Dict[str, Any]]:
        """并发执行一组生成任务，返回题目列表（失败任务记入errors）"""
        semaphore = asyncio.Semaphore(settings.max_concurrent_llm_calls)

        async def run_task(task: Dict[str, Any]) -> List[Dict[str, Any]]:
            async with semaphore:
                # RAG: 检索历史相似题作为参考(避免重复)
                references: List[Dict[str, Any]] = []
                if enable_rag:
                    probe = {
                        "subject": subject,
                        "content": task["knowledge_point"],
                        "knowledge_points": [task["knowledge_point"]],
                    }
                    references = await self.knowledge_base.search_similar(
                        probe, top_k=3, subject=subject,
                        question_type=task["question_type"],
                    )
                try:
                    return await self.generator.generate_questions(
                        grade=grade,
                        subject=subject,
                        knowledge_point=task["knowledge_point"],
                        question_type=task["question_type"],
                        difficulty=task["difficulty"],
                        count=task["count"],
                        reference_questions=references,
                    )
                except Exception as e:  # noqa: BLE001 - 单任务失败不应中断全部
                    msg = f"生成任务失败 {task}: {e}"
                    logger.error(f"[workflow] {msg}")
                    errors.append(msg)
                    return []

        results = await asyncio.gather(*[run_task(t) for t in tasks])
        return [q for group in results for q in group]

    async def _generate_questions(self, state: GenerationState) -> GenerationState:
        """并发执行所有生成任务"""
        requirement = state["requirement"]
        tasks = state.get("generation_tasks", [])
        grade = requirement.get("grade", "")
        subject = requirement.get("subject", "")
        errors: List[str] = []

        questions = await self._run_generation_tasks(
            tasks, grade, subject, errors,
            enable_rag=state.get("enable_rag", True),
        )

        logger.info(f"[workflow] 题目生成完成 | 共 {len(questions)} 道题")
        return {
            "questions": questions,
            "current_step": "generate_questions",
            "errors": errors,
        }

    async def _review_questions(self, state: GenerationState) -> GenerationState:
        """质量审核：并发审核每道题，过滤未通过的题目"""
        questions = state.get("questions", [])
        if not state.get("enable_review", True):
            logger.info("[workflow] 质量审核已跳过")
            return {"current_step": "review_questions"}

        approved = await self._review_batch(questions)
        rejected_count = len(questions) - len(approved)

        logger.info(
            f"[workflow] 质量审核完成 | 通过 {len(approved)} 道 | 拒绝 {rejected_count} 道"
        )
        return {
            "questions": approved,
            "current_step": "review_questions",
        }

    async def _dedup_against_existing(
        self, new_questions: List[Dict[str, Any]], existing_questions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        对新题目与已有题目去重，返回不重复的新题目。

        阈值: 0.85 (相似度>0.85视为重复)
        """
        if not new_questions or not self.embedding:
            return new_questions

        if not existing_questions:
            return new_questions

        SIMILARITY_THRESHOLD = 0.85

        try:
            import asyncio
            import numpy as np

            # 计算新题目和已有题目的embedding
            new_texts = [
                f"{q.get('subject', '')} {' '.join(q.get('knowledge_points', []))} {q.get('content', '')}"
                for q in new_questions
            ]
            existing_texts = [
                f"{q.get('subject', '')} {' '.join(q.get('knowledge_points', []))} {q.get('content', '')}"
                for q in existing_questions
            ]

            all_vectors = await asyncio.gather(*[
                self.embedding.async_create_embedding(text)
                for text in new_texts + existing_texts
            ])

            new_vectors = all_vectors[:len(new_questions)]
            existing_vectors = all_vectors[len(new_questions):]

            def cosine_similarity(v1, v2):
                v1, v2 = np.array(v1), np.array(v2)
                return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

            # 过滤与已有题目重复的新题目
            kept = []
            duplicate_count = 0

            for i, new_q in enumerate(new_questions):
                is_duplicate = False
                for j, existing_v in enumerate(existing_vectors):
                    similarity = cosine_similarity(new_vectors[i], existing_v)
                    if similarity > SIMILARITY_THRESHOLD:
                        is_duplicate = True
                        duplicate_count += 1
                        logger.debug(
                            f"[workflow] 补偿题目与已有题目重复 | 相似度: {similarity:.3f} | "
                            f"新题: {new_q.get('content', '')[:30]}... | "
                            f"已有: {existing_questions[j].get('content', '')[:30]}..."
                        )
                        break

                if not is_duplicate:
                    kept.append(new_q)

            if duplicate_count > 0:
                logger.info(
                    f"[workflow] 补偿去重 | 新生成 {len(new_questions)} 道 | "
                    f"重复 {duplicate_count} 道 | 保留 {len(kept)} 道"
                )

            return kept

        except Exception as e:
            logger.warning(f"[workflow] 补偿去重失败，保留所有新题目: {e}")
            return new_questions

    async def _deduplicate_questions(self, state: GenerationState) -> GenerationState:
        """
        试卷内部去重：计算当前试卷题目间的相似度，移除重复题目。

        阈值: 0.85 (相似度>0.85视为重复)
        策略: 保留第一道，丢弃后续重复的
        """
        questions = list(state.get("questions", []))
        if not questions:
            return {"current_step": "deduplicate_questions"}

        if not self.embedding:
            logger.warning("[workflow] embedding未初始化，跳过去重")
            return {"questions": questions, "current_step": "deduplicate_questions"}

        SIMILARITY_THRESHOLD = 0.85

        # 计算所有题目的embedding
        logger.info(f"[workflow] 开始试卷内部去重 | 题目数: {len(questions)} | 阈值: {SIMILARITY_THRESHOLD}")

        embed_texts = []
        for q in questions:
            text = f"{q.get('subject', '')} {' '.join(q.get('knowledge_points', []))} {q.get('content', '')}"
            embed_texts.append(text)

        try:
            import asyncio
            vectors = await asyncio.gather(*[
                self.embedding.async_create_embedding(text)
                for text in embed_texts
            ])
        except Exception as e:
            logger.warning(f"[workflow] embedding失败，跳过去重: {e}")
            return {"questions": questions, "current_step": "deduplicate_questions"}

        # 计算余弦相似度并去重
        import numpy as np

        def cosine_similarity(v1, v2):
            v1, v2 = np.array(v1), np.array(v2)
            return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

        kept_indices = []
        duplicate_count = 0

        for i in range(len(questions)):
            is_duplicate = False
            for j in kept_indices:
                similarity = cosine_similarity(vectors[i], vectors[j])
                if similarity > SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    duplicate_count += 1
                    logger.debug(
                        f"[workflow] 发现重复题目 | 相似度: {similarity:.3f} | "
                        f"题目{i}: {questions[i].get('content', '')[:30]}... | "
                        f"题目{j}: {questions[j].get('content', '')[:30]}..."
                    )
                    break

            if not is_duplicate:
                kept_indices.append(i)

        deduplicated = [questions[i] for i in kept_indices]

        logger.info(
            f"[workflow] 去重完成 | 保留 {len(deduplicated)} 道 | 移除 {duplicate_count} 道重复"
        )

        return {
            "questions": deduplicated,
            "current_step": "deduplicate_questions",
        }

    async def _compensate(self, state: GenerationState) -> GenerationState:
        """
        补偿生成：审核/去重过滤后某些题型数量不足时，自动补齐到需求数量。

        最多尝试 settings.max_retries 轮，每轮针对缺口生成并(若启用)审核。
        注：生成的题目不再自动入库，历史题库由用户上传优质题目填充。
        """
        requirement = state["requirement"]
        questions = list(state.get("questions", []))
        errors = list(state.get("errors", []))
        target: Dict[str, int] = requirement.get("question_types", {})
        if not target:
            return {"questions": questions, "current_step": "compensate"}

        grade = requirement.get("grade", "")
        subject = requirement.get("subject", "")
        knowledge_points = requirement.get("knowledge_points", []) or ["综合"]
        difficulty_dist = requirement.get(
            "difficulty_distribution", {"简单": 0.4, "中等": 0.4, "困难": 0.2}
        )
        enable_review = state.get("enable_review", True)
        max_rounds = max(1, settings.max_retries)

        for round_no in range(1, max_rounds + 1):
            # 统计各题型当前数量与缺口
            current = _count_by_type(questions)
            shortfall = {
                qt: target[qt] - current.get(qt, 0)
                for qt in target
                if target[qt] - current.get(qt, 0) > 0
            }
            if not shortfall:
                break

            logger.info(f"[workflow] 补偿生成第{round_no}轮 | 缺口: {shortfall}")

            # 为缺口构建任务：优先补未覆盖的知识点
            comp_tasks = _build_compensation_tasks(
                shortfall, questions, knowledge_points, difficulty_dist
            )
            new_questions = await self._run_generation_tasks(
                comp_tasks, grade, subject, errors,
                enable_rag=state.get("enable_rag", True),
            )

            if enable_review and new_questions:
                new_questions = await self._review_batch(new_questions)

            # 补偿题目与已有题目去重
            if new_questions:
                new_questions = await self._dedup_against_existing(new_questions, questions)

            # 仅补足缺口数量，避免超额
            added = 0
            for qt, need in shortfall.items():
                picked = [q for q in new_questions if q.get("question_type") == qt][:need]
                questions.extend(picked)
                added += len(picked)

            # 本轮无新增则提前结束，避免空转
            if added == 0:
                logger.warning(f"[workflow] 补偿第{round_no}轮无新增，提前结束")
                break

        # 裁剪：每个题型最多保留目标数量，避免超额(初次生成或补偿超量)
        questions = _trim_to_target(questions, target)

        final_counts = _count_by_type(questions)
        logger.info(f"[workflow] 补偿完成 | 各题型数量: {final_counts} | 目标: {target}")
        return {
            "questions": questions,
            "errors": errors,
            "current_step": "compensate",
        }

    async def _review_batch(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对一批题目执行质量审核，返回通过的题目"""
        semaphore = asyncio.Semaphore(settings.max_concurrent_llm_calls)

        async def review_one(q: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                verdict = await self.quality_review.review(q)
                q["quality_score"] = verdict.get("quality_score")
                q["review_issues"] = verdict.get("issues", [])
                q["is_approved"] = bool(verdict.get("approved", True))
                return q

        reviewed = await asyncio.gather(*[review_one(q) for q in questions])
        return [q for q in reviewed if q.get("is_approved")]

    async def _assemble_paper(self, state: GenerationState) -> GenerationState:
        """组装试卷元数据"""
        requirement = state["requirement"]
        questions = state.get("questions", [])

        knowledge_points_covered = sorted({
            kp for q in questions for kp in q.get("knowledge_points", [])
        })

        paper = {
            "title": f"{requirement.get('grade', '')}{requirement.get('subject', '')}单元测试卷",
            "metadata": {
                "grade": requirement.get("grade", ""),
                "subject": requirement.get("subject", ""),
                "duration_minutes": requirement.get("duration_minutes", 60),
                "total_score": requirement.get("total_score", 100),
                "difficulty_distribution": requirement.get("difficulty_distribution", {}),
                "knowledge_points_covered": knowledge_points_covered,
                "question_count": len(questions),
            },
        }
        logger.info(f"[workflow] 试卷组装完成 | {paper['title']} | {len(questions)} 题")
        return {
            "paper": paper,
            "current_step": "assemble_paper",
        }

    # ==================== 入口 ====================
    async def run(
        self,
        requirement: Dict[str, Any],
        enable_review: bool = True,
        enable_rag: bool = True,
        progress_callback=None,
    ) -> GenerationState:
        """
        执行完整生成流程

        Args:
            requirement: 试卷需求(dict)
            enable_review: 是否启用质量审核(AutoGen群聊)
            enable_rag: 是否启用RAG(历史题库检索参考+去重+入库)
            progress_callback: 可选的异步回调 async (step: str, state: dict)，
                每完成一个节点时调用，用于上报进度

        Returns:
            最终的Workflow状态，包含questions和paper
        """
        initial_state: GenerationState = {
            "requirement": requirement,
            "current_step": "init",
            "errors": [],
            "enable_review": enable_review,
            "enable_rag": enable_rag,
        }

        if progress_callback is None:
            return await self.graph.ainvoke(initial_state)

        # 使用astream逐节点观察进度
        final_state: GenerationState = dict(initial_state)
        async for chunk in self.graph.astream(initial_state):
            for node_name, node_state in chunk.items():
                if isinstance(node_state, dict):
                    final_state.update(node_state)
                try:
                    await progress_callback(node_name, final_state)
                except Exception as e:  # noqa: BLE001 - 进度上报失败不应中断
                    logger.warning(f"[workflow] 进度回调失败: {e}")
        return final_state
