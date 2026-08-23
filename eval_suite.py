"""
BANT Qualification Agent — Evaluation Harness
Run: python eval_suite.py
Reports category accuracy and MAE on score vs hand-labelled ground truth.
"""
import json
import sys
from qualification_agent import extract_bant_and_score

# ── Ground Truth Transcripts ──────────────────────────────────────────────────
# Each entry: conversation text, expected BANT category, expected score (rough mid)
TRANSCRIPTS = [
    # HOT leads — explicit intent, clear budget, near timeline
    {
        "conversation": "user: I want to buy a 2BHK. My budget is around 95 lakhs.\nassistant: Great! Would you like to schedule a visit?\nuser: Yes, within this month if possible. I am the sole decision maker.",
        "expected_category": "Hot",
        "expected_score": 90,
    },
    {
        "conversation": "user: We need to move in by December. Our budget is up to 1 crore.\nassistant: Understood. We have 3BHK options.\nuser: Yes let's finalise a date to visit the site this weekend.",
        "expected_category": "Hot",
        "expected_score": 92,
    },
    {
        "conversation": "user: I have already spoken to my bank. Loan of 70L is sanctioned. I need a 2BHK urgently.\nassistant: We can arrange a visit.\nuser: Tomorrow works for me. Let's lock it.",
        "expected_category": "Hot",
        "expected_score": 95,
    },
    {
        "conversation": "user: My company is relocating me to Whitefield in 6 weeks. I need a flat immediately.\nassistant: We have ready-to-move units.\nuser: Budget is 85-90L. I'll pay booking amount this week.",
        "expected_category": "Hot",
        "expected_score": 93,
    },
    {
        "conversation": "user: Parents approved. Budget is finalised at 1.05 Cr. Can we visit Saturday?\nassistant: Saturday 11 AM works.\nuser: Confirmed. See you then.",
        "expected_category": "Hot",
        "expected_score": 97,
    },

    # WARM leads — interest shown, some friction or timeline unclear
    {
        "conversation": "user: I am interested in a 2BHK. Budget around 90L.\nassistant: We have great options.\nuser: I need to discuss with my wife first before committing.",
        "expected_category": "Warm",
        "expected_score": 60,
    },
    {
        "conversation": "user: What are the amenities? I am thinking of buying in the next 3-4 months.\nassistant: Clubhouse, pool, gym.\nuser: Okay, sounds good. I'll consider it.",
        "expected_category": "Warm",
        "expected_score": 55,
    },
    {
        "conversation": "user: Budget is 80-100L. I want 2BHK or maybe 3BHK.\nassistant: Both available.\nuser: I'll need a few weeks to decide. Can you send me the brochure?",
        "expected_category": "Warm",
        "expected_score": 50,
    },
    {
        "conversation": "user: I've visited two other projects. This one looks comparable.\nassistant: We offer better pricing per sq ft.\nuser: Let me think and get back to you next week.",
        "expected_category": "Warm",
        "expected_score": 58,
    },
    {
        "conversation": "user: My budget is around 95L but I'm not in a hurry.\nassistant: We have units available.\nuser: Maybe in 6 months. Not sure yet.",
        "expected_category": "Warm",
        "expected_score": 45,
    },

    # COLD leads — just exploring, no timeline, no budget clarity
    {
        "conversation": "user: Just checking out options. No budget decided yet.\nassistant: We have options for all budgets.\nuser: Okay I'll look around.",
        "expected_category": "Cold",
        "expected_score": 10,
    },
    {
        "conversation": "user: What is the price of a 2BHK?\nassistant: Starting from 82 lakhs.\nuser: That's quite high. Thanks.",
        "expected_category": "Cold",
        "expected_score": 8,
    },
    {
        "conversation": "user: Just exploring. My friend bought a flat here.\nassistant: Great! Would you like details?\nuser: No thanks, just browsing.",
        "expected_category": "Cold",
        "expected_score": 5,
    },
    {
        "conversation": "user: Do you have any rental options?\nassistant: We only have purchase options.\nuser: Oh okay, not interested then.",
        "expected_category": "Cold",
        "expected_score": 3,
    },
    {
        "conversation": "user: Can you send me a brochure?\nassistant: Sure, what's your email?\nuser: abc@gmail.com. I'll have a look whenever.",
        "expected_category": "Cold",
        "expected_score": 12,
    },

    # Mixed / edge cases
    {
        "conversation": "user: I am an NRI. Budget is 1.2Cr.\nassistant: We have premium 3BHK.\nuser: I'll decide when I visit India in 8 months.",
        "expected_category": "Warm",
        "expected_score": 40,
    },
    {
        "conversation": "user: I need a 2BHK for investment purpose, not self-use.\nassistant: Rental yield is 3.5%.\nuser: That's decent. I might invest. Timeline is 2-3 months.",
        "expected_category": "Warm",
        "expected_score": 62,
    },
    {
        "conversation": "user: We are a family of 4. Need 3BHK. Budget is tight at 85L.\nassistant: Our 3BHK starts at 1.1Cr.\nuser: That's out of budget. Never mind.",
        "expected_category": "Cold",
        "expected_score": 15,
    },
    {
        "conversation": "user: I want to visit this weekend.\nassistant: Sunday 10 AM works!\nuser: Budget is 88L. I'll bring my father too.",
        "expected_category": "Hot",
        "expected_score": 82,
    },
    {
        "conversation": "user: Loan pre-approval is pending. Budget should be around 90L.\nassistant: We can hold a slot for you.\nuser: Yes please, hold it for next weekend.",
        "expected_category": "Hot",
        "expected_score": 78,
    },
]


def run_eval():
    print("=" * 60)
    print("BANT Qualification Agent — Evaluation Harness")
    print("=" * 60)
    print(f"Running {len(TRANSCRIPTS)} test cases...\n")

    correct_cat = 0
    score_errors = []
    results = []

    for i, tc in enumerate(TRANSCRIPTS, 1):
        try:
            pred = extract_bant_and_score(tc["conversation"])
        except Exception as e:
            pred = {"score": 0, "category": "Cold"}
            print(f"  [EXCEPTION] Case {i}: {e}")

        pred_cat = pred.get("category", "Cold")
        pred_score = pred.get("score", 0)
        exp_cat = tc["expected_category"]
        exp_score = tc["expected_score"]

        cat_ok = pred_cat == exp_cat
        err = abs(pred_score - exp_score)
        if cat_ok:
            correct_cat += 1
        score_errors.append(err)

        status = "✅" if cat_ok else "❌"
        results.append({
            "case": i,
            "status": status,
            "exp_cat": exp_cat,
            "pred_cat": pred_cat,
            "exp_score": exp_score,
            "pred_score": pred_score,
            "score_err": err,
        })
        print(f"  {status} Case {i:02d}: Expected {exp_cat:4s}/{exp_score:3d} | Got {pred_cat:4s}/{pred_score:3d} | Δ={err}")

    accuracy = correct_cat / len(TRANSCRIPTS) * 100
    mae = sum(score_errors) / len(score_errors)

    print("\n" + "=" * 60)
    print(f"  Category Accuracy : {correct_cat}/{len(TRANSCRIPTS)}  ({accuracy:.1f}%)")
    print(f"  Score MAE         : {mae:.1f} points")
    print("=" * 60)

    # Fail if accuracy is below 70%
    if accuracy < 70:
        print("\n⚠️  Accuracy below 70% threshold — review model or prompt.")
        sys.exit(1)
    else:
        print("\n✅ Evaluation passed.")


if __name__ == "__main__":
    run_eval()
