# 可观测性与监控

## 概述

阶段4为系统添加了完整的可观测性支持，包括：
- **LangSmith追踪**：LLM调用和Agent对话追踪
- **Prometheus指标**：系统性能和业务指标
- **自动化测试**：单元测试、集成测试、端到端测试

## LangSmith集成

### 启用LangSmith

在`.env`文件中配置：

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=exam-generator
```

### 追踪内容

- LLM API调用（请求/响应/token使用）
- Agent任务执行
- Workflow节点执行
- RAG检索操作

## Prometheus监控

### 启用Metrics

在`.env`文件中配置：

```bash
ENABLE_METRICS=true
METRICS_PORT=9090
```

### 访问指标端点

```bash
curl http://localhost:8000/metrics
```

### 可用指标

#### LLM调用指标
- `llm_requests_total` - LLM请求总数（按provider/model/status）
- `llm_request_duration_seconds` - LLM请求耗时
- `llm_tokens_used_total` - Token使用总量（按类型：prompt/completion）

#### Agent指标
- `agent_task_total` - Agent任务总数
- `agent_task_duration_seconds` - Agent任务耗时

#### Workflow指标
- `workflow_execution_total` - Workflow执行总数
- `workflow_execution_duration_seconds` - Workflow执行耗时
- `workflow_node_duration_seconds` - Workflow节点耗时

#### 题目生成指标
- `questions_generated_total` - 生成题目总数
- `questions_approved_total` - 审核通过题目数
- `questions_rejected_total` - 审核拒绝题目数
- `paper_generation_total` - 生成试卷总数

#### RAG指标
- `rag_search_total` - RAG检索总数
- `rag_search_duration_seconds` - RAG检索耗时
- `rag_duplicate_found_total` - 发现重复题目数

#### API指标
- `api_requests_total` - API请求总数
- `api_request_duration_seconds` - API请求耗时

### Grafana可视化

1. 启动Prometheus：

```bash
# prometheus.yml
scrape_configs:
  - job_name: 'exam-generator'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

2. 在Grafana中添加Prometheus数据源

3. 导入预置Dashboard或自定义

## 自动化测试

### 测试结构

```
tests/
├── conftest.py           # 测试配置和fixtures
├── test_config.py        # 核心配置测试
├── test_llm_client.py    # LLM客户端测试
└── test_workflow.py      # Workflow集成测试
```

### 运行测试

```bash
cd backend

# 运行所有测试
make test

# 运行快速测试（跳过慢速测试）
make test-fast

# 运行测试并生成覆盖率报告
make test-cov

# 运行端到端测试（需要真实LLM）
make test-e2e
```

### 直接使用pytest

```bash
# 运行所有测试
pytest tests/ -v

# 跳过慢速测试
pytest tests/ -v -m "not slow"

# 运行特定测试文件
pytest tests/test_config.py -v

# 生成覆盖率报告
pytest tests/ -v --cov=app --cov-report=html
```

### 测试标记

- `@pytest.mark.slow` - 慢速测试（>5秒）
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.e2e` - 端到端测试（需要真实LLM）

### CI/CD

GitHub Actions配置位于`.github/workflows/ci.yml`，在每次push/PR时自动运行：

1. 代码检查（ruff）
2. 类型检查（mypy）
3. 单元测试
4. 覆盖率报告

## 开发工具

### 代码检查

```bash
make lint
```

### 代码格式化

```bash
make format
```

### 清理临时文件

```bash
make clean
```

## 性能分析

### 查看LLM调用统计

```bash
curl http://localhost:8000/metrics | grep llm_requests_total
```

### 查看Workflow执行时间

```bash
curl http://localhost:8000/metrics | grep workflow_execution_duration
```

### 查看题目生成质量

```bash
curl http://localhost:8000/metrics | grep questions_approved_total
curl http://localhost:8000/metrics | grep questions_rejected_total
```

## 故障排查

### LangSmith追踪未启用

检查`.env`配置：
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=<your-key>
```

### Metrics端点404

检查`.env`配置：
```bash
ENABLE_METRICS=true
```

### 测试失败

1. 检查环境变量是否正确
2. 检查依赖是否完整安装：`pip install -r requirements.txt`
3. 查看测试日志：`pytest tests/ -v -s`

## 最佳实践

### 1. 监控关键指标

- LLM调用成功率：`llm_requests_total{status="success"} / llm_requests_total`
- 题目审核通过率：`questions_approved_total / (questions_approved_total + questions_rejected_total)`
- Workflow平均耗时：`rate(workflow_execution_duration_seconds_sum[5m]) / rate(workflow_execution_duration_seconds_count[5m])`

### 2. 设置告警

- LLM调用失败率 > 10%
- Workflow执行时间 > 300s
- 题目审核通过率 < 50%

### 3. 定期查看LangSmith

- 分析LLM调用链路
- 优化Prompt效果
- 排查Agent执行问题

### 4. 持续测试

- 每次代码变更运行测试
- 定期运行端到端测试验证真实效果
- 监控测试覆盖率（目标>80%）
