FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN git clone https://tangled.org/liamegan.com/helios /helios && \
    git clone https://tangled.org/liamegan.com/luna /luna

WORKDIR /app

COPY .python-version pyproject.toml uv.lock ./

RUN uv python install
RUN uv sync --no-dev --no-install-project

COPY . .

RUN uv sync --no-dev

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uv", "run", "gunicorn", "app.main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
