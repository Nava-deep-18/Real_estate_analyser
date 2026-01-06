import pandas as pd
from pathlib import Path
import re

# Path to finalized backend analysis CSV
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "kolkata_buy_vs_rent_full_analysis.csv"


def extract_bedrooms(query: str) -> int:
    """
    Extract bedroom count from query using regex.
    """
    # Map common number words to digits
    word_map = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6
    }
    
    q = query.lower()
    
    # 1. Try finding digits (e.g. "2bhk", "2-bed", "2 bedroom")
    # Matches digit followed by optional space/hyphen then keyword
    match_digit = re.search(r"(\d+)\s*-?\s*(?:bhk|bedroom|bed)", q)
    if match_digit:
        return int(match_digit.group(1))
        
    # 2. Try finding words (e.g. "threebhk", "two-bed")
    # Matches word from map followed by optional space/hyphen then keyword
    for word, digit in word_map.items():
        if re.search(rf"{word}\s*-?\s*(?:bhk|bedroom|bed)", q):
            return digit
            
    return 0


def extract_location(query: str, all_locations: list) -> str:
    """
    Identify the most likely location in the query from the known dataset locations.
    Matches longest phrases first (e.g. "New Town Action Area 1" over "New Town").
    """
    q = query.lower()
    # Sort locations by length descending to match specific areas first
    sorted_locs = sorted(all_locations, key=len, reverse=True)
    
    for loc in sorted_locs:
        if isinstance(loc, str) and loc.lower() in q:
            return loc
    return ""


def retrieve_properties(intent: str, user_query: str) -> pd.DataFrame:
    """
    Deterministic property retrieval layer.
    Uses dynamic filtering based on dataset contents.
    """

    df = pd.read_csv(CSV_PATH)
    
    # Pre-processing for robust matching
    # [COMPLIANT] "wealth_difference" MUST exist in backend CSV.
    # We do NOT calculate it here.

    q = user_query.lower()

    # =========================
    # FILTER INTENT & GENERIC SEARCH
    # =========================
    if intent in ["FILTER", "EXPLAIN"]:
        
        filtered_df = df.copy()

        # 1. Dynamic Location Filter
        # Get all unique locations from dataset
        start_count = len(filtered_df)
        unique_locations = filtered_df["Address"].dropna().unique().tolist()
        matched_location = extract_location(user_query, unique_locations)
        
        if matched_location:
            # Filter strictly by the matched location substring
            filtered_df = filtered_df[filtered_df["Address"].str.contains(matched_location, case=False, na=False)]

        # 2. Dynamic Bedroom Filter
        beds = extract_bedrooms(user_query)
        if beds > 0:
            filtered_df = filtered_df[filtered_df["Bedrooms"] == beds]

        # 3. Handle specifics for EXPLAIN
        if intent == "EXPLAIN":
            # If user asks for a specific property name
            for name in filtered_df["Name"].dropna().unique():
                 if name.lower() in q:
                     return filtered_df[filtered_df["Name"] == name].head(1)
            
            # If no name match, but we have filtered down, return top result
            if len(filtered_df) < start_count:
                 return filtered_df.head(1)
            
            return pd.DataFrame() # No specific property found

        # 4. Return results for FILTER
        return filtered_df.head(5)


    # =========================
    # COMPARE INTENT
    # =========================
    if intent == "COMPARE":
        # Sort by wealth difference (pre-calculated or derived)
        # We sort by absolute magnitude of impact or just benefit of buying
        df = df.sort_values("wealth_difference", ascending=False)
        return df.head(2)

    # =========================
    # EDUCATIONAL INTENT
    # =========================
    # Return a representative property to provide grounded context for general questions
    return df.head(1)
