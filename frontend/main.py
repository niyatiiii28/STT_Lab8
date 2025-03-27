from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

BACKEND_URL = "http://backend:8000"  # Backend container name

html = """
<!DOCTYPE html>
<html>
<head><title>FastAPI Frontend</title></head>
<body>
    <form action="/insert/" method="post">
        <input type="text" name="text" placeholder="Enter text">
        <button type="submit">Insert</button>
    </form>
    <form action="/get/" method="get">
        <button type="submit">Get Best Document</button>
    </form>
    <p>{message}</p>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return html.format(message="")

@app.post("/insert/")
async def insert_document(text: str = Form(...)):
    response = requests.post(f"{BACKEND_URL}/insert/", json={"text": text})
    return html.format(message=response.json())
  
@app.get("/get/")
async def get_document():
    response = requests.get(f"{BACKEND_URL}/get/")
    return html.format(message=response.json())
