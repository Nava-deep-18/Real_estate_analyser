def classify_intent(user_query: str) -> str:
    """
    Classify user intent BEFORE any retrieval or LLM usage.
    This is a mandatory safety gate.
    """

    q = user_query.lower()

    if any(word in q for word in ["compare", "vs", "difference"]):
        return "COMPARE"

    if any(word in q for word in ["why", "explain", "reason"]):
        return "EXPLAIN"

    if any(word in q for word in ["show", "list", "find", "properties"]):
        return "FILTER"

    if any(word in q for word in ["what is", "how does", "explain tax", "tax"]):
        return "EDUCATIONAL"

    # Default fallback (still safe)
    return "EXPLAIN"
