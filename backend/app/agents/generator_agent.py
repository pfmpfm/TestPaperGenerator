"""
题目生成Agent - 根据知识点/题型/难度调用LLM生成题目
"""
from typing import Any, Dict, List, Optional

from app.agents.base_agent import BaseAgent
from app.core.logging import logger
from app.tools.figure_generator import get_figure_generator
from app.tools.textbook_kb import get_textbook_kb

SYSTEM_PROMPT = """你是一位资深的中小学__SUBJECT__命题专家。
你需要根据要求生成高质量的试题，题目必须符合指定年级学生的认知水平，表述清晰、答案准确。

【重要-题目多样性】
1. 同一批次生成的多道题目，必须在以下维度体现多样性：
   - 题干角度：不同的问题切入点和表述方式
   - 数据素材：数字、人物、场景、物品、事件等要有变化
   - 考查侧重：同一知识点的不同方面和层次
   - 情境设定：生活场景、故事背景、实例要丰富多元
2. 严禁生成内容高度相似的题目（例如：多道题使用相同的素材、相同的场景、相同的数据）。
3. 即使知识点相同，也要确保题目内容、考查角度、呈现方式有明显区别。
4. 优先使用不同的实例、案例、场景来考查同一概念。

输出要求：
1. 严格输出JSON数组，不要包含任何额外说明文字。
2. 数组中每个元素是一道题，包含以下字段：
   - content: 题目内容（字符串）
   - answer: 正确答案（字符串）
   - explanation: 解析（字符串）
   - question_type: 题型，必须是 "选择题"、"填空题" 或 "应用题" 之一
   - difficulty: 难度，必须是 "简单"、"中等" 或 "困难" 之一
   - knowledge_points: 该题考查的知识点（字符串数组）
   - figure_spec: 配图规格（对象），若不需要配图则为 null
3. 【重要】选择题的content必须完整包含题干和A/B/C/D四个选项的具体内容，answer为正确选项的字母。
   选择题content正确示例："计算 $15 + 23$ 的结果是？\\nA. 36  B. 38  C. 40  D. 42"
   选择题content错误示例(缺选项，禁止)："15 + 23 = ?"
4. 【重要-数学公式】所有数学表达式必须使用LaTeX语法，并用 $...$ 包裹（行内公式）。
   - 分数必须用 \\frac，如 二分之一 写作 $\\frac{1}{2}$，禁止写成 "1/2"。
   - 乘除用 \\times \\div，如 $3 \\times 4$、$12 \\div 3$。
   - 上标下标用 ^ _，如 $x^2$、$a_1$。
   - 带单位时单位放在$外，如 "边长为 $5$ cm"。
   - 答案/解析中的数学表达式同样使用LaTeX，如 answer 写 "$\\frac{3}{4}$"。
   - 只能用行内公式 $...$，禁止使用块级公式 $$...$$。
   - 不要在content里用文字描述配图(如"$$（配图：...）$$")，配图一律通过 figure_spec 字段提供。
5. 【重要-配图】若题目涉及几何图形(矩形/三角形/圆/正方形)、数轴、或数据统计图
   (柱状图/饼图/折线图)，必须提供 figure_spec，不可省略，也不可用表格替代统计图。
   尤其当知识点明确提到"折线图/折线统计图"时，必须输出 line_chart；提到"柱状图"输出
   bar_chart；提到"饼图/扇形图"输出 pie_chart。格式为：
   {"figure_type": "类型", "params": {"参数名": 数值}}

   【配图支持范围-重要限制】
   配图系统仅支持平面图形，不支持立体图形。支持的figure_type及参数：

   平面几何图形（2D）：
   - rectangle: width, height, unit  (矩形)
   - square: side, unit  (正方形)
   - triangle: base, height, unit  (三角形)
   - circle: radius, unit  (圆)

   统计图表：
   - bar_chart: labels(字符串数组), values(数值数组), title, xlabel, ylabel  (柱状图)
   - pie_chart: labels(字符串数组), values(数值数组), title  (饼图)
   - line_chart: labels(字符串数组,如月份), values(数值数组), title, xlabel, ylabel  (折线图)
     多条折线用 series 数组: [{"name":"系列名","values":[数值数组]}]

   数学工具：
   - number_line: start, end, step, points([{"value":数,"label":"A"}])  (数轴)

   【不支持的图形类型】
   以下立体图形不支持配图，请用文字描述或提供平面投影说明：
   - 正方体、长方体、立方体 (cube, cuboid)
   - 圆柱体、圆锥体 (cylinder, cone)
   - 球体、半球体 (sphere, hemisphere)
   - 棱柱、棱锥 (prism, pyramid)
   - 其他3D立体几何图形

   若题目必须涉及立体几何，请在 content 中用文字清晰描述几何体的特征
   （如"一个正方体，棱长为 $5$ cm"），figure_spec 设为 null。

   所有数值参数使用数字类型(不加引号)。不涉及上述支持的图形时 figure_spec 为 null。
6. 【重要-表格】若题目需要展示表格数据(如对照表、统计表)，content中必须
   使用标准Markdown表格语法：
   | 表头1 | 表头2 |
   | --- | --- |
   | 数据1 | 数据2 |
   表格单元格内的数学表达式同样用 $...$ 包裹。禁止用空格对齐的伪表格。
   说明：表格与统计图配图(figure_spec)可按题目实际需要并存——例如折线/柱状统计图题，
   常见做法是先用Markdown表格列出原始数据，再用 figure_spec 提供对应的统计图。
   是否需要表格由你根据题目情况判断，不强制，但不要因为有配图就刻意省略本应有的数据表格。
"""

