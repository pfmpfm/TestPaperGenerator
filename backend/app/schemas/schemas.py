"""
Pydantic schemas - 数据验证和序列化
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ==================== 枚举类型 ====================
class DifficultyLevel(str, Enum):
    """难度等级"""
    EASY = "简单"
    MEDIUM = "中等"
    HARD = "困难"


class QuestionType(str, Enum):
    """题型"""
    CHOICE = "选择题"
    FILL_BLANK = "填空题"
    APPLICATION = "应用题"


class SessionStatus(str, Enum):
    """会话状态"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ==================== 试卷需求 ====================
class ExamRequirement(BaseModel):
    """试卷生成需求"""
    grade: str = Field(..., description="年级，如：小学三年级")
    subject: str = Field(..., description="科目，如：数学")
    knowledge_points: List[str] = Field(..., description="知识点列表")
    question_types: Dict[str, int] = Field(
        ...,
        description="题型和数量，如：{'选择题': 10, '填空题': 5, '应用题': 3}"
    )
    difficulty_distribution: Dict[str, float] = Field(
        default={"简单": 0.4, "中等": 0.4, "困难": 0.2},
        description="难度分布"
    )
    duration_minutes: int = Field(default=60, description="考试时长（分钟）")
    total_score: int = Field(default=100, description="总分")

    @field_validator("difficulty_distribution")
    @classmethod
    def validate_difficulty_distribution(cls, v):
        """验证难度分布总和为1"""
        total = sum(v.values())
        if not (0.99 <= total <= 1.01):  # 允许浮点误差
            raise ValueError("难度分布总和必须为1.0")
        return v


# ==================== 题目 ====================
class QuestionBase(BaseModel):
    """题目基础信息"""
    content: str = Field(..., description="题目内容")
    answer: str = Field(..., description="答案")
    explanation: Optional[str] = Field(None, description="解析")
    question_type: QuestionType
    difficulty: DifficultyLevel
    grade: str
    subject: str
    knowledge_points: List[str]
    figure_url: Optional[str] = None
    figure_spec: Optional[Dict[str, Any]] = None


class QuestionCreate(QuestionBase):
    """创建题目"""
    pass


class QuestionInDB(QuestionBase):
    """数据库中的题目"""
    id: str
    quality_score: Optional[float] = None
    usage_count: int = 0
    is_approved: bool = False
    qdrant_point_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Question(QuestionInDB):
    """题目响应"""
    pass


# ==================== 试卷 ====================
class ExamPaperMetadata(BaseModel):
    """试卷元数据"""
    grade: str
    subject: str
    duration_minutes: int
    total_score: int
    difficulty_distribution: Dict[str, float]
    knowledge_points_covered: List[str]
    generation_time: datetime
    quality_score: float


class ExamPaperCreate(BaseModel):
    """创建试卷"""
    title: str
    metadata: ExamPaperMetadata
    question_ids: List[str]
    teacher_id: Optional[str] = None
    session_id: str


class ExamPaperInDB(BaseModel):
    """数据库中的试卷"""
    id: str
    title: str
    metadata: Dict[str, Any]
    question_ids: List[str]
    quality_score: Optional[float] = None
    teacher_id: Optional[str] = None
    session_id: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExamPaper(ExamPaperInDB):
    """试卷响应"""
    questions: Optional[List[Question]] = None


# ==================== 审核结果 ====================
class ReviewResult(BaseModel):
    """审核结果"""
    approved: bool = Field(..., description="是否通过")
    major_issues: List[str] = Field(default_factory=list, description="主要问题")
    suggestions: List[str] = Field(default_factory=list, description="改进建议")
    need_regenerate: bool = Field(default=False, description="是否需要重新生成")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="质量评分")


# ==================== 生成会话 ====================
class GenerationSessionCreate(BaseModel):
    """创建生成会话"""
    requirement: ExamRequirement


class GenerationSessionInDB(BaseModel):
    """数据库中的会话"""
    session_id: str
    status: SessionStatus
    requirement: Dict[str, Any]
    workflow_state: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerationSession(GenerationSessionInDB):
    """生成会话响应"""
    pass


# ==================== Workflow状态 ====================
class WorkflowState(BaseModel):
    """Workflow状态"""
    requirement: ExamRequirement
    knowledge_graph: Optional[Dict[str, Any]] = None
    question_pool: List[Question] = Field(default_factory=list)
    selected_questions: List[Question] = Field(default_factory=list)
    paper: Optional[ExamPaper] = None
    review_result: Optional[ReviewResult] = None
    retry_count: int = 0
    errors: List[str] = Field(default_factory=list)
    current_step: str = "init"


# ==================== API响应 ====================
class ResponseBase(BaseModel):
    """基础响应"""
    success: bool = True
    message: str = "操作成功"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    detail: Optional[Any] = None


# ==================== 知识点 ====================
class KnowledgePointBase(BaseModel):
    """知识点基础信息"""
    name: str
    grade: str
    subject: str
    parent_id: Optional[str] = None
    level: int = 1
    description: Optional[str] = None


class KnowledgePointCreate(KnowledgePointBase):
    """创建知识点"""
    pass


class KnowledgePointInDB(KnowledgePointBase):
    """数据库中的知识点"""
    id: str
    qdrant_point_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgePoint(KnowledgePointInDB):
    """知识点响应"""
    children: Optional[List["KnowledgePoint"]] = None


# ==================== 教师 ====================
class TeacherBase(BaseModel):
    """教师基础信息"""
    name: str
    email: str


class TeacherCreate(TeacherBase):
    """创建教师"""
    password: str


class TeacherInDB(TeacherBase):
    """数据库中的教师"""
    id: str
    preferences: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Teacher(TeacherInDB):
    """教师响应"""
    pass


class TeacherLogin(BaseModel):
    """教师登录"""
    email: str
    password: str


class Token(BaseModel):
    """JWT Token"""
    access_token: str
    token_type: str = "bearer"


# ==================== 配图规格 ====================
class FigureSpec(BaseModel):
    """配图规格"""
    figure_type: str = Field(..., description="图形类型")
    params: Dict[str, Any] = Field(..., description="参数")

    class Config:
        json_schema_extra = {
            "example": {
                "figure_type": "rectangle",
                "params": {
                    "width": 5,
                    "height": 3,
                    "unit": "cm",
                    "show_dimensions": True
                }
            }
        }


# 更新前向引用
KnowledgePoint.model_rebuild()
