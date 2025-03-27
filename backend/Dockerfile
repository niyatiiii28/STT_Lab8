Use Python 3.10 as the base image
FROM python:3.10


WORKDIR /app


COPY . .


RUN pip install --no-cache-dir fastapi uvicorn elasticsearch==7.10.1


EXPOSE 8000


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
