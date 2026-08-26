from segmentation_agent import load_brochure
from llm_client import get_groq_completion
brochure_content = load_brochure()
messages = [
    {
        "role": "system",
        "content": (
            "You are an expert Real Estate Marketing AI Agent. Your goal is to analyze historical "
            "enquiry data for Catchment A, generate 3-5 buyer personas, and provide ad copy for Meta and Google. "
            "You MUST output ONLY a valid JSON object with the following structure:\n"
            "{\n  \"insights\": \"Demand insights text\",\n  \"personas\": [\n    {\n      \"name\": \"Persona Name\",\n      \"description\": \"Description\",\n      \"targeting\": \"Targeting details\",\n      \"meta_ad\": {\"headline\": \"(Max 40 chars)\", \"primary_text\": \"...\", \"image_placeholder\": \"[Image: Approved_Asset_Name]\"},\n      \"google_ad\": {\"headline\": \"(Max 30 chars)\", \"description\": \"(Max 90 chars)\"}\n    }\n  ]\n}\n"
            f"\n\nProject Brochure:\n{brochure_content}"
        )
    },
    {
        "role": "user",
        "content": "Historical enquiries:\nEmpty\n\nGenerate JSON."
    }
]
response = get_groq_completion(messages, max_tokens=2500)
print("RAW LLM RESPONSE:")
print(response)
