FROM python:3.9-slim

WORKDIR /app
EXPOSE 8000
VOLUME ["/data"]

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
