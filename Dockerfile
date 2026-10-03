FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DB_PATH=/data/learning.db PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 학습 기록(SQLite)은 볼륨에 둔다 — 컨테이너를 다시 만들어도 유지된다
VOLUME ["/data"]
EXPOSE 8000
CMD gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2 --timeout 60
