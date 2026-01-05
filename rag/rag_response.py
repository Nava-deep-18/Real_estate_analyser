import json
from pathlib import Path
from typing import List
import pandas as pd

# Path to explanation records (RAG-safe)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPLANATIONS_PATH = PROJECT_ROOT / "backend" / "explanation" / "property_explanations.json"


def build_rag_context(retrieved_df: pd.DataFrame) -> str:
    """
    Build text-only context from explanation records.
    """

    with open(EXPLANATIONS_PATH, "r", encoding="utf-8") as f:
        explanations = json.load(f)

    context_blocks: List[str] = []

    for _, row in retrieved_df.iterrows():
        for record in explanations.values():
            if record["name"] == row["Name"]:
                context_blocks.append(record["explanation"])

    return "\n\n".join(context_blocks)


def generate_rag_response(
    user_query: str,
    intent: str,
    retrieved_df: pd.DataFrame,
) -> str:
    """
    Generate a RAG response using explanation records only.
    """

    if retrieved_df.empty:
        return "The requested property could not be identified clearly. Please specify the property."

    context = build_rag_context(retrieved_df)

    prompt = f"""
You are a real estate investment assistant.

Use ONLY the information provided below.
Do NOT calculate, invent, or modify any numeric values.
Do NOT change any BUY or RENT decision.

PROPERTY INFORMATION:
{context}

USER QUESTION:
{user_query}

Provide a clear and concise explanation.
"""

    # ---- LLM CALL (placeholder) ----
    # Replace this with Gemini / OpenAI API call later
    response_text = "<LLM_RESPONSE_PLACEHOLDER>"

    return response_text
