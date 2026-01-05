import pandas as pd
import json
from pathlib import Path

# ---------- CONFIG ----------
CSV_PATH = Path("../../kolkata_buy_vs_rent_full_analysis.csv")
OUTPUT_PATH = Path("property_explanations.json")


def generate_explanation(row: pd.Series) -> str:
    """
    Generate a deterministic, text-only explanation record
    derived strictly from backend-computed values.
    """

    explanation = (
        f"This is a {int(row['Bedrooms'])} BHK residential property located in "
        f"{row['Address']}, Kolkata. "
        f"The property has an area of {int(row['Area'])} square feet and is "
        f"{row['Furnishing'].lower()}. "
        f"The property price is ₹{row['property_price_lakhs']} lakh. "
        f"The estimated comparable monthly rent for this property is "
        f"₹{int(row['initial_monthly_rent'])}. "
        f"The calculated monthly EMI is ₹{int(row['monthly_emi'])}, and the "
        f"effective monthly ownership cost reflects backend tax considerations. "
        f"Tax benefits have been applied according to the chosen tax regime. "
        f"Over the full analysis period, "
        f"{'buying' if row['decision'] == 'BUY' else 'renting'} results in higher "
        f"final wealth compared to the alternative. "
        f"Final backend decision: {row['decision']}."
    )

    return explanation


def main():
    df = pd.read_csv(CSV_PATH)

    explanations = {}

    for idx, row in df.iterrows():
        explanations[f"property_{idx+1:04d}"] = {
            "name": row["Name"],
            "decision": row["decision"],
            "explanation": generate_explanation(row),
        }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(explanations, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
