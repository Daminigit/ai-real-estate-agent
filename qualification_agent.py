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


def extract_bant_and_score(conversation_history: str, lead_info: dict = None) -> dict:
    lead_context = ""
    if lead_info:
        lead_context = (
            f"\n\nLead Profile (from initial capture form):\n"
            f"- Name: {lead_info.get('name', 'Unknown')}\n"
            f"- Budget: ₹{lead_info.get('budget_min')}L - ₹{lead_info.get('budget_max')}L\n"
            f"- Locality: {lead_info.get('locality', 'Unknown')}\n"
            f"- Profession: {lead_info.get('profession', 'Unknown')}\n"
        )
        
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert lead qualifier. Read the following conversation and extract "
                "BANT details (Budget, Authority, Need, Timeline). "
                "Also provide a score from 0 to 100 based on their intent to buy. "
                "Note: The user may have already provided their budget or details in the Lead Profile below. Use it to inform your scoring. "
                "Output ONLY a valid JSON object with keys: 'budget', 'authority', 'need', "
                "'timeline', 'score' (integer 0-100), 'category' (must be exactly Hot, Warm, or Cold). "
                "Do not include markdown code fences."
                f"{lead_context}"
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
