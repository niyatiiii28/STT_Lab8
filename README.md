# Document Search System

A containerized document retrieval system with a FastAPI frontend, FastAPI backend, and Elasticsearch 7.10.1. Demonstrates Docker networking, persistent volumes, and service-to-service communication in a minimal architecture.

---

## Architecture

```mermaid
flowchart LR
    Browser[Browser] -->|HTTP :9567| Frontend[Frontend FastAPI\n:9567]
    Frontend -->|Docker network\ndoc-search-net| Backend[Backend FastAPI\n:8000]
    Backend -->|Docker network\ndoc-search-net| Elasticsearch[Elasticsearch 7.10.1\n:9200]
    Elasticsearch -->|Docker volume| Volume[(es-data volume)]
```

**Request Flow:**
```
Browser (port 9567)
    ↓
Frontend (FastAPI, port 9567) — public, user-facing
    ↓ HTTP (internal Docker network)
Backend (FastAPI, port 8000) — internal only, no host exposure
    ↓ HTTP (internal Docker network)
Elasticsearch (port 9200) — internal only, no host exposure
    ↓
Persistent Docker volume (es-data)
```

### Why This Architecture?

- **Frontend is public (port 9567)**: The only service users interact with. It serves HTML and proxies API calls to the backend.
- **Backend is internal (port 8000)**: Not exposed to the host. Contains business logic, validation, and Elasticsearch communication. This reduces attack surface.
- **Elasticsearch is internal (port 9200)**: Not exposed to the host. Data store only accessible via backend.
- **Docker volume (`es-data`)**: Persists Elasticsearch data across container restarts/recreation. Verified by deleting and recreating the Elasticsearch container while retaining the volume — previously inserted documents survive.

---

## Technologies

| Component | Technology | Version |
|-----------|------------|---------|
| Frontend | FastAPI + Uvicorn | 0.141.x |
| Backend | FastAPI + Uvicorn | 0.141.x |
| Search Engine | Elasticsearch | 7.10.1 |
| Containerization | Docker | — |
| Networking | Custom bridge network (`doc-search-net`) | — |
| Persistence | Docker named volume (`es-data`) | — |
| Base Images | `python:3.10-slim`, `elasticsearch:7.10.1` | — |

---

## Repository Structure

```
.
├── backend/
│   ├── Dockerfile
│   └── main.py
├── elastic search/
│   └── Dockerfile
├── frontend/
│   ├── Dockerfile
│   └── main.py
├── .gitignore
├── README.md
└── STT_Lab8.pdf
```

---

## Backend API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/documents` | Insert a document (JSON: `{"text": "..."}`) |
| `GET` | `/documents/search?q=<query>` | Match query search, returns top 10 with scores |

### Request/Response Examples

**Insert Document**
```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"text": "Your document text here"}'
```
Response:
```json
{"message": "Document inserted", "id": "abc123"}
```

**Search Documents**
```bash
curl "http://localhost:8000/documents/search?q=India"
```
Response:
```json
{
  "query": "India",
  "total": 3,
  "results": [
    {"id": "1", "text": "...", "score": 1.25},
    {"id": "2", "text": "...", "score": 1.05}
  ]
}
```

**Error Responses**
- `400`: Invalid input (missing/empty `text` or `q`)
- `503`: Elasticsearch unavailable
- `500`: Elasticsearch transport error

---

## Elasticsearch Index & Mapping

**Index name:** `documents`

**Mapping:**
```json
{
  "mappings": {
    "properties": {
      "id": { "type": "keyword" },
      "text": { "type": "text" }
    }
  }
}
```

**Seed Documents:** 4 documents inserted on first initialization (first 4 paragraphs from Wikipedia "India" page). Document IDs are explicit (`"1"`, `"2"`, `"3"`, `"4"`). Subsequent inserts use Elasticsearch-generated IDs.

**Idempotent Initialization:** On startup, backend waits for Elasticsearch (30 retries, 1s delay), creates index with mapping if missing, seeds documents, and validates existing mapping matches expected schema.

---

## Docker Networking

- **Network:** `doc-search-net` (custom bridge)
- **Containers on network:** `doc-search-frontend`, `doc-search-backend`, `doc-search-es`
- **Published ports:** Only frontend port 9567 → host port 9567
- **Internal ports:** Backend 8000, Elasticsearch 9200/9300 (not published)

Create network:
```bash
docker network create doc-search-net
```

---

## Persistent Volume & Persistence Experiment

**Volume:** `es-data` (Docker named volume, local driver)

