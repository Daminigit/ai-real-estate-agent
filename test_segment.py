import pandas as pd
from segmentation_agent import analyze_and_segment

# Create mock data
data = {
    'name': ['John', 'Alice', 'Bob', 'Eve'],
    'phone': ['123', '456', '789', '012'],
    'source': ['Google', 'Meta', 'Google', 'LinkedIn'],
    'profession': ['IT', 'IT', 'Business', 'NRI'],
    'locality': ['Whitefield', 'Hoodi', 'Sarjapur', 'Whitefield'],
    'budget_min': [80, 75, 120, 150],
    'budget_max': [95, 90, 150, 200],
    'intent_score': [80, 90, 60, 40],
    'category': ['Hot', 'Hot', 'Warm', 'Cold']
}
df = pd.DataFrame(data)

print("Running segmentation...")
try:
    res = analyze_and_segment(df)
    print("Success. Length of response:", len(res))
    print(res[:500])
except Exception as e:
    print("FAILED:", type(e), e)
