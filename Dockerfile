# Используем официальный Python-образ
FROM python:3.11.0-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем локальный код в контейнер
COPY . .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Указываем команду для запуска бота
CMD ["python", "bot.py"]
