import json
import logging
from typing import Literal
from pydantic import BaseModel, ValidationError, field_validator
from llm_client import get_groq_completion

logger = logging.getLogger(__name__)


class BANTResult(BaseModel):
    budget: str = "Unknown"
    authority: str = "Unknown"
    need: str = "Unknown"
    timeline: str = "Unknown"
    score: int = 0
    category: Literal["Hot", "Warm", "Cold"] = "Cold"

    @field_validator('score')
    @classmethod
    def clamp_score(cls, v):
        return max(0, min(100, v))


def extract_bant_and_score(conversation_history: str) -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert lead qualifier. Read the following conversation and extract "
                "BANT details (Budget, Authority, Need, Timeline). "
                "Also provide a score from 0 to 100 based on their intent to buy. "
                "Output ONLY a valid JSON object with keys: 'budget', 'authority', 'need', "
                "'timeline', 'score' (integer 0-100), 'category' (must be exactly Hot, Warm, or Cold). "
                "Do not include markdown code fences."
            )
        },
        {
            "role": "user",
            "content": conversation_history
        }
    ]

    response_text = get_groq_completion(messages, response_format={"type": "json_object"})

    try:
        raw = response_text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        result = BANTResult(**parsed)
        return result.model_dump()
    except (json.JSONDecodeError, ValidationError, Exception) as e:
        logger.warning(
            "BANT parse failure — falling back to Cold/0. "
            f"Error: {e!r} | Raw response: {response_text!r}"
        )
        return BANTResult().model_dump()
