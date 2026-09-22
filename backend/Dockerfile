FROM python:3.10-slim

WORKDIR /app

COPY main.py .

RUN pip install --no-cache-dir fastapi uvicorn elasticsearch==7.10.1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]