**Mount point in Elasticsearch container:** `/usr/share/elasticsearch/data`

**Verification performed:**
1. Inserted documents via frontend
2. Stopped and removed Elasticsearch container (`docker rm -f doc-search-es`)
3. Recreated Elasticsearch container with same volume (`-v es-data:/usr/share/elasticsearch/data`)
4. Verified previously inserted documents were still searchable

This confirms data survives container lifecycle operations.

---

## Setup & Run

### Prerequisites
- Docker Engine 20+
- Docker network `doc-search-net`
- Docker volume `es-data`

### One-time Setup
```bash
docker network create doc-search-net
docker volume create es-data
```

### Build Images
```bash
docker build -t doc-search-backend:latest ./backend
docker build -t doc-search-frontend:latest ./frontend
docker build -t doc-search-elasticsearch:latest "./elastic search"
```

### Run Containers
```bash
# Elasticsearch (with persistent volume)
docker run -d \
  --name doc-search-es \
  --network doc-search-net \
  -v es-data:/usr/share/elasticsearch/data \
  doc-search-elasticsearch:latest

# Backend (internal only)
docker run -d \
  --name doc-search-backend \
  --network doc-search-net \
  -e ES_HOST=http://doc-search-es:9200 \
  doc-search-backend:latest

# Frontend (published to host port 9567)
docker run -d \
  --name doc-search-frontend \
  --network doc-search-net \
  -p 9567:9567 \
  -e BACKEND_URL=http://doc-search-backend:8000 \
  doc-search-frontend:latest
```

### Access
Open `http://localhost:9567` in browser.

---

## Example Usage

1. **Search existing documents:** Enter "India" → returns 3 seed documents with relevance scores
2. **Insert new document:** Enter text → click Insert → shows success with generated ID
3. **Search inserted document:** Query terms from your document → appears in results with score
4. **Empty search:** Submit blank query → "Please enter a search query." error
5. **Empty insert:** Submit blank text → "Document text cannot be empty." error

---

## Error Handling

| Layer | Errors Handled |
|-------|----------------|
| Frontend | Empty query, empty insert, backend connection error, backend timeout, backend HTTP errors (400, 500, 503), validation errors |
| Backend | Missing/invalid `text` field, empty `text`, Elasticsearch connection error (503), Elasticsearch transport error (500) |
| Elasticsearch | Startup retry logic (30 attempts), mapping validation on existing index |

---

## Reliability Testing

| Test | Result |
|------|--------|
| Frontend loads at :9567 | ✅ |
| Search seeded documents | ✅ |
| Insert via frontend → search inserted doc | ✅ |
| Direct backend API insert → search | ✅ |
| Empty query validation | ✅ |
| Empty insert validation | ✅ |
| Backend ES connection retry on startup | ✅ |
| ES container deletion + recreation with same volume | ✅ (data persisted) |
| Backend container restart | ✅ (reconnects to ES) |

---

## Docker Image Sizes

| Image | Size |
|-------|------|
| `doc-search-backend:latest` | 171 MB |
| `doc-search-frontend:latest` | 171 MB |
| `elasticsearch:7.10.1` | 811 MB |

*Sizes measured via `docker images`. Python slim base keeps FastAPI images reasonable. Elasticsearch dominates total footprint.*

---

## Design Decisions & Tradeoffs

| Decision | Rationale |
|----------|-----------|
| No docker-compose | Kept minimal per requirements; manual `docker run` demonstrates networking/volumes explicitly |
| Frontend serves HTML directly | No separate static file server; simple template rendering in FastAPI |
| Backend initializes index at import time | Simplifies startup; blocks until ES ready. Alternative: FastAPI lifespan handler — not adopted to avoid complexity |
| Elasticsearch 7.10.1 (not 8.x) | Lab requirement; avoids breaking changes in mapping syntax and security defaults |
| `python:3.10-slim` base | Smaller than full image; adequate for FastAPI + elasticsearch-py |
| Match query only | Lab requirement; no advanced queries (bool, phrase, fuzzy) implemented |
| CORS `allow_origins=["*"]` | Acceptable for lab; would restrict in production |
| No authentication/authorization | Out of scope for this system |

---

## Future Improvements

- Replace module-level `initialize_index()` with FastAPI `lifespan` handler
- Add structured logging (JSON) for observability
- Add health check endpoints for Docker `HEALTHCHECK`
- Implement pagination for search results beyond top 10
- Add integration tests (pytest + testcontainers)
- Use multi-stage Docker builds for smaller images
- Add request ID propagation for tracing
- Restrict CORS origins in production

---

