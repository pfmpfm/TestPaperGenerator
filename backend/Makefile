.PHONY: test test-fast test-cov test-e2e lint format clean help

help:
	@echo "可用命令:"
	@echo "  make test       - 运行所有测试"
	@echo "  make test-fast  - 运行快速测试（跳过慢速测试）"
	@echo "  make test-cov   - 运行测试并生成覆盖率报告"
	@echo "  make test-e2e   - 运行端到端测试（包含真实LLM调用）"
	@echo "  make lint       - 运行代码检查"
	@echo "  make format     - 格式化代码"
	@echo "  make clean      - 清理临时文件"

test:
	pytest tests/ -v

test-fast:
	pytest tests/ -v -m "not slow"

test-cov:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-e2e:
	pytest tests/ -v --run-e2e

lint:
	ruff check app/ tests/
	mypy app/

format:
	black app/ tests/
	ruff check --fix app/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf .ruff_cache