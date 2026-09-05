FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY demo ./demo
COPY artifacts/serving ./artifacts/serving
# src-layout 패키지(millie_rec) 설치. 이 줄이 없으면 uvicorn 이 모듈을 못 찾는다
RUN uv sync --frozen --no-dev
# USER 를 두지 않는다: Railway 볼륨(/data)은 root 소유라 비root 프로세스는 SQLite 를 쓸 수 없다
ENV DATA_DIR=/data
CMD ["sh", "-c", "uv run --no-sync uvicorn millie_rec.app.server:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
