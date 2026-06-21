"""
数据库模型定义
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DECIMAL,
    DateTime,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def generate_uuid() -> str:
    """生成UUID"""
    return str(uuid.uuid4())


class Question(Base):
    """题目表"""

    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    content = Column(Text, nullable=False, comment="题目内容")
    answer = Column(Text, nullable=False, comment="答案")
    explanation = Column(Text, comment="解析")
    question_type = Column(String(50), comment="题型(选择题/填空题/应用题)")
    difficulty = Column(String(20), comment="难度(简单/中等/困难)")
    grade = Column(String(50), comment="年级")
    subject = Column(String(50), comment="科目")
    knowledge_points = Column(JSON, comment="知识点列表")
    figure_url = Column(String(500), comment="配图URL")
    figure_spec = Column(JSON, comment="配图规格")
    quality_score = Column(DECIMAL(3, 2), comment="质量评分")
    usage_count = Column(Integer, default=0, comment="使用次数")
    is_approved = Column(Boolean, default=False, comment="是否已审核通过")
    qdrant_point_id = Column(String(36), comment="Qdrant中的点ID")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 索引
    __table_args__ = (
        Index("idx_grade_subject", "grade", "subject"),
        Index("idx_difficulty", "difficulty"),
        Index("idx_question_type", "question_type"),
    )

    def __repr__(self):
        return f"<Question(id={self.id}, type={self.question_type}, difficulty={self.difficulty})>"


class KnowledgePoint(Base):
    """知识点表"""

    __tablename__ = "knowledge_points"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False, comment="知识点名称")
    grade = Column(String(50), comment="年级")
    subject = Column(String(50), comment="科目")
    parent_id = Column(String(36), ForeignKey("knowledge_points.id", ondelete="CASCADE"), comment="父知识点ID")
    level = Column(Integer, default=1, comment="层级(1/2/3)")
    description = Column(Text, comment="描述")
    qdrant_point_id = Column(String(36), comment="Qdrant中的点ID")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 自引用关系
    children = relationship("KnowledgePoint", backref="parent", remote_side=[id])

    def __repr__(self):
        return f"<KnowledgePoint(id={self.id}, name={self.name}, level={self.level})>"


class ExamPaper(Base):
    """试卷表"""

    __tablename__ = "exam_papers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(200), comment="试卷标题")
    paper_metadata = Column(JSON, comment="元数据(年级/科目/时长/总分等)")
    question_ids = Column(JSON, comment="题目ID列表")
    quality_score = Column(DECIMAL(3, 2), comment="质量评分")
    teacher_id = Column(String(36), ForeignKey("teachers.id"), comment="教师ID")
    session_id = Column(String(36), comment="生成会话ID")
    status = Column(String(50), default="draft", comment="状态(draft/published/archived)")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    teacher = relationship("Teacher", back_populates="papers")

    # 索引
    __table_args__ = (Index("idx_teacher", "teacher_id"),)

    def __repr__(self):
        return f"<ExamPaper(id={self.id}, title={self.title}, status={self.status})>"


class ReviewDiscussion(Base):
    """审核讨论记录表 (AutoGen对话记录)"""

    __tablename__ = "review_discussions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    question_id = Column(String(36), ForeignKey("questions.id"), comment="题目ID")
    paper_id = Column(String(36), ForeignKey("exam_papers.id"), comment="试卷ID")
    discussion_type = Column(String(50), comment="讨论类型(quality_review)")
    agent_messages = Column(JSON, comment="Agent消息列表")
    consensus_result = Column(JSON, comment="讨论结果")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    question = relationship("Question")
    paper = relationship("ExamPaper")

    def __repr__(self):
        return f"<ReviewDiscussion(id={self.id}, type={self.discussion_type})>"


class GenerationSession(Base):
    """生成会话表"""

    __tablename__ = "generation_sessions"

    session_id = Column(String(36), primary_key=True, default=generate_uuid)
    status = Column(String(50), default="in_progress", comment="状态(in_progress/completed/failed)")
    requirement = Column(JSON, comment="用户需求")
    workflow_state = Column(JSON, comment="Workflow状态")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    expires_at = Column(DateTime, comment="过期时间")

    # 索引
    __table_args__ = (Index("idx_status", "status"),)

    def __repr__(self):
        return f"<GenerationSession(id={self.session_id}, status={self.status})>"


class Teacher(Base):
    """教师表"""

    __tablename__ = "teachers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), comment="姓名")
    email = Column(String(200), unique=True, comment="邮箱")
    password_hash = Column(String(255), comment="密码哈希")
    preferences = Column(JSON, comment="偏好设置")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    papers = relationship("ExamPaper", back_populates="teacher")

    def __repr__(self):
        return f"<Teacher(id={self.id}, name={self.name}, email={self.email})>"
