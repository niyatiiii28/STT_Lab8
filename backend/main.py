rom fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from elasticsearch import Elasticsearch
import os

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Backend is running! Use /insert/ and /get/ endpoints."}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
es = Elasticsearch(ES_HOST)
INDEX_NAME = "documents"


if not es.indices.exists(index=INDEX_NAME):
    es.indices.create(index=INDEX_NAME)

@app.post("/insert/")
async def insert_document(doc: dict):
    try:
        response = es.index(index=INDEX_NAME, body=doc)
        return {"message": "Document inserted", "id": response["_id"]}
    except Exception as e:
  raise HTTPException(status_code=500, detail=str(e))

@app.get("/get/")
async def get_best_document():
    try:
        response = es.search(index=INDEX_NAME, body={
            "query": {"match_all": {}},
            "size": 1,
            "sort": [{"_score": "desc"}]
        })
        if response["hits"]["hits"]:
            return response["hits"]["hits"][0]["_source"]
        return {"message": "No documents found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
