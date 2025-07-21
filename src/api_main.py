# pip install fastapi uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from src.micro_saas_client import MicroSaasClient
from src.ai_evaluator import AIEvaluator
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class Req(BaseModel):
    api_key: str
    keyword: str
    limit: int = 10

@app.get("/")
async def root():
    return {"message": "Welcome to the Micro-SaaS Idea Scout API"}

@app.post("/evaluate")
async def evaluate(req: Req):
    client = MicroSaasClient()
    ideas  = await client.deep_extract_ideas(req.keyword, req.limit)
    evaluator = AIEvaluator(req.keyword)
    return evaluator.evaluate(ideas)
# uvicorn main:app --reload --port 8000