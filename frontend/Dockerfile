FROM python:3.10-slim

WORKDIR /app

COPY main.py .

RUN pip install --no-cache-dir fastapi uvicorn requests python-multipart

EXPOSE 9567

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9567"]