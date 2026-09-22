from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError
from elasticsearch.exceptions import TransportError
import os

app = FastAPI(title="Document Search Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
INDEX_NAME = "documents"

es = Elasticsearch(ES_HOST)

SEED_DOCUMENTS = [
    {"id": "1", "text": "India, officially the Republic of India, is a country in South Asia. It is the seventh-largest country by area, the most populous country as of June 2023, and from the time of its independence in 1947, the world's most populous democracy."},
    {"id": "2", "text": "India is a federal union comprising 28 states and 8 union territories. The states and union territories are further subdivided into districts and smaller administrative divisions."},
    {"id": "3", "text": "The Indian economy is the world's fifth-largest by nominal GDP and the third-largest by purchasing power parity (PPP). India is a newly industrialized country and a major exporter of software services, textiles, and chemicals."},
    {"id": "4", "text": "India's culture is among the world's oldest, dating back over 4,500 years. The country is the birthplace of Hinduism, Buddhism, Jainism, and Sikhism, and has also been home to Islam, Christianity, Judaism, and Zoroastrianism for centuries."},
]

INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "text": {"type": "text"},
        }
    }
}


def wait_for_es(max_retries: int = 30, delay: float = 1.0) -> bool:
    import time
    for _ in range(max_retries):
        try:
            if es.ping():
                return True
        except ESConnectionError:
            pass
        time.sleep(delay)
    return False


def initialize_index():
    if not wait_for_es():
        raise RuntimeError("Elasticsearch not available after retries")

    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
        for doc in SEED_DOCUMENTS:
            es.index(index=INDEX_NAME, id=doc["id"], body={"text": doc["text"]}, refresh=True)
    else:
        existing_mapping = es.indices.get_mapping(index=INDEX_NAME)
        props = existing_mapping[INDEX_NAME]["mappings"].get("properties", {})
        if "id" not in props or "text" not in props:
            raise RuntimeError(f"Index '{INDEX_NAME}' exists but has unexpected mapping")


initialize_index()


@app.get("/")
async def root():
    return {"message": "Backend is running. Use POST /documents to insert, GET /documents/search?q=... to search."}


@app.post("/documents")
async def insert_document(doc: dict):
    text = doc.get("text")
    if not isinstance(text, str):
        raise HTTPException(status_code=400, detail="Field 'text' is required and must be a string")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Field 'text' cannot be empty")

    try:
        response = es.index(index=INDEX_NAME, body={"text": text}, refresh=True)
        return {"message": "Document inserted", "id": response["_id"]}
    except ESConnectionError:
        raise HTTPException(status_code=503, detail="Elasticsearch unavailable")
    except TransportError as e:
        raise HTTPException(status_code=500, detail=f"Elasticsearch error: {e.error}")


@app.get("/documents/search")
async def search_documents(q: str = Query(..., min_length=1, description="Search query")):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty")

    try:
        response = es.search(
            index=INDEX_NAME,
            body={
                "query": {"match": {"text": q}},
                "size": 10,
            }
        )
        hits = response["hits"]["hits"]
        results = [
            {
                "id": hit["_id"],
                "text": hit["_source"]["text"],
                "score": hit["_score"],
            }
            for hit in hits
        ]
        return {"query": q, "total": response["hits"]["total"]["value"], "results": results}
    except ESConnectionError:
        raise HTTPException(status_code=503, detail="Elasticsearch unavailable")
    except TransportError as e:
        raise HTTPException(status_code=500, detail=f"Elasticsearch error: {e.error}")