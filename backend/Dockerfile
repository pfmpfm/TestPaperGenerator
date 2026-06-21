# ==================== 构建阶段 ====================
FROM python:3.11-slim as builder

WORKDIR /build

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ==================== 运行阶段 ====================
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖和中文字体
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fonts-wqy-zenhei \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -fv

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 设置 PATH 使用虚拟环境
ENV PATH="/opt/venv/bin:$PATH"

# 设置 matplotlib 缓存目录
ENV MPLCONFIGDIR=/tmp/matplotlib

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 创建必要的目录并设置权限
RUN mkdir -p /app/static/figures /app/logs \
    && chmod -R 755 /app/static \
    && chmod -R 755 /app/logs \
    && chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
