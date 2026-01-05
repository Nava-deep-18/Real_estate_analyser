import pandas as pd
from pathlib import Path

# Path to finalized backend analysis CSV
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "kolkata_buy_vs_rent_full_analysis.csv"



def retrieve_properties(intent: str, user_query: str) -> pd.DataFrame:
    """
    Deterministic property retrieval layer.
    This function MUST NOT use LLMs or perform explanations.
    """

    df = pd.read_csv(CSV_PATH)
    q = user_query.lower()

    # =========================
    # FILTER INTENT
    # =========================
    # User wants a subset of properties
    if intent == "FILTER":

        # Bedrooms filter
        if "1 bhk" in q:
            df = df[df["Bedrooms"] == 1]
        elif "2 bhk" in q:
            df = df[df["Bedrooms"] == 2]
        elif "3 bhk" in q:
            df = df[df["Bedrooms"] == 3]
        elif "4 bhk" in q:
            df = df[df["Bedrooms"] == 4]

        # Location filter
        if "new town" in q:
            df = df[df["Address"].str.contains("new town", case=False, na=False)]
        elif "rajarhat" in q:
            df = df[df["Address"].str.contains("rajarhat", case=False, na=False)]
        elif "sonarpur" in q:
            df = df[df["Address"].str.contains("sonarpur", case=False, na=False)]

        # Deterministic limit
        return df.head(5)

    # =========================
    # EXPLAIN INTENT
    # =========================
    # User wants explanation of ONE specific property
    if intent == "EXPLAIN":

        # Property must be explicitly identifiable
        for _, row in df.iterrows():
            property_name = row["Name"].lower()
            if property_name in q:
                return df[df["Name"] == row["Name"]]

        # Safe failure if property not identified
        return pd.DataFrame()

    # =========================
    # COMPARE INTENT
    # =========================
    # User wants comparison of multiple properties
    if intent == "COMPARE":

        # Compute wealth difference deterministically (backend data only)
        df = df.copy()
        df["wealth_difference"] = (
            df["final_buying_wealth"] - df["final_renting_wealth"]
        )

        # Sort deterministically
        df = df.sort_values("wealth_difference", ascending=False)

        # Return top 2 for comparison
        return df.head(2)

    # =========================
    # EDUCATIONAL INTENT
    # =========================
    # No property retrieval required
    return pd.DataFrame()
