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

    @field_validator('budget', 'authority', 'need', 'timeline', mode='before')
    @classmethod
    def cast_to_string(cls, v):
        if v is None:
            return "Unknown"
        return str(v)

    @field_validator('score')
    @classmethod
    def clamp_score(cls, v):
        return max(0, min(100, int(v)))


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
                "You are an expert real estate lead qualifier. Read the following conversation and extract "
                "BANT details (Budget, Authority, Need, Timeline).\n\n"
                "Also determine an overall lead score (integer 0-100) and category (must be exactly one of: Hot, Warm, or Cold) based on this logic:\n"
                "1. **Hot (Score 75-100)**: Lead shows strong purchase intent. They have a clear budget that matches the project (starts at ~80L-90L), "
                "clear need (e.g. 2BHK or 3BHK for self-use or investment), decision-making authority, and an immediate or short timeline (e.g., this month, 2-3 months, urgent relocation). "
                "Crucially, any lead requesting or confirming a site visit this weekend, tomorrow, etc. MUST be classified as **Hot** with a score of 80+.\n"
                "2. **Warm (Score 40-74)**: Lead shows genuine interest, but has minor friction, e.g., needs to discuss with spouse, NRI visiting India in 8 months, "
                "timeline is 3-6 months, or needs to check the brochure first before booking a visit.\n"
                "3. **Cold (Score 0-39)**: Lead is not interested, just browsing/exploring, looking for rentals only, or budget is completely unrealistic/too tight "
                "for the project (e.g., tight 85L for a 3BHK starting at 1.1Cr, or left after brief/no answers).\n\n"
                "Output ONLY a valid JSON object with keys: 'budget', 'authority', 'need', 'timeline', 'score', and 'category'. "
                "Do not include markdown code fences or any surrounding text. "
                "For BANT fields, summarize what you know or set to 'Unknown' if not mentioned."
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
        import re
        # Extract json block using regex to ignore any conversational text
        json_match = re.search(r'(\{[\s\S]+\})', response_text)
        raw = json_match.group(1) if json_match else response_text
        parsed = json.loads(raw)
        return BANTResult(**parsed).model_dump()
    except (json.JSONDecodeError, ValidationError, Exception) as e:
        logger.warning(
            "BANT parse failure — falling back to Cold/0. "
            f"Error: {e!r} | Raw response: {response_text!r}"
        )
        return BANTResult().model_dump()

