FROM python:3.13-alpine

WORKDIR /app

# Копируем requirements.txt отдельно для лучшего кэширования слоев
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Теперь копируем все остальные файлы
COPY __init__.py connection_api.py faiss_module.py llm_module.py postgres_module.py ./

# Открываем порт для FastAPI
EXPOSE 8000

# Запускаем приложение
CMD ["uvicorn", "connection_api:app", "--host", "0.0.0.0", "--port", "8000"]