"""
Prometheus监控指标模块
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from fastapi import Response
from app.core.config import settings

# ==================== LLM调用指标 ====================
llm_requests_total = Counter(
    'llm_requests_total',
    'Total number of LLM API requests',
    ['provider', 'model', 'status']
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM API request duration in seconds',
    ['provider', 'model'],
    buckets=(1, 5, 10, 30, 60, 120, 300)
)

llm_tokens_used = Counter(
    'llm_tokens_used_total',
    'Total tokens used in LLM requests',
    ['provider', 'model', 'type']  # type: prompt/completion
)

# ==================== Agent指标 ====================
agent_task_total = Counter(
    'agent_task_total',
    'Total number of agent tasks',
    ['agent_name', 'status']
)

agent_task_duration_seconds = Histogram(
    'agent_task_duration_seconds',
    'Agent task duration in seconds',
    ['agent_name'],
    buckets=(1, 5, 10, 30, 60, 120, 300)
)

# ==================== Workflow指标 ====================
workflow_execution_total = Counter(
    'workflow_execution_total',
    'Total number of workflow executions',
    ['workflow_name', 'status']
)

workflow_execution_duration_seconds = Histogram(
    'workflow_execution_duration_seconds',
    'Workflow execution duration in seconds',
    ['workflow_name'],
    buckets=(10, 30, 60, 120, 300, 600)
)

workflow_node_duration_seconds = Histogram(
    'workflow_node_duration_seconds',
    'Workflow node execution duration in seconds',
    ['workflow_name', 'node_name'],
    buckets=(1, 5, 10, 30, 60, 120)
)

# ==================== 题目生成指标 ====================
questions_generated_total = Counter(
    'questions_generated_total',
    'Total number of questions generated',
    ['subject', 'question_type', 'difficulty']
)

questions_approved_total = Counter(
    'questions_approved_total',
    'Total number of questions approved by review',
    ['subject', 'question_type']
)

questions_rejected_total = Counter(
    'questions_rejected_total',
    'Total number of questions rejected by review',
    ['subject', 'question_type', 'reason']
)

paper_generation_total = Counter(
    'paper_generation_total',
    'Total number of papers generated',
    ['subject', 'grade', 'status']
)

# ==================== RAG指标 ====================
rag_search_total = Counter(
    'rag_search_total',
    'Total number of RAG searches',
    ['collection', 'status']
)

rag_search_duration_seconds = Histogram(
    'rag_search_duration_seconds',
    'RAG search duration in seconds',
    ['collection'],
    buckets=(0.1, 0.5, 1, 2, 5, 10)
)

rag_duplicate_found_total = Counter(
    'rag_duplicate_found_total',
    'Total number of duplicate questions found',
    ['subject']
)

# ==================== 系统指标 ====================
active_generation_sessions = Gauge(
    'active_generation_sessions',
    'Number of active generation sessions'
)

cache_hits_total = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

# ==================== API指标 ====================
api_requests_total = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10)
)


def metrics_endpoint():
    """Prometheus metrics endpoint"""
    if not settings.enable_metrics:
        return Response(content="Metrics disabled", status_code=404)

    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )