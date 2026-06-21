"""
Pytest配置和fixtures
"""
import os
import sys
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings


# ==================== Pytest配置 ====================

def pytest_configure(config):
    """Pytest配置"""
    # 设置测试环境变量
    os.environ["ENV"] = "testing"
    os.environ["DEBUG"] = "True"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    os.environ["ENABLE_METRICS"] = "false"


# ==================== Event Loop ====================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== Mock数据 ====================

@pytest.fixture
def mock_requirement():
    """模拟试卷需求"""
    return {
        "grade": "六年级",
        "subject": "数学",
        "knowledge_points": ["分数加减法", "分数乘除法"],
        "question_types": {
            "选择题": 3,
            "填空题": 2,
            "应用题": 1,
        },
        "difficulty_distribution": {
            "简单": 0.5,
            "中等": 0.3,
            "困难": 0.2,
        },
        "duration_minutes": 60,
        "total_score": 100,
    }


@pytest.fixture
def mock_question():
    """模拟单个题目"""
    return {
        "content": "计算 $\\frac{1}{2} + \\frac{1}{3}$ 的值。",
        "answer": "$\\frac{5}{6}$",
        "explanation": "通分后相加：$\\frac{3}{6} + \\frac{2}{6} = \\frac{5}{6}$",
        "question_type": "填空题",
        "difficulty": "简单",
        "knowledge_points": ["分数加减法"],
        "figure_spec": None,
        "grade": "六年级",
        "subject": "数学",
    }


@pytest.fixture
def mock_questions(mock_question):
    """模拟题目列表"""
    questions = []
    for i in range(6):
        q = mock_question.copy()
        q["content"] = f"题目 {i+1}: " + q["content"]
        if i < 3:
            q["question_type"] = "选择题"
        elif i < 5:
            q["question_type"] = "填空题"
        else:
            q["question_type"] = "应用题"
        questions.append(q)
    return questions


# ==================== Mock LLM ====================

@pytest.fixture
def mock_llm_response():
    """Mock LLM响应"""
    class MockResponse:
        def __init__(self):
            self.choices = [
                type('obj', (object,), {
                    'message': type('obj', (object,), {
                        'content': '{"result": "test"}'
                    })()
                })()
            ]
            self.usage = type('obj', (object,), {
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            })()

    return MockResponse()


# ==================== Mock DB ====================

@pytest.fixture
async def mock_db_session():
    """Mock数据库会话"""
    # 这里可以创建测试数据库或使用SQLite内存数据库
    # 暂时返回None，实际项目中应该创建真实的测试DB
    yield None


# ==================== 辅助函数 ====================

def assert_valid_question(question: dict):
    """验证题目结构"""
    required_fields = [
        "content", "answer", "explanation",
        "question_type", "difficulty", "knowledge_points"
    ]
    for field in required_fields:
        assert field in question, f"题目缺少字段: {field}"

    assert question["question_type"] in ["选择题", "填空题", "应用题"]
    assert question["difficulty"] in ["简单", "中等", "困难"]
    assert isinstance(question["knowledge_points"], list)
    assert len(question["knowledge_points"]) > 0


def assert_valid_paper(paper: dict):
    """验证试卷结构"""
    assert "title" in paper
    assert "metadata" in paper
    metadata = paper["metadata"]
    assert "grade" in metadata
    assert "subject" in metadata
    assert "question_count" in metadata