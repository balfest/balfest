FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /opt/balfest
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/

FROM base AS test
COPY requirements-dev.txt ./
RUN python -m pip install --no-cache-dir -r requirements-dev.txt
COPY tests/ ./tests/
RUN python -m unittest discover -s tests -v

FROM base AS runtime
RUN groupadd --system --gid 10001 balfest && useradd --system --uid 10001 --gid balfest --create-home balfest
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
