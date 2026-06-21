"""
Workflow集成测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.workflows.generation_workflow import (
    GenerationWorkflow,
    _build_tasks,
    _count_by_type,
    _trim_to_target,
)


class TestWorkflowHelpers:
    """工作流辅助函数测试"""

    def test_build_tasks(self, mock_requirement):
        """测试任务构建"""
        tasks = _build_tasks(mock_requirement)

        assert len(tasks) > 0
        for task in tasks:
            assert "knowledge_point" in task
            assert "question_type" in task
            assert "difficulty" in task
            assert "count" in task

    def test_count_by_type(self, mock_questions):
        """测试按题型计数"""
        counts = _count_by_type(mock_questions)

        assert "选择题" in counts
        assert "填空题" in counts
        assert "应用题" in counts
        assert counts["选择题"] == 3
        assert counts["填空题"] == 2
        assert counts["应用题"] == 1

    def test_trim_to_target(self, mock_questions):
        """测试裁剪到目标数量"""
        target = {
            "选择题": 2,
            "填空题": 1,
            "应用题": 1,
        }
        trimmed = _trim_to_target(mock_questions, target)

        counts = _count_by_type(trimmed)
        assert counts["选择题"] == 2
        assert counts["填空题"] == 1
        assert counts["应用题"] == 1


class TestGenerationWorkflow:
    """生成工作流测试"""

    @pytest.fixture
    def workflow(self):
        """创建workflow实例"""
        return GenerationWorkflow()

    def test_workflow_init(self, workflow):
        """测试workflow初始化"""
        assert workflow.generator is not None
        assert workflow.quality_review is not None
        assert workflow.graph is not None

    @pytest.mark.asyncio
    async def test_parse_requirement(self, workflow, mock_requirement):
        """测试需求解析"""
        state = {"requirement": mock_requirement}
        result = await workflow._parse_requirement(state)

        assert "generation_tasks" in result
        assert len(result["generation_tasks"]) > 0
        assert result["current_step"] == "parse_requirement"

    @pytest.mark.asyncio
    @patch('app.workflows.generation_workflow.GenerationWorkflow._run_generation_tasks')
    async def test_generate_questions(self, mock_gen_tasks, workflow, mock_requirement, mock_questions):
        """测试题目生成"""
        mock_gen_tasks.return_value = mock_questions

        state = {
            "requirement": mock_requirement,
            "generation_tasks": _build_tasks(mock_requirement),
        }
        result = await workflow._generate_questions(state)

        assert "questions" in result
        assert len(result["questions"]) > 0
        assert result["current_step"] == "generate_questions"

    @pytest.mark.asyncio
    async def test_assemble_paper(self, workflow, mock_requirement, mock_questions):
        """测试试卷组装"""
        state = {
            "requirement": mock_requirement,
            "questions": mock_questions,
        }
        result = await workflow._assemble_paper(state)

        assert "paper" in result
        paper = result["paper"]
        assert "title" in paper
        assert "metadata" in paper
        assert paper["metadata"]["question_count"] == len(mock_questions)


class TestWorkflowIntegration:
    """Workflow端到端集成测试"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    @patch('app.agents.generator_agent.GeneratorAgent.generate_questions')
    @patch('app.agents.quality_review_group.QualityReviewGroup.review')
    async def test_full_workflow_mock(
        self,
        mock_review,
        mock_generate,
        mock_requirement,
        mock_questions
    ):
        """测试完整workflow（mock LLM）"""
        # Mock生成
        mock_generate.return_value = mock_questions[:3]

        # Mock审核
        mock_review.return_value = {
            "approved": True,
            "quality_score": 0.8,
            "issues": []
        }

        workflow = GenerationWorkflow()
        result = await workflow.run(
            requirement=mock_requirement,
            enable_review=True,
            enable_rag=False,
        )

        assert "questions" in result
        assert "paper" in result
        assert len(result["questions"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-e2e", default=False),
        reason="需要--run-e2e参数才运行真实LLM测试"
    )
    async def test_full_workflow_real(self, mock_requirement):
        """测试完整workflow（真实LLM调用）"""
        # 缩小需求规模
        mock_requirement["question_types"] = {
            "选择题": 1,
            "填空题": 1,
        }

        workflow = GenerationWorkflow()
        result = await workflow.run(
            requirement=mock_requirement,
            enable_review=False,  # 关闭审核加速测试
            enable_rag=False,
        )

        assert "questions" in result
        assert "paper" in result
        assert len(result["questions"]) >= 2