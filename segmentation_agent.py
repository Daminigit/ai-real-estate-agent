import json
import os
from llm_client import get_groq_completion
from data_parser import load_enquiries, get_insights_summary

def load_brochure():
    brochure_path = "document/project_brochure.md"
    if os.path.exists(brochure_path):
        with open(brochure_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Brochure not found."

def analyze_and_segment(data_summary: str):
    brochure_content = load_brochure()
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert Real Estate Marketing AI Agent. Your goal is to analyze historical "
                "enquiry data for a new residential project in Catchment A, generate 3-5 concrete buyer personas, "
                "and provide platform-specific targeting parameters (Meta, LinkedIn, Google) and ad copy for each. "
                "Use the provided project brochure to ensure the ad copy highlights actual project amenities, pricing, and USPs. "
                "Use ONLY the numbers provided in the historical data for the personas. Do not calculate, convert, or invent any statistics. "
                "Your job is interpretation and marketing implications, not math."
                f"\n\nProject Brochure:\n{brochure_content}"
            )
        },
        {
            "role": "user",
            "content": f"Here is the summary of historical enquiries:\n{data_summary}\n\nPlease provide:\n1. Key Demand Insights\n2. 3-5 Buyer Personas\n3. Targeting Parameters & Ad Copy for Meta, LinkedIn, and Google."
        }
    ]
    return get_groq_completion(messages)

if __name__ == "__main__":
    df = load_enquiries()
    summary = get_insights_summary(df)
    print("Generating segmentation report (this may take a moment)...")
    print(analyze_and_segment(summary))
