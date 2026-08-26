import json
import os
import re
from llm_client import get_groq_completion
from data_parser import load_enquiries, get_insights_summary

def load_brochure():
    brochure_path = "document/project_brochure.md"
    if os.path.exists(brochure_path):
        with open(brochure_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Brochure not found."

def check_c1_hallucination(ad_copy_text: str, brochure_content: str) -> bool:
    messages = [
        {
            "role": "system",
            "content": "You are a strict compliance judge. Determine if ANY amenity or numerical claim in the provided ad copy is NOT explicitly stated in the provided brochure. Output ONLY a JSON object with key 'hallucination_found' (boolean: true if a claim is unsupported, false if all claims are supported)."
        },
        {
            "role": "user",
            "content": f"Brochure:\n{brochure_content}\n\nAd Copy:\n{ad_copy_text}"
        }
    ]
    response = get_groq_completion(messages, max_tokens=150)
    try:
        json_match = re.search(r'\{[\s\S]+\}', response)
        raw = json_match.group(0) if json_match else response
        data = json.loads(raw)
        return data.get("hallucination_found", True)
    except Exception:
        return True

def run_compliance_engine(ad_json, brochure_content):
    full_text = json.dumps(ad_json).lower()
    report = []
    
    # Extract all copies for length checking
    meta_headlines = []
    google_headlines = []
    google_descs = []
    
    for p in ad_json.get("personas", []):
        meta = p.get("meta_ad", {})
        google = p.get("google_ad", {})
        if "headline" in meta: meta_headlines.append(meta["headline"])
        if "headline" in google: google_headlines.append(google["headline"])
        if "description" in google: google_descs.append(google["description"])
        
    # C1: Hallucination check (LLM-as-judge)
    print("Running C1 Hallucination check...")
    hallucination = check_c1_hallucination(json.dumps(ad_json), brochure_content)
    if hallucination:
        report.append("❌ **C1**: LLM-as-judge found unsupported claims or amenities not in the brochure.")
    else:
        report.append("✅ **C1**: All numbers and amenities trace back to the brochure.")
        
    # C2: No proposed stated as existing
    if "proposed" in full_text or "upcoming" in full_text:
        report.append("❌ **C2**: Used the word 'proposed' or 'upcoming'. (Rule: Must not state proposed amenities as existing, avoid ambiguous words).")
    else:
        report.append("✅ **C2**: No proposed amenities incorrectly stated as existing.")
        
    # C3: RERA Registration Number present
    if "prm/ka/rera/1251/446/pr/2026/007841" in full_text.replace(" ", ""):
        report.append("✅ **C3**: RERA Registration number present.")
    else:
        report.append("❌ **C3**: Missing RERA Registration number (PRM/KA/RERA/1251/446/PR/2026/007841).")
        
    # C4: QR Code present
    if "[qr code]" in full_text:
        report.append("✅ **C4**: QR Code placeholder present.")
    else:
        report.append("❌ **C4**: Missing [QR Code] placeholder.")
        
    # C5: Authority website URL present
    if "rera.karnataka.gov.in" in full_text:
        report.append("✅ **C5**: Authority website URL present.")
    else:
        report.append("❌ **C5**: Missing authority website URL (rera.karnataka.gov.in).")
        
    # C6: No targeting referencing religion/community
    blacklist = ['hindu', 'muslim', 'christian', 'jain', 'temple', 'mosque', 'church', 'caste']
    found = [word for word in blacklist if word in full_text]
    if found:
        report.append(f"❌ **C6**: Community/Religion terms found: {', '.join(found)}")
    else:
        report.append("✅ **C6**: No targeting or copy referencing religion or community.")
        
    # C7: Character limits met
    limit_failures = []
    for hl in meta_headlines:
        if len(hl) > 40: limit_failures.append(f"Meta Headline too long ({len(hl)} > 40)")
    for hl in google_headlines:
        if len(hl) > 30: limit_failures.append(f"Google Headline too long ({len(hl)} > 30)")
    for desc in google_descs:
        if len(desc) > 90: limit_failures.append(f"Google Desc too long ({len(desc)} > 90)")
        
    if limit_failures:
        report.append(f"❌ **C7**: Character limit violations: {', '.join(limit_failures)}")
    else:
        report.append("✅ **C7**: Character limits met per platform placement.")
        
    # C8: Visual asset is from approved library
    if "[image:" in full_text:
        report.append("✅ **C8**: Visual asset placeholder from library present.")
    else:
        report.append("❌ **C8**: Missing [Image: Approved_Asset] placeholder.")
        
    return "\n".join(report)

def analyze_and_segment(data_summary: str):
    brochure_content = load_brochure()
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert Real Estate Marketing AI. Analyze historical enquiry data for Catchment A. "
                "Generate EXACTLY 2 buyer personas. Keep all text extremely concise (max 1 sentence per field) to fit within strict token limits. "
                "You MUST output ONLY a valid JSON object with the following structure:\n"
                "{\n"
                "  \"insights\": \"Demand insights text\",\n"
                "  \"personas\": [\n"
                "    {\n"
                "      \"name\": \"Persona Name\",\n"
                "      \"description\": \"Description\",\n"
                "      \"targeting\": \"Targeting details\",\n"
                "      \"meta_ad\": {\"headline\": \"(Max 40 chars)\", \"primary_text\": \"...\", \"image_placeholder\": \"[Image: Approved_Asset_Name]\"},\n"
                "      \"google_ad\": {\"headline\": \"(Max 30 chars)\", \"description\": \"(Max 90 chars)\"}\n"
                "    }\n"
                "  ]\n"
                "}\n"
                "CRITICAL COMPLIANCE REQUIREMENTS (EVERY AD COPY MUST INCLUDE THESE):\n"
                "1. Include the exact RERA Number: PRM/KA/RERA/1251/446/PR/2026/007841\n"
                "2. Include the exact URL: rera.karnataka.gov.in\n"
                "3. Include the exact text: [QR Code]\n"
                "4. Do NOT mention any religion, temple, or community.\n"
                "5. Stick strictly to the character limits for Meta and Google.\n"
                "Use ONLY the numbers provided in the historical data for personas. Use the project brochure for ad copy amenities and pricing."
                f"\n\nProject Brochure (Summary):\n{brochure_content[:300]}..."
            )
        },
        {
            "role": "user",
            "content": f"Historical enquiries:\n{data_summary}\n\nGenerate JSON."
        }
    ]
    
    print("Generating personas and ad copy via LLM...")
    # Don't use response_format=json_object — prompt is too large and causes Groq 400 errors.
    # Instead, let the model output free text and extract the JSON block via regex.
    response = get_groq_completion(messages, max_tokens=2500)
    
    # Extract JSON block from response (handles ```json ... ``` or bare {...})
    json_match = re.search(r'```json\s*([\s\S]+?)\s*```', response)
    if json_match:
        raw_json = json_match.group(1)
    else:
        # Try to find a bare JSON object
        brace_match = re.search(r'(\{[\s\S]+\})', response)
        raw_json = brace_match.group(1) if brace_match else response

    try:
        print(f"RAW JSON REPR: {repr(raw_json)[:500]}...")
        ad_json = json.loads(raw_json)
    except Exception as e:
        # JSON extraction failed — show the raw markdown response directly
        return f"### AI Response Error\nThe AI failed to generate the required format.\n\n**Raw Output:**\n```text\n{response}\n```\n\n---\n> ⚠️ Compliance checks skipped (could not parse JSON). Error: {e}"
        
    print("Running compliance checks...")
    compliance_report = run_compliance_engine(ad_json, brochure_content)
    
    # Format to markdown
    md = f"## Key Demand Insights\n{ad_json.get('insights', '')}\n\n## Buyer Personas & Ad Copy\n"
    for p in ad_json.get("personas", []):
        md += f"### {p.get('name')}\n"
        md += f"**Description:** {p.get('description')}\n\n"
        md += f"**Targeting:** {p.get('targeting')}\n\n"
        meta = p.get("meta_ad", {})
        md += f"**Meta Ad:**\n- **Headline:** {meta.get('headline')}\n- **Primary Text:** {meta.get('primary_text')}\n- **Visual:** {meta.get('image_placeholder')}\n\n"
        google = p.get("google_ad", {})
        md += f"**Google Ad:**\n- **Headline:** {google.get('headline')}\n- **Description:** {google.get('description')}\n\n"
        
    md += "---\n## Compliance Report\n"
    md += compliance_report
    
    return md

if __name__ == "__main__":
    df = load_enquiries()
    summary = get_insights_summary(df)
    print(analyze_and_segment(summary))
