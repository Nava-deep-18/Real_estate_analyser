
import pandas as pd
import os

csv_path = "kolkata_buy_vs_rent_full_analysis.csv"

if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    
    # Calculate Wealth Difference (Compliance Requirement)
    # RAG layer is strictly forbidden from doing this calculation.
    df["wealth_difference"] = df["final_buying_wealth"] - df["final_renting_wealth"]
    
    df.to_csv(csv_path, index=False)
    print(f"✅ patched {csv_path} with 'wealth_difference' column.")
    print(df[["wealth_difference"]].head())
else:
    print(f"❌ File not found: {csv_path}")
