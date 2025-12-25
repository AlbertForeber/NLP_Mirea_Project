FROM python:3.13-alpine

WORKDIR /app

COPY __init__.py .
COPY messages_handlers ./messages_handlers
COPY controllers ./controllers
COPY requirements.txt .
COPY middleware.py .
COPY bot.py .
COPY keyboards ./keyboards
ENV PYTHONPATH=/app:$PYTHONPATH
ENV BOT_TOKEN="8119060681:AAFt0-AiNxUVihxhaSrBOBGU_ijST4nTSkY"
ENV dns="postgresql://postgres:postgres@host.docker.internal:5432/books"
# подключение к локальной бд

# "postgresql://nlp_user:farshIzum@postgres_db:5432/mind_org"

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "-u", "bot.py"]