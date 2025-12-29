# 使用 Python 3.13 作为基础镜像
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install --no-cache-dir uv

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY requirements.txt ./
COPY server.py ./
COPY tools/ ./tools/
COPY utils/ ./utils/
COPY prompts/ ./prompts/
COPY staticFiles/ ./staticFiles/

# 使用 uv 安装依赖
RUN uv sync --frozen

# 暴露端口（如果需要 HTTP 传输）
EXPOSE 8000

# 运行 MCP 服务器
CMD ["uv", "run", "fastmcp", "dev", "server.py"]

