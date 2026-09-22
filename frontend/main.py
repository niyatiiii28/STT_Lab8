from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
import requests
import os

app = FastAPI(title="Document Search Frontend")

BACKEND_URL = os.getenv("BACKEND_URL", "http://doc-search-backend:8000")

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Document Search</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }}
        h1 {{ color: #333; }}
        .section {{ margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
        .section h2 {{ margin-top: 0; }}
        label {{ display: block; margin-bottom: 8px; font-weight: bold; }}
        input[type="text"] {{ width: 100%; padding: 10px; font-size: 16px; box-sizing: border-box; margin-bottom: 10px; }}
        button {{ padding: 10px 20px; font-size: 16px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 3px; }}
        button:hover {{ background: #0056b3; }}
        .message {{ margin-top: 15px; padding: 15px; border-radius: 3px; }}
        .success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
        .error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
        .info {{ background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }}
        .results {{ margin-top: 20px; }}
        .result-item {{ padding: 15px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 3px; background: #f9f9f9; }}
        .result-text {{ margin-bottom: 8px; }}
        .result-meta {{ font-size: 13px; color: #666; }}
        .score {{ font-weight: bold; color: #007bff; }}
    </style>
</head>
<body>
    <h1>Document Search System</h1>

    <div class="section">
        <h2>Search Documents</h2>
        <form action="/search" method="get">
            <label for="q">Search Query:</label>
            <input type="text" name="q" id="q" placeholder="Enter search terms..." value="{query}" required>
            <button type="submit">Search</button>
        </form>
        {search_message}
        {search_results}
    </div>

    <div class="section">
        <h2>Insert Document</h2>
        <form action="/insert" method="post">
            <label for="text">Document Text:</label>
            <input type="text" name="text" id="text" placeholder="Enter document text..." required>
            <button type="submit">Insert</button>
        </form>
        {insert_message}
    </div>
</body>
</html>
"""

RESULT_ITEM = """
<div class="result-item">
    <div class="result-text">{text}</div>
    <div class="result-meta">ID: {id} | Score: <span class="score">{score:.4f}</span></div>
</div>
"""


def render_page(query: str = "", search_message: str = "", search_results: str = "", insert_message: str = ""):
    return HTML.format(
        query=query,
        search_message=search_message,
        search_results=search_results,
        insert_message=insert_message,
    )


def make_message(text: str, msg_type: str = "info") -> str:
    if not text:
        return ""
    return f'<div class="message {msg_type}">{text}</div>'


def make_results(results: list, total: int, query: str) -> str:
    if not results:
        return make_message(f'No results found for "{query}".', "info")

    items = "".join(
        RESULT_ITEM.format(id=r["id"], text=r["text"], score=r["score"])
        for r in results
    )
    return f'<div class="results"><p>Found {total} result(s) for "{query}":</p>{items}</div>'


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if request.url.path == "/search":
        return HTMLResponse(render_page(search_message=make_message("Please enter a search query.", "error")))
    if request.url.path == "/insert":
        return HTMLResponse(render_page(insert_message=make_message("Document text cannot be empty.", "error")))
    return HTMLResponse(render_page(search_message=make_message("Invalid request.", "error")))


@app.get("/", response_class=HTMLResponse)
async def home():
    return render_page()


@app.get("/search", response_class=HTMLResponse)
async def search(q: str = Query(default="")):
    if not q.strip():
        return render_page(query=q, search_message=make_message("Please enter a search query.", "error"))

    try:
        resp = requests.get(f"{BACKEND_URL}/documents/search", params={"q": q}, timeout=10)
    except requests.exceptions.ConnectionError:
        return render_page(query=q, search_message=make_message("Backend unavailable. Please try again later.", "error"))
    except requests.exceptions.Timeout:
        return render_page(query=q, search_message=make_message("Search request timed out.", "error"))
    except requests.exceptions.RequestException as e:
        return render_page(query=q, search_message=make_message(f"Search failed: {e}", "error"))

    if resp.status_code == 200:
        data = resp.json()
        results_html = make_results(data.get("results", []), data.get("total", 0), q)
        return render_page(query=q, search_results=results_html)
    elif resp.status_code == 400:
        detail = resp.json().get("detail", "Invalid query")
        return render_page(query=q, search_message=make_message(f"Invalid search: {detail}", "error"))
    else:
        return render_page(query=q, search_message=make_message(f"Search failed: {resp.text}", "error"))


@app.post("/insert", response_class=HTMLResponse)
async def insert(text: str = Form(default="")):
    if not text.strip():
        return render_page(insert_message=make_message("Document text cannot be empty.", "error"))

    try:
        resp = requests.post(f"{BACKEND_URL}/documents", json={"text": text}, timeout=10)
    except requests.exceptions.ConnectionError:
        return render_page(insert_message=make_message("Backend unavailable. Please try again later.", "error"))
    except requests.exceptions.Timeout:
        return render_page(insert_message=make_message("Insert request timed out.", "error"))
    except requests.exceptions.RequestException as e:
        return render_page(insert_message=make_message(f"Insert failed: {e}", "error"))

    if resp.status_code == 200:
        data = resp.json()
        return render_page(insert_message=make_message(f'Document inserted successfully! ID: {data.get("id")}', "success"))
    elif resp.status_code == 400:
        detail = resp.json().get("detail", "Invalid document")
        return render_page(insert_message=make_message(f"Insert failed: {detail}", "error"))
    else:
        return render_page(insert_message=make_message(f"Insert failed: {resp.text}", "error"))