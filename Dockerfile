FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# La base SQLite vit dans /app/data : monte un volume dessus pour que les
# sorties survivent aux redéploiements (ex. `-v botdata:/app/data`).
CMD ["python", "-m", "bot.main"]
