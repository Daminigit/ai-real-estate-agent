import pandas as pd

def load_enquiries(filepath="data/catchment_enquiries.csv"):
    df = pd.read_csv(filepath)
    return df

def get_insights_summary(df: pd.DataFrame) -> str:
    total = len(df)
    if total == 0:
        return "No data available."
        
    def get_percent(series):
        return (series.value_counts() / total * 100).round(1).astype(str) + '%'

    prof_split = get_percent(df['profession']).to_dict()
    config_split = get_percent(df['config_interested']).to_dict()
    source_split = get_percent(df['enquiry_source']).to_dict()
    
    # Check if timeline exists, if not provide a fallback
    timeline_split = get_percent(df['timeline']).to_dict() if 'timeline' in df.columns else "N/A"
    
    budget_mid = (df['budget_min_lakh'] + df['budget_max_lakh']) / 2
    mean_budget = round(budget_mid.mean(), 1)
    median_budget = round(budget_mid.median(), 1)
    
    buckets = pd.cut(budget_mid, bins=[0, 90, 115, float('inf')], labels=['<90L', '90-115L', '115L+'])
    budget_buckets = (buckets.value_counts() / total * 100).round(1).astype(str) + '%'
    
    summary = f"Total Enquiries: {total}\n\n"
    summary += f"--- PROFESSION SPLIT ---\n{prof_split}\n\n"
    summary += f"--- BUDGET DISTRIBUTION ---\nMean Budget: {mean_budget}L\nMedian Budget: {median_budget}L\n"
    summary += f"Buckets (<90L, 90-115L, 115L+): {budget_buckets.to_dict()}\n\n"
    summary += f"--- CONFIGURATION SPLIT ---\n{config_split}\n\n"
    summary += f"--- TIMELINE SPLIT ---\n{timeline_split}\n\n"
    summary += f"--- SOURCE SPLIT ---\n{source_split}\n"
    
    return summary

if __name__ == "__main__":
    df = load_enquiries()
    print("Data Sample:")
    print(df.head())
    print("\n--- Insights Summary ---")
    print(get_insights_summary(df))
