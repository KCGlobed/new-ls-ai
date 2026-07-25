import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI
import json

from app.core.config import settings

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
logger = structlog.get_logger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key)

class EvaluationRequest(BaseModel):
    original_answer: str
    user_answer: str

class EvaluationResponse(BaseModel):
    score: int
    explanation: str

@router.post("/score", response_model=EvaluationResponse)
async def evaluate_answer(request: EvaluationRequest):
    """
    Evaluates a user's answer against the original answer using an LLM.
    Scores out of 10 based on semantic meaning, ignoring phrasing differences.
    """
    try:
        system_prompt = (
            "You are an expert AI grader. Your task is to evaluate a user's answer against an original, "
            "correct answer. You must score the user's answer out of 10.\n"
            "Focus on SEMANTIC MEANING. If the user captures the core concept and meaning in their own words, "
            "they should get a high score (9-10). Do not penalize for different phrasing, grammar, or missing "
            "trivial details, as long as the fundamental meaning matches.\n\n"
            "You MUST return a JSON object with EXACTLY two fields:\n"
            '1. "score": an integer from 0 to 10.\n'
            '2. "explanation": a brief string explaining why this score was given.'
        )

        user_prompt = f"Original Answer:\n{request.original_answer}\n\nUser Answer:\n{request.user_answer}"

        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("No content returned from LLM")
            
        result = json.loads(content)
        
        return EvaluationResponse(
            score=int(result.get("score", 0)),
            explanation=str(result.get("explanation", "Failed to generate explanation."))
        )
    except Exception as e:
        logger.error("evaluation_failed", exc_info=True, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to evaluate answer")