USER_PROMPT = """请为以下要求生成试题：
- 年级：{grade}
- 科目：{subject}
- 知识点：{knowledge_point}
- 题型：{question_type}
- 难度：{difficulty}
- 数量：{count} 道

请生成 {count} 道符合上述要求的题目，直接输出JSON数组。"""


class GeneratorAgent(BaseAgent):
    """题目生成Agent"""

    agent_name = "question_generator"

    async def generate_questions(
        self,
        grade: str,
        subject: str,
        knowledge_point: str,
        question_type: str,
        difficulty: str,
        count: int,
        reference_questions: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        生成一组题目

        Args:
            grade: 年级
            subject: 科目
            knowledge_point: 知识点
            question_type: 题型
            difficulty: 难度
            count: 生成数量
            reference_questions: 历史相似题(RAG检索结果)，用于提示LLM避免重复

        Returns:
            题目字典列表，已补全grade/subject字段并生成配图URL
        """
        # 教材知识库RAG: 查询知识点定义作为生成上下文
        textbook_kb = get_textbook_kb()
        knowledge_context = ""
        try:
            kb_results = await textbook_kb.search_knowledge(
                query=knowledge_point,
                grade=grade,
                subject=subject,
                top_k=2,  # 取最相关的2个文档片段
            )
            if kb_results:
                context_parts = [
                    f"[教材参考] {r['content'][:300]}"  # 限制长度避免prompt过长
                    for r in kb_results[:2]
                ]
                knowledge_context = "\n\n".join(context_parts)
                logger.bind(agent=True).debug(
                    f"[generator] 教材知识库检索到 {len(kb_results)} 条参考"
                )
        except Exception as e:
            logger.bind(agent=True).warning(f"[generator] 教材知识库检索失败(降级): {e}")

        system_prompt = SYSTEM_PROMPT.replace("__SUBJECT__", subject)
        user_prompt = USER_PROMPT.format(
            grade=grade,
            subject=subject,
            knowledge_point=knowledge_point,
            question_type=question_type,
            difficulty=difficulty,
            count=count,
        )

        # 附加教材知识库上下文
        if knowledge_context:
            user_prompt += f"\n\n【教材知识库参考】\n{knowledge_context}\n请参考以上教材内容生成题目。"

        # RAG: 附上历史相似题，要求LLM避免重复
        if reference_questions:
            refs = "\n".join(
                f"  {i+1}. {(r.get('content') or '')[:80]}"
                for i, r in enumerate(reference_questions[:5])
            )
            user_prompt += (
                f"\n\n以下是题库中已有的相似题目，请生成与它们考点相近但"
                f"题目内容、数据不重复的新题：\n{refs}"
            )

        logger.bind(agent=True).info(
            f"[generator] 生成题目 | {grade}/{subject}/{knowledge_point} "
            f"| {question_type}/{difficulty} x{count}"
        )

        raw = await self.call_llm_json(
            system_prompt, user_prompt, temperature=0.9
        )

        # 兼容LLM可能返回 {"questions": [...]} 的情况
        if isinstance(raw, dict):
            raw = raw.get("questions") or raw.get("data") or [raw]

        questions = self._normalize(
            raw, grade, subject, knowledge_point, question_type, difficulty
        )
        # 裁剪到请求数量，避免LLM超量返回污染数量控制
        if len(questions) > count:
            questions = questions[:count]
        return questions

    @staticmethod
    def _has_options(content: str) -> bool:
        """判断选择题content是否包含至少A/B两个选项"""
        import re
        labels = re.findall(r"[ABCD][.、．)）]", content)
        return len(set(labels)) >= 2

    def _normalize(
        self,
        raw: List[Dict[str, Any]],
        grade: str,
        subject: str,
        knowledge_point: str,
        question_type: str,
        difficulty: str,
    ) -> List[Dict[str, Any]]:
        """规范化题目字段，并按需生成配图"""
        figure_gen = get_figure_generator()
        normalized: List[Dict[str, Any]] = []

        for item in raw:
            if not isinstance(item, dict) or not item.get("content"):
                continue

            content = str(item["content"]).strip()
            q_type = item.get("question_type") or question_type

            # 校验：选择题content必须包含选项，否则丢弃(避免污染后续审核)
            if "选择" in str(q_type) and not self._has_options(content):
                logger.bind(agent=True).warning(
                    f"[generator] 丢弃缺选项的选择题: {content[:50]}"
                )
                continue

            kps = item.get("knowledge_points") or [knowledge_point]
            if isinstance(kps, str):
                kps = [kps]

            question = {
                "content": content,
                "answer": str(item.get("answer", "")).strip(),
                "explanation": (item.get("explanation") or "").strip() or None,
                "question_type": q_type,
                "difficulty": item.get("difficulty") or difficulty,
                "grade": grade,
                "subject": subject,
                "knowledge_points": kps,
                "figure_spec": None,
                "figure_url": None,
            }

            figure_spec = item.get("figure_spec")
            if isinstance(figure_spec, dict) and figure_spec.get("figure_type"):
                figure_url = figure_gen.generate(figure_spec)
                question["figure_spec"] = figure_spec
                question["figure_url"] = figure_url

            normalized.append(question)

        logger.bind(agent=True).info(
            f"[generator] 解析到 {len(normalized)} 道有效题目"
        )
        return normalized
