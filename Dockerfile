FROM python:3.14-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml .
COPY . .

RUN pip install --upgrade pip && \
    pip install -e .

CMD ["/bin/bash"]