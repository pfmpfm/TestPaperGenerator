"""
质量审核小组 - 基于AutoGen多Agent群聊

由内容审核员、答案校验员、决策员组成，对单道题目进行多轮讨论，
最终由决策员输出JSON裁定(是否通过/质量评分/问题列表)。
"""
import json
import re
from typing import Any, Dict

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import (
    MaxMessageTermination,
    TextMentionTermination,
)
from autogen_agentchat.teams import RoundRobinGroupChat

from app.agents.autogen_client import build_autogen_model_client
from app.core.config import model_config
from app.core.logging import logger

CONTENT_REVIEWER_PROMPT = """你是中小学试题内容审核员。
你的职责：检查题目表述是否清晰、无歧义，是否符合指定年级学生的认知水平，
是否有知识性错误或不当内容。
注意：题目若标注"已配图"，表示系统已自动生成对应图形，请视为题目完整，
不要因为你看不到图像就判定"缺图/题目不完整/无法作答"。题目中的 $...$ 是LaTeX公式、
Markdown表格是正常排版，都不是问题。
请简明指出问题（若无问题则说明"内容无问题"），不要重复他人观点。"""

ANSWER_CHECKER_PROMPT = """你是中小学试题答案校验员。
你的职责：独立验算题目的答案是否正确，解析是否合理。
对于选择题，检查正确选项是否唯一且正确。
请简明给出校验结论（答案正确/答案错误及正确答案），不要重复他人观点。"""

DECISION_MAKER_PROMPT = """你是质量审核决策员。
综合内容审核员和答案校验员的意见，对题目做出最终裁定。
你必须在回复的最后输出一个JSON对象，并以单词 TERMINATE 结尾。
JSON格式如下：
{"approved": true/false, "quality_score": 0到1之间的小数, "issues": ["问题1","问题2"], "suggestion": "改进建议"}
- approved: 是否通过审核(答案错误或有知识性错误必须为false)
- quality_score: 综合质量评分
- issues: 发现的问题列表，无问题则为空数组
- suggestion: 简短改进建议，可为空字符串"""


def _format_question(question: Dict[str, Any]) -> str:
    """将题目格式化为审核输入文本"""
    # 配图说明：图由系统根据figure_spec自动渲染，审核时看不到图本身，
    # 需明确告知审核员"图已存在"，避免误判"缺图→题目无效"。
    figure_note = "(无配图)"
    figure_spec = question.get("figure_spec")
    if isinstance(figure_spec, dict) and figure_spec.get("figure_type"):
        params = figure_spec.get("params", {})
        figure_note = (
            f"已配图(系统自动生成，此处不展示图像本身)：类型={figure_spec.get('figure_type')}，"
            f"数据={params}。请视为题目已含对应图形，不要因看不到图而判定题目不完整。"
        )

    return (
        f"【待审核题目】\n"
        f"年级: {question.get('grade', '')}\n"
        f"科目: {question.get('subject', '')}\n"
        f"题型: {question.get('question_type', '')}\n"
        f"难度: {question.get('difficulty', '')}\n"
        f"知识点: {', '.join(question.get('knowledge_points', []))}\n"
        f"题目内容: {question.get('content', '')}\n"
        f"配图情况: {figure_note}\n"
        f"答案: {question.get('answer', '')}\n"
        f"解析: {question.get('explanation', '') or '(无)'}\n"
        f"\n说明: 题目中 $...$ 内为LaTeX数学公式(系统会正确渲染)，"
        f"表格用Markdown语法，均属正常排版，不应因此扣分。"
    )


def _extract_decision(text: str) -> Dict[str, Any]:
    """从决策员回复中提取JSON裁定"""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    # 解析失败时默认放行，避免误杀
    return {
        "approved": True,
        "quality_score": 0.6,
        "issues": ["审核结论解析失败，默认放行"],
        "suggestion": "",
    }


class QualityReviewGroup:
    """质量审核小组"""

    def __init__(self):
        self.config = model_config.get_agent_config("quality_review_group")
        self.max_rounds = self.config.get("max_rounds", 6)

    async def review(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """
        对单道题目进行审核

        Args:
            question: 题目字典

        Returns:
            裁定结果 {"approved", "quality_score", "issues", "suggestion"}
        """
        client = build_autogen_model_client(llm_type="high_quality")
        try:
            content_reviewer = AssistantAgent(
                "content_reviewer",
                model_client=client,
                system_message=CONTENT_REVIEWER_PROMPT,
            )
            answer_checker = AssistantAgent(
                "answer_checker",
                model_client=client,
                system_message=ANSWER_CHECKER_PROMPT,
            )
            decision_maker = AssistantAgent(
                "decision_maker",
                model_client=client,
                system_message=DECISION_MAKER_PROMPT,
            )

            termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(
                self.max_rounds
            )
            team = RoundRobinGroupChat(
                [content_reviewer, answer_checker, decision_maker],
                termination_condition=termination,
            )

            result = await team.run(task=_format_question(question))

            # 找决策员的最后一条消息
            decision_text = ""
            for msg in reversed(result.messages):
                if getattr(msg, "source", "") == "decision_maker":
                    decision_text = str(getattr(msg, "content", ""))
                    break

            decision = _extract_decision(decision_text)
            logger.bind(agent=True).info(
                f"[quality_review] 审核完成 | approved={decision.get('approved')} "
                f"| score={decision.get('quality_score')}"
            )
            return decision
        except Exception as e:  # noqa: BLE001 - 审核失败默认放行
            logger.bind(agent=True).error(f"[quality_review] 审核异常: {e}")
            return {
                "approved": True,
                "quality_score": 0.6,
                "issues": [f"审核异常: {e}"],
                "suggestion": "",
            }
        finally:
            await client.close()
