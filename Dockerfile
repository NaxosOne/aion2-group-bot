FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The SQLite database lives in /app/data: mount a volume there so events
# survive redeployments (e.g. `-v botdata:/app/data`).
CMD ["python", "-m", "bot.main"]
