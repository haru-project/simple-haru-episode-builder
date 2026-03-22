FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

ENV PORT=8501

EXPOSE ${PORT}

HEALTHCHECK CMD python -c "import urllib.request, os; urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/_stcore/health')" || exit 1

ENTRYPOINT ["sh", "-c", "uv run streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0"]
